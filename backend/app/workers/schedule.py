"""The pursuit calendar for an analysis.

A solicitation prints two or three dates. A capture team works to a dozen: the
intent notice, the question deadline, the day answers come back, the internal
solution and draft reviews, production, submission, orals, award. Margin reads
the document, and then lays the rest of the calendar out around what it read —
so a person opening the deadlines view on the day a document lands sees the
whole run of the pursuit, not one date in three weeks' time.

Two rules keep this honest:

* Every milestone says where it came from. ``source: "document"`` means the
  date is printed in the solicitation and carries the clause it came from;
  ``source: "derived"`` means Margin placed it, and it has no citation because
  there is nothing to cite.
* A derived milestone is never invented out of nothing. Without a date in the
  document to anchor to, the calendar is whatever the document gave and no more.

The calendar is built regardless of the bid decision. Deciding not to bid is a
decision a team makes *because* they can see the dates, so the dates cannot
wait on the decision.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger

logger = get_logger()

# Every stage a pursuit passes through, in the order it happens. `kind` is the
# stable identifier the API and the workspace share.
KINDS = (
    "intent-due",
    "questions-due",
    "answers-expected",
    "site-visit",
    "solution-review",
    "draft-review",
    "final-review",
    "proposal-due",
    "orals",
    "award",
    "start",
    "amendment",
)

KIND_LABELS = {
    "intent-due": "Notice of intent due",
    "questions-due": "Written questions due",
    "answers-expected": "Agency answers expected",
    "site-visit": "Site visit",
    "solution-review": "Solution review (internal)",
    "draft-review": "Draft review (internal)",
    "final-review": "Final production and sign-off",
    "proposal-due": "Proposal due",
    "orals": "Oral presentations",
    "award": "Award expected",
    "start": "Period of performance starts",
    "amendment": "Amendment issued",
}


@dataclass(frozen=True)
class Derived:
    kind: str
    #: Days relative to the submission deadline. Negative is before.
    offset_days: int


# The shape of a normal pursuit, measured backwards from the submission date.
# These are placeholders a capture lead moves; they exist so the calendar has
# the right *shape* on day one rather than one lonely entry.
DERIVED_SCHEDULE: tuple[Derived, ...] = (
    Derived("intent-due", -21),
    Derived("questions-due", -18),
    Derived("answers-expected", -11),
    Derived("solution-review", -14),
    Derived("draft-review", -7),
    Derived("final-review", -2),
    Derived("orals", 14),
    Derived("award", 45),
)

# A derived milestone that would land in the past, or after the deadline it was
# supposed to precede, is noise. Anything inside this window of "now" is kept
# anyway — a pursuit that starts late still has to do the work.
_MIN_LEAD = timedelta(days=0)

_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?")


def parse_when(raw: str) -> datetime | None:
    """A date from a model, parsed defensively. Anything unreadable is dropped
    rather than guessed at — a wrong deadline is worse than a missing one."""
    if not raw:
        return None
    match = _ISO.search(str(raw))
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    hour = int(match.group(4) or 0)
    minute = int(match.group(5) or 0)
    second = int(match.group(6) or 0)
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None


def _kind(raw: str, label: str) -> str:
    value = str(raw or "").strip().lower().replace(" ", "-").replace("_", "-")
    if value in KINDS:
        return value
    text = f"{value} {label}".lower()
    # Order matters: "questions due" and "answers to questions" both mention
    # questions, so the more specific reading has to be tried first.
    for needle, kind in (
        ("intent", "intent-due"),
        ("answer", "answers-expected"),
        ("question", "questions-due"),
        ("site visit", "site-visit"),
        ("pre-proposal", "site-visit"),
        ("oral", "orals"),
        ("demonstration", "orals"),
        ("interview", "orals"),
        ("amend", "amendment"),
        ("award", "award"),
        ("performance", "start"),
        ("kick", "start"),
        ("commence", "start"),
        ("due", "proposal-due"),
        ("submission", "proposal-due"),
        ("closing", "proposal-due"),
        ("deadline", "proposal-due"),
    ):
        if needle in text:
            return kind
    return "proposal-due"


def normalise_extracted(items: list[dict]) -> list[dict]:
    """Turn what the dates agent returned into key-date records."""
    dates: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        when = parse_when(str(item.get("at") or item.get("date") or ""))
        if when is None:
            continue
        label = str(item.get("label") or "").strip()
        kind = _kind(str(item.get("kind") or ""), label)
        dates.append(
            {
                "id": f"kd_{uuid.uuid4().hex[:8]}",
                "label": label or KIND_LABELS[kind],
                "at": when.isoformat(),
                "timezone": str(item.get("timezone") or "UTC")[:40],
                "kind": kind,
                "citation": item.get("citation"),
                "source": "document",
            }
        )
    return dates


def build_schedule(
    extracted: list[dict],
    *,
    now: datetime | None = None,
) -> list[dict]:
    """The full pursuit calendar: what the document said, plus the stages around it."""
    now = now or datetime.now(UTC)
    dates = normalise_extracted(extracted)

    anchor = _submission_anchor(dates)
    if anchor is None:
        logger.info("schedule_no_anchor", stated=len(dates))
        return sorted(dates, key=lambda d: d["at"])

    stated_kinds = {d["kind"] for d in dates}
    for step in DERIVED_SCHEDULE:
        if step.kind in stated_kinds:
            # The document named this one. Never place a guess beside a fact.
            continue
        when = anchor + timedelta(days=step.offset_days)
        if step.offset_days < 0 and when < now - _MIN_LEAD:
            # The window for this stage has already closed.
            continue
        dates.append(
            {
                "id": f"kd_{uuid.uuid4().hex[:8]}",
                "label": KIND_LABELS[step.kind],
                "at": when.isoformat(),
                "timezone": _anchor_timezone(dates),
                "kind": step.kind,
                "citation": None,
                "source": "derived",
            }
        )

    dates.sort(key=lambda d: d["at"])
    logger.info(
        "schedule_built",
        stated=sum(1 for d in dates if d["source"] == "document"),
        derived=sum(1 for d in dates if d["source"] == "derived"),
    )
    return dates


def _submission_anchor(dates: list[dict]) -> datetime | None:
    """The date everything else hangs off: the submission deadline if the
    document gave one, otherwise the last date it gave."""
    parsed = [(d, parse_when(d["at"])) for d in dates]
    due = [when for d, when in parsed if when and d["kind"] == "proposal-due"]
    if due:
        return max(due)
    others = [when for _, when in parsed if when]
    return max(others) if others else None


def _anchor_timezone(dates: list[dict]) -> str:
    for date in dates:
        if date["kind"] == "proposal-due" and date.get("timezone"):
            return str(date["timezone"])
    return dates[0].get("timezone", "UTC") if dates else "UTC"
