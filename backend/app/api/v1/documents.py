"""Documents router — upload the solicitation an analysis is about."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DbSession
from app.core.security import AuthUser
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.pipeline.extract import extract_text

router = APIRouter(tags=["documents"])
logger = get_logger()

ALLOWED_KINDS = {"base", "attachment", "amendment"}


def _to_response(d: Document) -> dict:
    return {
        "id": d.id,
        "analysisId": d.analysis_id,
        "fileName": d.file_name,
        "fileSize": d.file_size or 0,
        "contentType": d.content_type or "",
        "kind": d.doc_kind,
        "version": d.version,
        "pageCount": d.page_count or 0,
        "hasText": bool(d.raw_text),
        "at": d.created_at.isoformat() if isinstance(d.created_at, datetime) else str(d.created_at),
    }


async def _load_analysis(analysis_id: str, user: AuthUser, db: AsyncSession) -> Analysis:
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.org_id == user.org_id,
            Analysis.deleted_at.is_(None),
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.post("/analyses/{analysis_id}/document", status_code=status.HTTP_201_CREATED)
async def upload_document(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    kind: str = Form("base"),
):
    """Attach a document to an analysis. The extracted text is stored with the
    row so a run never depends on the container that received the upload still
    holding the file."""
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown document kind: {kind}")

    analysis = await _load_analysis(analysis_id, user, db)

    settings = get_settings()
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"That file is larger than the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file is empty.")

    filename = Path(file.filename or "document").name
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    raw_text = extract_text(content, filename)

    storage_path: str | None = None
    try:
        directory = Path(settings.UPLOADS_DIR) / user.org_id / analysis_id
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{doc_id}{Path(filename).suffix}"
        target.write_bytes(content)
        storage_path = str(target)
    except OSError as exc:
        # The extracted text is what a run actually needs, so a read-only or
        # full volume degrades the upload rather than failing it.
        logger.warning("upload_store_failed", error=str(exc), analysis_id=analysis_id)

    existing = await db.execute(
        select(Document).where(Document.analysis_id == analysis_id, Document.doc_kind == kind)
    )
    version = len(existing.scalars().all()) + 1

    document = Document(
        id=doc_id,
        analysis_id=analysis_id,
        org_id=user.org_id,
        file_name=filename,
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        doc_kind=kind,
        version=version,
        page_count=max(1, raw_text.count("\f") + 1) if raw_text else 0,
        raw_text=raw_text or None,
    )
    db.add(document)

    if kind == "base":
        analysis.file_name = filename
        analysis.file_size = len(content)
        analysis.updated_at = datetime.now(UTC)

    await db.flush()
    logger.info("document_uploaded", analysis_id=analysis_id, doc_id=doc_id, chars=len(raw_text))
    return _to_response(document)


@router.get("/analyses/{analysis_id}/documents")
async def list_documents(analysis_id: str, user: CurrentUser, db: DbSession):
    await _load_analysis(analysis_id, user, db)
    result = await db.execute(
        select(Document)
        .where(Document.analysis_id == analysis_id)
        .order_by(Document.created_at.asc())
    )
    return [_to_response(d) for d in result.scalars().all()]
