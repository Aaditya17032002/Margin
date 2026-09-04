"""Documents router — upload the solicitation an analysis is about."""

from __future__ import annotations

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
from app.core.documents import ALLOWED_KINDS, store_document, to_response as _to_response

router = APIRouter(tags=["documents"])
logger = get_logger()

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

    document = await store_document(
        db,
        analysis,
        content=content,
        filename=Path(file.filename or "document").name,
        kind=kind,
        content_type=file.content_type,
    )
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


