"""Mechanical compliance: the rules a machine settles on its own.

Page counts, fonts, margins, spacing, file names, file sizes, required forms,
signatures and volume structure are countable. Nothing about them is a matter
of opinion, and a language model asked to judge one can be wrong — which is the
entire reason to keep them out of its hands. Every check here is a rule you can
read, disagree with, and correct.

The second principle matters as much as the first: **a check that cannot be
performed says so.** Font size, margins and line spacing are properties of a
rendered PDF, not of the text extracted from one. When the response arrives as
text, the honest answer is `unverifiable` with the reason attached, never
`satisfied` because nothing contradicted it. A compliance matrix full of green
ticks nobody earned is worse than one with honest gaps: the gaps get worked.

Statuses
--------
``satisfied``      The rule was checked and the response meets it.
``failed``         The rule was checked and the response does not meet it.
``not_found``      The response contains nothing addressing it at all.
``unverifiable``   The rule could not be checked from what was supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger
from app.pipeline.anchor import normalize
from app.pipeline.corpus import Corpus

logger = get_logger()

SATISFIED = "satisfied"
FAILED = "failed"
NOT_FOUND = "not_found"
UNVERIFIABLE = "unverifiable"


@dataclass
class Check:
    """One mechanical rule, applied.

    ``rule`` names which rule fired, so a disputed result can be traced to the
    line of code that produced it rather than to a prompt nobody kept.
    """

    status: str
    rule: str
    detail: str
    #: What the requirement demanded and what the response actually had.
    expected: str = ""
    actual: str = ""
    evidence: dict | None = None

    @property
    def decided(self) -> bool:
        return self.status in (SATISFIED, FAILED)


# ── Rule patterns ────────────────────────────────────────────────────────

_PAGE_LIMIT = re.compile(
    r"""(?ix)
    (?:not\s+(?:to\s+)?exceed|no\s+(?:more\s+than|longer\s+than)|maximum\s+of|limited\s+to|within)
    \s+(\d{1,4})\s*(?:total\s+)?pages
    | (\d{1,4})\s*-?\s*page\s+(?:limit|maximum)
    """
)
_FILE_SIZE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(KB|MB|GB)\b")
_FONT_SIZE = re.compile(r"(?i)\b(\d{1,2})\s*-?\s*point\b|\bfont\s+size\s+(\d{1,2})\b")
_MARGIN = re.compile(r"(?i)\b(\d+(?:\.\d+)?)\s*-?\s*inch\s+margins?\b")
_SPACING = re.compile(r"(?i)\b(single|double|1\.5)\s*-?\s*spaced\b")
_TYPEFACE = re.compile(
    r"(?i)\b(Times New Roman|Arial|Calibri|Helvetica|Garamond|Cambria|Verdana|Georgia)\b"
)

#: A form or attachment a response has to include. Matched by name because that
#: is how a solicitation names them and how a response titles them.
_FORM = re.compile(
    r"""(?x)
    (Standard\s+Form\s+\d+ | SF\s*-?\s*\d+
     | Attachment\s+[A-Z]-?\d* | Exhibit\s+[A-Z]-?\d*
     | Appendix\s+[A-Z]\b
     | [A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,4}\s+(?:Plan|Form|Certificate|Certification|Worksheet))
    """
)
_VOLUME = re.compile(r"(?i)\bvolume\s+([IVX]+|\d+)\b")
_NAMING = re.compile(r"(?i)(?:convention|named?|naming)\s*[:\s]\s*([A-Za-z0-9_\-]+(?:[_\-][A-Za-z0-9]+){2,}(?:\.[a-z]{3,4})?)")
_SIGNATURE = re.compile(r"(?i)\b(signed|signature|wet\s+signature|executed\s+by|initial(?:l)?ed)\b")

#: Rules whose evidence lives in the rendering of a document rather than in its
#: words. Extracted text cannot answer them at all.
_RENDERING_ONLY = "The response was read as text; this rule is a property of the rendered document."


def check(requirement_text: str, response: Corpus, *, file_names: list[str] | None = None) -> Check | None:
    """Apply the first mechanical rule that matches this requirement.

    Returns ``None`` when no rule applies, which means the requirement is
    substantive and belongs to the model layer. Rules are tried in order of how
    decisively they answer: a page limit is a number against a number, while a
    required form is a search that can be defeated by an unusual heading.
    """
    for rule in (
        _check_page_limit,
        _check_file_size,
        _check_naming,
        _check_typography,
        _check_volume,
        _check_form,
        _check_signature,
    ):
        result = rule(requirement_text, response, file_names or [])
        if result is not None:
            return result
    return None


def _check_page_limit(text: str, response: Corpus, _files: list[str]) -> Check | None:
    match = _PAGE_LIMIT.search(text)
    if not match:
        return None
    limit = int(match.group(1) or match.group(2))
    actual = response.page_count

    # A limit that names a volume applies to that volume, and counting the
    # whole response against it would fail a compliant proposal. Without the
    # volume's own boundaries the count is not this rule's to make.
    volume = _VOLUME.search(text)
    if volume:
        pages = _volume_pages(response, volume.group(1))
        if pages is None:
            return Check(
                UNVERIFIABLE,
                "page_limit.volume",
                f"The limit applies to Volume {volume.group(1)}, which could not be "
                "located in the response. Counting every page against it would fail a "
                "response that complies.",
                expected=f"{limit} pages",
            )
        actual = pages

    return Check(
        SATISFIED if actual <= limit else FAILED,
        "page_limit",
        f"The response is {actual} page{'' if actual == 1 else 's'} against a limit of {limit}."
        + ("" if actual <= limit else f" That is {actual - limit} over."),
        expected=f"at most {limit} pages",
        actual=f"{actual} pages",
    )


def _check_file_size(text: str, response: Corpus, _files: list[str]) -> Check | None:
    if not _FILE_SIZE.search(text) or "exceed" not in text.lower():
        return None
    return Check(
        UNVERIFIABLE,
        "file_size",
        "A file size limit can only be checked against the file that will be "
        "submitted, not against its extracted text.",
        expected=_FILE_SIZE.search(text).group(0),
    )


def _check_naming(text: str, _response: Corpus, file_names: list[str]) -> Check | None:
    if not re.search(r"(?i)file\s*names?|naming\s+convention", text):
        return None
    match = _NAMING.search(text)
    if not match:
        return Check(
            UNVERIFIABLE,
            "file_name.pattern",
            "The requirement asks for a file naming convention but does not state one "
            "in a form that can be checked automatically.",
        )
    convention = match.group(1)
    # The convention is a template with placeholders — VendorName, VolumeX. Its
    # fixed parts are what a real file name has to carry.
    literals = [
        part.lower()
        for part in re.split(r"[_\-.]", convention)
        if part and not re.search(r"(?i)name|volume|number|x$|title", part)
    ]
    if not literals or not file_names:
        return Check(
            UNVERIFIABLE,
            "file_name.pattern",
            "No response file names were supplied, so the convention cannot be checked.",
            expected=convention,
        )
    offenders = [
        name for name in file_names if not all(literal in name.lower() for literal in literals)
    ]
    return Check(
        SATISFIED if not offenders else FAILED,
        "file_name",
        f"Convention {convention}."
        + (
            " Every supplied file name carries it."
            if not offenders
            else f" These do not: {', '.join(offenders)}."
        ),
        expected=convention,
        actual=", ".join(file_names),
    )


def _check_typography(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    """Font, size, margins and spacing — read from the page, not from the text.

    Extracted text carries none of these. Reporting `satisfied` because nothing
    contradicted the rule would be an invention, so the check names precisely
    what it could not see.
    """
    demands: list[str] = []
    if (font := _FONT_SIZE.search(text)):
        demands.append(font.group(0))
    if (face := _TYPEFACE.search(text)):
        demands.append(face.group(0))
    if (margin := _MARGIN.search(text)):
        demands.append(margin.group(0))
    if (spacing := _SPACING.search(text)):
        demands.append(spacing.group(0))
    if not demands:
        return None
    return Check(
        UNVERIFIABLE,
        "typography",
        f"Requires {', '.join(demands)}. {_RENDERING_ONLY} Check it in the file before "
        "submission — this is the kind of rule proposals are rejected on.",
        expected=", ".join(demands),
    )


def _check_volume(text: str, response: Corpus, _files: list[str]) -> Check | None:
    volumes = {_roman(v) for v in _VOLUME.findall(text)}
    if not volumes or len(volumes) < 2:
        return None
    present = {_roman(v) for v in _VOLUME.findall(_response_text(response))}
    missing = sorted(volumes - present)
    return Check(
        SATISFIED if not missing else FAILED,
        "volume_structure",
        (
            f"All {len(volumes)} required volumes appear in the response."
            if not missing
            else f"No heading found for Volume {', '.join(missing)}."
        ),
        expected=f"Volumes {', '.join(sorted(volumes))}",
        actual=f"Volumes {', '.join(sorted(present)) or 'none found'}",
    )


def _check_form(text: str, response: Corpus, _files: list[str]) -> Check | None:
    if not re.search(r"(?i)\b(submit|complete|include|provide|attach|furnish)\b", text):
        return None
    names = _forms_named(text)
    if not names:
        return None

    body = normalize(_response_text(response))
    missing = [name for name in names if normalize(name) not in body]
    found = [name for name in names if normalize(name) in body]

    if not found:
        return Check(
            NOT_FOUND,
            "required_form",
            f"The response never mentions {', '.join(missing)}.",
            expected=", ".join(names),
        )
    if missing:
        return Check(
            FAILED,
            "required_form",
            f"Found {', '.join(found)}; no mention of {', '.join(missing)}.",
            expected=", ".join(names),
            actual=", ".join(found),
        )
    # Naming a form is not the same as attaching a completed one. The check
    # goes as far as the evidence does and stops.
    return Check(
        UNVERIFIABLE,
        "required_form",
        f"{', '.join(found)} {'is' if len(found) == 1 else 'are'} referenced in the "
        "response, but whether the completed form is attached and signed cannot be "
        "read from the text.",
        expected=", ".join(names),
        actual=", ".join(found),
        evidence=_locate(response, found[0]),
    )


def _check_signature(text: str, response: Corpus, _files: list[str]) -> Check | None:
    if not _SIGNATURE.search(text):
        return None
    return Check(
        UNVERIFIABLE,
        "signature",
        "A signature is a property of the executed document. Confirm it against the "
        "file that will be submitted.",
        expected=_SIGNATURE.search(text).group(0),
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _response_text(response: Corpus) -> str:
    return "\n".join(chunk.text for chunk in response.chunks)


def _volume_pages(response: Corpus, label: str) -> int | None:
    """Pages between this volume's heading and the next one.

    Returns None when the volume cannot be found or has no successor to bound
    it, because a guess here fails a compliant response.
    """
    wanted = _roman(label)
    starts: list[tuple[int, str]] = []
    for chunk in response.chunks:
        for found in _VOLUME.findall(chunk.text):
            starts.append((chunk.page, _roman(found)))
    if not starts:
        return None
    ordered = sorted({(page, name) for page, name in starts})
    for index, (page, name) in enumerate(ordered):
        if name != wanted:
            continue
        end = ordered[index + 1][0] - 1 if index + 1 < len(ordered) else response.page_count
        return max(1, end - page + 1)
    return None


def _forms_named(text: str) -> list[str]:
    names: list[str] = []
    for match in _FORM.finditer(text):
        name = " ".join(match.group(1).split())
        if name and name not in names:
            names.append(name)
    return names[:4]


def _locate(response: Corpus, needle: str) -> dict | None:
    target = normalize(needle)
    for chunk in response.chunks:
        if target in normalize(chunk.text):
            return {
                "documentId": chunk.document_id,
                "documentName": chunk.document_name,
                "page": chunk.page,
                "section": chunk.section_path,
                "quote": chunk.text[:300],
                "located": True,
            }
    return None


def _roman(value: str) -> str:
    """Volume II and Volume 2 are the same volume."""
    numerals = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI"}
    return numerals.get(value.strip(), value.strip().upper())
