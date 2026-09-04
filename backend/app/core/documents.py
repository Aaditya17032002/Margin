"""Attaching a document to an analysis, wherever the bytes came from.

An upload from a browser, a file picked out of SharePoint, and an attachment
lifted off an Outlook thread all have to end in the same place: extracted text
with its page breaks intact, stored with the row, so a run never depends on the
container that received the bytes still holding them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.pipeline.extract import PAGE_SEP, extract_text

logger = get_logger()

#: What the generic uploader accepts. `response` is deliberately absent: a
#: draft response is bound to a solicitation through its own endpoint, which
#: refuses the binding until the solicitation has actually been read. Letting
#: one in here would produce a gap report with nothing to compare against.
ALLOWED_KINDS = {"base", "attachment", "amendment"}


async def store_document(
    db: AsyncSession,
    analysis: Analysis,
    *,
    content: bytes,
    filename: str,
    kind: str = "base",
    content_type: str | None = None,
    source: str = "upload",
) -> Document:
    """Extract, persist, and attach. The caller has already authorised the org."""
    filename = Path(filename or "document").name
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    raw_text = extract_text(content, filename)

    storage_path: str | None = None
    settings = get_settings()
    try:
        directory = Path(settings.UPLOADS_DIR) / analysis.org_id / analysis.id
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{doc_id}{Path(filename).suffix}"
        target.write_bytes(content)
        storage_path = str(target)
    except OSError as exc:
        # The extracted text is what a run actually needs, so a read-only or
        # full volume degrades the upload rather than failing it.
        logger.warning("upload_store_failed", error=str(exc), analysis_id=analysis.id)

    existing = await db.execute(
        select(Document).where(Document.analysis_id == analysis.id, Document.doc_kind == kind)
    )
    version = len(existing.scalars().all()) + 1

    document = Document(
        id=doc_id,
        analysis_id=analysis.id,
        org_id=analysis.org_id,
        file_name=filename,
        file_size=len(content),
        content_type=content_type or "application/octet-stream",
        storage_path=storage_path,
        doc_kind=kind,
        version=version,
        page_count=(raw_text.count(PAGE_SEP) + 1) if raw_text else 0,
        raw_text=raw_text or None,
    )
    db.add(document)

    if kind == "base":
        analysis.file_name = filename
        analysis.file_size = len(content)
        analysis.source = source if source in {"upload", "outlook", "sharepoint", "onedrive"} else "upload"
        analysis.updated_at = datetime.now(UTC)

    await db.flush()
    logger.info(
        "document_stored",
        analysis_id=analysis.id,
        doc_id=doc_id,
        pages=document.page_count,
        chars=len(raw_text),
        source=source,
    )
    return document


def to_response(d: Document) -> dict:
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
