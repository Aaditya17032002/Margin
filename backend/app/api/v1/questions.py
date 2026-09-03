"""Questions router — CRUD + reorder for Q&A builder."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.core.deps import CurrentUser, DbSession
from app.db.models.question import Question
from app.schemas.resources import (
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ReorderRequest,
)

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
        citation=body.citation.model_dump() if body.citation else None,
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
    for key, value in update_data.items():
        col = "go_no_go_impact" if key == "go_no_go_impact" else key
        if hasattr(q, col):
            setattr(q, col, value)
    await db.flush()
    return _to_response(q)


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
