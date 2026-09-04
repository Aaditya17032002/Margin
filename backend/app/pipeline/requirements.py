"""The Requirement Ledger: what the solicitation demands, with a stable name.

Before this module, every run of an analysis threw the compliance matrix away
and rebuilt it from the model's output. That is fine exactly once. On the
second run the rows are new objects with new ids, so an assignment made on
Tuesday attaches to a row that no longer exists on Wednesday, and an amendment
that reworded one clause looks like the whole document changed.

A requirement therefore needs an identity that is a property of the
requirement, not of the run that found it. That identity is derived from the
requirement's own words:

* Two runs over the same text produce the same key, so ownership, status and
  notes survive a re-read.
* A requirement that disappears between runs can be *reported* as gone rather
  than silently vanishing, which is what an amendment removing an obligation
  actually looks like.
* The compliance matrix stops being a separate list that happens to resemble
  the findings, and becomes a projection of this ledger.

Two other things are decided here, both deliberately in code rather than by a
model:

``verification``
    Whether a requirement can be checked by counting (a page limit, a font, a
    required form, a file name) or only by reading (an obligation to "provide
    a quality control plan"). Mechanical rules must never be judged by an LLM,
    so the split has to be made by a rule that can be read and argued with.

``stakes``
    Whether failing it removes you from the competition. Certifications,
    submission mechanics and explicit prohibitions are treated as
    disqualifying by default, because the cost of being wrong is asymmetric.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from app.pipeline.anchor import normalize
from app.pipeline.sweep import SweepHit

# ── Verification ─────────────────────────────────────────────────────────

MECHANICAL = "mechanical"
SUBSTANTIVE = "substantive"

#: Sweep categories that are countable by their nature. A page limit is a
#: number; a required form is present or it is not.
MECHANICAL_KINDS = frozenset({"limit", "form", "volume"})

#: A countable rule stated inside an ordinary obligation sentence — "Text shall
#: be 12-point Times New Roman" arrives as an obligation but is checked with a
#: ruler, not an opinion.
_MECHANICAL_MARKERS = re.compile(
    r"""(?ix)
    \b(?:
        \d+\s*(?:-\s*)?point                      # 12-point
      | (?:font|typeface|margins?|spacing)
      | (?:single|double)\s*-?\s*spaced
      | (?:page|word|character)\s+(?:limit|count)
      | (?:not\s+to\s+exceed|shall\s+not\s+exceed|must\s+not\s+exceed|no\s+more\s+than)
      | \d+\s*(?:MB|GB|KB)\b
      | file\s*names?|naming\s+convention|file\s+format
      | (?:PDF|DOCX|XLSX)\b
      | (?:separately\s+bound|separate\s+volume|separate\s+PDF|volume\s+[IVX0-9])
      | (?:signed|signature|wet\s+signature|initialled|initialed)
      | (?:copies|hard\s+cop(?:y|ies)|original)\b
      | (?:Standard\s+Form|SF-?\d+|Attachment\s+[A-Z]-?\d*|Exhibit\s+[A-Z])
    )\b
    """
)

# ── Stakes ───────────────────────────────────────────────────────────────

#: Categories where a miss is normally fatal rather than merely scored.
_DISQUALIFYING_KINDS = frozenset({"certification", "form", "limit", "volume"})

_DISQUALIFYING_MARKERS = re.compile(
    r"""(?ix)
    \b(?:
        (?:shall|will|may)\s+not\s+be\s+considered
      | deemed\s+non\s*-?\s*responsive
      | rejected|disqualif\w+|ineligible|excluded
      | (?:is|are)\s+(?:prohibited|forbidden)
      | fail(?:ure)?\s+to\s+(?:comply|submit|provide|include)
      | mandatory|minimum\s+qualification
      | late\s+proposals?
    )\b
    """
)

_INFORMATIONAL_KINDS = frozenset({"clause", "cross_reference", "date"})

# ── Requirement type ─────────────────────────────────────────────────────

_MAY = re.compile(r"(?i)\bmay\b(?!\s+not)")
_SHOULD = re.compile(r"(?i)\bshould\b|\bis\s+encouraged\b|\bpreferred\b")


@dataclass
class RequirementDraft:
    """One requirement as extracted, before it meets the ledger.

    A draft has no id and no history. It knows what it says, where it says it,
    and which pass found it — the ledger decides whether it is something new or
    something already known under the same key.
    """

    key: str
    text: str
    reference: str
    kind: str
    type: str
    stakes: str
    verification: str
    citation: dict
    document_id: str = ""
    page: int = 0
    #: "sweep" for the deterministic pass, "model" for a specialist, "manual"
    #: for a person. Kept because a requirement only a model saw deserves less
    #: confidence than one the pattern layer also found.
    sources: set[str] = field(default_factory=set)
    note: str = ""

    @property
    def confirmed(self) -> bool:
        """Found by both passes. Neither layer alone is proof, but agreement
        between a pattern and a reading is as close as extraction gets."""
        return {"sweep", "model"} <= self.sources


def stable_key(text: str, reference: str = "") -> str:
    """The requirement's name, derived from what it says.

    Normalisation absorbs the differences that are not differences —
    whitespace, casing, curly quotes, a parser that puts a line break in a new
    place. The reference is deliberately *not* part of the key: the same
    obligation moved from L.3.2 to L.3.3 by an amendment is the same
    obligation, and treating it as new is exactly the failure this replaces.
    """
    body = normalize(text)
    if not body:
        # Nothing to hash but the reference — better a stable key on a weak
        # signal than a random one that changes every run.
        body = normalize(reference)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:20]


def classify_verification(kind: str, text: str) -> str:
    """Mechanical when it can be counted, substantive when it must be read.

    This is a rule and not a judgement on purpose. A page limit checked by a
    language model is a page limit that can be wrong, and the whole value of a
    mechanical check is that it cannot.
    """
    if kind in MECHANICAL_KINDS:
        return MECHANICAL
    return MECHANICAL if _MECHANICAL_MARKERS.search(text) else SUBSTANTIVE


def classify_stakes(kind: str, text: str) -> str:
    if _DISQUALIFYING_MARKERS.search(text):
        return "disqualifying"
    if kind in _DISQUALIFYING_KINDS:
        return "disqualifying"
    if kind in _INFORMATIONAL_KINDS:
        return "informational"
    # A countable rule is disqualifying by default. Page limits, fonts,
    # margins, file names, missing forms and unsigned certifications are the
    # things proposals are actually thrown out for, and they arrive as ordinary
    # obligation sentences — "Text shall be 12-point Times New Roman" is not a
    # scored preference. Erring toward disqualifying costs an afternoon;
    # erring the other way costs the bid.
    if classify_verification(kind, text) == MECHANICAL:
        return "disqualifying"
    return "scored"


def classify_type(text: str) -> str:
    """`shall` unless the sentence says otherwise.

    Defaulting to the binding form is the safe direction: reading a `should` as
    a `shall` costs effort, and reading a `shall` as a `should` costs the bid.
    """
    if re.search(r"(?i)\b(?:shall|must|required|will\s+be\s+required|prohibited)\b", text):
        return "shall"
    if _SHOULD.search(text):
        return "should"
    if _MAY.search(text):
        return "may"
    return "shall"


# ── Extraction ───────────────────────────────────────────────────────────

#: Sweep categories that state a requirement. Dates, clause numbers and
#: cross-references are recorded elsewhere — they are context for requirements
#: rather than requirements themselves.
REQUIREMENT_KINDS = frozenset(
    {"obligation", "instruction", "limit", "form", "certification", "volume"}
)

#: Below this, a "requirement" is a fragment — a heading, a stray form number —
#: and putting it in front of a capture manager as work costs more than it adds.
MIN_TEXT = 25


def from_sweep(hits: list[SweepHit], anchor=None) -> list[RequirementDraft]:
    """Requirements the deterministic pass found. This is the floor: it is not
    clever, but it read every page and it will say the same thing tomorrow."""
    drafts: dict[str, RequirementDraft] = {}
    for hit in hits:
        if hit.kind not in REQUIREMENT_KINDS:
            continue
        text = " ".join(hit.text.split())
        if len(text) < MIN_TEXT:
            continue
        key = stable_key(text)
        existing = drafts.get(key)
        if existing:
            existing.sources.add("sweep")
            continue
        citation = _citation_for(hit, anchor)
        drafts[key] = RequirementDraft(
            key=key,
            text=text,
            reference=hit.section or citation.get("section", "") or "Unreferenced",
            kind=hit.kind,
            type=classify_type(text),
            stakes=classify_stakes(hit.kind, text),
            verification=classify_verification(hit.kind, text),
            citation=citation,
            document_id=hit.document_id,
            page=hit.page,
            sources={"sweep"},
        )
    return list(drafts.values())


def from_findings(findings: list[dict], kind: str = "obligation") -> list[RequirementDraft]:
    """Requirements a specialist stated in prose.

    The model contributes what a pattern cannot: a requirement spread over a
    table, an obligation implied by a scoring scheme, the sense of a clause
    that never uses the word "shall". It is the ceiling, and it is not trusted
    on its own for anything mechanical.
    """
    drafts: list[RequirementDraft] = []
    for finding in findings:
        citation = finding.get("citation") or {}
        label = str(finding.get("label") or "").strip()
        value = str(finding.get("value") or "").strip()
        text = f"{label}: {value}".strip(": ").strip()
        if len(text) < MIN_TEXT:
            continue
        # A model finding is only as good as its citation. One that never
        # landed on a page is kept — dropping it would hide it — but it is
        # marked so the ledger can show it as unlocated.
        drafts.append(
            RequirementDraft(
                key=stable_key(text),
                text=text,
                reference=citation.get("section") or label or "Unreferenced",
                kind=kind,
                type=classify_type(text),
                stakes=str(finding.get("stakes") or classify_stakes(kind, text)),
                verification=classify_verification(kind, text),
                citation=citation,
                document_id=str(citation.get("documentId") or ""),
                page=int(citation.get("page") or 0),
                sources={"model"},
                note=str(finding.get("detail") or ""),
            )
        )
    return drafts


def merge(*groups: list[RequirementDraft]) -> list[RequirementDraft]:
    """One list, keyed by identity, in reading order.

    Where both passes found the same requirement the record keeps the sweep's
    verbatim text — it is the document's own words rather than a paraphrase —
    and gains the model's note and the fact that both agreed.
    """
    merged: dict[str, RequirementDraft] = {}
    for group in groups:
        for draft in group:
            existing = merged.get(draft.key)
            if existing is None:
                merged[draft.key] = draft
                continue
            existing.sources |= draft.sources
            if not existing.note and draft.note:
                existing.note = draft.note
            # A located citation always beats an unlocated one.
            if not existing.citation.get("located") and draft.citation.get("located"):
                existing.citation = draft.citation
                existing.page = draft.page
                existing.document_id = draft.document_id
            if existing.reference in ("", "Unreferenced") and draft.reference:
                existing.reference = draft.reference
            # Stakes never soften on merge: if either pass called it
            # disqualifying, it is treated as disqualifying.
            if draft.stakes == "disqualifying":
                existing.stakes = "disqualifying"
    return _drop_fragments(sorted(merged.values(), key=lambda d: (d.document_id, d.page, d.reference)))


def _drop_fragments(drafts: list[RequirementDraft]) -> list[RequirementDraft]:
    """Remove a requirement that is a fragment of another on the same page.

    Overlapping patterns produce near-duplicates — "The Offeror shall submit a
    plan" and "Offeror shall submit a plan" are one requirement caught twice,
    and shipping both means a compliance lead assigns the same work to two
    people. The longer capture wins because it carries the subject.
    """
    kept: list[RequirementDraft] = []
    for draft in sorted(drafts, key=lambda d: -len(d.text)):
        body = normalize(draft.text)
        if any(
            other.document_id == draft.document_id
            and other.page == draft.page
            and body in normalize(other.text)
            for other in kept
        ):
            continue
        kept.append(draft)
    return sorted(kept, key=lambda d: (d.document_id, d.page, d.reference))


def _citation_for(hit: SweepHit, anchor) -> dict:
    if anchor is None:
        return {
            "page": hit.page,
            "documentId": hit.document_id,
            "documentName": "",
            "section": hit.section,
            "quote": hit.text,
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "located": False,
        }
    from app.pipeline.anchor import resolve_citation

    return resolve_citation(anchor, hit.text, claimed_page=hit.page, claimed_section=hit.section)
