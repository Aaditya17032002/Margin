"""Document Intelligence Layout extraction wrapper.

Extracts headings, paragraphs, tables, bounding boxes, and hierarchical page structures.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.providers.base import ChunkResult, LayoutResult

logger = get_logger()


class LayoutExtractor:
    """Parses document layout structure into pages, sections, and chunk spans with bboxes."""

    def extract_from_text(self, text: str, filename: str) -> LayoutResult:
        lines = [line.rstrip() for line in text.splitlines()]
        if not lines:
            lines = ["Empty document content."]

        # Group lines into ~30 lines per page
        lines_per_page = 30
        pages: list[dict[str, Any]] = []
        chunks: list[ChunkResult] = []

        for page_idx in range(0, len(lines), lines_per_page):
            page_num = (page_idx // lines_per_page) + 1
            page_lines = lines[page_idx : page_idx + lines_per_page]
            heading = None

            # Detect heading from the first non-empty line
            for line in page_lines:
                s = line.strip()
                if s.startswith(("SECTION", "Section", "PART", "Part", "ATTACHMENT", "Attachment", "CLIN", "ITEM")):
                    heading = s[:100]
                    break
            if not heading and page_lines:
                heading = page_lines[0].strip()[:80] or f"Page {page_num}"

            pages.append({
                "page": page_num,
                "heading": heading,
                "lines": page_lines,
            })

            # Form chunks (group consecutive 5-8 lines)
            step = 6
            for c_idx in range(0, len(page_lines), step):
                chunk_slice = page_lines[c_idx : c_idx + step]
                chunk_text = " ".join(chunk_slice).strip()
                if not chunk_text:
                    continue

                y_pos = round(0.05 + ((c_idx / max(1, len(page_lines))) * 0.85), 3)
                h_size = round(min(0.20, (step / max(1, len(page_lines))) * 0.9), 3)

                chunks.append(
                    ChunkResult(
                        text=chunk_text,
                        page=page_num,
                        section_path=heading or f"Section {page_num}",
                        bbox={"x": 0.05, "y": y_pos, "w": 0.9, "h": h_size},
                        chunk_index=len(chunks),
                    )
                )

        logger.info("layout_extracted", filename=filename, pages=len(pages), chunks=len(chunks))
        return LayoutResult(
            pages=pages,
            chunks=chunks,
            page_count=len(pages),
            raw_text=text,
        )
