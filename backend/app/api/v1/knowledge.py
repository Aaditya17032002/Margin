"""Knowledge router — CRUD for past bids + vector search."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.knowledge import KnowledgeItem
from app.schemas.resources import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _to_response(k: KnowledgeItem) -> dict:
    return {
        "id": k.id,
        "title": k.title,
        "agency": k.agency,
        "submittedAt": k.submitted_at or "",
        "outcome": k.outcome,
        "value": k.value or 0,
        "debrief": k.debrief or "",
        "lessons": k.lessons or [],
        "incumbent": k.incumbent,
        "scoreGap": k.score_gap,
    }


@router.get("", response_model=list[KnowledgeResponse])
async def list_knowledge(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.org_id == user.org_id)
    )
    return [_to_response(k) for k in result.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge(body: KnowledgeCreate, user: CurrentUser, db: DbSession):
    k = KnowledgeItem(
        id=f"k_{uuid.uuid4().hex[:8]}",
        org_id=user.org_id,
        title=body.title,
        agency=body.agency,
        submitted_at=body.submitted_at,
        outcome=body.outcome,
        value=body.value,
        debrief=body.debrief,
        lessons=body.lessons,
        incumbent=body.incumbent,
        score_gap=body.score_gap,
    )
    db.add(k)
    await db.flush()
    return _to_response(k)


@router.patch("/{item_id}")
async def update_knowledge(item_id: str, body: KnowledgeUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.org_id == user.org_id)
    )
    k = result.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(k, key):
            setattr(k, key, value)
    await db.flush()
    return _to_response(k)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(item_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.org_id == user.org_id)
    )
    k = result.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found")
    await db.delete(k)


@router.get("/search")
async def search_knowledge(q: str, user: CurrentUser, db: DbSession):
    """Simple text search over knowledge items. In production, this would use pgvector."""
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.org_id == user.org_id)
    )
    items = result.scalars().all()
    query_lower = q.lower()
    matches = [
        {**_to_response(k), "score": 1.0}
        for k in items
        if query_lower in k.title.lower() or query_lower in (k.debrief or "").lower()
    ]
    return matches[:20]
