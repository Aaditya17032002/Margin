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
) -> list[QueueItem]:
    """Collect every open question across the analysis."""
    items: list[QueueItem] = []
    items += _coverage(analysis)
    items += _ledger(analysis)
    items += _gates(analysis)
    items += _citations(analysis)
    items += _requirements(requirements)
    items += _checks(checks, {r.id: r for r in requirements})

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
                    why=check.detail[:160] or "The check could not reach a conclusion.",
                    consequence="It stays unresolved until a person looks, and unresolved is not compliant.",
                    tab="response",
                    reference=reference,
                    owner=check.owner,
                    detail=check.gap[:200],
                )
            )
    return items
