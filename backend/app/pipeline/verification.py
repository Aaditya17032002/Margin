"""The Verification Queue: everything that needs a person, in one place.

Margin produces several kinds of doubt, and until now each one lived where it
was produced — an unlocated citation on a findings tab, an unreached page in
the coverage ledger, a mandatory requirement awaiting sign-off in the response
trace, an answer an amendment invalidated on the amendments panel. A capture
manager with four days left does not tour six tabs looking for them.

So they are collected into one list, ordered by what it costs to be wrong:

``blocking``
    Wrong here and the bid can be lost outright — a mandatory requirement the
    response does not answer, a hard gate nobody has answered, an answer an
    amendment invalidated.
``important``
    Wrong here and a score suffers, or a claim in the analysis turns out to
    rest on nothing — an unlocated citation, an unverifiable mandatory check.
``routine``
    Worth a look before submission, not before lunch.

Every item says the same four things: what needs deciding, why a machine could
not decide it, where to go, and what happens if nobody does. An item nobody can
act on does not belong in a queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

BLOCKING = "blocking"
IMPORTANT = "important"
ROUTINE = "routine"

_ORDER = {BLOCKING: 0, IMPORTANT: 1, ROUTINE: 2}


@dataclass
class QueueItem:
    """One thing a person has to settle."""

    id: str
    kind: str
    severity: str
    title: str
    #: Why this could not be settled by a rule or a model. The queue is a list
    #: of admissions, and each one should say what the limit was.
    why: str
    #: What happens if nobody does anything.
    consequence: str
    #: Which workspace tab settles it.
    tab: str
    reference: str = ""
    citation: dict | None = None
    owner: str | None = None
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "why": self.why,
            "consequence": self.consequence,
            "tab": self.tab,
            "reference": self.reference,
            "citation": self.citation,
            "owner": self.owner,
            "detail": self.detail,
        }


def build(
    *,
    analysis,
    requirements: list,
    checks: list,
    questions: list | None = None,
    reviews: list | None = None,
    review_findings: list | None = None,
    contradictions: list | None = None,
) -> list[QueueItem]:
    """Collect every open question across the analysis."""
    items: list[QueueItem] = []
    items += _coverage(analysis)
    items += _ledger(analysis)
    items += _gates(analysis)
    items += _citations(analysis)
    items += _requirements(requirements)
    items += _checks(checks, {r.id: r for r in requirements})
    items += _questions(questions or [], analysis)
    items += _reviews(reviews or [], review_findings or [], analysis)
    items += _contradictions(contradictions or [])

    items.sort(key=lambda item: (_ORDER.get(item.severity, 3), item.reference or item.title))
    return items


def summarise(items: list[QueueItem]) -> dict:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.severity] = counts.get(item.severity, 0) + 1
    return {
        "total": len(items),
        "blocking": counts.get(BLOCKING, 0),
        "important": counts.get(IMPORTANT, 0),
        "routine": counts.get(ROUTINE, 0),
    }


# ── Sources ──────────────────────────────────────────────────────────────


def _coverage(analysis) -> list[QueueItem]:
    coverage = analysis.coverage or {}
    totals = coverage.get("totals") or {}
    items: list[QueueItem] = []

    for document in coverage.get("documents") or []:
        if document.get("state") == "no_text":
            items.append(
                QueueItem(
                    id=f"coverage:no_text:{document.get('documentId', '')}",
                    kind="coverage",
                    severity=BLOCKING,
                    title=f"{document.get('name', 'A document')} produced no readable text",
                    why="Extraction returned nothing — almost always a scan with no text layer.",
                    consequence=(
                        "Nothing in this document was read, so no requirement in it exists "
                        "anywhere in this analysis."
                    ),
                    tab="coverage",
                    detail="Supply an OCR'd copy or a text version and run the analysis again.",
                )
            )
        elif document.get("chunksUnreached"):
            spans = ", ".join(
                str(start) if start == end else f"{start}–{end}"
                for start, end in (document.get("unreachedPages") or [])
            )
            items.append(
                QueueItem(
                    id=f"coverage:unreached:{document.get('documentId', '')}",
                    kind="coverage",
                    severity=IMPORTANT,
                    title=f"{document.get('name', 'A document')} has pages no pass reached",
                    why="Neither the pattern sweep nor a specialist read this text.",
                    consequence="Any requirement stated on these pages is missing from the ledger.",
                    tab="coverage",
                    detail=f"Pages {spans}." if spans else "",
                )
            )

    if totals.get("chunksUnreached") and not items:
        items.append(
            QueueItem(
                id="coverage:unreached",
                kind="coverage",
                severity=IMPORTANT,
                title=f"{totals['chunksUnreached']} passages were not reached by any pass",
                why="Neither the pattern sweep nor a specialist read them.",
                consequence="Requirements stated in them are missing from the ledger.",
                tab="coverage",
            )
        )
    return items


def _ledger(analysis) -> list[QueueItem]:
    ledger = analysis.ledger or {}
    items: list[QueueItem] = []

    for reference in ledger.get("invalidated") or []:
        items.append(
            QueueItem(
                id=f"ledger:invalidated:{reference}",
                kind="amendment",
                severity=BLOCKING,
                title=f"An answer was written against wording that changed — {reference}",
                why="An amendment replaced the requirement this section answers.",
                consequence=(
                    "The response answers a clause that no longer exists. Nobody can tell "
                    "whether it still complies until someone reads the new wording."
                ),
                tab="amendments",
                reference=reference,
            )
        )

    for reference in ledger.get("removedWithWork") or []:
        items.append(
            QueueItem(
                id=f"ledger:removed:{reference}",
                kind="ledger",
                severity=IMPORTANT,
                title=f"Assigned work whose requirement is gone — {reference}",
                why="The latest read of the package no longer finds this requirement.",
                consequence=(
                    "Either an amendment removed it, in which case the work can stop, or "
                    "extraction missed it, in which case it cannot."
                ),
                tab="coverage",
                reference=reference,
            )
        )
    return items


def _gates(analysis) -> list[QueueItem]:
    items: list[QueueItem] = []
    for gate in analysis.gates or []:
        if gate.get("answer") not in (None, "", "unknown"):
            continue
        hard = gate.get("weight") == "hard"
        items.append(
            QueueItem(
                id=f"gate:{gate.get('id', gate.get('question', ''))[:60]}",
                kind="gate",
                severity=BLOCKING if hard else ROUTINE,
                title=gate.get("question", "An eligibility gate is unanswered"),
                why="Only your organisation knows the answer — it is not in the document.",
                consequence=(
                    "A hard gate you do not meet disqualifies the bid outright."
                    if hard
                    else "The bid/no-bid picture is incomplete without it."
                ),
                tab="go-no-go",
                citation=gate.get("citation"),
            )
        )
    return items


#: Sections of the analysis whose findings carry citations worth grounding.
_FINDING_SECTIONS = ("identity", "scope", "legal", "eligibility", "pricing", "post_award")


def _citations(analysis) -> list[QueueItem]:
    """Claims whose quote could not be found in the document.

    A finding with an unlocated citation is not necessarily wrong, but nothing
    in the package has been shown to support it — which is exactly the state a
    person has to resolve before it goes in front of a reviewer.
    """
    items: list[QueueItem] = []
    for section in _FINDING_SECTIONS:
        for finding in getattr(analysis, section, None) or []:
            citation = finding.get("citation") or {}
            if not citation.get("quote") or citation.get("located") is not False:
                continue
            items.append(
                QueueItem(
                    id=f"citation:{section}:{finding.get('id', finding.get('label', ''))[:60]}",
                    kind="citation",
                    severity=IMPORTANT if finding.get("stakes") == "disqualifying" else ROUTINE,
                    title=finding.get("label", "A finding cites text that could not be located"),
                    why="The quote behind this finding was not found anywhere in the package.",
                    consequence="The finding may be right, but nothing in the document has been shown to support it.",
                    tab=_TAB_FOR_SECTION.get(section, "overview"),
                    citation=citation,
                    detail=str(finding.get("value", ""))[:200],
                )
            )
    return items


_TAB_FOR_SECTION = {
    "identity": "overview",
    "scope": "scope",
    "legal": "legal",
    "eligibility": "evaluation",
    "pricing": "scope",
    "post_award": "scope",
}


def _requirements(requirements: list) -> list[QueueItem]:
    items: list[QueueItem] = []
    for requirement in requirements:
        if requirement.state != "open":
            continue
        if requirement.stakes == "disqualifying" and not requirement.owner:
            items.append(
                QueueItem(
                    id=f"requirement:unowned:{requirement.key}",
                    kind="requirement",
                    severity=IMPORTANT,
                    title=f"Nobody owns a mandatory requirement — {requirement.reference}",
                    why="Ownership is a decision about your team, not something a document states.",
                    consequence="A mandatory requirement with no owner is the ordinary way one gets missed.",
                    tab="matrix",
                    reference=requirement.reference,
                    citation=requirement.citation,
                    detail=requirement.text[:200],
                )
            )
    return items


def _checks(checks: list, by_id: dict) -> list[QueueItem]:
    """A check names its clause through the requirement it was made against.

    The reference is never copied onto the check: an amendment can renumber a
    clause, and a record that kept a stale copy would send someone to a
    paragraph that no longer exists.
    """
    items: list[QueueItem] = []
    for check in checks:
        if check.confirmed_by:
            continue
        requirement = by_id.get(check.requirement_id)
        if requirement is not None and requirement.state != "open":
            # The clause was withdrawn or superseded. Whatever the check said
            # about it is history, and putting it in a worklist sends somebody
            # to answer a requirement that no longer exists.
            continue
        reference = requirement.reference if requirement else check.requirement_id

        if check.needs_confirmation:
            items.append(
                QueueItem(
                    id=f"check:confirm:{check.id}",
                    kind="response",
                    severity=IMPORTANT,
                    title=f"A mandatory requirement is answered but not signed off — {reference}",
                    why=(
                        "It was counted by a rule."
                        if check.decided_by == "rule"
                        else "A model read the response and thought it was answered."
                    )
                    + " Neither clears a mandatory requirement on its own.",
                    consequence="It will not be counted as settled, and will read as an open gap at submission.",
                    tab="response",
                    reference=reference,
                    owner=check.owner,
                    detail=check.detail[:200],
                )
            )
            continue

        # A verdict that was settled and has been undone is described as that,
        # whatever its risk. Filing it as "the response does not answer this"
        # would be wrong — somebody answered it, and something since then made
        # the answer unreliable.
        if any(e.get("event") == "reopened" for e in (check.history or [])):
            items.append(
                QueueItem(
                    id=f"check:reopened:{check.id}",
                    kind="response",
                    severity=BLOCKING if check.risk == "high" else IMPORTANT,
                    title=f"An answer was written and then reopened — {reference}",
                    why=check.detail[:200] or "Something changed after this was checked.",
                    consequence=(
                        "The section still exists, but nobody has confirmed it answers the "
                        "requirement as it now stands."
                    ),
                    tab="response",
                    reference=reference,
                    owner=check.owner,
                    detail=check.gap[:200],
                )
            )
            continue

        if check.risk == "high":
            items.append(
                QueueItem(
                    id=f"check:gap:{check.id}",
                    kind="response",
                    severity=BLOCKING,
                    title=f"The response does not answer a mandatory requirement — {reference}",
                    why="Nothing in the draft addresses it, or what is there does not comply.",
                    consequence="This is the kind of gap a proposal is rejected for.",
                    tab="response",
                    reference=reference,
                    owner=check.owner,
                    detail=(check.gap or check.detail)[:200],
                )
            )
        elif check.status == "unverifiable":
            items.append(
                QueueItem(
                    id=f"check:unverifiable:{check.id}",
                    kind="response",
                    severity=ROUTINE,
                    title=f"Could not be checked automatically — {reference}",
                    why=check.detail[:200] or "The check could not reach a conclusion.",
                    consequence=(
                        "It stays unresolved until a person looks, and unresolved is not compliant."
                    ),
                    tab="response",
                    reference=reference,
                    owner=check.owner,
                    detail=check.gap[:200],
                )
            )
    return items


def _questions(questions: list, analysis) -> list[QueueItem]:
    """Questions the agency has not answered, and the deadline that closes them.

    A question is not finished when it is sent. One that materially affects the
    bid and was never answered is a decision made on an assumption — and once
    the cut-off passes, it is an assumption that can no longer be resolved by
    asking.
    """
    if not questions:
        return []

    items: list[QueueItem] = []
    cutoff = _questions_due(analysis)
    past_cutoff = bool(cutoff and cutoff < datetime.now(UTC))

    drafts = [q for q in questions if (getattr(q, "status", None) or "draft") == "draft"]
    unanswered = [q for q in questions if (getattr(q, "status", None) or "draft") == "submitted"]

    if drafts and past_cutoff:
        items.append(
            QueueItem(
                id="question:missed_cutoff",
                kind="question",
                severity=BLOCKING if any(q.go_no_go_impact for q in drafts) else IMPORTANT,
                title=f"{len(drafts)} question(s) were never sent, and the deadline has passed",
                why="The window for asking the agency closed while these were still drafts.",
                consequence=(
                    "Whatever they were going to resolve now has to be decided on an "
                    "assumption, and the assumption cannot be checked."
                ),
                tab="questions",
            )
        )
    elif drafts and cutoff:
        items.append(
            QueueItem(
                id="question:unsent",
                kind="question",
                severity=IMPORTANT if any(q.go_no_go_impact for q in drafts) else ROUTINE,
                title=f"{len(drafts)} question(s) drafted and not sent",
                why=f"Questions are due {cutoff.date().isoformat()}.",
                consequence="After that date the agency does not have to answer them.",
                tab="questions",
            )
        )

    for question in unanswered:
        if not question.go_no_go_impact:
            continue
        items.append(
            QueueItem(
                id=f"question:unanswered:{question.id}",
                kind="question",
                severity=BLOCKING if past_cutoff else IMPORTANT,
                title=f"A question that affects the bid decision has no answer — {question.text[:90]}",
                why=(
                    "It was sent and the agency has not answered."
                    + (" The question period has closed." if past_cutoff else "")
                ),
                consequence=(
                    "The decision this was meant to inform will be made without it."
                    if past_cutoff
                    else "Chase it, or plan for the answer not arriving."
                ),
                tab="questions",
                detail=(question.rationale or "")[:200],
            )
        )

    # An amendment usually carries the answers, and nothing here can tell which
    # paragraph answers which question.
    if unanswered and (analysis.amendments or []):
        latest = (analysis.amendments or [])[-1]
        items.append(
            QueueItem(
                id="question:check_amendment",
                kind="question",
                severity=ROUTINE,
                title=(
                    f"{len(unanswered)} question(s) are still open and "
                    f"{latest.get('label', 'an amendment')} has landed"
                ),
                why=(
                    "Agencies usually publish Q&A answers with an amendment, and Margin cannot "
                    "tell which paragraph answers which question."
                ),
                consequence=(
                    "An answer that arrived and was never recorded changes nothing: work done "
                    "against the old reading stays marked as done."
                ),
                tab="questions",
            )
        )
    return items


def _questions_due(analysis) -> datetime | None:
    """The date the agency stops accepting questions."""
    for date in analysis.dates or []:
        if str(date.get("kind")) != "questions-due":
            continue
        raw = str(date.get("at") or "")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _reviews(rounds: list, findings: list, analysis) -> list[QueueItem]:
    """What the review rounds left open, and what they reviewed.

    Two things belong in a worklist. A must-fix finding nobody has resolved is
    the plainest kind of outstanding work there is. And a round that reviewed
    an earlier draft has stopped saying anything about the one about to be
    sent — a Red Team on draft 2 is not a Red Team on draft 4, and a closed
    round quietly ageing out is exactly how a team believes it has been
    reviewed when it has not.
    """
    if not rounds:
        return []

    items: list[QueueItem] = []
    current = int((analysis.response or {}).get("version") or 0)
    by_round = {r.id: r for r in rounds}

    for finding in findings:
        if finding.state != "open" or finding.severity != "must_fix":
            continue
        round_row = by_round.get(finding.round_id)
        colour = (round_row.colour if round_row else "review").replace("_", " ")
        items.append(
            QueueItem(
                id=f"review:finding:{finding.id}",
                kind="review",
                severity=BLOCKING,
                title=f"{colour.title()} review must-fix: {finding.text[:90]}",
                why=f"Raised by {finding.raised_by or 'a reviewer'} and not resolved.",
                consequence="The round it belongs to cannot be signed off while it is open.",
                tab="reviews",
                reference=finding.location or "",
                owner=finding.raised_by or None,
                detail=finding.text[:200],
            )
        )

    for round_row in rounds:
        if round_row.status == "open":
            open_findings = [
                f for f in findings if f.round_id == round_row.id and f.state == "open"
            ]
            items.append(
                QueueItem(
                    id=f"review:open:{round_row.id}",
                    kind="review",
                    severity=ROUTINE,
                    title=f"{round_row.colour.replace('_', ' ').title()} review is still open",
                    why=f"{len(open_findings)} finding(s) unresolved; nobody has signed it off.",
                    consequence="An unsigned round is not a review that happened.",
                    tab="reviews",
                )
            )
        elif current and round_row.response_version and round_row.response_version < current:
            items.append(
                QueueItem(
                    id=f"review:stale:{round_row.id}",
                    kind="review",
                    severity=IMPORTANT,
                    title=(
                        f"The {round_row.colour.replace('_', ' ')} review covered draft "
                        f"{round_row.response_version}, and the current draft is {current}"
                    ),
                    why="A round says something about the draft it read and nothing about a later one.",
                    consequence=(
                        "The team believes this has been reviewed. What has been reviewed is a "
                        "version that is no longer being sent."
                    ),
                    tab="reviews",
                )
            )
    return items


def _contradictions(rows: list) -> list[QueueItem]:
    """Requirements that cannot both be met.

    This is the one kind of item where the product has read the document
    correctly and the document is the problem. Nothing downstream can resolve
    it: the compliance matrix will show both clauses as live work, the response
    check will judge the answer against whichever one it was given, and both
    will look right.
    """
    items: list[QueueItem] = []
    for row in rows:
        if row.state != "open":
            continue
        items.append(
            QueueItem(
                id=f"contradiction:{row.id}",
                kind="contradiction",
                severity=BLOCKING if row.severity == "blocking" else IMPORTANT,
                title=row.summary[:200],
                why=(
                    "Both clauses were extracted correctly. They disagree with each other, and "
                    "no amount of reading the response can settle which one the team has to "
                    "meet."
                ),
                consequence=(
                    "Whichever clause somebody happened to read is the one being written to, "
                    "and the other is a compliance failure nobody is looking at."
                ),
                tab="contradictions",
                detail=row.rationale[:200],
            )
        )
    return items
