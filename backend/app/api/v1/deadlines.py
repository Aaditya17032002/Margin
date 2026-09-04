"""Deadlines router — derived from analyses' date arrays."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis
from app.schemas.resources import DeadlineResponse

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("", response_model=list[DeadlineResponse])
async def list_deadlines(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analyses = result.scalars().all()

    deadlines = []
    for a in analyses:
        for d in (a.dates or []):
            deadlines.append({
                "id": d.get("id", ""),
                "label": d.get("label", ""),
                "at": d.get("at", ""),
                "timezone": d.get("timezone", "UTC"),
                "kind": d.get("kind", "proposal-due"),
                "source": d.get("source", "document"),
                "analysisId": a.id,
                "analysisTitle": a.title,
                # The calendar is built for every analysis, so the view needs to
                # be able to tell a live pursuit from one already decided.
                "analysisStage": a.stage,
                "goNoGo": a.go_no_go,
            })

    # Sort by date
    deadlines.sort(key=lambda x: x["at"])
    return deadlines
