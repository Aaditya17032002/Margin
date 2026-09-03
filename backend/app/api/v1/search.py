"""Search router — hybrid search across analyses + knowledge."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis
from app.db.models.knowledge import KnowledgeItem
from app.schemas.resources import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=1),
    user: CurrentUser = None,  # type: ignore[assignment]
    db: DbSession = None,  # type: ignore[assignment]
):
    """Hybrid text search. In production, this would combine pgvector similarity
    with full-text search. For now, simple ILIKE matching."""
    query_lower = q.lower()
    results: list[dict] = []

    # Search analyses
    analysis_result = await db.execute(
        select(Analysis).where(Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    for a in analysis_result.scalars().all():
        if query_lower in a.title.lower() or query_lower in a.agency.lower() or query_lower in (a.summary or "").lower():
            results.append({
                "kind": "analysis",
                "id": a.id,
                "title": a.title,
                "snippet": (a.summary or a.agency)[:200],
                "score": 1.0,
            })

    # Search knowledge base
    knowledge_result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.org_id == user.org_id)
    )
    for k in knowledge_result.scalars().all():
        if query_lower in k.title.lower() or query_lower in (k.debrief or "").lower():
            results.append({
                "kind": "knowledge",
                "id": k.id,
                "title": k.title,
                "snippet": (k.debrief or "")[:200],
                "score": 0.8,
            })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:20]
