"""What can actually stop this response going out, in the order it will.

A deadline list says the proposal is due in nine days. A task list says forty
things are open. Neither says the thing a capture manager needs, which is
*which of those forty can still be finished, and which one is already too
late*.

The chain is: a requirement has an owner and an internal due date, the answer
has to be written, then reviewed, then the whole thing has to clear a
production check and be submitted. Every link takes time, and the links are
serial — a Red Team cannot review a section nobody has drafted, and a
white-glove pass cannot check a volume that is still being rewritten.

So this walks backwards from the submission deadline through the review gates
the team has actually scheduled, works out the latest date each requirement can
still be started, and reports what is past it. Two numbers matter and they are
different:

``at risk``
    Slipping, and recoverable if somebody moves today.
``past the point``
    The date by which this needed to start has gone. It is not a warning any
    more; either scope comes out or the deadline moves, and both of those are
    decisions rather than tasks.

Nothing here estimates how long work takes. It uses the dates the team set,
because a tool inventing a duration is a tool inventing a crisis — and the one
thing worse than an unhelpful schedule is a confident wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from app.core.logging import get_logger

logger = get_logger()

#: Working days a review round needs between the draft being ready and the
#: response going out. Not an estimate of the work — a floor below which the
#: round cannot happen at all, taken from how these are actually run.
REVIEW_DAYS = {"pink": 2, "red": 3, "gold": 2, "white_glove": 1}

#: Days between the last review closing and submission. Production, printing,
#: uploading, and the hour everybody loses to a portal.
SUBMISSION_BUFFER_DAYS = 1

CLEAR = "clear"
AT_RISK = "at risk"
PAST = "past the point"


@dataclass
class Step:
    """One link in the chain, with the date it has to be done by."""

    kind: str
    label: str
    due: date | None
    state: str = CLEAR
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "due": self.due.isoformat() if self.due else None,
            "state": self.state,
            "detail": self.detail,
        }


@dataclass
class PathItem:
    """One requirement, and whether it can still be finished in time."""

    requirement_id: str
    reference: str
    text: str
    stakes: str
    owner: str | None
    status: str
    #: The latest date drafting can start and still clear every gate.
    latest_start: date | None
    days_left: int | None
    state: str
    reason: str
    blocking: bool = False

    def as_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "reference": self.reference,
            "text": self.text[:300],
            "stakes": self.stakes,
            "owner": self.owner,
            "status": self.status,
            "latestStart": self.latest_start.isoformat() if self.latest_start else None,
            "daysLeft": self.days_left,
            "state": self.state,
            "reason": self.reason,
            "blocking": self.blocking,
        }


@dataclass
class CriticalPath:
    submission: date | None
    steps: list[Step] = field(default_factory=list)
    items: list[PathItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        past = [i for i in self.items if i.state == PAST]
        at_risk = [i for i in self.items if i.state == AT_RISK]
        return {
            "submission": self.submission.isoformat() if self.submission else None,
            "steps": [s.as_dict() for s in self.steps],
            "items": [i.as_dict() for i in self.items],
            "notes": self.notes,
            "summary": {
                "total": len(self.items),
                "pastThePoint": len(past),
                "atRisk": len(at_risk),
                "clear": len(self.items) - len(past) - len(at_risk),
                # The number that turns a schedule into a decision: mandatory
                # requirements whose start date has already gone.
                "blockingPastThePoint": sum(1 for i in past if i.blocking),
            },
        }


#: Statuses that mean the drafting has not started.
_NOT_STARTED = frozenset({"unassigned", "assigned"})
#: Statuses that mean the work is done as far as the schedule is concerned.
_DONE = frozenset({"complete"})


def _submission_date(analysis) -> date | None:
    """The date everything else is measured back from."""
    best: date | None = None
    for entry in analysis.dates or []:
        if str(entry.get("kind")) not in ("proposal-due", "submission", "closing"):
            continue
        raw = str(entry.get("at") or "")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if best is None or parsed < best:
            best = parsed
    return best


def _gates(submission: date, rounds: list) -> list[Step]:
    """The review gates between "drafted" and "submitted", latest first.

    Only rounds the team has actually scheduled or opened. Inventing a Red Team
    nobody planned would produce a deadline nobody agreed to.
    """
    steps: list[Step] = [
        Step("submission", "Submission", submission, detail="The date in the solicitation.")
    ]
    cursor = submission - timedelta(days=SUBMISSION_BUFFER_DAYS)
    steps.append(
        Step(
            "production",
            "Production and upload",
            cursor,
            detail=(
                "Printing, assembling, uploading, and the hour everybody loses to a portal."
            ),
        )
    )

    planned = [r for r in rounds if r.status == "open"]
    order = {"white_glove": 0, "gold": 1, "red": 2, "pink": 3}
    for round_row in sorted(planned, key=lambda r: order.get(r.colour, 9)):
        days = REVIEW_DAYS.get(round_row.colour, 2)
        cursor = cursor - timedelta(days=days)
        steps.append(
            Step(
                "review",
                f"{round_row.colour.replace('_', ' ').title()} review closes",
                cursor,
                detail=f"Needs {days} day(s), and cannot review a section nobody has drafted.",
            )
        )
    return steps


def build(*, analysis, requirements: list, rounds: list | None = None, today: date | None = None) -> CriticalPath:
    today = today or datetime.now(UTC).date()
    submission = _submission_date(analysis)
    path = CriticalPath(submission=submission)

    if submission is None:
        path.notes.append(
            "No submission date was extracted, so nothing can be scheduled backwards from it. "
            "Set the proposal due date on the Overview tab and this becomes a real path."
        )
        return path

    path.steps = _gates(submission, list(rounds or []))
    # The latest a requirement can start is the earliest gate it has to clear.
    earliest_gate = min((s.due for s in path.steps if s.due), default=submission)

    for step in path.steps:
        if step.due and step.due < today:
            step.state = PAST
            step.detail = f"{step.detail} This date has passed.".strip()
        elif step.due and (step.due - today).days <= 2:
            step.state = AT_RISK

    for requirement in requirements:
        if requirement.state != "open":
            continue

        status = requirement.status or "unassigned"
        if status in _DONE:
            continue

        # A requirement with its own internal date is measured against that;
        # everything else against the last date it could start and still clear
        # every gate the team has scheduled.
        own_due = requirement.due_at.date() if requirement.due_at else None
        latest_start = min(filter(None, [own_due, earliest_gate])) if earliest_gate else own_due
        days_left = (latest_start - today).days if latest_start else None
        blocking = requirement.stakes == "disqualifying"

        if days_left is None:
            state, reason = CLEAR, "No date to measure against."
        elif days_left < 0 and status in _NOT_STARTED:
            state = PAST
            reason = (
                f"Nothing has been drafted and the date this needed to start by was "
                f"{abs(days_left)} day(s) ago. Either scope comes out or the deadline moves — "
                "both are decisions rather than tasks."
            )
        elif days_left < 0:
            state = AT_RISK
            reason = (
                f"Work is under way but it is {abs(days_left)} day(s) past the date it needed to "
                "start. It can still make it if nothing else goes wrong."
            )
        elif days_left <= 2 and status in _NOT_STARTED:
            state = AT_RISK
            reason = f"Not started, and {days_left} day(s) from the point it has to be."
        elif not requirement.owner and blocking:
            state = AT_RISK
            reason = (
                "Mandatory and unowned. A requirement with no owner is the ordinary way one "
                "gets missed, and it cannot be scheduled at all."
            )
        else:
            state, reason = CLEAR, f"{days_left} day(s) of slack."

        path.items.append(
            PathItem(
                requirement_id=requirement.id,
                reference=requirement.reference,
                text=requirement.text,
                stakes=requirement.stakes,
                owner=requirement.owner,
                status=status,
                latest_start=latest_start,
                days_left=days_left,
                state=state,
                reason=reason,
                blocking=blocking,
            )
        )

    # Worst first, then most urgent, then mandatory ahead of scored: the top of
    # this list is the next conversation somebody has to have.
    order = {PAST: 0, AT_RISK: 1, CLEAR: 2}
    path.items.sort(
        key=lambda item: (
            order.get(item.state, 3),
            item.days_left if item.days_left is not None else 9999,
            0 if item.blocking else 1,
            item.reference,
        )
    )

    if not any(r.status == "open" for r in (rounds or [])):
        path.notes.append(
            "No review round is open, so this path assumes the draft goes straight to "
            "production. Open the rounds you intend to run and the dates move back to make "
            "room for them."
        )

    logger.info(
        "critical_path_built",
        submission=submission.isoformat(),
        items=len(path.items),
        past=sum(1 for i in path.items if i.state == PAST),
    )
    return path
