"""What a change touches, and what it deliberately leaves alone.

Four things can change under a team mid-pursuit: an amendment lands, the agency
answers a question, somebody resolves a contradiction, or a new draft of the
response is bound. Each of them invalidates *some* of the work already done.

The two easy answers are both wrong, and both are what tools in this category
actually do.

Reopening everything is safe and useless. A hundred requirements go amber
because one clause moved, the team stops reading the amber, and the next real
change is invisible inside it. A worklist that cries wolf is a worklist people
learn to close.

Reopening nothing is what happens by default, and it is how a response ships
answering a clause that was withdrawn three weeks ago.

So a change names its origin and this module walks outward from it along
edges that actually exist:

    requirement → the response checks made against it
    requirement → the questions asked about it
    requirement → the contradictions it is half of
    requirement → the review findings raised against it
    requirement → the requirement it supersedes, and the one that supersedes it

Only what is reachable is touched. Everything else is left exactly as it was,
which is the point: a change that reopens twelve things is legible, and a
change that reopens four hundred is noise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.logging import get_logger

logger = get_logger()

#: Why something was reopened. Carried through to the record, because "this was
#: reopened" is much less useful than "this was reopened by Amendment 0002".
AMENDMENT = "amendment"
ANSWER = "agency answer"
CONTRADICTION = "contradiction resolution"
REVISION = "response revision"


@dataclass
class Impact:
    """One thing a change reached."""

    kind: str
    id: str
    reference: str
    reason: str
    #: True when the thing had already been settled and is now not.
    reopened: bool = False

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "id": self.id,
            "reference": self.reference,
            "reason": self.reason,
            "reopened": self.reopened,
        }


@dataclass
class Graph:
    """Everything hanging off a requirement, indexed once.

    Built from lists the caller already has rather than by querying per
    requirement: propagation runs inside a request, and a walk that issues a
    query per edge is a walk that times out on a large pursuit.
    """

    requirements: dict = field(default_factory=dict)
    checks_by_requirement: dict = field(default_factory=dict)
    questions_by_requirement: dict = field(default_factory=dict)
    findings_by_requirement: dict = field(default_factory=dict)
    contradictions_by_requirement: dict = field(default_factory=dict)
    #: requirement id → the requirement that superseded it, and vice versa.
    successor: dict = field(default_factory=dict)
    predecessor: dict = field(default_factory=dict)


def build_graph(
    *,
    requirements: list,
    checks: list | None = None,
    questions: list | None = None,
    findings: list | None = None,
    contradictions: list | None = None,
) -> Graph:
    graph = Graph(requirements={r.id: r for r in requirements})

    for check in checks or []:
        graph.checks_by_requirement.setdefault(check.requirement_id, []).append(check)
    for question in questions or []:
        if getattr(question, "requirement_id", None):
            graph.questions_by_requirement.setdefault(question.requirement_id, []).append(question)
    for finding in findings or []:
        if getattr(finding, "requirement_id", None):
            graph.findings_by_requirement.setdefault(finding.requirement_id, []).append(finding)
    for conflict in contradictions or []:
        for side in (conflict.left_id, conflict.right_id):
            graph.contradictions_by_requirement.setdefault(side, []).append(conflict)

    for requirement in requirements:
        if requirement.superseded_by_id:
            graph.successor[requirement.id] = requirement.superseded_by_id
        if requirement.supersedes_id:
            graph.predecessor[requirement.id] = requirement.supersedes_id

    return graph


def reachable(graph: Graph, origin_ids: list[str], *, follow_lineage: bool = True) -> set[str]:
    """Requirements a change at `origin_ids` can affect.

    Lineage is followed in both directions and nowhere else. A superseding
    requirement's answer was written for its predecessor, so a change to either
    reaches both; two requirements that merely sit in the same section have no
    edge between them and no business being reopened together.
    """
    seen: set[str] = set()
    frontier = [rid for rid in origin_ids if rid]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if not follow_lineage:
            continue
        for neighbour in (graph.successor.get(current), graph.predecessor.get(current)):
            if neighbour and neighbour not in seen:
                frontier.append(neighbour)
    return seen


def propagate(
    graph: Graph,
    origin_ids: list[str],
    *,
    cause: str,
    detail: str,
    at: datetime | None = None,
) -> list[Impact]:
    """Reopen what the change reached, and record why.

    Only settled work is reopened. Something already open, already a gap, or
    already being worked stays exactly as it is — a change log full of
    "reopened something that was never closed" is noise, and noise is what
    stops people reading it.
    """
    at = at or datetime.now(UTC)
    touched = reachable(graph, origin_ids)
    impacts: list[Impact] = []

    for requirement_id in sorted(touched):
        requirement = graph.requirements.get(requirement_id)
        reference = getattr(requirement, "reference", requirement_id)

        for check in graph.checks_by_requirement.get(requirement_id, []):
            if check.status != "satisfied" and not check.confirmed_by:
                continue
            check.status = "unverifiable"
            check.decided_by = "rule"
            check.needs_confirmation = False
            check.confirmed_by = None
            check.confirmed_at = None
            check.detail = f"Reopened by {cause}. {detail}"
            check.gap = "Re-read the change against what the response says."
            check.risk = (
                "high" if getattr(requirement, "stakes", "scored") == "disqualifying" else "medium"
            )
            check.history = [
                *(check.history or []),
                {"at": at.isoformat(), "event": "reopened", "detail": f"{cause}: {detail}"},
            ]
            impacts.append(
                Impact("response_check", check.id, reference, f"Reopened by {cause}.", reopened=True)
            )

        for finding in graph.findings_by_requirement.get(requirement_id, []):
            if finding.state == "open":
                continue
            # A reviewer's finding was resolved against wording that has moved.
            # Reopening it is right; silently leaving it closed is how a Red
            # Team finding gets buried by an amendment.
            finding.state = "open"
            finding.resolution = (
                f"{finding.resolution or ''} — reopened by {cause}: {detail}"
            ).strip(" —")
            finding.resolved_by = None
            finding.resolved_at = None
            impacts.append(
                Impact("review_finding", finding.id, reference, f"Reopened by {cause}.", reopened=True)
            )

        for question in graph.questions_by_requirement.get(requirement_id, []):
            # Questions are never reopened — an answer already given stays
            # given. They are reported so somebody can see that the clause
            # they asked about has moved underneath the answer.
            impacts.append(
                Impact(
                    "question",
                    question.id,
                    reference,
                    f"This question was about a clause {cause} changed.",
                )
            )

        for conflict in graph.contradictions_by_requirement.get(requirement_id, []):
            if conflict.state == "open":
                continue
            impacts.append(
                Impact(
                    "contradiction",
                    conflict.id,
                    reference,
                    f"A resolved conflict involved a clause {cause} changed.",
                )
            )

    logger.info(
        "change_propagated",
        cause=cause,
        origins=len(origin_ids),
        requirements=len(touched),
        reopened=sum(1 for i in impacts if i.reopened),
    )
    return impacts


def summarise(impacts: list[Impact], *, cause: str, considered: int) -> dict:
    """What the change touched, and what it did not.

    `untouched` is reported deliberately. The value of narrow propagation is
    invisible unless somebody can see how much was left alone — otherwise
    "reopened 4 things" and "reopened 4 of 300 things" read the same.
    """
    reopened = [i for i in impacts if i.reopened]
    return {
        "cause": cause,
        "reopened": len(reopened),
        "flagged": len(impacts) - len(reopened),
        "considered": considered,
        "untouched": max(0, considered - len({i.reference for i in impacts})),
        "items": [i.as_dict() for i in impacts[:100]],
    }
