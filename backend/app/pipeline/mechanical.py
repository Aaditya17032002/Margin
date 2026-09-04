"""Mechanical compliance: the rules a machine settles on its own.

Page counts, word counts, fonts, margins, spacing, file names, file formats,
file sizes, required forms, signatures, copies and volume structure are
countable. Nothing about them is a matter of opinion, and a language model
asked to judge one can be wrong — which is the entire reason to keep them out
of its hands. Every rule here is a rule you can read, disagree with, and
correct.

Three principles hold across all of them.

**A check that cannot be performed says so.** Font size, margins and line
spacing are properties of a rendered PDF, not of the text extracted from one.
When the response arrives as text, the honest answer is `unverifiable` with the
reason attached, never `satisfied` because nothing contradicted it. A
compliance matrix full of green ticks nobody earned is worse than one with
honest gaps: the gaps get worked.

**A rule never guesses in the direction of failure.** A page limit that applies
to a volume the response does not label, or a count that a stated exclusion
would change, stops rather than reporting a failure that might be the rule's
fault rather than the response's. Failing a compliant proposal costs the same
trust as passing a non-compliant one, and is much easier to do by accident.

**A compound requirement produces every check it contains.** "Proposals shall
not exceed 40 pages in 12-point Times New Roman, submitted as a single PDF
under 25 MB" is four rules in one sentence. Reporting only the first is how a
response passes a page count and fails on a font.

Statuses
--------
``satisfied``      Checked, and the response meets it.
``failed``         Checked, and the response does not.
``not_found``      The response contains nothing addressing it at all.
``unverifiable``   Could not be checked from what was supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger
from app.pipeline.anchor import normalize
from app.pipeline.corpus import Corpus

logger = get_logger()

SATISFIED = "satisfied"
FAILED = "failed"
NOT_FOUND = "not_found"
UNVERIFIABLE = "unverifiable"

#: Worst first. A requirement that fails one of its rules fails, whatever the
#: others say; one that cannot be checked is not satisfied.
_SEVERITY = [FAILED, NOT_FOUND, UNVERIFIABLE, SATISFIED]


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
    #: The other rules this requirement carried, when it carried more than one.
    also: list = field(default_factory=list)

    @property
    def decided(self) -> bool:
        return self.status in (SATISFIED, FAILED)


# ── Shared patterns ──────────────────────────────────────────────────────

_PAGE_LIMIT = re.compile(
    r"""(?ix)
    (?:not\s+(?:to\s+)?exceed|no\s+(?:more\s+than|longer\s+than)|maximum\s+of|limited\s+to|within)
    \s+(\d{1,4})\s*(?:total\s+)?pages
    | (\d{1,4})\s*-?\s*page\s+(?:limit|maximum)
    """
)
_WORD_LIMIT = re.compile(
    r"""(?ix)
    (?:not\s+(?:to\s+)?exceed|no\s+more\s+than|maximum\s+of|limited\s+to|within)
    \s+([\d,]{1,7})\s*words
    | ([\d,]{1,7})\s*-?\s*word\s+(?:limit|maximum|count)
    """
)
_FILE_SIZE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(KB|MB|GB)\b")
_FONT_SIZE = re.compile(r"(?i)\b(\d{1,2})\s*-?\s*(?:point|pt)\b|\bfont\s+size\s+(\d{1,2})\b")
_MARGIN = re.compile(r"(?i)\b(\d+(?:\.\d+)?)\s*-?\s*inch\s+margins?\b")
_SPACING = re.compile(r"(?i)\b(single|double|1\.5)\s*-?\s*spaced\b|\bline\s+spacing\b")
_PAPER = re.compile(r"(?i)\b(8\.5\s*[x×]\s*11|letter|A4|8\s*1/2\s*[x×]\s*11)\b\s*(?:inch|paper|size|pages?)?")
_TYPEFACE = re.compile(
    r"(?i)\b(Times New Roman|Arial|Calibri|Helvetica|Garamond|Cambria|Verdana|Georgia|Book Antiqua)\b"
)
_FORM = re.compile(
    r"""(?x)
    (Standard\s+Form\s+\d+ | SF\s*-?\s*\d+
     | Attachment\s+[A-Z]-?\d* | Exhibit\s+[A-Z]-?\d* | Appendix\s+[A-Z]\b
     | [A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,4}\s+(?:Plan|Form|Certificate|Certification|Worksheet|Schedule))
    """
)
_VOLUME = re.compile(r"(?i)\bvolume\s+([IVX]+|\d+)\b")
_NAMING = re.compile(
    r"(?i)(?:convention|named?|naming)\s*[:\s]\s*([A-Za-z0-9_\-]+(?:[_\-][A-Za-z0-9]+){2,}(?:\.[a-z]{3,4})?)"
)
_SIGNATURE = re.compile(r"(?i)\b(signed|signature|wet\s+signature|executed\s+by|initial(?:l)?ed|notaris)")
_FILE_FORMAT = re.compile(r"(?i)\b(searchable\s+)?(PDF/A|PDF|DOCX|DOC|XLSX|XLS|PPTX)\b")
_COPIES = re.compile(
    r"(?i)\b(?:(\d+|one|two|three|four|five|six)\s+)?(?:hard\s+cop(?:y|ies)|paper\s+cop(?:y|ies)|"
    r"original(?:\s+and\s+\w+\s+cop(?:y|ies))?|bound\s+cop(?:y|ies))"
)
_BINDING = re.compile(r"(?i)\b(three\s*-?\s*ring|spiral\s*-?\s*bound|tabbed|tab\s+dividers?|comb\s*-?\s*bound|binder)\b")
_PORTAL = re.compile(
    r"(?i)\b(SAM\.gov|PASSPort|eBuy|GSA\s+eBuy|FedConnect|BidExpress|BonfireHub|Bonfire|"
    r"electronic\s+submission|submitted\s+(?:via|through)\s+(?:the\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?))"
)

#: Phrases that carve pages out of a limit. When one is present, the naive
#: whole-document count is an upper bound rather than the number the rule
#: means.
_EXCLUSION = re.compile(
    r"(?i)\b(?:excluding|exclusive\s+of|not\s+counted|do(?:es)?\s+not\s+count\s+(?:toward|against)|"
    r"shall\s+not\s+count|exempt\s+from\s+the\s+page)\b([^.;]{0,120})"
)

#: The front and back matter solicitations usually exclude, and the headings
#: they carry in a response. Recognising them turns "we cannot apply the
#: exclusion" into a number often enough to be worth doing — and where it does
#: not, the check still refuses to guess.
_EXCLUDABLE = {
    "cover letter": r"(?i)\bcover\s+letter|letter\s+of\s+transmittal|transmittal\s+letter\b",
    "title page": r"(?i)\btitle\s+page\b",
    "table of contents": r"(?i)\btable\s+of\s+contents\b|\bcontents\b\s*$",
    "index": r"(?i)\bindex\b",
    "resumes": r"(?i)\bresum(?:e|é)s?\b|\bcurricul(?:um|a)\s+vitae\b|\bCVs?\b",
    "acronyms": r"(?i)\bacronym|\bglossar(?:y|ies)\b|\babbreviations\b",
    "dividers": r"(?i)\bdividers?\b|\btab\s+pages?\b",
    "appendices": r"(?i)\bappendi(?:x|ces)\b",
    "exhibits": r"(?i)\bexhibits?\b",
    "forms": r"(?i)\bstandard\s+form|\bSF\s*-?\s*\d+\b|\brequired\s+forms?\b",
    "past performance": r"(?i)\bpast\s+performance\s+(?:forms?|questionnaires?|references?)\b",
}

_RENDERING_ONLY = "The response was read as text; this rule is a property of the rendered document."


# ── Entry points ─────────────────────────────────────────────────────────


def check_all(
    requirement_text: str, response: Corpus, *, file_names: list[str] | None = None
) -> list[Check]:
    """Every mechanical rule this requirement carries.

    A compound requirement — a page limit, a font, a format and a size in one
    sentence — is several rules. Returning only the first is how a response
    passes a page count and fails on a font.
    """
    files = file_names or []
    checks: list[Check] = []
    for rule in _RULES:
        result = rule(requirement_text, response, files)
        if result is not None:
            checks.append(result)
    return checks


def check(
    requirement_text: str, response: Corpus, *, file_names: list[str] | None = None
) -> Check | None:
    """One verdict for the requirement, or ``None`` when no rule applies.

    ``None`` means the requirement is substantive and belongs to the model
    layer. When several rules fire, the worst outcome decides — a requirement
    that fails one of its parts fails — and the others travel on `also` so the
    detail can name all of them.
    """
    checks = check_all(requirement_text, response, file_names=file_names)
    if not checks:
        return None
    if len(checks) == 1:
        return checks[0]

    checks.sort(key=lambda c: _SEVERITY.index(c.status))
    primary, rest = checks[0], checks[1:]
    return Check(
        status=primary.status,
        rule=primary.rule,
        detail=" ".join(c.detail for c in checks),
        expected="; ".join(c.expected for c in checks if c.expected),
        actual="; ".join(c.actual for c in checks if c.actual),
        evidence=primary.evidence,
        also=rest,
    )


# ── Counting rules ───────────────────────────────────────────────────────


def _check_page_limit(text: str, response: Corpus, _files: list[str]) -> Check | None:
    match = _PAGE_LIMIT.search(text)
    if not match:
        return None
    limit = int(match.group(1) or match.group(2))
    counted = response.page_count
    scope = "The response"

    # A limit that names a volume applies to that volume, and counting the
    # whole response against it would fail a compliant proposal.
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
        counted = pages
        scope = f"Volume {volume.group(1)}"

    exclusion = _EXCLUSION.search(text)
    if counted <= limit:
        # Under the limit counting everything, so it is under the limit however
        # the exclusions are applied. The strongest thing this rule can say.
        return Check(
            SATISFIED,
            "page_limit",
            f"{scope} is {counted} page{'' if counted == 1 else 's'} against a limit of {limit}"
            + (", counting every page including any the requirement excludes." if exclusion else "."),
            expected=f"at most {limit} pages",
            actual=f"{counted} pages",
        )

    if not exclusion:
        return Check(
            FAILED,
            "page_limit",
            f"{scope} is {counted} pages against a limit of {limit}. That is {counted - limit} over.",
            expected=f"at most {limit} pages",
            actual=f"{counted} pages",
        )

    # Over the limit, and the requirement carves pages out. Find the ones it
    # names before deciding: front matter is usually identifiable, and a
    # response that is over even without it is over.
    excluded_text = " ".join(exclusion.group(1).split())[:80]
    identified = _excluded_pages(response, exclusion.group(1))
    net = counted - len(identified)

    if net > limit:
        return Check(
            FAILED,
            "page_limit",
            f"{scope} is {counted} pages against a limit of {limit}"
            + (
                f", and {len(identified)} identifiable excluded page(s) would still leave "
                f"{net}. That is {net - limit} over."
                if identified
                else f", excluding {excluded_text or 'some pages'}. No excluded pages could be "
                f"identified, and even removing them all would have to save {counted - limit} "
                "pages to comply."
            ),
            expected=f"at most {limit} pages excluding {excluded_text}",
            actual=f"{counted} pages ({net} after identifiable exclusions)",
        )

    # Removing what could be identified brings it within the limit. Genuinely
    # borderline: reporting a failure here would be the rule's fault rather
    # than the response's.
    return Check(
        UNVERIFIABLE,
        "page_limit.exclusion",
        f"{scope} is {counted} pages against a limit of {limit}, but the requirement excludes "
        f"{excluded_text or 'some pages'} and {len(identified)} page(s) matching that appear in "
        f"the response, leaving {net}. Whether those are the pages the requirement means is a "
        "judgement — count it by hand before treating it as either.",
        expected=f"at most {limit} pages excluding {excluded_text}",
        actual=f"{counted} pages in total, {net} after identifiable exclusions",
    )


def _check_word_limit(text: str, response: Corpus, _files: list[str]) -> Check | None:
    match = _WORD_LIMIT.search(text)
    if not match:
        return None
    limit = int((match.group(1) or match.group(2)).replace(",", ""))

    volume = _VOLUME.search(text)
    if volume and _volume_pages(response, volume.group(1)) is None:
        return Check(
            UNVERIFIABLE,
            "word_limit.volume",
            f"The limit applies to Volume {volume.group(1)}, which could not be located.",
            expected=f"{limit} words",
        )

    words = len(_response_text(response).split())
    if not words:
        return Check(
            UNVERIFIABLE,
            "word_limit",
            "No text could be read from the response, so its words cannot be counted.",
            expected=f"at most {limit:,} words",
        )
    return Check(
        SATISFIED if words <= limit else FAILED,
        "word_limit",
        f"The response is {words:,} words against a limit of {limit:,}."
        + ("" if words <= limit else f" That is {words - limit:,} over.")
        + " Counted from extracted text, which may differ slightly from a word processor's count.",
        expected=f"at most {limit:,} words",
        actual=f"{words:,} words",
    )


def _check_file_size(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    if not _FILE_SIZE.search(text):
        return None
    if not re.search(r"(?i)\b(exceed|larger|greater|maximum|limit|under|no\s+more)\b", text):
        return None
    return Check(
        UNVERIFIABLE,
        "file_size",
        "A file size limit can only be checked against the file that will be submitted, "
        "not against its extracted text.",
        expected=_FILE_SIZE.search(text).group(0),
    )


def _check_file_format(text: str, _response: Corpus, files: list[str]) -> Check | None:
    if not re.search(r"(?i)\b(format|submitted\s+as|submitted\s+in|saved\s+as|file\s+type)\b", text):
        return None
    match = _FILE_FORMAT.search(text)
    if not match:
        return None
    wanted = match.group(2).lower()
    if not files:
        return Check(
            UNVERIFIABLE,
            "file_format",
            f"Requires {match.group(0)}. No response file names were supplied, so the format "
            "cannot be checked.",
            expected=match.group(0),
        )

    suffixes = {Path(name).suffix.lower().lstrip(".") for name in files}
    accepted = {"pdf/a": "pdf"}.get(wanted, wanted)
    wrong = [name for name in files if Path(name).suffix.lower().lstrip(".") != accepted]
    if wrong:
        return Check(
            FAILED,
            "file_format",
            f"Requires {match.group(0)}; these are not: {', '.join(wrong)}.",
            expected=match.group(0),
            actual=", ".join(sorted(suffixes)),
        )
    if match.group(1) or wanted == "pdf/a":
        # "Searchable PDF" and PDF/A are properties of how the file was made,
        # not of its extension. Having the right extension is necessary and not
        # sufficient, and saying so is more useful than a tick.
        return Check(
            UNVERIFIABLE,
            "file_format.variant",
            f"The files are PDFs, but {match.group(0)} is a property of how the PDF was "
            "produced and cannot be read from its name or its text.",
            expected=match.group(0),
            actual=", ".join(sorted(suffixes)),
        )
    return Check(
        SATISFIED,
        "file_format",
        f"Every supplied file is {accepted.upper()}.",
        expected=match.group(0),
        actual=", ".join(sorted(suffixes)),
    )


def _check_naming(text: str, _response: Corpus, file_names: list[str]) -> Check | None:
    """A file naming convention, when the requirement states a checkable one.

    Gated on the *template* rather than on the word "named": a template is a
    token with three or more separated parts, which prose does not produce, so
    "a subcontractor named in Volume II" cannot fire this. The phrase "file
    names" or "naming convention" is the weaker signal and only enough to
    report that a convention was demanded and not stated checkably.
    """
    match = _NAMING.search(text)
    if not match:
        if not re.search(r"(?i)file\s*names?|naming\s+convention", text):
            return None
        return Check(
            UNVERIFIABLE,
            "file_name.pattern",
            "The requirement asks for a file naming convention but does not state one in a "
            "form that can be checked automatically.",
        )
    convention = match.group(1)
    # The convention is a template with placeholders — VendorName, VolumeX. Its
    # fixed parts are what a real file name has to carry.
    literals = [
        part.lower()
        for part in re.split(r"[_\-.]", convention)
        if part and not re.search(r"(?i)name|volume|number|x$|title|date", part)
    ]
    if not literals or not file_names:
        return Check(
            UNVERIFIABLE,
            "file_name.pattern",
            "No response file names were supplied, so the convention cannot be checked."
            if not file_names
            else "The stated convention has no fixed part to check a file name against.",
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


def _check_volume(text: str, response: Corpus, _files: list[str]) -> Check | None:
    volumes = {_roman(v) for v in _VOLUME.findall(text)}
    if len(volumes) < 2:
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
    if not re.search(r"(?i)\b(submit|complete|include|provide|attach|furnish|accompan)\w*\b", text):
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
        f"{', '.join(found)} {'is' if len(found) == 1 else 'are'} referenced in the response, "
        "but whether the completed form is attached and signed cannot be read from the text.",
        expected=", ".join(names),
        actual=", ".join(found),
        evidence=_locate(response, found[0]),
    )


# ── Rules that can only be answered by looking at the file ───────────────


def _check_typography(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    """Font, size, margins, spacing and paper — read from the page, not the text.

    Extracted text carries none of these. Reporting `satisfied` because nothing
    contradicted the rule would be an invention, so the check names precisely
    what it could not see.
    """
    demands: list[str] = []
    for pattern in (_FONT_SIZE, _TYPEFACE, _MARGIN, _SPACING, _PAPER):
        found = pattern.search(text)
        if found:
            demands.append(" ".join(found.group(0).split()))
    if not demands:
        return None
    return Check(
        UNVERIFIABLE,
        "typography",
        f"Requires {', '.join(demands)}. {_RENDERING_ONLY} Check it in the file before "
        "submission — this is the kind of rule proposals are rejected on.",
        expected=", ".join(demands),
    )


def _check_signature(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    match = _SIGNATURE.search(text)
    if not match:
        return None
    return Check(
        UNVERIFIABLE,
        "signature",
        "A signature is a property of the executed document. Confirm it against the file "
        "that will be submitted.",
        expected=" ".join(match.group(0).split()),
    )


def _check_copies(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    match = _COPIES.search(text)
    if not match:
        return None
    return Check(
        UNVERIFIABLE,
        "copies",
        f"Requires {' '.join(match.group(0).split())}. How many physical copies are produced "
        "is not a property of the document, and nothing in the response can show it.",
        expected=" ".join(match.group(0).split()),
    )


def _check_binding(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    match = _BINDING.search(text)
    if not match:
        return None
    return Check(
        UNVERIFIABLE,
        "binding",
        f"Requires {match.group(0)}. Physical assembly cannot be checked from a file, and it "
        "is a common reason a hand-delivered proposal is rejected at the counter.",
        expected=match.group(0),
    )


def _check_portal(text: str, _response: Corpus, _files: list[str]) -> Check | None:
    if not re.search(r"(?i)\b(submit|upload|deliver|transmit)\w*\b", text):
        return None
    match = _PORTAL.search(text)
    if not match:
        return None
    where = " ".join((match.group(1) or match.group(0)).split())
    return Check(
        UNVERIFIABLE,
        "submission_method",
        f"Submission through {where}. Whether that happened is a fact about the submission, "
        "not about the document — and it is one somebody has to confirm on the day.",
        expected=where,
    )


#: Order matters only for which rule names a combined verdict when several
#: share the worst status. Counting rules come first because they say the most.
_RULES = (
    _check_page_limit,
    _check_word_limit,
    _check_volume,
    _check_form,
    _check_file_format,
    _check_naming,
    _check_file_size,
    _check_typography,
    _check_signature,
    _check_copies,
    _check_binding,
    _check_portal,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _response_text(response: Corpus) -> str:
    """Everything extracted, not just what became a chunk.

    A volume title page carries one line and produces no chunk, so a
    chunk-based presence check reports "no heading found for Volume II" against
    a response that opens Volume II on its own page — failing exactly the
    properly structured proposals it is supposed to pass.
    """
    return response.full_text


def _volume_pages(response: Corpus, label: str) -> int | None:
    """Pages between this volume's heading and the next one.

    Returns None when the volume cannot be found, because a guess here fails a
    compliant response.
    """
    wanted = _roman(label)
    starts: list[tuple[int, str]] = []
    for page in response.pages_for_anchor():
        text = "\n".join(page.get("lines", []))
        for found in _VOLUME.findall(text):
            starts.append((int(page.get("page", 0)), _roman(found)))
    if not starts:
        return None
    ordered = sorted(set(starts))
    for index, (page, name) in enumerate(ordered):
        if name != wanted:
            continue
        end = ordered[index + 1][0] - 1 if index + 1 < len(ordered) else response.page_count
        return max(1, end - page + 1)
    return None


def _excluded_pages(response: Corpus, exclusion_text: str) -> set[int]:
    """Pages that look like the front and back matter a limit excludes.

    Only the categories the requirement actually names, and only pages whose
    text carries the heading. It is a lower bound on the exclusion by design: a
    rule that over-counts what to remove would pass a response that is over.
    """
    wanted = [
        pattern
        for name, pattern in _EXCLUDABLE.items()
        if re.search(_EXCLUDABLE[name], exclusion_text)
    ]
    if not wanted:
        return set()
    pages: set[int] = set()
    for page in response.pages_for_anchor():
        # The heading has to be near the top of the page. A resume mentioned in
        # passing on page 12 does not make page 12 a resume.
        head = "\n".join(page.get("lines", []))[:120]
        if any(re.search(pattern, head) for pattern in wanted):
            pages.add(int(page.get("page", 0)))
    return pages


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
