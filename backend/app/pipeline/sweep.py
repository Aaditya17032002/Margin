"""The deterministic sweep: what Margin finds without asking a model.

Retrieval decides what a specialist *looks* at, and a specialist decides what
is worth reporting. Both are useful and neither is exhaustive — a requirement
nobody thought to search for is still missed. So before any model runs, every
chunk of every document is passed through this: a fixed set of patterns for the
things a solicitation always states somewhere, matched by rule.

Three properties matter and all three follow from being deterministic:

* **Complete.** Every chunk is visited. Coverage is a fact about this pass, not
  an estimate about the other one.
* **Repeatable.** The same document yields the same hits today and in eight
  months. A prompt change cannot silently move the floor.
* **Measurable.** Because it is repeatable, its recall can be scored against a
  labelled corpus and gated in CI. See ``evals/``.

This is the floor, not the ceiling. It finds *that* a page limit is stated on
page 300; understanding what it applies to is still the model's job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from app.core.logging import get_logger

logger = get_logger()

# The categories a solicitation states somewhere, whether or not anyone asks.
# These are the labels the evaluation harness scores recall against, so adding
# one here means adding it to the labelled corpus too.
KINDS = (
    "obligation",       # shall / must / is required to
    "instruction",      # submit / provide / furnish — Section L imperatives
    "limit",            # page, word, font, margin, spacing limits
    "form",             # SF-33, OF-347, Attachment J-1, Exhibit A
    "certification",    # certifications and representations
    "clause",           # FAR / DFARS clause references
    "date",             # stated deadlines and milestones
    "evaluation",       # evaluation factors, basis of award, weighting
    "cross_reference",  # "as described in Section C.3"
    "volume",           # Volume / Factor / Tab structure
)


@dataclass(frozen=True)
class SweepHit:
    """One pattern match, anchored well enough to cite."""

    kind: str
    #: The matched text, trimmed to something quotable.
    text: str
    document_id: str
    page: int
    section: str
    chunk_index: int
    #: Character offsets within the chunk, so the anchor can be exact.
    start: int
    end: int
    #: Which pattern fired, for debugging a false positive without guessing.
    pattern: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "text": self.text,
            "documentId": self.document_id,
            "page": self.page,
            "section": self.section,
            "chunkIndex": self.chunk_index,
            "start": self.start,
            "end": self.end,
            "pattern": self.pattern,
        }


@dataclass
class SweepResult:
    hits: list[SweepHit] = field(default_factory=list)
    #: chunk_index → True for every chunk this pass visited. The coverage
    #: ledger's "scanned" state comes from here and nowhere else.
    visited: set[int] = field(default_factory=set)

    def by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {kind: 0 for kind in KINDS}
        for hit in self.hits:
            counts[hit.kind] = counts.get(hit.kind, 0) + 1
        return counts


# ── Patterns ─────────────────────────────────────────────────────────────
#
# Written to favour recall over precision. A false positive costs a reviewer a
# glance; a false negative is the thing this module exists to prevent. Every
# pattern is named, so a bad one can be found from its hits rather than
# rediscovered by reading the file.

_P = re.compile


def _pattern(name: str, expr: str, flags: int = re.IGNORECASE) -> tuple[str, re.Pattern[str]]:
    return name, _P(expr, flags)


# Obligations are matched as whole sentences, not from the modal verb onward.
# "shall complete the representations" does not say who, and an extraction that
# drops the subject is a requirement nobody can assign. The evaluation harness
# caught this: five of its six misses were the subject being cut off.
# A sentence ends at a period or semicolon followed by whitespace — never at
# the period inside "SAM.gov" or "FAR 52.204-8", which used to truncate a third
# of the certification hits mid-token.
_END = r"(?:[.;](?=\s|$)|$)"
_SENTENCE = r"(?:(?<=^)|(?<=[.;\n]))\s*[^;\n]{{0,140}}?\b{modal}\b[^;\n]{{0,220}}?" + _END

OBLIGATION_PATTERNS = [
    _pattern("modal.shall", _SENTENCE.format(modal=r"shall(?:\s+not)?")),
    _pattern("modal.must", _SENTENCE.format(modal=r"must(?:\s+not)?")),
    _pattern("modal.may_not", _SENTENCE.format(modal=r"may\s+not")),
    _pattern("modal.required", _SENTENCE.format(modal=r"(?:is|are)\s+required\s+to")),
    _pattern("modal.prohibited", _SENTENCE.format(modal=r"(?:is|are)\s+(?:prohibited|forbidden)")),
    _pattern("modal.will", _SENTENCE.format(modal=r"(?:contractor|offeror|bidder|vendor|proposer)s?\s+will")),
    _pattern("modal.responsible", _SENTENCE.format(modal=r"(?:is|are|shall\s+be)\s+responsible\s+for")),
]

INSTRUCTION_PATTERNS = [
    _pattern("instr.submit", r"\b(?:offerors?|bidders?|proposers?|vendors?)\s+(?:shall|must|should|are\s+to)\s+(?:submit|provide|furnish|include|complete|sign)\b[^;\n]{0,200}?" + _END),
    _pattern("instr.imperative", r"(?:^|[.;]\s+)(?:Submit|Provide|Furnish|Include|Complete|Attach|Sign|Upload)\b[^;\n]{0,180}?" + _END),
    _pattern("instr.proposal", r"\bproposals?\s+(?:shall|must|are\s+to)\s+be\b[^;\n]{0,200}?" + _END),
]

LIMIT_PATTERNS = [
    _pattern("limit.pages", r"\b(?:not\s+to\s+exceed|no\s+more\s+than|maximum\s+of|limited\s+to|shall\s+not\s+exceed)\s+\(?\d{1,4}\)?\s*(?:single|double)?[\s-]*(?:sided\s+)?pages?\b"),
    _pattern("limit.page_limit", r"\b\d{1,4}[\s-]*page\s+(?:limit|maximum|cap)\b"),
    _pattern("limit.words", r"\b(?:not\s+to\s+exceed|no\s+more\s+than|maximum\s+of|limited\s+to)\s+\(?[\d,]{1,7}\)?\s*words?\b"),
    _pattern("limit.font", r"\b\d{1,2}[\s-]*(?:point|pt)\b[^.;]{0,80}\b(?:font|type|typeface)\b|\b(?:font|typeface)\b[^.;]{0,60}\b\d{1,2}[\s-]*(?:point|pt)\b"),
    _pattern("limit.pointsize", r"\b\d{1,2}[\s-]*(?:point|pt)\b"),
    _pattern("limit.typeface", r"\b(?:Times\s+New\s+Roman|Arial|Calibri|Helvetica|Courier(?:\s+New)?|Garamond)\b"),
    _pattern("limit.margin", r"\b\d(?:\.\d+)?[\s-]*(?:inch|in\.?|\")\s+margins?\b|\bmargins?\s+(?:of|shall\s+be)\s+[^.;]{0,40}\b\d(?:\.\d+)?\s*(?:inch|in\.?|\")"),
    _pattern("limit.spacing", r"\b(?:single|double|1\.5)[\s-]*spac(?:ed|ing)\b"),
    _pattern("limit.filesize", r"\b(?:not\s+)?(?:exceed(?:ing)?|limit(?:ed)?\s+to|maximum\s+of|no\s+(?:more|larger)\s+than)\s+\d{1,4}\s*(?:MB|GB|megabytes?|gigabytes?)\b|\b\d{1,4}\s*(?:MB|GB|megabytes?|gigabytes?)\b[^;\n]{0,60}\b(?:limit|maximum|exceed)\w*"),
    _pattern("limit.filename", r"\bfile\s+(?:names?|naming)\s+(?:convention|shall|must|format)\b[^.;]{0,160}[.;]"),
]

FORM_PATTERNS = [
    _pattern("form.standard", r"\b(?:SF|OF|DD)[\s-]?\d{1,4}[A-Z]?\b"),
    _pattern("form.standard_form", r"\bStandard\s+Form\s+\d{1,4}\b"),
    _pattern("form.attachment", r"\b(?:Attachment|Exhibit|Appendix|Annex|Enclosure)\s+[A-Z]{1,2}(?:-\d{1,3})?\b"),
    _pattern("form.wage", r"\bwage\s+determination\s*(?:no\.?|number)?\s*[\d-]*\b"),
]

CERTIFICATION_PATTERNS = [
    _pattern("cert.certify", _SENTENCE.format(modal=r"certif(?:y|ies|ication|ications)")),
    _pattern("cert.reps", r"\brepresentations?\s+and\s+certifications?\b"),
    _pattern("cert.sam", r"\b(?:SAM\.gov|System\s+for\s+Award\s+Management)\b[^.;]{0,140}[.;]"),
    _pattern("cert.debarment", r"\b(?:debarment|suspension|excluded\s+parties)\b[^.;]{0,140}[.;]"),
]

CLAUSE_PATTERNS = [
    _pattern("clause.far", r"\b(?:FAR|DFARS|GSAR|AGAR|HHSAR)\s+\d{1,3}\.\d{1,3}(?:-\d{1,3})?(?:\s*\([a-z0-9]{1,3}\))*"),
    _pattern("clause.bare", r"\b52\.\d{3}-\d{1,3}\b"),
    _pattern("clause.section", r"\bSection\s+[A-M]\b(?:\s*[—–-]\s*[A-Z][^.;\n]{0,60})?"),
]

DATE_PATTERNS = [
    _pattern("date.iso", r"\b\d{4}-\d{2}-\d{2}\b"),
    _pattern("date.us", r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"),
    _pattern("date.numeric", r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    _pattern("date.due", r"\b(?:due|deadline|no\s+later\s+than|closing|closes|shall\s+be\s+received)\b[^.;\n]{0,120}\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})"),
]

EVALUATION_PATTERNS = [
    _pattern("eval.factor", r"\b(?:evaluation\s+)?(?:factor|subfactor)\s+\d+\b[^.;\n]{0,120}"),
    _pattern("eval.basis", r"\bbasis\s+for\s+award\b[^.;]{0,200}[.;]"),
    _pattern("eval.method", r"\b(?:best\s+value|lowest\s+price\s+technically\s+acceptable|LPTA|trade[\s-]?off)\b[^.;]{0,160}[.;]"),
    _pattern("eval.weight", r"\b\d{1,3}\s*(?:%|percent)\b[^.;\n]{0,100}\b(?:weight|weighted|evaluation|factor|score|points?)\b|\b(?:weight|weighted|worth)\b[^.;\n]{0,60}\b\d{1,3}\s*(?:%|percent|points?)\b"),
    _pattern("eval.parenthetical", r"\b[A-Z][A-Za-z /&-]{2,40}\s*\(\s*\d{1,3}\s*(?:%|percent|points?)\s*\)"),
    _pattern("eval.evaluated_on", r"\b(?:will\s+be\s+)?evaluated\s+on\b[^;\n]{0,200}?" + _END),
    _pattern("eval.significance", r"\b(?:significantly\s+more\s+important|approximately\s+equal|more\s+important\s+than)\b[^.;]{0,160}[.;]"),
]

CROSS_REFERENCE_PATTERNS = [
    _pattern("xref.described", r"\b(?:as\s+(?:described|set\s+forth|specified|defined|required|provided)\s+in|in\s+accordance\s+with|pursuant\s+to|refer\s+to|see)\s+(?:Section|Part|Article|Attachment|Exhibit|Appendix|Annex|Clause|Paragraph|Table|Volume)\s+[A-Z0-9][\w.\-]*"),
    _pattern("xref.per", r"\bper\s+(?:Section|Attachment|Exhibit|Appendix|Clause)\s+[A-Z0-9][\w.\-]*"),
    _pattern("xref.numbered", r"\b(?:described|specified|stated|listed)\s+in\s+(?:paragraph|subsection|section)\s+\d+(?:\.\d+)*"),
]

VOLUME_PATTERNS = [
    _pattern("vol.roman", r"\bVolume\s+(?:[IVX]{1,5}|\d{1,2})\b(?:\s*[—–:-]\s*[A-Z][^.;\n]{0,60})?"),
    _pattern("vol.tab", r"\bTab\s+[A-Z0-9]{1,3}\b"),
    _pattern("vol.separate", r"\bseparate(?:ly)?\s+(?:bound|sealed|submitted|volume|file|document|pdf|attachment|part)s?\b[^;\n]{0,140}?" + _END),
]

PATTERN_SETS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "obligation": OBLIGATION_PATTERNS,
    "instruction": INSTRUCTION_PATTERNS,
    "limit": LIMIT_PATTERNS,
    "form": FORM_PATTERNS,
    "certification": CERTIFICATION_PATTERNS,
    "clause": CLAUSE_PATTERNS,
    "date": DATE_PATTERNS,
    "evaluation": EVALUATION_PATTERNS,
    "cross_reference": CROSS_REFERENCE_PATTERNS,
    "volume": VOLUME_PATTERNS,
}

# Which sweep kinds each specialist is given alongside its retrieved passages.
# A specialist that never sees the page limits found on page 300 cannot report
# them, however good its retrieval was.
AGENT_KINDS: dict[str, tuple[str, ...]] = {
    "intake": ("form", "clause", "volume"),
    "scope": ("obligation", "cross_reference"),
    "compliance": ("obligation", "instruction", "limit", "form", "certification", "volume", "cross_reference"),
    "eligibility": ("obligation", "certification", "clause"),
    "evaluation": ("evaluation", "clause"),
    "risk": ("obligation", "clause"),
    "pricing": ("obligation", "form"),
    "dates": ("date",),
    "qa": ("cross_reference", "limit", "obligation"),
}

MAX_HIT_CHARS = 400


def sweep_text(
    text: str,
    *,
    document_id: str,
    page: int,
    section: str,
    chunk_index: int,
    kinds: Iterable[str] | None = None,
) -> list[SweepHit]:
    """Every pattern hit in one chunk of text."""
    wanted = tuple(kinds) if kinds else KINDS
    hits: list[SweepHit] = []

    for kind in wanted:
        spans: list[tuple[int, int, str, str]] = []
        for name, pattern in PATTERN_SETS.get(kind, []):
            for match in pattern.finditer(text):
                start, end = match.span()
                matched = " ".join(match.group(0).split())[:MAX_HIT_CHARS]
                if len(matched) >= 3:
                    spans.append((start, end, matched, name))

        # Longest first, then drop anything contained in a hit already kept:
        # "FAR 52.204-7" and "52.204-7" are one clause reference, and reporting
        # both would inflate every count the eval harness measures.
        spans.sort(key=lambda s: (s[0] - s[1], s[0]))
        kept: list[tuple[int, int, str, str]] = []
        for start, end, matched, name in spans:
            if any(start >= k_start and end <= k_end for k_start, k_end, _, _ in kept):
                continue
            kept.append((start, end, matched, name))

        for start, end, matched, name in sorted(kept):
            hits.append(
                SweepHit(
                    kind=kind,
                    text=matched,
                    document_id=document_id,
                    page=page,
                    section=section,
                    chunk_index=chunk_index,
                    start=start,
                    end=end,
                    pattern=name,
                )
            )
    return hits


def sweep_chunks(chunks: list, *, kinds: Iterable[str] | None = None) -> SweepResult:
    """Visit every chunk. The visit is the point, not the hits.

    ``chunks`` is any sequence of objects carrying ``text``, ``page``,
    ``section_path``, ``chunk_index`` and — for a package corpus —
    ``document_id``.
    """
    result = SweepResult()
    for chunk in chunks:
        index = getattr(chunk, "chunk_index", 0)
        result.visited.add(index)
        result.hits.extend(
            sweep_text(
                getattr(chunk, "text", "") or "",
                document_id=getattr(chunk, "document_id", "") or "",
                page=getattr(chunk, "page", 1),
                section=getattr(chunk, "section_path", "") or "",
                chunk_index=index,
                kinds=kinds,
            )
        )
    logger.info(
        "sweep_complete",
        chunks=len(result.visited),
        hits=len(result.hits),
        **{f"hits_{k}": v for k, v in result.by_kind().items() if v},
    )
    return result


def hits_for_agent(result: SweepResult, agent_id: str, limit: int = 120) -> list[SweepHit]:
    """The sweep hits worth putting in front of one specialist.

    Capped, because a specialist drowning in 4,000 obligations reports none of
    them well. The cap is a context-window concession and it is why the sweep's
    own output is persisted separately: what the model sees is a sample, what
    the ledger records is everything.
    """
    kinds = AGENT_KINDS.get(agent_id)
    if not kinds:
        return []
    picked = [hit for hit in result.hits if hit.kind in kinds]
    if len(picked) <= limit:
        return picked

    # Spread the cap across kinds rather than letting the most common one — it
    # is always "obligation" — crowd out every page limit in the document.
    per_kind = max(1, limit // len(kinds))
    out: list[SweepHit] = []
    for kind in kinds:
        out.extend([hit for hit in picked if hit.kind == kind][:per_kind])
    return out[:limit]
