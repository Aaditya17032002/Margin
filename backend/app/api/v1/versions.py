"""Versions router — version history + diff."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis

router = APIRouter(tags=["versions"])


@router.get("/analyses/{analysis_id}/versions")
async def list_versions(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis.versions or []


@router.get("/analyses/{analysis_id}/diff")
async def diff_versions(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    from_version: str = Query(..., alias="from"),
    to_version: str = Query(..., alias="to"),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    versions = analysis.versions or []
    from_ver = next((v for v in versions if v.get("id") == from_version), None)
    to_ver = next((v for v in versions if v.get("id") == to_version), None)

    return {
        "from": from_ver,
        "to": to_ver,
        "changes": [],  # In a full implementation, this would diff the finding snapshots
    }
