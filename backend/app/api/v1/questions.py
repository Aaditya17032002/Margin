"""Questions to the agency, from drafting to the answer coming back.

A question is not finished when it is sent. The answer is the point, and an
answer that never reaches the requirement it was about has changed nothing —
so a question can name the clause it concerns, and recording the answer
reopens the work done against the old reading of that clause.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from datetime import UTC, datetime

from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.question import Question
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.schemas.resources import (
    QuestionAnswer,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ReorderRequest,
)

logger = get_logger()

router = APIRouter(tags=["questions"])


def _to_response(q: Question) -> dict:
    return {
        "id": q.id,
        "analysisId": q.analysis_id,
        "text": q.text,
        "rationale": q.rationale,
        "sourceKind": q.source_kind,
        "goNoGoImpact": q.go_no_go_impact,
        "order": q.order,
        "sent": q.sent,
        "citation": q.citation,
        "status": q.status,
        "submittedAt": q.submitted_at.isoformat() if q.submitted_at else None,
        "answeredAt": q.answered_at.isoformat() if q.answered_at else None,
        "answer": q.answer,
        "answerSource": q.answer_source or "",
        "requirementId": q.requirement_id,
        "history": q.history or [],
    }


@router.get("/analyses/{analysis_id}/questions", response_model=list[QuestionResponse])
async def list_questions(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Question)
        .where(Question.analysis_id == analysis_id, Question.org_id == user.org_id)
        .order_by(Question.order)
    )
    return [_to_response(q) for q in result.scalars().all()]


@router.post("/analyses/{analysis_id}/questions", status_code=status.HTTP_201_CREATED)
async def create_question(analysis_id: str, body: QuestionCreate, user: CurrentUser, db: DbSession):
    # Get next order value
    count_result = await db.execute(
        select(func.count()).select_from(Question).where(
            Question.analysis_id == analysis_id, Question.org_id == user.org_id
        )
    )
    order = count_result.scalar() or 0

    q = Question(
        id=f"q_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        org_id=user.org_id,
        text=body.text,
        rationale=body.rationale,
        source_kind=body.source_kind,
        go_no_go_impact=body.go_no_go_impact,
        order=order,
        sent=False,
        status="draft",
        requirement_id=body.requirement_id,
        citation=body.citation.model_dump() if body.citation else None,
        history=[],
    )
    db.add(q)
    await db.flush()
    return _to_response(q)


# Declared before `/{question_id}`: FastAPI matches in declaration order, and a
# parameterised path would otherwise swallow "reorder" as an id.
@router.patch("/analyses/{analysis_id}/questions/reorder")
async def reorder_questions(analysis_id: str, body: ReorderRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Question).where(Question.analysis_id == analysis_id, Question.org_id == user.org_id)
    )
    questions = {q.id: q for q in result.scalars().all()}
    for index, qid in enumerate(body.ordered_ids):
        if qid in questions:
            questions[qid].order = index
    await db.flush()
    return {"reordered": len(body.ordered_ids)}


@router.patch("/analyses/{analysis_id}/questions/{question_id}")
async def update_question(analysis_id: str, question_id: str, body: QuestionUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Question).where(
            Question.id == question_id, Question.analysis_id == analysis_id, Question.org_id == user.org_id
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    update_data = body.model_dump(exclude_unset=True, by_alias=False)
    now = datetime.now(UTC)
    for key, value in update_data.items():
        col = "go_no_go_impact" if key == "go_no_go_impact" else key
        if hasattr(q, col):
            setattr(q, col, value)

    # `sent` is the old boolean the workspace still reads. It is kept in step
    # with the lifecycle rather than left to drift into disagreeing with it.
    if "sent" in update_data:
        if q.sent and q.status == "draft":
            q.status = "submitted"
            q.submitted_at = now
            q.history = [*(q.history or []), _event(now, "submitted", "Sent to the agency.")]
        elif not q.sent and q.status == "submitted":
            q.status = "draft"
            q.submitted_at = None
            q.history = [*(q.history or []), _event(now, "unsent", "Pulled back to draft.")]
    await db.flush()
    return _to_response(q)


@router.post("/analyses/{analysis_id}/questions/{question_id}/answer")
async def record_answer(
    analysis_id: str, question_id: str, body: QuestionAnswer, user: CurrentUser, db: DbSession
):
    """Record the agency's answer, and reopen what it invalidates.

    An answer that only lands in a list has changed nothing. When the question
    names a requirement, the answer is written into that requirement's history
    and any response check that was *satisfied* against the old reading is
    reopened — the same rule an amendment gets, for the same reason: an answer
    written before the clarification is not an answer to the clarified clause.
    """
    q = await _question(db, analysis_id, question_id, user.org_id)
    now = datetime.now(UTC)

    q.answer = body.answer
    q.answer_source = body.source[:255]
    q.answered_at = now
    q.status = "answered"
    q.sent = True
    if q.submitted_at is None:
        q.submitted_at = now
    q.history = [
        *(q.history or []),
        _event(now, "answered", f"{body.source or 'The agency'} answered: {body.answer[:300]}"),
    ]

    reopened: list[str] = []
    if q.requirement_id:
        requirement = (
            await db.execute(
                select(Requirement).where(
                    Requirement.id == q.requirement_id, Requirement.analysis_id == analysis_id
                )
            )
        ).scalar_one_or_none()
        if requirement is not None:
            requirement.history = [
                *(requirement.history or []),
                _event(
                    now,
                    "clarified",
                    f"Answered by the agency ({body.source or 'Q&A'}): {body.answer[:300]}",
                ),
            ]
            checks = (
                await db.execute(
                    select(ResponseCheck).where(ResponseCheck.requirement_id == requirement.id)
                )
            ).scalars().all()
            for check in checks:
                if check.status != "satisfied":
                    continue
                check.status = "unverifiable"
                check.decided_by = "rule"
                check.needs_confirmation = False
                check.confirmed_by = None
                check.confirmed_at = None
                check.detail = (
                    "The agency answered a question about this requirement after this was "
                    "checked. The answer may change what compliance means here."
                )
                check.gap = "Re-read the answer against what the response says."
                check.risk = "high" if requirement.stakes == "disqualifying" else "medium"
                check.history = [
                    *(check.history or []),
                    _event(now, "reopened", f"Reopened by an agency answer ({body.source or 'Q&A'})."),
                ]
                reopened.append(requirement.reference)

    await db.flush()
    logger.info("question_answered", analysis_id=analysis_id, question=question_id, reopened=len(reopened))
    return {**_to_response(q), "reopened": reopened}


async def _question(db, analysis_id: str, question_id: str, org_id: str) -> Question:
    result = await db.execute(
        select(Question).where(
            Question.id == question_id, Question.analysis_id == analysis_id, Question.org_id == org_id
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return q


def _event(at, event: str, detail: str) -> dict:
    return {"at": at.isoformat(), "event": event, "detail": detail}


@router.delete("/analyses/{analysis_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(analysis_id: str, question_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Question).where(
            Question.id == question_id, Question.analysis_id == analysis_id, Question.org_id == user.org_id
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    await db.delete(q)
