"""Tracing one requirement from the clause to the person who signed it off.

The full chain Margin can now answer for:

    requirement → the clause it was extracted from (document, page, quote)
      → the response section that answers it (document, page, section)
        → the claim that section makes
          → the evidence quoted for that claim
            → who verified it, when, and on what basis

The interesting part is what happens on the next draft. When a response is
revised, the naive behaviour is to check it again from scratch — which throws
away every signature and asks the team to re-verify a hundred requirements
because two sections changed. The opposite naive behaviour is to carry the
verdicts forward, which quietly asserts that somebody checked text they never
saw.

Neither is right. This module compares each requirement's evidence between two
drafts and decides:

``unchanged``
    The passage answering it is the same text. A human verdict carries forward,
    marked as carried — a signature on a page nobody re-read is worth being
    able to see.
``changed``
    The passage moved or was rewritten. Whatever was concluded about the old
    text is not a conclusion about the new text, and the verdict is dropped.
``lost``
    The new draft has nothing answering it at all. This is the dangerous one:
    a section that used to be there and is not, on a requirement somebody had
    already signed off.
``new``
    A requirement the previous draft was never checked against.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.pipeline.anchor import normalize

logger = get_logger()

UNCHANGED = "unchanged"
CHANGED = "changed"
LOST = "lost"
NEW = "new"

#: Below this the two passages are different text, whatever the diff tool
#: says. Chosen so reformatting and a typo fix carry forward and a rewritten
#: paragraph does not.
SAME_ENOUGH = 0.92


@dataclass
class Link:
    """What happened to one requirement's answer between two drafts."""

    requirement_id: str
    state: str
    previous_check_id: str | None
    #: Set when a human verdict from the previous draft can be carried.
    carry_verdict: bool = False
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "state": self.state,
            "previousCheckId": self.previous_check_id,
            "carryVerdict": self.carry_verdict,
            "detail": self.detail,
        }


