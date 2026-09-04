"""The bid/no-bid record, and the path to submission.

Two endpoints that answer the two questions a capture manager has on the same
morning: *should we bid this*, and *can we still finish it*.

Neither answers on its own. The first assembles what was known and records what
a person decided; the second walks the deadline backwards and says what is
already too late.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.contradiction import Contradiction
from app.db.models.decision import DecisionRecord
from app.db.models.question import Question
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.db.models.review import ReviewFinding, ReviewRound
from app.pipeline import critical_path, decision, verification, weighting
from app.schemas.resources import DecisionCreate, DecisionOutcome

router = APIRouter(tags=["decisions"])
logger = get_logger()


def _to_response(row: DecisionRecord) -> dict:
    return {
        "id": row.id,
        "analysisId": row.analysis_id,
        "decision": row.decision,
        "rationale": row.rationale,
        "decidedBy": row.decided_by,
        "decidedAt": row.decided_at.isoformat() if row.decided_at else None,
        "participants": list(row.participants or []),
        "evidence": row.evidence or {},
        "acknowledged": list(row.acknowledged or []),
        "supersedesId": row.supersedes_id,
        "outcome": row.outcome,
        "outcomeNote": row.outcome_note,
    }


async def _analysis(db, analysis_id: str, org_id: str) -> Analysis:
    row = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id, Analysis.org_id == org_id, Analysis.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return row


async def _load(db, analysis_id: str):
    async def rows(model):
        return list(
            (await db.execute(select(model).where(model.analysis_id == analysis_id))).scalars().all()
        )

    return (
        await rows(Requirement),
        await rows(ResponseCheck),
        await rows(Contradiction),
        await rows(Question),
        await rows(ReviewRound),
        await rows(ReviewFinding),
    )


@router.get("/analyses/{analysis_id}/decision/evidence")
async def decision_evidence(analysis_id: str, user: CurrentUser, db: DbSession):
    """What is known right now, in the shape a decision record freezes.

    Deliberately the uncomfortable half: failed gates, unowned mandatory
    requirements, incomplete coverage, unresolved contradictions, weight on
    factors the response does not answer. A record that only carried the
    reasons to bid would be a marketing document, and the whole value of one is
    that it is what you read when it went wrong.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)
    requirements, checks, conflicts, questions, rounds, findings = await _load(db, analysis_id)

    version = int((analysis.response or {}).get("version") or 0)
    current_checks = [c for c in checks if c.response_version == version] if version else []

    lens = weighting.summarise(
        weighting.build(analysis.evaluation or [], requirements, current_checks)
    )
    queue = verification.summarise(
        verification.build(
            analysis=analysis,
            requirements=requirements,
            checks=current_checks,
            questions=questions,
            reviews=rounds,
            review_findings=findings,
            contradictions=conflicts,
        )
    )

    evidence = decision.assemble(
        analysis=analysis,
        requirements=requirements,
        checks=current_checks,
        contradictions=conflicts,
        weighting=lens,
        queue_summary=queue,
    )
    return {**evidence.as_dict(), "readiness": decision.readiness(evidence)}


@router.get("/analyses/{analysis_id}/decision")
async def list_decisions(analysis_id: str, user: CurrentUser, db: DbSession):
    await _analysis(db, analysis_id, user.org_id)
    rows = (
        await db.execute(
            select(DecisionRecord)
            .where(DecisionRecord.analysis_id == analysis_id, DecisionRecord.org_id == user.org_id)
            .order_by(DecisionRecord.decided_at.desc())
        )
    ).scalars().all()
    return [_to_response(row) for row in rows]


@router.post("/analyses/{analysis_id}/decision", status_code=status.HTTP_201_CREATED)
async def record_decision(
    analysis_id: str, body: DecisionCreate, user: CurrentUser, db: DbSession
):
    """Record the decision, with the evidence frozen as it stood.

    A rationale is required. It is the one field that cannot be derived from
    anything else and the only one that matters in a debrief — and a decision
    record without it is a status field with extra steps.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)
    if not body.rationale.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A decision needs a reason. It is the one thing here that cannot be derived, "
                "and the only thing anybody will want six months from now."
            ),
        )

    evidence = await decision_evidence(analysis_id, user, db)

    previous = (
        await db.execute(
            select(DecisionRecord)
            .where(DecisionRecord.analysis_id == analysis_id)
            .order_by(DecisionRecord.decided_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    row = DecisionRecord(
        id=f"dr_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        org_id=user.org_id,
        decision=body.decision,
        rationale=body.rationale.strip(),
        decided_by=user.id,
        decided_at=now,
        participants=list(body.participants or []),
        evidence=evidence,
        acknowledged=list(body.acknowledged or []),
        supersedes_id=previous.id if previous else None,
    )
    db.add(row)

    # The board reads `go_no_go`, so the two stay in step. The record is the
    # truth; the field is the projection.
    analysis.go_no_go = body.decision
    analysis.decision_note = body.rationale.strip()
    analysis.stage = "decided"
    analysis.updated_at = now

    await db.flush()
    logger.info(
        "decision_recorded",
        analysis_id=analysis_id,
        decision=body.decision,
        against=evidence.get("against"),
        unknown=evidence.get("unknown"),
    )
    return _to_response(row)


@router.patch("/analyses/{analysis_id}/decision/{record_id}")
async def record_outcome(
    analysis_id: str, record_id: str, body: DecisionOutcome, user: CurrentUser, db: DbSession
):
    """What actually happened.

    The half that makes the record worth keeping. Without an outcome the
    evidence is a snapshot; with one it is the only data anybody has about
    whether their bid decisions are any good.
    """
    row = (
        await db.execute(
            select(DecisionRecord).where(
                DecisionRecord.id == record_id,
                DecisionRecord.analysis_id == analysis_id,
                DecisionRecord.org_id == user.org_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    row.outcome = body.outcome
    row.outcome_note = body.note
    await db.flush()
    return _to_response(row)


@router.get("/analyses/{analysis_id}/critical-path")
async def path(analysis_id: str, user: CurrentUser, db: DbSession):
    """What can still stop this going out, in the order it will.

    Walks backwards from the submission date through the review rounds the team
    has actually opened. Nothing here estimates how long work takes — it uses
    the dates the team set, because a tool inventing a duration is a tool
    inventing a crisis.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)
    requirements, _, _, _, rounds, _ = await _load(db, analysis_id)
    return critical_path.build(
        analysis=analysis, requirements=requirements, rounds=rounds
    ).as_dict()
