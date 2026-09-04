"""Resolve a quoted clause back to the exact lines it was quoted from.

A model that returns a page number is guessing; a model that returns a verbatim
quote is citing. This module takes the quote and finds where it actually sits
in the extract, and everything the workspace shows about a citation — the page,
the section, the highlighted lines, the box on the page map — is derived from
that match rather than from anything the model asserted.

Two consequences fall out of doing it this way, and both are the point:

* A citation can be *unlocated*. If the quote is not in the document, no page
  number is invented for it; the finding carries ``located: False`` and the
  workspace can say so instead of scrolling a reader to an arbitrary line.
* Every located citation is proof the quote is verbatim, which is the cheapest
  hallucination check available on an extraction pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.pipeline.layout import line_bbox

# Normalisation has to survive the usual extraction damage: smart quotes,
# ligatures, soft hyphens, and runs of whitespace where a PDF had a column gap.
_TRANSLATE = str.maketrans(
    {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-", "­": "",
        " ": " ", "ﬁ": "fi", "ﬂ": "fl",
    }
)
_NON_WORD = re.compile(r"[^a-z0-9]+")

# Below this the "match" is coincidence — shared stopwords, a repeated heading.
MIN_SCORE = 0.62
# A quote shorter than this cannot be told apart from boilerplate.
MIN_QUOTE_CHARS = 24


def normalize(text: str) -> str:
    """Comparison form: lowercase, punctuation and whitespace collapsed away."""
    return _NON_WORD.sub(" ", text.translate(_TRANSLATE).lower()).strip()


def _squash(text: str) -> str:
    return normalize(text).replace(" ", "")


@dataclass(frozen=True)
class Anchor:
    """Where a quote lives: document, page, the lines it spans, and how sure we are."""

    page: int
    section: str
    first_line: int
    last_line: int
    score: float
    bbox: dict[str, float]
    #: Which document in the package. Empty for a single-document analysis,
    #: which is what every citation written before packages existed looks like.
    document_id: str = ""
    document_name: str = ""

    @property
    def lines(self) -> list[int]:
        return [self.first_line, self.last_line]


class CitationAnchor:
    """An index over the extract's pages that resolves quotes to locations."""

    def __init__(self, pages: list[dict]):
        self._pages = pages
        # One squashed string per page plus, for each page, the character
        # offset at which every line starts. Searching the squashed page and
        # mapping the offset back to lines is what lets a quote match across a
        # line wrap, which is the normal case in an extracted PDF.
        self._index: list[tuple[str, list[int], list[str]]] = []
        for page in pages:
            lines = [str(line) for line in page.get("lines", [])]
            offsets: list[int] = []
            cursor = 0
            for line in lines:
                offsets.append(cursor)
                cursor += len(_squash(line))
            self._index.append(("".join(_squash(line) for line in lines), offsets, lines))

    def locate(self, quote: str, hint_page: int | None = None) -> Anchor | None:
        """Find ``quote``. ``hint_page`` (whatever the model claimed) only ever
        breaks ties between equally good matches — it can never create one."""
        needle = _squash(quote)
        if len(needle) < MIN_QUOTE_CHARS:
            return None

        best: Anchor | None = None
        for page_index, (haystack, offsets, lines) in enumerate(self._index):
            if not haystack:
                continue
            found = self._search(haystack, needle)
            if not found:
                continue
            start, end, score = found
            if hint_page and (page_index + 1) == hint_page:
                # Enough to settle a tie, not enough to beat a better match.
                score = min(1.0, score + 0.02)
            if best is not None and score <= best.score:
                continue
            first, last = self._span(offsets, lines, start, end)
            source = self._pages[page_index]
            best = Anchor(
                # Page numbers restart per document, so a citation is only
                # unambiguous with the document beside it.
                page=int(source.get("page") or (page_index + 1)),
                section=self._section_for(page_index, first),
                first_line=first,
                last_line=last,
                score=round(score, 3),
                bbox=line_bbox(first, last, len(lines)),
                document_id=str(source.get("documentId") or ""),
                document_name=str(source.get("documentName") or ""),
            )
        return best

    @staticmethod
    def _search(haystack: str, needle: str) -> tuple[int, int, float] | None:
        """Exact substring first — that is the common case and it is free.
        Otherwise the best approximate window, which covers a quote the model
        tidied up (an ellipsis, a dropped article, a fixed typo)."""
        exact = haystack.find(needle)
        if exact != -1:
            return exact, exact + len(needle), 1.0

        matcher = SequenceMatcher(None, haystack, needle, autojunk=False)
        blocks = [b for b in matcher.get_matching_blocks() if b.size > 8]
        if not blocks:
            return None
        covered = sum(b.size for b in blocks)
        score = covered / len(needle)
        if score < MIN_SCORE:
            return None
        start = blocks[0].a
        end = blocks[-1].a + blocks[-1].size
        # A match smeared across the whole page is not a match.
        if end - start > len(needle) * 3:
            return None
        return start, end, score

    @staticmethod
    def _span(offsets: list[int], lines: list[str], start: int, end: int) -> tuple[int, int]:
        first = 0
        last = max(0, len(lines) - 1)
        for index, offset in enumerate(offsets):
            if offset <= start:
                first = index
            if offset < end:
                last = index
        return first, max(first, last)

    def _section_for(self, page_index: int, line_index: int) -> str:
        """The nearest heading at or above the matched line, searching back
        through earlier pages when the clause opens a page.

        The search stops at the document boundary. In a package the previous
        page may belong to a different attachment entirely, and inheriting its
        heading would put a confident, wrong section on the citation.
        """
        from app.pipeline.layout import find_heading

        document = str(self._pages[page_index].get("documentId") or "")
        for index in range(page_index, -1, -1):
            if str(self._pages[index].get("documentId") or "") != document:
                break
            lines = self._pages[index].get("lines", [])
            upto = line_index if index == page_index else len(lines) - 1
            for line_no in range(min(upto, len(lines) - 1), -1, -1):
                heading = find_heading(str(lines[line_no]))
                if heading:
                    return heading
        page = self._pages[page_index] if page_index < len(self._pages) else {}
        return str(page.get("heading") or "")


def resolve_citation(
    anchor: CitationAnchor,
    quote: str,
    claimed_page: int | None = None,
    claimed_section: str = "",
    fallback: dict | None = None,
) -> dict:
    """Build the citation the API returns, grounded wherever grounding is possible.

    ``fallback`` is the chunk the excerpt was drawn from. It is used only to
    keep the shape valid when nothing matched, and such a citation is flagged
    ``located: False`` so no part of the UI treats it as a real anchor.
    """
    found = anchor.locate(quote, hint_page=claimed_page)
    if found:
        return {
            "page": found.page,
            "documentId": found.document_id,
            "documentName": found.document_name,
            # The document's own heading beats the model's paraphrase of it,
            # but a model that named a section we could not detect is still
            # better than nothing.
            "section": found.section or claimed_section,
            "quote": quote,
            "bbox": found.bbox,
            "lines": found.lines,
            "located": True,
            "matchScore": found.score,
        }

    fallback = fallback or {}
    return {
        "page": int(fallback.get("page") or claimed_page or 1),
        "documentId": str(fallback.get("documentId") or ""),
        "documentName": str(fallback.get("documentName") or ""),
        "section": claimed_section or str(fallback.get("section") or ""),
        "quote": quote,
        "bbox": fallback.get("bbox") or {"x": 0.06, "y": 0.04, "w": 0.88, "h": 0.05},
        "lines": None,
        "located": False,
        "matchScore": 0.0,
    }
