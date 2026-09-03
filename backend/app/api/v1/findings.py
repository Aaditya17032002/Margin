"""Findings router — GET + PATCH with RBAC for disqualifying findings."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import AuthUser, RequireRole
from app.db.models.analysis import Analysis

router = APIRouter(tags=["findings"])


@router.get("/analyses/{analysis_id}/findings")
async def list_findings(analysis_id: str, user: CurrentUser, db: DbSession):
    """Return all finding arrays from the analysis JSONB."""
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    return {
        "identity": analysis.identity or [],
        "scope": analysis.scope or [],
        "legal": analysis.legal or [],
        "eligibility": analysis.eligibility or [],
        "pricing": analysis.pricing or [],
        "postAward": analysis.post_award or [],
    }


@router.patch("/analyses/{analysis_id}/findings/{field_path}")
async def update_finding(
    analysis_id: str,
    field_path: str,
    body: dict,
    user: CurrentUser,
    db: DbSession,
):
    """Update a specific finding within an analysis. Disqualifying findings require reviewer role."""
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.org_id == user.org_id, Analysis.deleted_at.is_(None))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # field_path format: "identity.f_123" or "scope.f_456"
    parts = field_path.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid field path. Use 'section.findingId'")

    section, finding_id = parts
    section_map = {
        "identity": "identity",
        "scope": "scope",
        "legal": "legal",
        "eligibility": "eligibility",
        "pricing": "pricing",
        "postAward": "post_award",
    }

    attr = section_map.get(section)
    if not attr:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown section: {section}")

    findings: list = list(getattr(analysis, attr) or [])
    target = None
    target_idx = None
    for idx, f in enumerate(findings):
        if f.get("id") == finding_id:
            target = f
            target_idx = idx
            break

    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding {finding_id} not found in {section}")

    # RBAC: disqualifying stakes require reviewer+
    from app.core.security import ROLE_HIERARCHY
    if target.get("stakes") == "disqualifying" and ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY["reviewer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Disqualifying findings require reviewer role or higher",
        )

    # Apply updates
    for key, value in body.items():
        target[key] = value

    findings[target_idx] = target
    setattr(analysis, attr, findings)
    analysis.updated_at = datetime.now(UTC)
    await db.flush()

    return target
