"""Matching what a solicitation asks for against what the organisation has done.

Two matchers, both deterministic, both scoring on evidence a person can check.

The past performance matcher answers the question every solicitation asks in
Section L and every team answers from memory: *which of our contracts is
relevant here?* It scores agency, scope, capabilities, value, recency and NAICS
separately and reports each, because "this one matches" is an assertion and
"this one is for the same agency, in the same NAICS, and ended eight months
ago" is a case somebody can make in a proposal.

The content matcher answers the other one: *have we written this before?* It
never suggests text on similarity alone. A block is offered with what happened
to it — the requirement it answered, whether it was verified, whether that bid
was won, when it was last used — because that context is the whole difference
between a library and a pile of paragraphs. A block that has been retired is
never offered at all.

Neither ranks by a single number without showing the parts. A score somebody
cannot argue with is a score somebody stops reading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.core.logging import get_logger
from app.pipeline.anchor import normalize

logger = get_logger()

#: Below this a past performance record shares vocabulary with the requirement
#: and nothing else.
RELEVANCE_FLOOR = 0.18

#: Contracts older than this are usually outside a solicitation's recency
#: window. Not a hard filter — it is reported as an age, because the window
#: varies and the team knows theirs.
TYPICAL_RECENCY_YEARS = 3

_NOISE = frozenset(
    """the a an of and or to in on at by for with from into any all such other than that this
    these those shall must will may not be is are contractor offeror government proposal
    response section volume page provide provides submit submitted include included describe
    description services service work support system systems""".split()
)


def _terms(text: str) -> set[str]:
    return {word for word in normalize(text or "").split() if word not in _NOISE and len(word) > 3}


# ── Past performance ─────────────────────────────────────────────────────


@dataclass
class Relevance:
    """Why one contract is or is not relevant to this solicitation."""

    record_id: str
    title: str
    score: float
    #: Each signal, separately, so a proposal can make the case rather than
    #: assert a number.
    signals: dict = field(default_factory=dict)
    concerns: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "recordId": self.record_id,
            "title": self.title,
            "score": round(self.score, 4),
            "signals": self.signals,
            "concerns": self.concerns,
        }


def _years_since(when: date | None) -> float | None:
    if not when:
        return None
    return (date.today() - when).days / 365.25


def relevance(record, *, requirement_text: str, agency: str = "", naics: str = "",
              value: float = 0.0) -> Relevance:
    """How relevant one contract is, and on what evidence."""
    signals: dict = {}
    concerns: list[str] = []
    score = 0.0

    wanted = _terms(requirement_text)
    have = _terms(f"{record.scope} {record.title} {' '.join(record.capabilities or [])}")
    overlap = len(wanted & have) / len(wanted) if wanted else 0.0
    if overlap:
        signals["scope"] = {
            "score": round(overlap, 3),
            "shared": sorted(wanted & have)[:6],
        }
        score += overlap * 0.45

    if agency and record.agency and normalize(agency) == normalize(record.agency):
        signals["agency"] = {"score": 1.0, "detail": f"Same customer: {record.agency}."}
        score += 0.2
    elif agency and record.agency and (
        _terms(agency) & _terms(record.agency)
    ):
        signals["agency"] = {"score": 0.5, "detail": f"Related customer: {record.agency}."}
        score += 0.1

    if naics and record.naics and naics.strip() == record.naics.strip():
        signals["naics"] = {"score": 1.0, "detail": f"Same NAICS {record.naics}."}
        score += 0.1

    age = _years_since(record.ended_at if not record.ongoing else date.today())
    if record.ongoing:
        signals["recency"] = {"score": 1.0, "detail": "Currently running."}
        score += 0.15
    elif age is not None:
        recency = max(0.0, 1.0 - (age / (TYPICAL_RECENCY_YEARS * 2)))
        signals["recency"] = {"score": round(recency, 3), "detail": f"Ended {age:.1f} years ago."}
        score += recency * 0.15
        if age > TYPICAL_RECENCY_YEARS:
            concerns.append(
                f"Ended {age:.1f} years ago, which is outside the recency window most "
                "solicitations state. Check this one's."
            )

    if value and record.value:
        ratio = min(record.value, value) / max(record.value, value)
        signals["value"] = {
            "score": round(ratio, 3),
            "detail": f"${record.value:,.0f} against an estimated ${value:,.0f}.",
        }
        score += ratio * 0.1
        if ratio < 0.2:
            concerns.append(
                "An order of magnitude apart in value. Evaluators read 'comparable scope' as "
                "including size."
            )

    if not record.reference_name:
        concerns.append("No reference recorded. Most past performance forms require one.")
    elif record.reference_checked_at:
        stale = _years_since(record.reference_checked_at)
        if stale and stale > 1:
            concerns.append(
                f"The reference was last confirmed {stale:.1f} years ago. A reference who has "
                "moved on fails at the worst possible time."
            )
    else:
        concerns.append("Nobody has confirmed this reference is still willing.")

    return Relevance(
        record_id=record.id, title=record.title, score=min(1.0, score),
        signals=signals, concerns=concerns,
    )


def match_past_performance(
    records: list, *, requirement_text: str, agency: str = "", naics: str = "",
    value: float = 0.0, limit: int = 5,
) -> list[Relevance]:
    scored = [
        relevance(record, requirement_text=requirement_text, agency=agency, naics=naics, value=value)
        for record in records
    ]
    kept = [item for item in scored if item.score >= RELEVANCE_FLOOR]
    kept.sort(key=lambda item: (-item.score, item.title))
    logger.info("past_performance_matched", considered=len(records), returned=len(kept[:limit]))
    return kept[:limit]


# ── Content blocks ───────────────────────────────────────────────────────


@dataclass
class Suggestion:
    """A block that answered something like this before, and what happened."""

    block_id: str
    title: str
    text: str
    score: float
    #: The sentence that makes this worth offering rather than just similar.
    provenance: str
    #: Reasons to read it before using it.
    cautions: list[str] = field(default_factory=list)
    outcome: str = "unknown"
    verified_by: str | None = None
    times_used: int = 0

    def as_dict(self) -> dict:
        return {
            "blockId": self.block_id,
            "title": self.title,
            "text": self.text,
            "score": round(self.score, 4),
            "provenance": self.provenance,
            "cautions": self.cautions,
            "outcome": self.outcome,
            "verifiedBy": self.verified_by,
            "timesUsed": self.times_used,
        }


_OUTCOME_WORDS = {
    "won": "that bid was won",
    "lost": "that bid was lost",
    "no_award": "no award was made",
    "withdrawn": "the bid was withdrawn",
    "unknown": "the outcome was never recorded",
}


def suggest(blocks: list, requirement, *, limit: int = 4) -> list[Suggestion]:
    """Blocks that answered something like this requirement before.

    Filtered by requirement kind first: a page-limit block is never offered for
    a narrative requirement, however much vocabulary they share. Retired blocks
    are never offered at all — a block somebody marked as no longer true is
    exactly the text that must not resurface at 2am.
    """
    kind = getattr(requirement, "kind", "obligation")
    wanted = _terms(getattr(requirement, "text", ""))
    if not wanted:
        return []

    out: list[Suggestion] = []
    for block in blocks:
        if block.retired_at is not None:
            continue
        if block.requirement_kind and block.requirement_kind != kind:
            continue
        have = _terms(f"{block.source_requirement} {block.title} {' '.join(block.tags or [])}")
        if not have:
            continue
        score = len(wanted & have) / len(wanted)
        if score < RELEVANCE_FLOOR:
            continue

        out.append(
            Suggestion(
                block_id=block.id,
                title=block.title or block.source_reference or "Untitled block",
                text=block.text,
                score=score,
                provenance=_provenance(block),
                cautions=_cautions(block),
                outcome=block.outcome,
                verified_by=block.verified_by,
                times_used=block.times_used,
            )
        )

    out.sort(key=lambda item: (-item.score, -item.times_used))
    logger.info("content_suggested", considered=len(blocks), returned=len(out[:limit]))
    return out[:limit]


def _provenance(block) -> str:
    """Where it came from, in one sentence somebody can act on."""
    parts = []
    if block.source_reference and block.source_solicitation:
        parts.append(f"Answered {block.source_reference} on {block.source_solicitation}")
    elif block.source_solicitation:
        parts.append(f"Written for {block.source_solicitation}")
    else:
        parts.append("No source recorded")
    if block.source_agency:
        parts.append(f"for {block.source_agency}")
    parts.append(f"— {_OUTCOME_WORDS.get(block.outcome, 'the outcome was never recorded')}")
    if block.verified_by:
        parts.append(f", and {block.verified_by} verified it as {block.last_verdict or 'answered'}")
    return " ".join(parts) + "."


def _cautions(block) -> list[str]:
    """Reasons to read it before using it.

    The point of the library is that it hands over context, not text. A block
    nobody ever verified, from a bid that lost, that has not been touched in
    two years is still worth offering — and it is worth saying all three
    things.
    """
    cautions: list[str] = []
    if not block.verified_by:
        cautions.append("Nobody ever verified this answered the requirement it was written for.")
    if block.outcome == "lost":
        cautions.append(
            "The bid it was written for was lost. Most losses have nothing to do with any one "
            "paragraph, but it has not been shown to work."
        )
    if block.last_used_at:
        age = (datetime.now(UTC) - block.last_used_at).days / 365.25
        if age > 2:
            cautions.append(
                f"Last used {age:.1f} years ago. Check that it still describes how the company "
                "actually works."
            )
    elif block.times_used == 0:
        cautions.append("This has never been used in a submitted response.")
    return cautions
