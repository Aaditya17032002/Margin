"""The verification queue — everything in this analysis that needs a person.

Built on read, not stored. Every item is derived from the current state of the
coverage ledger, the requirement ledger, the response trace and the findings,
so an item disappears the moment the thing it was about is settled. A queue
that has to be reconciled with reality is a queue nobody trusts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import verification

router = APIRouter(tags=["verification"])


@router.get("/analyses/{analysis_id}/verification")
async def verification_queue(analysis_id: str, user: CurrentUser, db: DbSession):
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

    requirements = (
        await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
    ).scalars().all()

    version = int((analysis.response or {}).get("version") or 0)
    checks = []
    if version:
        checks = (
            await db.execute(
                select(ResponseCheck).where(
                    ResponseCheck.analysis_id == analysis_id,
                    ResponseCheck.response_version == version,
                )
            )
        ).scalars().all()

    items = verification.build(analysis=analysis, requirements=list(requirements), checks=list(checks))
    return {"summary": verification.summarise(items), "items": [item.as_dict() for item in items]}
