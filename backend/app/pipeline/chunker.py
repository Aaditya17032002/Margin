"""Structural chunker — splits text by clause, section, and paragraph while preserving source coordinates."""

from __future__ import annotations

import re
from typing import Any

from app.providers.base import ChunkResult

# Regex matching standard government RFP clauses (e.g. C.1.2, FAR 52.212-1, Section L.3)
CLAUSE_PATTERN = re.compile(
    r"(?:(?:Section|SECTION|Part|PART)\s+[A-M]|(?:FAR|DFARS)\s+\d+\.\d+[-\d]*|[A-M]\.\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


class StructuralChunker:
    """Chunks documents into semantically coherent clauses with exact location metadata."""

    def __init__(self, target_chunk_size: int = 500, overlap: int = 50):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_document(
        self,
        pages: list[dict[str, Any]],
    ) -> list[ChunkResult]:
        chunks: list[ChunkResult] = []

        for p in pages:
            page_num = p.get("page", 1)
            heading = p.get("heading") or f"Page {page_num}"
            lines = p.get("lines", [])
            full_page_text = "\n".join(lines)

            # Look for subclauses on the page
            matches = list(CLAUSE_PATTERN.finditer(full_page_text))
            if matches:
                last_idx = 0
                current_section = heading
                for i, match in enumerate(matches):
                    start = match.start()
                    if start > last_idx:
                        clause_body = full_page_text[last_idx:start].strip()
                        if len(clause_body) > 30:
                            chunks.append(
                                ChunkResult(
                                    text=clause_body,
                                    page=page_num,
                                    section_path=current_section,
                                    bbox={"x": 0.05, "y": round(0.05 + (last_idx / max(1, len(full_page_text)) * 0.85), 3), "w": 0.9, "h": 0.1},
                                    chunk_index=len(chunks),
                                )
                            )
                    current_section = match.group(0)
                    last_idx = start

                # Remaining tail
                tail = full_page_text[last_idx:].strip()
                if tail:
                    chunks.append(
                        ChunkResult(
                            text=tail,
                            page=page_num,
                            section_path=current_section,
                            bbox={"x": 0.05, "y": round(0.05 + (last_idx / max(1, len(full_page_text)) * 0.85), 3), "w": 0.9, "h": 0.1},
                            chunk_index=len(chunks),
                        )
                    )
            else:
                # Regular paragraph-based chunking
                paragraphs = [para.strip() for para in full_page_text.split("\n\n") if para.strip()]
                for p_idx, para in enumerate(paragraphs):
                    chunks.append(
                        ChunkResult(
                            text=para,
                            page=page_num,
                            section_path=heading,
                            bbox={"x": 0.05, "y": round(0.05 + (p_idx / max(1, len(paragraphs)) * 0.85), 3), "w": 0.9, "h": 0.1},
                            chunk_index=len(chunks),
                        )
                    )

        return chunks
