"""Activity router — audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.activity import ActivityLog
from app.schemas.resources import ActivityCreate, ActivityResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityResponse])
async def list_activity(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.org_id == user.org_id)
        .order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [
        {
            "id": a.id,
            "at": a.created_at.isoformat() if isinstance(a.created_at, datetime) else str(a.created_at),
            "actor": a.actor,
            "action": a.action,
            "target": a.target,
            "analysisId": a.analysis_id,
        }
        for a in result.scalars().all()
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ActivityResponse)
async def create_activity(body: ActivityCreate, user: CurrentUser, db: DbSession):
    """Append an entry to the org's audit trail."""
    entry = ActivityLog(
        id=f"a_{uuid.uuid4().hex[:8]}",
        org_id=user.org_id,
        actor=body.actor,
        action=body.action,
        target=body.target,
        analysis_id=body.analysis_id,
    )
    db.add(entry)
    await db.flush()
    return {
        "id": entry.id,
        "at": entry.created_at.isoformat()
        if isinstance(entry.created_at, datetime)
        else str(entry.created_at),
        "actor": entry.actor,
        "action": entry.action,
        "target": entry.target,
        "analysisId": entry.analysis_id,
    }
