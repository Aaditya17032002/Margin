"""Reading the review rounds against each other.

One round is a list of findings. Three rounds are an argument about whether the
proposal is getting better, and nothing in a per-round view answers it. The
questions a capture lead actually asks between Pink and Gold are:

*Did the last round's findings get fixed, or did they get closed?* A round
whose must-fix findings were all "accepted" rather than "fixed" reads as a pass
and is a deferral.

*Is anything coming back?* A requirement raised in Pink, marked fixed, and
raised again in Red is the single most useful signal a review programme
produces — it means the fix did not hold, and it is invisible unless the rounds
are compared.

*Does the sign-off still cover the draft?* A Red Team verdict on draft 2 says
nothing about draft 4. The round does not become wrong; it becomes stale, and
those are different words with different remedies.

Everything here is derived. A stored comparison would need reconciling with the
rounds it summarises, and the two would eventually disagree — at which point
the report is worse than not having one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger()

MUST_FIX = "must_fix"
SEVERITIES = ("must_fix", "should_fix", "consider")
STATES = ("open", "fixed", "accepted", "rejected")

#: Ordering for the narrative, worst first.
VERDICT_RANK = {"do_not_proceed": 0, "proceed_with_fixes": 1, "proceed": 2}


@dataclass
class RoundReport:
    round_id: str
    colour: str
    response_version: int
    status: str
    verdict: str | None
    opened_at: str
    closed_at: str | None
    reviewers: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    open_must_fix: int = 0
    #: Closed over its own open must-fix findings, with a written reason.
    overridden: bool = False
    override_reason: str | None = None
    #: True when a newer draft exists than the one this round read.
    stale: bool = False
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "roundId": self.round_id,
            "colour": self.colour,
            "responseVersion": self.response_version,
            "status": self.status,
            "verdict": self.verdict,
            "openedAt": self.opened_at,
            "closedAt": self.closed_at,
            "reviewers": self.reviewers,
            "counts": self.counts,
            "openMustFix": self.open_must_fix,
            "overridden": self.overridden,
            "overrideReason": self.override_reason,
            "stale": self.stale,
            "note": self.note,
        }


def _sort_key(row) -> tuple:
    opened = getattr(row, "opened_at", None)
    return (getattr(row, "response_version", 0), opened.isoformat() if opened else "")


def _counts(findings: list) -> dict:
    out = {
        "total": len(findings),
        "bySeverity": {s: 0 for s in SEVERITIES},
        "byState": {s: 0 for s in STATES},
        # Fixed versus accepted is the distinction the whole report turns on: a
        # round whose must-fix findings were accepted rather than fixed reads
        # as a pass and is a deferral.
        "mustFixFixed": 0,
        "mustFixAccepted": 0,
    }
    for finding in findings:
        severity = getattr(finding, "severity", "should_fix")
        state = getattr(finding, "state", "open")
        if severity in out["bySeverity"]:
            out["bySeverity"][severity] += 1
        if state in out["byState"]:
            out["byState"][state] += 1
        if severity == MUST_FIX and state == "fixed":
            out["mustFixFixed"] += 1
        if severity == MUST_FIX and state == "accepted":
            out["mustFixAccepted"] += 1
    return out


def _note(report: RoundReport) -> str:
    if report.status == "open":
        if report.open_must_fix:
            return (
                f"Open, with {report.open_must_fix} must-fix finding(s) outstanding. It cannot be "
                "signed off until they are resolved or the sign-off is recorded as an override."
            )
        return "Open, with nothing must-fix outstanding."
    if report.overridden:
        return (
            f"Closed as {report.verdict} over {report.open_must_fix} open must-fix finding(s). "
            "Recorded as an override, not as a pass."
        )
    accepted = report.counts.get("mustFixAccepted", 0)
    if accepted:
        return (
            f"Closed as {report.verdict}, but {accepted} must-fix finding(s) were accepted rather "
            "than fixed. Those are deferrals, and the next round will meet them again."
        )
    if report.stale:
        return (
            f"Closed as {report.verdict} against draft {report.response_version}, which is no "
            "longer the current draft. The verdict is not wrong; it no longer covers what is "
            "about to be submitted."
        )
    return f"Closed as {report.verdict}."


def build(rounds: list, findings: list, *, current_version: int = 0) -> dict:
    """The rounds read against each other, oldest first."""
    by_round: dict[str, list] = {}
    for finding in findings:
        by_round.setdefault(getattr(finding, "round_id", ""), []).append(finding)

    ordered = sorted(rounds, key=_sort_key)
    reports: list[RoundReport] = []
    for row in ordered:
        mine = by_round.get(row.id, [])
        opened = getattr(row, "opened_at", None)
        closed = getattr(row, "closed_at", None)
        report = RoundReport(
            round_id=row.id,
            colour=getattr(row, "colour", "red"),
            response_version=getattr(row, "response_version", 0),
            status=getattr(row, "status", "open"),
            verdict=getattr(row, "verdict", None),
            opened_at=opened.isoformat() if opened else "",
            closed_at=closed.isoformat() if closed else None,
            reviewers=list(getattr(row, "reviewers", []) or []),
            counts=_counts(mine),
            open_must_fix=sum(
                1
                for f in mine
                if getattr(f, "severity", "") == MUST_FIX and getattr(f, "state", "") == "open"
            ),
            overridden=bool(getattr(row, "override_reason", None)),
            override_reason=getattr(row, "override_reason", None),
            stale=bool(current_version and getattr(row, "response_version", 0) < current_version),
        )
        report.note = _note(report)
        reports.append(report)

    recurring = _recurring(ordered, by_round)
    carried = _carried(ordered, by_round)

    result = {
        "rounds": [r.as_dict() for r in reports],
        "recurring": recurring,
        "carried": carried,
        "reviewers": _reviewers(ordered, by_round),
        "trend": _trend(reports),
        "currentVersion": current_version,
    }
    logger.info(
        "review_comparison_built",
        rounds=len(reports),
        recurring=len(recurring),
        carried=len(carried),
    )
    return result


def _recurring(ordered: list, by_round: dict[str, list]) -> list[dict]:
    """Findings that came back after somebody said they were fixed.

    Matched on the requirement rather than on the wording: two reviewers
    describe the same defect in different sentences, and a text match would
    report nothing while the same clause failed three rounds running. Findings
    with no requirement attached are not matched at all — guessing at which
    prose comment is "the same" as another produces a list nobody trusts.
    """
    seen_fixed: dict[str, dict] = {}
    out: list[dict] = []

    for row in ordered:
        for finding in by_round.get(row.id, []):
            requirement_id = getattr(finding, "requirement_id", None)
            if not requirement_id:
                continue
            earlier = seen_fixed.get(requirement_id)
            if earlier and earlier["round_id"] != row.id:
                out.append(
                    {
                        "requirementId": requirement_id,
                        "firstRoundId": earlier["round_id"],
                        "firstColour": earlier["colour"],
                        "firstText": earlier["text"],
                        "againRoundId": row.id,
                        "againColour": getattr(row, "colour", ""),
                        "againText": getattr(finding, "text", ""),
                        "severity": getattr(finding, "severity", ""),
                        "why": (
                            f"Raised in the {earlier['colour']} round, marked "
                            f"{earlier['state']}, and raised again in the "
                            f"{getattr(row, 'colour', '')} round. The fix did not hold."
                        ),
                    }
                )
            if getattr(finding, "state", "") in ("fixed", "accepted"):
                seen_fixed[requirement_id] = {
                    "round_id": row.id,
                    "colour": getattr(row, "colour", ""),
                    "text": getattr(finding, "text", ""),
                    "state": getattr(finding, "state", ""),
                }
    return out


def _carried(ordered: list, by_round: dict[str, list]) -> list[dict]:
    """Must-fix findings still open from a round that has already closed.

    The quietest failure a review programme has: the round is closed, so it
    stops being looked at, and the finding stays open forever in a list nobody
    opens.
    """
    out: list[dict] = []
    for row in ordered:
        if getattr(row, "status", "") != "closed":
            continue
        for finding in by_round.get(row.id, []):
            if getattr(finding, "severity", "") != MUST_FIX:
                continue
            if getattr(finding, "state", "") != "open":
                continue
            out.append(
                {
                    "findingId": finding.id,
                    "roundId": row.id,
                    "colour": getattr(row, "colour", ""),
                    "text": getattr(finding, "text", ""),
                    "location": getattr(finding, "location", "") or "",
                    "requirementId": getattr(finding, "requirement_id", None),
                    "why": (
                        f"The {getattr(row, 'colour', '')} round closed with this must-fix "
                        "finding still open. A closed round stops being looked at, so nothing "
                        "will raise it again."
                    ),
                }
            )
    return out


def _reviewers(ordered: list, by_round: dict[str, list]) -> list[dict]:
    """Who reviewed, and whether they found anything.

    A reviewer named on three rounds who raised nothing is worth knowing about
    — not as a performance measure, but because a round nobody actually read is
    a sign-off with nothing behind it.
    """
    tally: dict[str, dict] = {}
    for row in ordered:
        for reviewer in getattr(row, "reviewers", []) or []:
            entry = tally.setdefault(reviewer, {"reviewer": reviewer, "rounds": 0, "raised": 0})
            entry["rounds"] += 1
        for finding in by_round.get(row.id, []):
            raised_by = getattr(finding, "raised_by", "")
            if not raised_by:
                continue
            entry = tally.setdefault(raised_by, {"reviewer": raised_by, "rounds": 0, "raised": 0})
            entry["raised"] += 1
    return sorted(tally.values(), key=lambda e: (-e["raised"], e["reviewer"]))


def _trend(reports: list[RoundReport]) -> dict:
    """Is it getting better, and does the sign-off still stand?"""
    closed = [r for r in reports if r.status == "closed"]
    if not closed:
        return {
            "direction": "unknown",
            "detail": "No round has closed yet, so there is nothing to compare.",
        }

    first, last = closed[0], closed[-1]
    first_must = first.counts["bySeverity"].get(MUST_FIX, 0)
    last_must = last.counts["bySeverity"].get(MUST_FIX, 0)

    if len(closed) == 1:
        direction = "single"
        detail = (
            f"One closed round ({first.colour}), with {first_must} must-fix finding(s). A second "
            "round is what makes the first one measurable."
        )
    elif last_must < first_must:
        direction = "improving"
        detail = (
            f"Must-fix findings fell from {first_must} in the {first.colour} round to "
            f"{last_must} in the {last.colour} round."
        )
    elif last_must > first_must:
        direction = "worsening"
        detail = (
            f"Must-fix findings rose from {first_must} in the {first.colour} round to "
            f"{last_must} in the {last.colour} round. A later round finding more than an "
            "earlier one usually means the draft grew faster than it was fixed."
        )
    else:
        direction = "flat"
        detail = (
            f"The same number of must-fix findings ({last_must}) in the {first.colour} and "
            f"{last.colour} rounds."
        )

    worst = min(
        (r for r in closed if r.verdict), key=lambda r: VERDICT_RANK.get(r.verdict or "", 3),
        default=None,
    )
    return {
        "direction": direction,
        "detail": detail,
        "roundsClosed": len(closed),
        "worstVerdict": worst.verdict if worst else None,
        "overrides": sum(1 for r in closed if r.overridden),
        "stale": sum(1 for r in closed if r.stale),
    }
