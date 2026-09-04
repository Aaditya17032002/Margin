"""The bound draft response, and the trace of it against the solicitation.

A response is never a loose document dropped into a general-purpose checker. It
is uploaded *to an analysis Margin has already read*, versioned separately from
the solicitation package, and compared requirement by requirement against that
solicitation's Requirement Ledger. The binding is deliberate, because a gap
report against the wrong solicitation is worse than no gap report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.documents import store_document, to_response as _document_response
from app.core.logging import get_logger
from app.core.queue import enqueue
from app.db.models.analysis import Analysis
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.schemas.resources import ResponseCheckResponse, ResponseCheckUpdate

router = APIRouter(tags=["response"])
logger = get_logger()


def _to_response(row: ResponseCheck, requirement: Requirement | None) -> dict:
    return {
        "id": row.id,
        "analysisId": row.analysis_id,
        "requirementId": row.requirement_id,
        "responseVersion": row.response_version,
        # The solicitation half of the trace.
        "reference": requirement.reference if requirement else "",
        "requirement": requirement.text if requirement else "",
        "stakes": requirement.stakes if requirement else "scored",
        "citation": (requirement.citation if requirement else {}) or {},
        # The response half.
        "status": row.status,
        "verification": row.verification,
        "decidedBy": row.decided_by,
        "rule": row.rule,
        "detail": row.detail,
        "gap": row.gap,
        "risk": row.risk,
        "owner": row.owner,
        "evidence": row.evidence or {},
        "needsConfirmation": row.needs_confirmation,
        "confirmedBy": row.confirmed_by,
        "confirmedAt": row.confirmed_at.isoformat() if row.confirmed_at else None,
        "note": row.note,
        "history": row.history or [],
    }


async def _analysis(db, analysis_id: str, org_id: str) -> Analysis:
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.org_id == org_id, Analysis.deleted_at.is_(None)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.post("/analyses/{analysis_id}/response", status_code=status.HTTP_201_CREATED)
async def bind_response(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    label: str = Form(""),
):
    """Bind a draft response to this solicitation and check it.

    Refused before the solicitation has been read: without a Requirement Ledger
    there is nothing to trace against, and a gap report built on no
    requirements would show a clean sheet — the most dangerous possible
    output.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)

    requirements = (
        await db.execute(
            select(Requirement).where(
                Requirement.analysis_id == analysis_id, Requirement.state == "open"
            )
        )
    ).scalars().first()
    if requirements is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This solicitation has not been read yet, so there are no requirements to "
                "check the response against. Run the analysis first."
            ),
        )

    settings = get_settings()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file is empty.")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"That file is larger than the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
        )

    # Each draft is its own version — `store_document` numbers documents within
    # their kind — so an earlier check stays answerable. "Was this gap there
    # last week?" is the question every revision raises.
    document = await store_document(
        db,
        analysis,
        content=content,
        filename=Path(file.filename or "response").name,
        kind="response",
        content_type=file.content_type,
    )
    version = document.version
    analysis.response = {
        "documentId": document.id,
        "fileName": document.file_name,
        "label": label or f"Draft {version}",
        "version": version,
        "boundAt": datetime.now(UTC).isoformat(),
        "at": None,
        "summary": {},
    }
    analysis.updated_at = datetime.now(UTC)
    await db.flush()

    job_id = await enqueue("app.workers.check_response.check_response_task", analysis_id)
    logger.info("response_bound", analysis_id=analysis_id, version=version, job=job_id)
    return {"document": _document_response(document), "version": version, "jobId": job_id}


@router.post("/analyses/{analysis_id}/response/recheck")
async def recheck_response(analysis_id: str, user: CurrentUser, db: DbSession):
    """Re-run the trace — after an amendment, or after the ledger changed."""
    analysis = await _analysis(db, analysis_id, user.org_id)
    if not (analysis.response or {}).get("documentId"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No response is bound to this analysis."
        )
    job_id = await enqueue("app.workers.check_response.check_response_task", analysis_id)
    return {"jobId": job_id, "status": "enqueued"}


@router.get("/analyses/{analysis_id}/response/checks", response_model=list[ResponseCheckResponse])
async def list_checks(analysis_id: str, user: CurrentUser, db: DbSession, version: int | None = None):
    analysis = await _analysis(db, analysis_id, user.org_id)
    wanted = version or int((analysis.response or {}).get("version") or 1)

    rows = (
        await db.execute(
            select(ResponseCheck).where(
                ResponseCheck.analysis_id == analysis_id,
                ResponseCheck.org_id == user.org_id,
                ResponseCheck.response_version == wanted,
            )
        )
    ).scalars().all()
    requirements = {
        row.id: row
        for row in (
            await db.execute(
                select(Requirement).where(Requirement.analysis_id == analysis_id)
            )
        )
        .scalars()
        .all()
    }
    traced = [_to_response(row, requirements.get(row.requirement_id)) for row in rows]
    # Highest risk first: the point of the view is what could lose the bid.
    order = {"high": 0, "medium": 1, "low": 2}
    traced.sort(key=lambda t: (order.get(t["risk"], 3), t["reference"]))
    return traced


@router.patch("/analyses/{analysis_id}/response/checks/{check_id}")
async def decide_check(
    analysis_id: str, check_id: str, body: ResponseCheckUpdate, user: CurrentUser, db: DbSession
):
    """A person's verdict, which outranks both the rule and the model.

    Confirming a mandatory requirement is the only way one gets cleared — the
    engine deliberately cannot do it. Overruling is recorded the same way, so
    the trace shows a decision rather than an unexplained change.
    """
    await _analysis(db, analysis_id, user.org_id)
    row = (
        await db.execute(
            select(ResponseCheck).where(
                ResponseCheck.id == check_id,
                ResponseCheck.analysis_id == analysis_id,
                ResponseCheck.org_id == user.org_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")

    now = datetime.now(UTC)
    update = body.model_dump(exclude_unset=True, by_alias=False)
    previous = row.status

    if "status" in update and update["status"] is not None:
        row.status = update["status"].value if hasattr(update["status"], "value") else update["status"]
        row.decided_by = "human"
    if "note" in update:
        row.note = update["note"]

    if update.get("confirmed"):
        row.confirmed_by = user.id
        row.confirmed_at = now
        row.needs_confirmation = False
        row.decided_by = "human"
    elif update.get("confirmed") is False:
        row.confirmed_by = None
        row.confirmed_at = None
        row.needs_confirmation = row.status == "satisfied" and row.risk != "low"

    detail = f"{previous} → {row.status}" if previous != row.status else f"confirmed as {row.status}"
    if row.note:
        detail = f"{detail}: {row.note}"
    row.history = [*(row.history or []), {"at": now.isoformat(), "event": "decided", "detail": detail}]
    await db.flush()

    requirement = (
        await db.execute(select(Requirement).where(Requirement.id == row.requirement_id))
    ).scalar_one_or_none()
    return _to_response(row, requirement)
