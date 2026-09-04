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
from app.db.models.question import Question
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.db.models.verdict import Verdict
from app.pipeline import verdicts, verification

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

    questions = (
        await db.execute(select(Question).where(Question.analysis_id == analysis_id))
    ).scalars().all()

    items = verification.build(
        analysis=analysis,
        requirements=list(requirements),
        checks=list(checks),
        questions=list(questions),
    )
    return {"summary": verification.summarise(items), "items": [item.as_dict() for item in items]}


@router.get("/verification/corpus")
async def verification_corpus(
    user: CurrentUser,
    db: DbSession,
    analysis_id: str | None = None,
    limit: int = 2000,
):
    """Where the machine and the people using it disagree.

    Every confirmation and correction is a labelled example produced by
    somebody who knows the answer. Grouped by the things a fix can be aimed at —
    the rule that fired, whether a rule or a model decided, mechanical against
    substantive — so the next change goes where the evidence points rather than
    where somebody guessed.

    `wouldHaveShipped` is the number to read first: corrections *out of*
    `satisfied`, where the machine said answered and a person said it was not.
    Those are the ones that would have gone out in a proposal.
    """
    query = select(Verdict).where(Verdict.org_id == user.org_id)
    if analysis_id:
        query = query.where(Verdict.analysis_id == analysis_id)
    rows = list(
        (await db.execute(query.order_by(Verdict.at.desc()).limit(min(limit, 5000)))).scalars().all()
    )

    report = verdicts.disagreement(rows)
    report["recent"] = [
        {
            "id": row.id,
            "at": row.at.isoformat() if row.at else None,
            "analysisId": row.analysis_id,
            "outcome": row.outcome,
            "reference": row.reference,
            "requirement": row.requirement_text[:300],
            "machineStatus": row.machine_status,
            "machineDecidedBy": row.machine_decided_by,
            "machineRule": row.machine_rule,
            "humanStatus": row.human_status,
            "note": row.note,
            "stakes": row.stakes,
            "actor": row.actor,
        }
        for row in rows[:50]
    ]
    return report
