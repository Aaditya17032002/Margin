"""Who owes what, and who changed what.

Two read-only views that exist because accountability is not a feature of any
single tab. A person's work is spread across every open pursuit, and the record
of who decided what is spread across three tables — neither is useful until it
is gathered in one place.

Both are derived on read. A stored worklist would need reconciling with the
requirements it points at, and a stored audit log would be a second version of
history that could disagree with the first.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.analysis import Analysis
from app.db.models.question import Question
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck

router = APIRouter(tags=["governance"])


@router.get("/work")
async def my_work(
    user: CurrentUser,
    db: DbSession,
    owner: str | None = Query(None, description="Whose work to list. Defaults to everyone's."),
):
    """Requirements someone owns, across every live pursuit.

    Ordered by the date the work is actually due, with anything overdue first
    and anything mandatory ahead of anything scored on the same day. A list
    ordered by analysis would make a person read all of them to find the one
    thing due tomorrow.
    """
    analyses = {
        row.id: row
        for row in (
            await db.execute(
                select(Analysis).where(
                    Analysis.org_id == user.org_id,
                    Analysis.deleted_at.is_(None),
                    Analysis.go_no_go != "no-bid",
                )
            )
        )
        .scalars()
        .all()
    }
    if not analyses:
        return {"items": [], "summary": {"total": 0, "overdue": 0, "unscheduled": 0}}

    query = select(Requirement).where(
        Requirement.org_id == user.org_id,
        Requirement.analysis_id.in_(list(analyses)),
        Requirement.state == "open",
        Requirement.status != "complete",
    )
    if owner:
        query = query.where(Requirement.owner == owner)
    else:
        query = query.where(Requirement.owner.is_not(None))

    rows = (await db.execute(query)).scalars().all()
    now = datetime.now(UTC)

    items = []
    for row in rows:
        analysis = analyses.get(row.analysis_id)
        overdue = bool(row.due_at and row.due_at < now)
        items.append(
            {
                "requirementId": row.id,
                "analysisId": row.analysis_id,
                "analysisTitle": analysis.title if analysis else "",
                "solicitationNumber": analysis.solicitation_number if analysis else "",
                "reference": row.reference,
                "requirement": row.text,
                "stakes": row.stakes,
                "verification": row.verification,
                "owner": row.owner,
                "status": row.status,
                "dueAt": row.due_at.isoformat() if row.due_at else None,
                "overdue": overdue,
                "responseLocation": row.response_location or "",
            }
        )

    # Overdue first, then by due date, then mandatory ahead of scored. A row
    # with no date sorts last: it is work nobody has committed to a day, which
    # is a different problem from work that is late.
    stakes_order = {"disqualifying": 0, "scored": 1, "informational": 2}
    items.sort(
        key=lambda item: (
            not item["overdue"],
            item["dueAt"] or "9999",
            stakes_order.get(item["stakes"], 3),
            item["reference"],
        )
    )
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "overdue": sum(1 for item in items if item["overdue"]),
            "unscheduled": sum(1 for item in items if not item["dueAt"]),
        },
    }


@router.get("/analyses/{analysis_id}/audit")
async def audit_trail(analysis_id: str, user: CurrentUser, db: DbSession):
    """Everything that happened to this analysis, newest first.

    Assembled from the append-only histories the requirement ledger, the
    response checks and the Q&A already keep, plus the run versions and the
    amendment records. Nothing is written for this view — an audit log kept
    separately from the thing it describes is a second version of history, and
    the two eventually disagree.
    """
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

    entries: list[dict] = []

    for version in analysis.versions or []:
        entries.append(
            {
                "at": version.get("at", ""),
                "scope": "run",
                "subject": version.get("label", "Analysis pass"),
                "event": "ran",
                "detail": version.get("note", ""),
                "actor": version.get("author", "Margin"),
            }
        )

    for record in analysis.amendments or []:
        entries.append(
            {
                "at": record.get("issued", ""),
                "scope": "amendment",
                "subject": record.get("label", "Amendment"),
                "event": "processed",
                "detail": record.get("summary", ""),
                "actor": "Margin",
            }
        )

    requirements = (
        await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
    ).scalars().all()
    by_id = {row.id: row for row in requirements}
    for row in requirements:
        for event in row.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "requirement",
                    "subject": row.reference,
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": row.confirmed_by if event.get("event") == "edited" else "Margin",
                }
            )

    checks = (
        await db.execute(select(ResponseCheck).where(ResponseCheck.analysis_id == analysis_id))
    ).scalars().all()
    for check in checks:
        requirement = by_id.get(check.requirement_id)
        subject = requirement.reference if requirement else check.requirement_id
        for event in check.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "response",
                    "subject": subject,
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": check.confirmed_by or "Margin",
                }
            )
        if check.confirmed_by and check.confirmed_at:
            entries.append(
                {
                    "at": check.confirmed_at.isoformat(),
                    "scope": "response",
                    "subject": subject,
                    "event": "signed off",
                    "detail": check.note or f"Accepted as {check.status}.",
                    "actor": check.confirmed_by,
                }
            )

    questions = (
        await db.execute(select(Question).where(Question.analysis_id == analysis_id))
    ).scalars().all()
    for question in questions:
        for event in question.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "question",
                    "subject": question.text[:80],
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": "Margin",
                }
            )

    entries.sort(key=lambda entry: str(entry.get("at") or ""), reverse=True)
    return {"entries": entries, "total": len(entries)}