def similarity(left: str, right: str) -> float:
    """Token overlap on normalised text.

    Same measure the amendment pairing uses, for the same reason: a number that
    is easy to reason about is worth more than one that is slightly better and
    impossible to explain when it decides that a signature carries forward.
    """
    a, b = set(normalize(left).split()), set(normalize(right).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compare(previous: list, current: list) -> list[Link]:
    """What each requirement's answer did between the two drafts.

    ``previous`` and ``current`` are ResponseCheck rows for two versions.
    """
    before = {check.requirement_id: check for check in previous}
    links: list[Link] = []

    for check in current:
        prior = before.pop(check.requirement_id, None)
        if prior is None:
            links.append(
                Link(check.requirement_id, NEW, None, detail="Not checked against the previous draft.")
            )
            continue

        old_quote = str((prior.evidence or {}).get("quote") or "")
        new_quote = str((check.evidence or {}).get("quote") or "")

        if not new_quote and old_quote:
            links.append(
                Link(
                    check.requirement_id,
                    LOST,
                    prior.id,
                    detail=(
                        "The previous draft had a passage answering this and the new one has "
                        "none. Either the section was cut, or it was rewritten past the point "
                        "where anything matches the requirement."
                    ),
                )
            )
            continue

        score = similarity(old_quote, new_quote)
        if score >= SAME_ENOUGH:
            # A person's verdict survives; a machine's is recomputed anyway, so
            # carrying it forward would only hide that it was.
            carry = bool(prior.confirmed_by) or prior.decided_by == "human"
            links.append(
                Link(
                    check.requirement_id,
                    UNCHANGED,
                    prior.id,
                    carry_verdict=carry,
                    detail=(
                        f"The passage answering this is unchanged ({score:.0%} the same)."
                        + (
                            f" {prior.confirmed_by or 'A reviewer'} signed it off against the "
                            "previous draft, and that carries."
                            if carry
                            else ""
                        )
                    ),
                )
            )
        else:
            links.append(
                Link(
                    check.requirement_id,
                    CHANGED,
                    prior.id,
                    detail=(
                        f"The passage answering this was rewritten ({score:.0%} the same). "
                        "Whatever was concluded about the old text is not a conclusion about "
                        "the new text."
                    ),
                )
            )

    # Anything left in `before` was answered in the old draft and is not in the
    # new set at all — usually because the requirement itself was superseded.
    for requirement_id, prior in before.items():
        links.append(
            Link(
                requirement_id,
                LOST,
                prior.id,
                detail="This requirement was checked against the previous draft and is not in this one.",
            )
        )

    counts: dict[str, int] = {}
    for link in links:
        counts[link.state] = counts.get(link.state, 0) + 1
    logger.info("lineage_compared", **{f"state_{k}": v for k, v in counts.items()})
    return links


def apply(links: list[Link], previous: list, current: list) -> dict:
    """Attach the lineage to this draft's checks, carrying what can be carried.

    Returns the summary a reviewer reads first: how much of the previous
    draft's verification still stands, and what stopped standing.
    """
    prior_by_id = {check.id: check for check in previous}
    current_by_requirement = {check.requirement_id: check for check in current}
    now = datetime.now(UTC)

    carried: list[str] = []
    invalidated: list[str] = []

    for link in links:
        check = current_by_requirement.get(link.requirement_id)
        if check is None:
            continue

        check.supersedes_id = link.previous_check_id
        check.lineage = {
            **(check.lineage or {}),
            "state": link.state,
            "detail": link.detail,
            "previousCheckId": link.previous_check_id,
            "comparedAt": now.isoformat(),
        }

        prior = prior_by_id.get(link.previous_check_id or "")
        if prior is None:
            continue

        if link.state == UNCHANGED and link.carry_verdict:
            # The passage is the same text, so the signature on it still means
            # something — and it is marked as carried, because a signature on a
            # page nobody re-read is worth being able to see.
            check.status = prior.status
            check.decided_by = prior.decided_by
            check.confirmed_by = prior.confirmed_by
            check.confirmed_at = prior.confirmed_at
            check.needs_confirmation = prior.needs_confirmation
            check.note = prior.note
            check.carried_verdict = True
            check.history = [
                *(check.history or []),
                {
                    "at": now.isoformat(),
                    "event": "carried",
                    "detail": (
                        f"Verdict carried from the previous draft: {link.detail} "
                        "The passage is unchanged, so the sign-off on it stands."
                    ),
                },
            ]
            carried.append(link.requirement_id)
        elif link.state in (CHANGED, LOST) and (prior.confirmed_by or prior.status == "satisfied"):
            check.history = [
                *(check.history or []),
                {
                    "at": now.isoformat(),
                    "event": "invalidated",
                    "detail": (
                        f"The previous draft was {prior.status}"
                        + (f", signed off by {prior.confirmed_by}" if prior.confirmed_by else "")
                        + f". {link.detail}"
                    ),
                },
            ]
            invalidated.append(link.requirement_id)

    summary = {
        "at": now.isoformat(),
        "carried": len(carried),
        "invalidated": len(invalidated),
        "counts": _counts(links),
        "lostReferences": [
            link.requirement_id for link in links if link.state == LOST
        ][:20],
    }
    logger.info("lineage_applied", carried=len(carried), invalidated=len(invalidated))
    return summary


def _counts(links: list[Link]) -> dict:
    counts: dict[str, int] = {}
    for link in links:
        counts[link.state] = counts.get(link.state, 0) + 1
    return counts


def trace(check, requirement) -> dict:
    """The full chain for one requirement, as a record rather than a join.

    Frozen into the check when it is written, so it still describes what was
    actually checked after the requirement is amended and the response is
    revised. A lineage that has to be reconstructed by joining live rows
    describes the present, which is the one thing an audit does not need.
    """
    evidence = check.evidence or {}
    citation = (requirement.citation if requirement else {}) or {}
    return {
        "requirementId": getattr(requirement, "id", "") or check.requirement_id,
        "requirementKey": getattr(requirement, "key", ""),
        # → the clause
        "clause": getattr(requirement, "reference", ""),
        "clauseDocument": citation.get("documentName", ""),
        "clausePage": citation.get("page", 0),
        "clauseQuote": citation.get("quote", ""),
        # → the response section
        "responseDocument": evidence.get("documentName", ""),
        "responsePage": evidence.get("page", 0),
        "responseSection": evidence.get("section", ""),
        # → the claim, and the evidence under it
        "claim": check.detail or "",
        "evidenceQuote": evidence.get("quote", ""),
        "evidenceLocated": bool(evidence.get("located", False)),
        # → who settled it
        "status": check.status,
        "decidedBy": check.decided_by,
        "rule": check.rule or "",
        "verifiedBy": check.confirmed_by,
        "verifiedAt": check.confirmed_at.isoformat() if check.confirmed_at else None,
        "carried": bool(getattr(check, "carried_verdict", False)),
    }
