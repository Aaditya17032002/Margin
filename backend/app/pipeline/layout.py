"""Layout extraction — turn extracted text into pages, sections, and chunks.

This is the fallback for when Document Intelligence is not configured, but it
is also the structure every citation is resolved against, so it has to be
honest about two things: a page is a page the document actually has, and a
section is a heading the document actually prints.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.pipeline.extract import pages_from_text
from app.providers.base import ChunkResult, LayoutResult

logger = get_logger()

# Headings a solicitation actually prints: "8.3. Contractor Expertise",
# "SECTION L — Instructions", "Attachment J-1", "PART II", "Article 14".
HEADING_PATTERNS = (
    re.compile(r"^\s*(\d{1,2}(?:\.\d{1,3}){0,3})[.)]?\s+(\S.{0,90})$"),
    re.compile(r"^\s*((?:SECTION|Section|PART|Part|ARTICLE|Article|APPENDIX|Appendix|ATTACHMENT|Attachment|EXHIBIT|Exhibit|ANNEX|Annex)\s+[A-Z0-9][-A-Z0-9.]*)[.:—–-]?\s*(.{0,90})$"),
    re.compile(r"^\s*([A-M]\.\d{1,2}(?:\.\d{1,2})*)\s+(\S.{0,90})$"),
    # Attachment and exhibit identifiers as headings: "J-1 Wage Determination".
    # Common enough in federal packages that missing them leaves every clause
    # in an attachment with no section at all.
    re.compile(r"^\s*([A-Z]{1,2}-\d{1,3}[a-z]?)\s+(\S.{0,90})$"),
)

# Lines that are shouted rather than numbered still read as headings.
ALL_CAPS = re.compile(r"^[A-Z0-9][A-Z0-9 ,'&/()\-.:]{6,80}$")

# Roughly the number of lines a reader takes in as one clause.
LINES_PER_CHUNK = 8


def find_heading(line: str) -> str | None:
    """The heading this line announces, or None if it is body text."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return None
    for pattern in HEADING_PATTERNS:
        match = pattern.match(stripped)
        if match:
            number, title = match.group(1), (match.group(2) or "").strip()
            # A numbered line that runs on into a sentence is a numbered
            # paragraph, not a heading.
            if title.endswith((".", ";")) and len(title) > 60:
                return None
            return f"{number} {title}".strip()
    if ALL_CAPS.match(stripped) and not stripped.endswith("."):
        return stripped
    return None


class LayoutExtractor:
    """Parses document text into pages, sections, and chunk spans."""

    def extract_from_text(self, text: str, filename: str) -> LayoutResult:
        return self.extract_from_pages(pages_from_text(text), filename, raw_text=text)

    def extract_from_pages(
        self, page_texts: list[str], filename: str, raw_text: str | None = None
    ) -> LayoutResult:
        if not page_texts:
            page_texts = ["Empty document content."]

        pages: list[dict[str, Any]] = []
        chunks: list[ChunkResult] = []
        # Sections run across page boundaries — a heading on page 24 still
        # governs the clause that spills onto page 25, which is exactly the
        # case a citation gets wrong when each page is read in isolation.
        current_section = ""

        for page_index, page_text in enumerate(page_texts):
            page_num = page_index + 1
            lines = [line.rstrip() for line in page_text.splitlines()]
            if not lines:
                lines = [""]

            page_heading: str | None = None
            # Which section each line belongs to, so a chunk can be labelled
            # with the heading above it rather than the heading on the page.
            line_sections: list[str] = []
            for line in lines:
                heading = find_heading(line)
                if heading:
                    current_section = heading
                    if page_heading is None:
                        page_heading = heading
                line_sections.append(current_section)

            pages.append(
                {
                    "page": page_num,
                    "heading": page_heading or current_section or f"Page {page_num}",
                    "lines": lines,
                }
            )

            total = max(1, len(lines))
            for start in range(0, len(lines), LINES_PER_CHUNK):
                window = lines[start : start + LINES_PER_CHUNK]
                body = " ".join(line.strip() for line in window if line.strip()).strip()
                if len(body) < 24:
                    continue
                end = start + len(window) - 1
                chunks.append(
                    ChunkResult(
                        text=body,
                        page=page_num,
                        section_path=line_sections[start] or page_heading or f"Page {page_num}",
                        bbox=line_bbox(start, end, total),
                        chunk_index=len(chunks),
                    )
                )

        logger.info("layout_extracted", filename=filename, pages=len(pages), chunks=len(chunks))
        return LayoutResult(
            pages=pages,
            chunks=chunks,
            page_count=len(pages),
            raw_text=raw_text if raw_text is not None else "\f".join(page_texts),
        )


def line_bbox(first_line: int, last_line: int, total_lines: int) -> dict[str, float]:
    """A normalised box covering a run of lines on a page.

    The extract has no glyph geometry, so this is a proportional box down the
    text column — enough for the source viewer's page map to point a reader to
    the right part of the page, and honest about not being pixel-accurate.
    """
    total = max(1, total_lines)
    top = min(0.95, 0.04 + (first_line / total) * 0.92)
    bottom = min(0.99, 0.04 + ((last_line + 1) / total) * 0.92)
    return {
        "x": 0.06,
        "y": round(top, 4),
        "w": 0.88,
        "h": round(max(0.012, bottom - top), 4),
    }
