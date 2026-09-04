"""Recording a judgement so it can be learned from later.

Called at the two places a person overrules or accepts something Margin
decided. It does one thing: freeze what both parties were looking at into a row
that will still make sense in a year.

`outcome` is derived rather than passed in, because whether a decision is a
correction is a property of the two verdicts and not something a caller should
be able to get wrong:

``confirmed``  the person agreed with the machine.
``corrected``  they reached a different conclusion.
``flagged``    they left a note without changing the verdict — usually "this is
               right but for the wrong reason", which is the most informative
               kind of feedback and the easiest kind to lose.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.verdict import CONFIRMED, CORRECTED, FLAGGED, Verdict

logger = get_logger()

#: Enough of the passage to see what the disagreement was about, without
#: copying a proposal into a second table.
_EXCERPT = 1200

#: How a person satisfied themselves. "Dana said this is satisfied" is a name
#: against an outcome; "Dana counted 38 pages in the rendered PDF" is evidence,
#: and only the second survives a debrief or makes a usable evaluation label.
_BASES = frozenset(
    {
        "read_the_document",
        "counted_in_the_file",
        "checked_with_the_agency",
        "team_knowledge",
        "prior_bid",
        "not_stated",
    }
)


def outcome_of(machine_status: str, human_status: str, note: str | None) -> str:
    if human_status and machine_status and human_status != machine_status:
        return CORRECTED
    if note and not (human_status and human_status != machine_status):
        return FLAGGED
    return CONFIRMED


async def record(
    db: AsyncSession,
    *,
    org_id: str,
    analysis_id: str,
    subject_kind: str,
    subject_id: str,
    machine_status: str = "",
    machine_decided_by: str = "",
    machine_rule: str = "",
    machine_detail: str = "",
    machine_evidence: dict | None = None,
    human_status: str = "",
    note: str | None = None,
    reference: str = "",
    requirement_text: str = "",
    stakes: str = "scored",
    verification: str = "substantive",
    response_excerpt: str = "",
    actor: str = "",
    basis: str = "not_stated",
    basis_detail: str = "",
    previous_verdict_id: str | None = None,
    response_version: int = 0,
) -> Verdict:
    outcome = outcome_of(machine_status, human_status, note)
    row = Verdict(
        id=f"vd_{uuid.uuid4().hex[:12]}",
        org_id=org_id,
        analysis_id=analysis_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        outcome=outcome,
        machine_status=machine_status or "",
        machine_decided_by=machine_decided_by or "",
        machine_rule=machine_rule or "",
        machine_detail=(machine_detail or "")[:2000],
        machine_evidence=machine_evidence or {},
        human_status=human_status or machine_status or "",
        note=note,
        reference=reference[:255],
        requirement_text=requirement_text or "",
        stakes=stakes or "scored",
        verification=verification or "substantive",
        response_excerpt=(response_excerpt or "")[:_EXCERPT],
        actor=actor or "",
        at=datetime.now(UTC),
        basis=basis if basis in _BASES else "not_stated",
        basis_detail=(basis_detail or "")[:1000],
        previous_verdict_id=previous_verdict_id,
        supersedes_verdict=bool(previous_verdict_id),
        response_version=response_version,
    )
    db.add(row)
    logger.info(
        "verdict_recorded",
        analysis_id=analysis_id,
        outcome=outcome,
        machine=machine_status,
        human=row.human_status,
        rule=machine_rule or None,
    )
    return row


def disagreement(rows: list[Verdict]) -> dict:
    """Where the machine and people disagree, and how much.

    Grouped by the things a fix can be aimed at — the rule that fired, whether
    a rule or a model decided, mechanical against substantive, and what the
    requirement costs. A single overall accuracy figure would say the product
    is 87% right and give nobody anywhere to start.
    """
    total = len(rows)
    corrected = [r for r in rows if r.outcome == CORRECTED]
    flagged = [r for r in rows if r.outcome == FLAGGED]

    def _group(key) -> list[dict]:
        seen: dict[str, dict] = {}
        for row in rows:
            name = key(row) or "—"
            bucket = seen.setdefault(name, {"name": name, "total": 0, "corrected": 0, "flagged": 0})
            bucket["total"] += 1
            if row.outcome == CORRECTED:
                bucket["corrected"] += 1
            elif row.outcome == FLAGGED:
                bucket["flagged"] += 1
        for bucket in seen.values():
            bucket["correctionRate"] = round(bucket["corrected"] / bucket["total"], 4)
        # Most corrected first, then most seen: the top of this list is where
        # the next hour of work belongs.
        return sorted(seen.values(), key=lambda b: (-b["corrected"], -b["total"]))

    #: Corrections *out of* a clearing verdict — the machine said answered and a
    #: person said it was not. These are the ones that would have shipped.
    dangerous = [
        r for r in corrected if r.machine_status == "satisfied" and r.human_status != "satisfied"
    ]

    # A verification with no stated basis is a name against an outcome. Worth
    # measuring: it is the difference between an audit trail and evidence.
    unstated = sum(1 for row in rows if (row.basis or "not_stated") == "not_stated")

    return {
        "total": total,
        "confirmed": total - len(corrected) - len(flagged),
        "withoutStatedBasis": unstated,
        "byBasis": _group(lambda r: r.basis or "not_stated"),
        "corrected": len(corrected),
        "flagged": len(flagged),
        "correctionRate": round(len(corrected) / total, 4) if total else 0.0,
        "wouldHaveShipped": len(dangerous),
        "byRule": _group(lambda r: r.machine_rule),
        "byDecider": _group(lambda r: r.machine_decided_by),
        "byVerification": _group(lambda r: r.verification),
        "byStakes": _group(lambda r: r.stakes),
        "transitions": _transitions(corrected),
    }


def _transitions(corrected: list[Verdict]) -> list[dict]:
    """Which way corrections go: `satisfied → failed` is a different problem
    from `unverifiable → satisfied`, and the second is mostly the product being
    too cautious rather than wrong."""
    seen: dict[tuple[str, str], int] = {}
    for row in corrected:
        key = (row.machine_status, row.human_status)
        seen[key] = seen.get(key, 0) + 1
    return sorted(
        ({"from": a, "to": b, "count": n} for (a, b), n in seen.items()),
        key=lambda t: -t["count"],
    )
