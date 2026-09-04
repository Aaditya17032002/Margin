"""The drop box: a way in for anything that can POST a file.

Not every source is worth building a connector for. A mail rule, a Power
Automate flow, a SharePoint "when a file is created" trigger, a scanner, a
partner's script — all of them can already send an HTTP request, and all of
them want the same thing: hand Margin a document and have it read.

So each workspace gets one address. Anything posted to it becomes an analysis
and starts reading immediately. The address is the credential, which is why it
is long, opaque, per-workspace, and shown only to someone already signed in.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.documents import store_document
from app.core.logging import get_logger
from app.core.queue import enqueue
from app.db.models.analysis import Analysis
from app.db.models.org import Org

router = APIRouter(tags=["ingest"])
logger = get_logger()

VALID_MODES = {"quick-triage", "standard", "deep-research", "matrix-only", "qa-only"}


def ingest_token(org_id: str) -> str:
    """A stable, unguessable address for a workspace.

    Derived rather than stored so there is no new table and no secret sitting
    in a column: it is an HMAC of the workspace id under the app secret, which
    means rotating ``SECRET_KEY`` revokes every address at once — the property
    you want from something that grants write access with no other credential.
    """
    digest = hmac.new(
        get_settings().SECRET_KEY.encode(), f"ingest:{org_id}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{org_id}.{digest[:40]}"


def _org_for(token: str) -> str | None:
    org_id, _, _ = token.partition(".")
    if not org_id:
        return None
    # Constant-time: a timing difference here would let someone walk the digest.
    return org_id if secrets.compare_digest(token, ingest_token(org_id)) else None


@router.get("/ingest/address")
async def show_address(request: Request, user: CurrentUser):
    """The address for this workspace, for someone setting up a flow."""
    base = str(request.base_url).rstrip("/")
    return {
        "url": f"{base}/api/v1/ingest/{ingest_token(user.org_id)}",
        "method": "POST",
        "field": "file",
        "note": (
            "Post a multipart form with the document in `file`. Optional fields: "
            "`title`, `agency`, `mode`. Anyone holding this URL can start an "
            "analysis in this workspace — treat it as a credential."
        ),
    }


@router.post("/ingest/{token}", status_code=status.HTTP_202_ACCEPTED)
async def ingest(
    token: str,
    db: DbSession,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    agency: str | None = Form(None),
    mode: str = Form("standard"),
):
    """Accept a document and start reading it. Deliberately unauthenticated
    beyond the address itself — the callers are flows and scripts that cannot
    hold a user session."""
    org_id = _org_for(token)
    if not org_id:
        # Same answer for a malformed token and a wrong one.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown ingest address")

    org = (await db.execute(select(Org).where(Org.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown ingest address")

    settings = get_settings()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file is empty.")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"That file is larger than the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
        )

    filename = Path(file.filename or "document").name
    analysis = Analysis(
        id=f"an_{uuid.uuid4().hex[:12]}",
        org_id=org_id,
        title=(title or filename.rsplit(".", 1)[0])[:500],
        agency=(agency or "Not yet determined")[:255],
        mode=mode if mode in VALID_MODES else "standard",
        stage="triage",
        owner="Margin ingest",
        source="upload",
        file_name=filename,
    )
    db.add(analysis)
    await db.flush()

    await store_document(
        db, analysis, content=content, filename=filename, kind="base", content_type=file.content_type
    )

    job = await enqueue("app.workers.run_analysis.run_analysis_task", analysis.id)
    if job is None:
        # The document is safely stored; the read can be started by hand.
        logger.error("ingest_queue_unavailable", analysis_id=analysis.id)

    logger.info("ingest_accepted", org_id=org_id, analysis_id=analysis.id, queued=job is not None)
    return {"analysisId": analysis.id, "queued": job is not None, "fileName": filename}
