"""Analyses router — CRUD, run, decide, duplicate, SSE events."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator

import orjson
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy import select, update
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUser, DbSession, RedisClient
from app.core.queue import enqueue
from app.core.security import RequireRole
from app.db.models.analysis import Analysis
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisListItem,
    AnalysisResponse,
    AnalysisUpdate,
    DecideRequest,
    RunRequest,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _to_response(a: Analysis, *, with_pages: bool = True) -> dict:
    """Convert an Analysis ORM object to the frontend-compatible dict."""
    return {
        "id": a.id,
        "title": a.title,
        "solicitationNumber": a.solicitation_number,
        "agency": a.agency,
        "subAgency": a.sub_agency,
        "docType": a.doc_type,
        "mode": a.mode,
        "stage": a.stage,
        "goNoGo": a.go_no_go,
        "decisionNote": a.decision_note,
        "createdAt": a.created_at.isoformat() if isinstance(a.created_at, datetime) else str(a.created_at),
        "updatedAt": a.updated_at.isoformat() if isinstance(a.updated_at, datetime) else str(a.updated_at),
        "owner": a.owner,
        "collaborators": a.collaborators or [],
        "naics": a.naics or "Not yet determined",
        "setAside": a.set_aside or "Not yet determined",
        "placeOfPerformance": a.place_of_performance or "Not yet determined",
        "estimatedValue": a.estimated_value or 0,
        "pageCount": a.page_count or 0,
        "fileName": a.file_name or "",
        "fileSize": a.file_size or 0,
        "source": a.source,
        "tags": a.tags or [],
        "summary": a.summary or "",
        "identity": a.identity or [],
        "scope": a.scope or [],
        "legal": a.legal or [],
        "eligibility": a.eligibility or [],
        "pricing": a.pricing or [],
        "postAward": a.post_award or [],
        "gates": a.gates or [],
        "evaluation": a.evaluation or [],
        "risks": a.risks or [],
        "silent": a.silent or [],
        "dates": a.dates or [],
        "clins": a.clins or [],
        "amendments": a.amendments or [],
        "pages": (a.pages or []) if with_pages else [],
        "versions": a.versions or [],
        "coverage": a.coverage or {},
        "ledger": a.ledger or {},
        "response": a.response or {},
        "research": a.research or {},
    }


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    user: CurrentUser,
    db: DbSession,
    stage: str | None = None,
    go_no_go: str | None = Query(None, alias="goNoGo"),
    tag: str | None = None,
):
    stmt = select(Analysis).where(Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    if stage:
        stmt = stmt.where(Analysis.stage == stage)
    if go_no_go:
        stmt = stmt.where(Analysis.go_no_go == go_no_go)
    stmt = stmt.order_by(Analysis.updated_at.desc())

    result = await db.execute(stmt)
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        d = _to_response(a, with_pages=False)
        if tag and tag not in d.get("tags", []):
            continue
        items.append(d)
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_analysis(body: AnalysisCreate, user: CurrentUser, db: DbSession):
    analysis = Analysis(
        id=f"an_{uuid.uuid4().hex[:12]}",
        title=body.title,
        solicitation_number=body.solicitation_number or "Pending assignment",
        agency=body.agency,
        doc_type=body.doc_type.value if body.doc_type else "RFP",
        mode=body.mode.value,
        stage="triage",
        go_no_go="undecided",
        owner=body.owner,
        org_id=user.org_id,
        file_name=body.file_name,
        file_size=body.file_size,
        source=body.source,
        tags=[body.mode.value.replace("-", " ").title()],
    )
    db.add(analysis)
    await db.flush()
    return _to_response(analysis)


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return _to_response(analysis)


@router.patch("/{analysis_id}")
async def update_analysis(analysis_id: str, body: AnalysisUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    update_data = body.model_dump(exclude_unset=True, by_alias=False)
    # Map camelCase schema fields to snake_case model columns
    field_map = {
        "solicitation_number": "solicitation_number",
        "sub_agency": "sub_agency",
        "doc_type": "doc_type",
        "go_no_go": "go_no_go",
        "decision_note": "decision_note",
        "set_aside": "set_aside",
        "place_of_performance": "place_of_performance",
        "estimated_value": "estimated_value",
    }
    for key, value in update_data.items():
        col = field_map.get(key, key)
        if hasattr(analysis, col):
            setattr(analysis, col, value.value if hasattr(value, "value") else value)

    analysis.updated_at = datetime.now(UTC)
    await db.flush()
    return _to_response(analysis)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis.deleted_at = datetime.now(UTC)
    await db.flush()


@router.post("/{analysis_id}/restore")
async def restore_analysis(analysis_id: str, user: CurrentUser, db: DbSession):
    """Undo a delete. Deletes are soft, so this is the same row coming back with
    the id every citation and matrix row still points at."""
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis.deleted_at = None
    analysis.updated_at = datetime.now(UTC)
    await db.flush()
    return _to_response(analysis)


@router.post("/{analysis_id}/run")
async def run_analysis(analysis_id: str, body: RunRequest, user: CurrentUser, db: DbSession, redis: RedisClient):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Idempotency check
    if body.idempotency_key:
        existing = await redis.get(f"run_idem:{body.idempotency_key}")
        if existing:
            return {"jobId": existing, "status": "already_enqueued"}

    job_id = await enqueue("app.workers.run_analysis.run_analysis_task", analysis_id)
    if job_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The analysis queue is unavailable. Try again once the worker is running.",
        )

    analysis.stage = "analyzing"
    analysis.updated_at = datetime.now(UTC)
    await db.flush()

    await redis.set(f"run_job:{job_id}", analysis_id, ex=3600)
    if body.idempotency_key:
        await redis.set(f"run_idem:{body.idempotency_key}", job_id, ex=3600)

    await redis.publish(
        f"analysis:{analysis_id}:events",
        orjson.dumps({"event": "run_enqueued", "agent": "orchestrator", "jobId": job_id}).decode(),
    )

    return {"jobId": job_id, "status": "enqueued"}


@router.post("/{analysis_id}/decide")
async def decide(analysis_id: str, body: DecideRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    analysis.go_no_go = body.decision.value
    analysis.decision_note = body.note
    analysis.stage = "decided" if body.decision.value != "undecided" else "review"
    analysis.updated_at = datetime.now(UTC)
    await db.flush()
    return _to_response(analysis)


@router.post("/{analysis_id}/duplicate")
async def duplicate_analysis(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    new_id = f"an_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    copy = Analysis(
        id=new_id,
        title=f"{source.title} (copy)",
        solicitation_number=source.solicitation_number,
        agency=source.agency,
        sub_agency=source.sub_agency,
        doc_type=source.doc_type,
        mode=source.mode,
        stage="triage",
        go_no_go="undecided",
        owner=source.owner,
        org_id=source.org_id,
        naics=source.naics,
        set_aside=source.set_aside,
        place_of_performance=source.place_of_performance,
        estimated_value=source.estimated_value,
        page_count=source.page_count,
        file_name=source.file_name,
        file_size=source.file_size,
        source=source.source,
        tags=list(source.tags or []),
        summary=source.summary,
        identity=list(source.identity or []),
        scope=list(source.scope or []),
        legal=list(source.legal or []),
        eligibility=list(source.eligibility or []),
        pricing=list(source.pricing or []),
        post_award=list(source.post_award or []),
        gates=list(source.gates or []),
        evaluation=list(source.evaluation or []),
        risks=list(source.risks or []),
        silent=list(source.silent or []),
        dates=list(source.dates or []),
        clins=list(source.clins or []),
        amendments=list(source.amendments or []),
        pages=list(source.pages or []),
        versions=[],
        # A duplicate has not been read yet, so it has done no research either.
        research={},
    )
    db.add(copy)
    await db.flush()
    return _to_response(copy)


@router.get("/{analysis_id}/events")
async def analysis_events(analysis_id: str, user: CurrentUser, redis: RedisClient):
    """SSE stream — relays Redis pub/sub events for the analysis."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"analysis:{analysis_id}:events")
        # Redis pub/sub has no replay, so a client that asks for a run before
        # this subscription exists never hears the agents work. This frame is
        # the handshake it waits on — response headers are sent earlier than
        # the subscribe above completes, so they cannot serve as the signal.
        yield {"event": "message", "data": orjson.dumps({"event": "stream_ready"}).decode()}
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    yield {"event": "message", "data": message["data"]}
                else:
                    # Keep-alive
                    yield {"event": "ping", "data": ""}
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"analysis:{analysis_id}:events")
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
