"""Reports router — generate DOCX, download, list."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core import permissions
from app.core.deps import CurrentUser, DbSession, RedisClient
from app.core.queue import enqueue
from app.db.models.analysis import Analysis
from app.db.models.report import Report
from app.schemas.resources import ReportGenerateRequest, ReportResponse

router = APIRouter(tags=["reports"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "md": "text/markdown; charset=utf-8",
}


def _to_response(r: Report) -> dict:
    return {
        "id": r.id,
        "at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
        "analysisId": r.analysis_id,
        "analysisTitle": r.analysis_title,
        "templateName": r.template_name,
        "format": r.format,
        "size": r.size or 0,
        "destination": r.destination,
        "status": r.status,
    }


@router.post("/analyses/{analysis_id}/report", status_code=status.HTTP_201_CREATED)
async def generate_report(
    analysis_id: str,
    body: ReportGenerateRequest,
    user: CurrentUser,
    db: DbSession,
    redis: RedisClient,
):
    # A report leaves the product. Whoever can generate one can hand the
    # package's contents to anybody, which is a different authority from being
    # able to read it here.
    permissions.require(user.role, "export")
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Idempotency check
    if body.idempotency_key:
        existing = await redis.get(f"report_idem:{body.idempotency_key}")
        if existing:
            return {"id": existing, "status": "already_enqueued"}

    report = Report(
        id=f"x_{uuid.uuid4().hex[:8]}",
        org_id=user.org_id,
        analysis_id=analysis_id,
        analysis_title=analysis.title,
        template_name=body.template_name,
        format=body.format,
        destination=body.destination,
        status="generating",
    )
    db.add(report)
    await db.flush()

    # A report that was never queued must not be handed back as `generating` —
    # it would sit in the export list forever with nothing rendering it.
    job = await enqueue("app.workers.generate_report.generate_report_task", report.id)
    if job is None:
        report.status = "failed"
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The export queue is unavailable. The report was not started.",
        )
    await redis.set(f"report_job:{report.id}", analysis_id, ex=3600)
    if body.idempotency_key:
        await redis.set(f"report_idem:{body.idempotency_key}", report.id, ex=3600)

    return _to_response(report)


@router.get("/reports/{report_id}")
async def download_report(report_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.org_id == user.org_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That report failed to render. Generate it again.",
        )
    if report.status != "ready" or not report.storage_path:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Report still generating")
    if not os.path.exists(report.storage_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The rendered file is no longer on disk. Generate the report again.",
        )

    # The extension and type come from the file that was actually rendered.
    # Serving a Markdown report as a .docx made the browser hand it to Word,
    # which then refused to open it.
    suffix = os.path.splitext(report.storage_path)[1].lstrip(".").lower() or "docx"
    return FileResponse(
        report.storage_path,
        media_type=MEDIA_TYPES.get(suffix, "application/octet-stream"),
        filename=f"{report.analysis_title} - {report.template_name}.{suffix}",
    )


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Report)
        .where(Report.org_id == user.org_id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )
    return [_to_response(r) for r in result.scalars().all()]
