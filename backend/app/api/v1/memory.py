"""Institutional memory: past performance, and the text that answered before.

Both endpoints are requirement-aware. A library you have to search by keyword
is a library nobody opens at 2am; the useful question is "what do we have for
*this clause*", and that is the only question these answer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.memory import ContentBlock, PastPerformance
from app.db.models.requirement import Requirement
from app.pipeline import memory
from app.schemas.resources import (
    ContentBlockCreate,
    ContentBlockUpdate,
    PastPerformanceCreate,
    PastPerformanceUpdate,
)

router = APIRouter(tags=["memory"])
logger = get_logger()


def _performance(row: PastPerformance) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "customer": row.customer,
        "agency": row.agency,
        "contractNumber": row.contract_number,
        "scope": row.scope,
        "value": row.value,
        "startedAt": row.started_at.isoformat() if row.started_at else None,
        "endedAt": row.ended_at.isoformat() if row.ended_at else None,
        "ongoing": row.ongoing,
        "naics": row.naics,
        "capabilities": list(row.capabilities or []),
        "placeOfPerformance": row.place_of_performance,
        "reference": {
            "name": row.reference_name,
            "title": row.reference_title,
            "email": row.reference_email,
            "phone": row.reference_phone,
            "checkedAt": row.reference_checked_at.isoformat() if row.reference_checked_at else None,
        },
        "rating": row.rating,
        "notes": row.notes,
    }


def _block(row: ContentBlock) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "text": row.text,
        "requirementKind": row.requirement_kind,
        "tags": list(row.tags or []),
        "source": {
            "analysisId": row.source_analysis_id,
            "solicitation": row.source_solicitation,
            "agency": row.source_agency,
            "reference": row.source_reference,
            "requirement": row.source_requirement,
        },
        "outcome": row.outcome,
        "lastVerdict": row.last_verdict,
        "verifiedBy": row.verified_by,
        "verifiedAt": row.verified_at.isoformat() if row.verified_at else None,
        "timesUsed": row.times_used,
        "lastUsedAt": row.last_used_at.isoformat() if row.last_used_at else None,
        "retiredAt": row.retired_at.isoformat() if row.retired_at else None,
        "retiredReason": row.retired_reason,
    }


# ── Past performance ─────────────────────────────────────────────────────


@router.get("/past-performance")
async def list_performance(user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(PastPerformance)
            .where(PastPerformance.org_id == user.org_id)
            .order_by(PastPerformance.ongoing.desc(), PastPerformance.ended_at.desc().nullslast())
        )
    ).scalars().all()
    return [_performance(row) for row in rows]


@router.post("/past-performance", status_code=status.HTTP_201_CREATED)
async def create_performance(body: PastPerformanceCreate, user: CurrentUser, db: DbSession):
    row = PastPerformance(
        id=f"pp_{uuid.uuid4().hex[:12]}",
        org_id=user.org_id,
        **body.to_columns(),
    )
    db.add(row)
    await db.flush()
    return _performance(row)


@router.patch("/past-performance/{record_id}")
async def update_performance(
    record_id: str, body: PastPerformanceUpdate, user: CurrentUser, db: DbSession
):
    row = (
        await db.execute(
            select(PastPerformance).where(
                PastPerformance.id == record_id, PastPerformance.org_id == user.org_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    for field, value in body.to_columns(partial=True).items():
        setattr(row, field, value)
    await db.flush()
    return _performance(row)


@router.get("/analyses/{analysis_id}/requirements/{requirement_id}/past-performance")
async def match_performance(
    analysis_id: str, requirement_id: str, user: CurrentUser, db: DbSession
):
    """Which of our contracts is relevant to this requirement, and why.

    Every signal is reported separately. "This one matches" is an assertion;
    "same agency, same NAICS, ended eight months ago" is a case somebody can
    make in a proposal.
    """
    analysis, requirement = await _pair(db, analysis_id, requirement_id, user.org_id)
    records = (
        await db.execute(select(PastPerformance).where(PastPerformance.org_id == user.org_id))
    ).scalars().all()

    matches = memory.match_past_performance(
        list(records),
        requirement_text=requirement.text,
        agency=analysis.agency or "",
        naics=analysis.naics or "",
        value=float(analysis.estimated_value or 0),
    )
    by_id = {row.id: row for row in records}
    return [
        {**item.as_dict(), "record": _performance(by_id[item.record_id])}
        for item in matches
        if item.record_id in by_id
    ]


# ── Content blocks ───────────────────────────────────────────────────────


@router.get("/content-blocks")
async def list_blocks(
    user: CurrentUser,
    db: DbSession,
    include_retired: bool = Query(False, alias="includeRetired"),
):
    query = select(ContentBlock).where(ContentBlock.org_id == user.org_id)
    if not include_retired:
        query = query.where(ContentBlock.retired_at.is_(None))
    rows = (await db.execute(query.order_by(ContentBlock.times_used.desc()))).scalars().all()
    return [_block(row) for row in rows]


@router.post("/content-blocks", status_code=status.HTTP_201_CREATED)
async def create_block(body: ContentBlockCreate, user: CurrentUser, db: DbSession):
    now = datetime.now(UTC)
    row = ContentBlock(
        id=f"cb_{uuid.uuid4().hex[:12]}",
        org_id=user.org_id,
        history=[{"at": now.isoformat(), "event": "added", "detail": f"Added by {user.id}."}],
        **body.to_columns(),
    )
    db.add(row)
    await db.flush()
    return _block(row)


@router.patch("/content-blocks/{block_id}")
async def update_block(block_id: str, body: ContentBlockUpdate, user: CurrentUser, db: DbSession):
    """Edit, record a use, or retire a block.

    Retiring needs a reason, and never deletes: a proposal that used the block
    still has to be explainable, and "we removed it" is not an explanation.
    """
    row = (
        await db.execute(
            select(ContentBlock).where(
                ContentBlock.id == block_id, ContentBlock.org_id == user.org_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    now = datetime.now(UTC)
    update = body.model_dump(exclude_unset=True, by_alias=False)

    if update.get("retire"):
        if not (update.get("retired_reason") or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Retiring a block needs a reason — a staffing model that changed, a "
                    "certification that lapsed. Six months from now it is the only explanation "
                    "of why a proposal used it and then stopped."
                ),
            )
        row.retired_at = now
        row.retired_reason = update["retired_reason"]
        row.history = [
            *(row.history or []),
            {"at": now.isoformat(), "event": "retired", "detail": f"{user.id}: {row.retired_reason}"},
        ]
    elif update.get("retire") is False and row.retired_at:
        row.retired_at = None
        row.retired_reason = None
        row.history = [
            *(row.history or []),
            {"at": now.isoformat(), "event": "reinstated", "detail": f"Reinstated by {user.id}."},
        ]

    if update.get("used"):
        row.times_used += 1
        row.last_used_at = now
        row.history = [
            *(row.history or []),
            {"at": now.isoformat(), "event": "used", "detail": f"Used by {user.id}."},
        ]

    for field in ("title", "text", "requirement_kind", "tags", "outcome"):
        if field in update and update[field] is not None:
            setattr(row, field, update[field])

    await db.flush()
    return _block(row)


@router.get("/analyses/{analysis_id}/requirements/{requirement_id}/content")
async def suggest_content(
    analysis_id: str, requirement_id: str, user: CurrentUser, db: DbSession
):
    """Text that answered something like this before, with what happened to it.

    Never text alone. A block comes back with the requirement it answered, who
    verified it, whether that bid was won, and the reasons to read it first —
    which is the whole difference between a library and a pile of paragraphs.
    """
    _, requirement = await _pair(db, analysis_id, requirement_id, user.org_id)
    blocks = (
        await db.execute(select(ContentBlock).where(ContentBlock.org_id == user.org_id))
    ).scalars().all()
    return [item.as_dict() for item in memory.suggest(list(blocks), requirement)]


async def _pair(db, analysis_id: str, requirement_id: str, org_id: str):
    analysis = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id, Analysis.org_id == org_id, Analysis.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    requirement = (
        await db.execute(
            select(Requirement).where(
                Requirement.id == requirement_id, Requirement.analysis_id == analysis_id
            )
        )
    ).scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    return analysis, requirement
