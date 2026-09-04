"""Where the score is, and whether the response is there.

Read-only and derived: the mapping between factors and requirements is
recomputed on every request from the current ledger and the current response
check, so resolving a gap moves the lens immediately rather than leaving a
stored figure to be reconciled.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import weighting

router = APIRouter(tags=["weighting"])


@router.get("/analyses/{analysis_id}/weighting")
async def evaluation_weighting(analysis_id: str, user: CurrentUser, db: DbSession):
    analysis = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.org_id == user.org_id,
                Analysis.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    requirements = list(
        (
            await db.execute(
                select(Requirement).where(
                    Requirement.analysis_id == analysis_id, Requirement.state == "open"
                )
            )
        )
        .scalars()
        .all()
    )

    version = int((analysis.response or {}).get("version") or 0)
    checks: list[ResponseCheck] = []
    if version:
        checks = list(
            (
                await db.execute(
                    select(ResponseCheck).where(
                        ResponseCheck.analysis_id == analysis_id,
                        ResponseCheck.response_version == version,
                    )
                )
            )
            .scalars()
            .all()
        )

    coverage = weighting.build(analysis.evaluation or [], requirements, checks)
    by_id = {r.id: r for r in requirements}

    return {
        "summary": weighting.summarise(coverage),
        # A response is needed for weakness to mean anything. Said plainly
        # rather than shown as a lens full of zeroes.
        "responseBound": bool(version),
        "factors": [
            {
                **factor.as_dict(),
                "requirementDetail": [
                    {
                        "id": rid,
                        "reference": by_id[rid].reference,
                        "text": by_id[rid].text[:300],
                        "stakes": by_id[rid].stakes,
                        "owner": by_id[rid].owner,
                        "status": next(
                            (c.status for c in checks if c.requirement_id == rid), "unchecked"
                        ),
                        "matchedBy": factor.matched_by.get(rid, ""),
                    }
                    for rid in factor.requirement_ids
                    if rid in by_id
                ],
            }
            for factor in coverage
        ],
    }
