"""Finding personal data in a document, before it leaves the building.

An evidence pack is designed to be handed to a lawyer, an auditor, or a
customer. A solicitation package and a draft response are full of things that
should not travel with it — the contracting officer's mobile number, a
reference's home email, the resumes in Appendix B, an SSN somebody pasted into
a form field.

Nothing here decides what is sensitive. It finds what *looks* like personal
data by pattern, reports where, and lets a person choose. Detection is
deterministic for the same reason everything else countable is: a model that
sometimes finds an SSN is worse than a regular expression that always finds
that shape, because the failure mode is invisible.

Two rules the redaction obeys.

**It never edits in place.** Redaction produces a copy with spans replaced and
a record of what was replaced. A tool that silently modified the document it
was given would make the original unrecoverable at exactly the moment somebody
needs it.

**A redacted span says what it was.** `[redacted: telephone]` rather than a
black bar, because a reader has to be able to tell whether the missing thing
mattered — and an auditor asking "what did you take out" deserves better than
"something".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger()


@dataclass(frozen=True)
class Detector:
    kind: str
    label: str
    pattern: re.Pattern
    #: Why this shape is worth flagging, shown when somebody asks.
    note: str


#: Ordered by how little doubt there is. An SSN-shaped number is almost never
#: anything else; a nine-digit number could be a contract line item, so it is
#: not looked for.
DETECTORS: tuple[Detector, ...] = (
    Detector(
        "ssn", "Social Security number",
        re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
        "Formatted as an SSN. Almost nothing else takes this shape.",
    ),
    Detector(
        "ein", "Employer Identification Number",
        re.compile(r"\b\d{2}-\d{7}\b"),
        "EIN-shaped. Often legitimate on a cover form and rarely needed downstream.",
    ),
    Detector(
        "email", "Email address",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "A reference's or an officer's address, which travels further than intended.",
    ),
    Detector(
        "phone", "Telephone number",
        re.compile(
            r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\d)"
        ),
        "A direct line or mobile, usually a person's rather than a switchboard's.",
    ),
    Detector(
        "passport", "Passport number",
        re.compile(r"(?i)\bpassport\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9]{6,9})\b"),
        "Named as a passport number in the text.",
    ),
    Detector(
        "dob", "Date of birth",
        re.compile(r"(?i)\b(?:date\s+of\s+birth|d\.?o\.?b\.?)\s*[:\-]?\s*\S{1,12}"),
        "Explicitly labelled as a date of birth.",
    ),
    Detector(
        "bank", "Bank or routing number",
        re.compile(r"(?i)\b(?:routing|aba|account)\s*(?:no\.?|number|#)?\s*[:\-]?\s*\d{6,17}\b"),
        "Labelled as a routing or account number.",
    ),
)


@dataclass
class Finding:
    kind: str
    label: str
    note: str
    start: int
    end: int
    text: str
    #: A little either side, so a reviewer can see whether it matters.
    context: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "note": self.note,
            "start": self.start,
            "end": self.end,
            # The value itself is never returned to a list view — showing every
            # SSN in a document in order to warn about them would be absurd.
            "preview": _mask(self.text),
            "context": self.context,
        }


@dataclass
class Scan:
    findings: list[Finding] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "total": len(self.findings),
            "counts": self.counts,
            "findings": [f.as_dict() for f in self.findings[:200]],
        }


def _mask(value: str) -> str:
    """Enough to recognise it, not enough to use it."""
    stripped = value.strip()
    if len(stripped) <= 4:
        return "•" * len(stripped)
    return f"{stripped[:2]}{'•' * (len(stripped) - 4)}{stripped[-2:]}"


def scan(text: str, *, kinds: list[str] | None = None) -> Scan:
    """Everything in this text that looks like personal data."""
    wanted = set(kinds) if kinds else {d.kind for d in DETECTORS}
    result = Scan()
    seen: set[tuple[int, int]] = set()

    for detector in DETECTORS:
        if detector.kind not in wanted:
            continue
        for match in detector.pattern.finditer(text or ""):
            span = (match.start(), match.end())
            # Detectors overlap — a phone number inside a labelled field, an
            # email inside a longer string. First match wins, and they are
            # ordered by how little doubt there is.
            if any(span[0] < s[1] and s[0] < span[1] for s in seen):
                continue
            seen.add(span)
            result.findings.append(
                Finding(
                    kind=detector.kind,
                    label=detector.label,
                    note=detector.note,
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                    context=_context(text, match.start(), match.end()),
                )
            )
            result.counts[detector.kind] = result.counts.get(detector.kind, 0) + 1

    result.findings.sort(key=lambda f: f.start)
    logger.info("pii_scanned", total=len(result.findings), **result.counts)
    return result


def _context(text: str, start: int, end: int, window: int = 48) -> str:
    before = text[max(0, start - window) : start].replace("\n", " ")
    after = text[end : end + window].replace("\n", " ")
    return f"…{before}[…]{after}…".strip()


def redact(text: str, findings: list[Finding]) -> tuple[str, list[dict]]:
    """A copy with the spans replaced, and a record of what was replaced.

    Never edits in place. A tool that silently modified the document it was
    given would make the original unrecoverable at exactly the moment somebody
    needs it — and the replacement says what it was, because an auditor asking
    "what did you take out" deserves better than "something".
    """
    if not findings:
        return text, []

    out: list[str] = []
    record: list[dict] = []
    cursor = 0
    for finding in sorted(findings, key=lambda f: f.start):
        if finding.start < cursor:
            continue
        out.append(text[cursor : finding.start])
        out.append(f"[redacted: {finding.label.lower()}]")
        record.append(
            {
                "kind": finding.kind,
                "label": finding.label,
                "at": finding.start,
                "preview": _mask(finding.text),
            }
        )
        cursor = finding.end
    out.append(text[cursor:])
    return "".join(out), record
