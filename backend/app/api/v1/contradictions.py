"""Requirements that cannot both be met, and the decision that settles them.

Detection is deterministic and runs with the analysis. Resolution is not: a
person reads both clauses and says which governs, because choosing for them
would be choosing which requirement the team writes to.

Resolving one acts on the ledger. The requirement that loses is superseded by
the one that wins — the same treatment an amendment produces — so the losing
clause stops appearing in the matrix as live work while staying answerable
about what happened to it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core import permissions
from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.contradiction import Contradiction
from app.db.models.requirement import Requirement
from app.schemas.resources import ContradictionResolve

router = APIRouter(tags=["contradictions"])
logger = get_logger()


def _to_response(row: Contradiction, requirements: dict) -> dict:
    def side(requirement_id: str) -> dict:
        requirement = requirements.get(requirement_id)
        return {
            "requirementId": requirement_id,
            "reference": requirement.reference if requirement else "",
            "text": requirement.text if requirement else "",
            "stakes": requirement.stakes if requirement else "scored",
            "state": requirement.state if requirement else "",
            "citation": (requirement.citation if requirement else {}) or {},
        }

    return {
        "id": row.id,
        "analysisId": row.analysis_id,
        "key": row.key,
        "dimension": row.dimension,
        "summary": row.summary,
        "severity": row.severity,
        "state": row.state,
        "left": {**side(row.left_id), "value": row.left_value},
        "right": {**side(row.right_id), "value": row.right_value},
        "recommendedId": row.recommended_id,
        "rationale": row.rationale,
        "governsId": row.governs_id,
        "resolution": row.resolution,
        "resolvedBy": row.resolved_by,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
        "questionId": row.question_id,
        "history": row.history or [],
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


@router.get("/analyses/{analysis_id}/contradictions")
async def list_contradictions(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    include_resolved: bool = Query(False, alias="includeResolved"),
):
    await _analysis(db, analysis_id, user.org_id)
    query = select(Contradiction).where(
        Contradiction.analysis_id == analysis_id, Contradiction.org_id == user.org_id
    )
    if not include_resolved:
        query = query.where(Contradiction.state == "open")
    rows = (await db.execute(query)).scalars().all()

    requirements = {
        r.id: r
        for r in (
            await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
        )
        .scalars()
        .all()
    }
    out = [_to_response(row, requirements) for row in rows]
    out.sort(key=lambda item: (0 if item["severity"] == "blocking" else 1, item["dimension"]))
    return out


@router.post("/analyses/{analysis_id}/contradictions/{contradiction_id}/resolve")
async def resolve(
    analysis_id: str,
    contradiction_id: str,
    body: ContradictionResolve,
    user: CurrentUser,
    db: DbSession,
):
    """Record which requirement governs, and act on it.

    `governsId` supersedes the other in the ledger, so the losing clause stops
    reading as live work. `disputed` records that the document itself is
    contradictory and a question is the only way out — a different outcome
    from picking a side, and the one most likely to move a deadline.
    """
    permissions.require(user.role, "resolve_contradiction")
    await _analysis(db, analysis_id, user.org_id)
    row = (
        await db.execute(
            select(Contradiction).where(
                Contradiction.id == contradiction_id,
                Contradiction.analysis_id == analysis_id,
                Contradiction.org_id == user.org_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contradiction not found")

    if body.outcome == "resolved" and body.governs_id not in (row.left_id, row.right_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Resolving means saying which of the two requirements governs, and that has "
                "to be one of them."
            ),
        )
    if not (body.resolution or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A resolution needs a reason. Six weeks from now this is the only record of "
                "why the team wrote to one clause and not the other."
            ),
        )

    now = datetime.now(UTC)
    impact: dict | None = None
    row.state = body.outcome
    row.resolution = body.resolution
    row.resolved_by = user.id
    row.resolved_at = now

    superseded: str | None = None
    if body.outcome == "resolved":
        row.governs_id = body.governs_id
        loser_id = row.right_id if body.governs_id == row.left_id else row.left_id
        winner, loser = await _pair(db, analysis_id, body.governs_id, loser_id)
        if winner is not None and loser is not None and loser.state == "open":
            loser.state = "superseded"
            loser.superseded_by_id = winner.id
            loser.history = [
                *(loser.history or []),
                {
                    "at": now.isoformat(),
                    "event": "superseded",
                    "detail": (
                        f"{user.id} decided {winner.reference} governs over this one: "
                        f"{body.resolution}"
                    ),
                },
            ]
            # The work follows the clause that governs, because the person who
            # was answering the losing one is the person who has to answer this.
            if loser.owner and not winner.owner:
                winner.owner = loser.owner
            if loser.response_location and not winner.response_location:
                winner.response_location = loser.response_location
            winner.history = [
                *(winner.history or []),
                {
                    "at": now.isoformat(),
                    "event": "governs",
                    "detail": f"Governs over {loser.reference}: {body.resolution}",
                },
            ]
            superseded = loser.reference

            # Work answered against the clause that lost is not an answer to
            # the one that governs. Walked through the graph so it reaches the
            # checks and review findings on both halves of the pair and
            # nothing beyond them.
            impact = await _propagate(
                db, analysis_id, [winner.id, loser.id], now,
                detail=f"{winner.reference} governs over {loser.reference}: {body.resolution}",
            )

    row.history = [
        *(row.history or []),
        {
            "at": now.isoformat(),
            "event": body.outcome,
            "detail": f"{user.id}: {body.resolution}",
        },
    ]
    await db.flush()
    logger.info(
        "contradiction_resolved",
        analysis_id=analysis_id,
        outcome=body.outcome,
        dimension=row.dimension,
    )

    requirements = {
        r.id: r
        for r in (
            await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
        )
        .scalars()
        .all()
    }
    return {**_to_response(row, requirements), "superseded": superseded, "impact": impact}


async def _propagate(db, analysis_id: str, origins: list[str], now, *, detail: str) -> dict:
    """Reopen the settled work that hangs off either half of a resolved pair."""
    from app.db.models.question import Question
    from app.db.models.response_check import ResponseCheck
    from app.db.models.review import ReviewFinding
    from app.pipeline import propagation

    async def load(model):
        return list((await db.execute(select(model).where(model.analysis_id == analysis_id))).scalars().all())

    requirements = await load(Requirement)
    graph = propagation.build_graph(
        requirements=requirements,
        checks=await load(ResponseCheck),
        questions=await load(Question),
        findings=await load(ReviewFinding),
    )
    impacts = propagation.propagate(
        graph, origins, cause="a resolved contradiction", detail=detail, at=now
    )
    return propagation.summarise(
        impacts, cause="a resolved contradiction", considered=len(requirements)
    )


async def _pair(db, analysis_id: str, winner_id: str, loser_id: str):
    rows = {
        r.id: r
        for r in (
            await db.execute(
                select(Requirement).where(
                    Requirement.analysis_id == analysis_id,
                    Requirement.id.in_([winner_id, loser_id]),
                )
            )
        )
        .scalars()
        .all()
    }
    return rows.get(winner_id), rows.get(loser_id)
