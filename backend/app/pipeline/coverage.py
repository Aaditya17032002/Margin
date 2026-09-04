"""The coverage ledger: what was read, by what, and what was not.

The product's central claim is that nothing gets missed. A claim like that is
only worth anything if it can be shown false, so this module records — per
chunk, from facts rather than estimates — what actually happened to every part
of the package.

The distinction that makes the ledger honest is between two different kinds of
reading, which most tools in this category collapse into one number:

``analysed``
    A specialist had this text in its context. Deep, interpretive, and by
    necessity selective — retrieval picks what looks relevant to a question.

``scanned``
    The deterministic sweep visited this text and matched it against every
    known pattern. Complete and shallow: it will find that a page limit is
    stated here, but not reason about what it applies to.

``no_text``
    Part of a document extraction produced nothing from — a scanned PDF with no
    text layer. Counted in the denominator, never silently dropped.

``unreached``
    Neither pass touched it. Should be empty, and the ledger exists to prove
    that rather than assume it.

So the honest headline is two numbers, not one: *594 of 594 pages scanned, 214
analysed in depth.* Reporting only the first would overstate the reading;
reporting only the second would understate it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.pipeline.corpus import Corpus

logger = get_logger()

ANALYSED = "analysed"
SCANNED = "scanned"
NO_TEXT = "no_text"
UNREACHED = "unreached"


@dataclass
class CoverageLedger:
    """Accumulates what each pass touched, then reports it."""

    corpus: Corpus
    #: chunk index → the agents that had it in context.
    analysed_by: dict[int, set[str]] = field(default_factory=dict)
    #: chunk indices the deterministic sweep visited.
    scanned: set[int] = field(default_factory=set)

    def record_analysed(self, agent_id: str, chunk_indices: list[int]) -> None:
        for index in chunk_indices:
            self.analysed_by.setdefault(index, set()).add(agent_id)

    def record_scanned(self, chunk_indices: set[int]) -> None:
        self.scanned |= chunk_indices

    # ── Reporting ────────────────────────────────────────────────────────

    def state_of(self, chunk_index: int) -> str:
        if chunk_index in self.analysed_by:
            return ANALYSED
        if chunk_index in self.scanned:
            return SCANNED
        return UNREACHED

    def pages_analysed(self, document_id: str) -> set[int]:
        return {
            chunk.page
            for index in self.analysed_by
            if (chunk := self.corpus.chunk(index)) and chunk.document_id == document_id
        }

    def build(self) -> dict:
        """The record that is persisted and shown. Every number here is counted,
        never inferred, and rounding is always downward."""
        documents: list[dict] = []
        totals = {
            "documents": len(self.corpus.documents),
            "emptyDocuments": 0,
            "pages": 0,
            "pagesScanned": 0,
            "pagesAnalysed": 0,
            "chunks": 0,
            "chunksAnalysed": 0,
            "chunksScanned": 0,
            "chunksUnreached": 0,
        }

        for doc in self.corpus.documents:
            if doc.empty:
                totals["emptyDocuments"] += 1
                documents.append(
                    {
                        "documentId": doc.id,
                        "name": doc.name,
                        "kind": doc.kind,
                        "pages": 0,
                        "state": NO_TEXT,
                        "pagesAnalysed": 0,
                        "chunks": 0,
                        "chunksAnalysed": 0,
                        "chunksUnreached": 0,
                        "unreachedPages": [],
                        "note": "No text could be extracted. Nothing in this document was read.",
                    }
                )
                continue

            analysed_pages = self.pages_analysed(doc.id)
            unreached = [i for i in doc.chunk_indices if self.state_of(i) == UNREACHED]
            unreached_pages = sorted(
                {chunk.page for i in unreached if (chunk := self.corpus.chunk(i))}
            )
            analysed_chunks = sum(1 for i in doc.chunk_indices if i in self.analysed_by)

            totals["pages"] += doc.page_count
            # A page counts as scanned only if no chunk on it was unreached.
            totals["pagesScanned"] += doc.page_count - len(unreached_pages)
            totals["pagesAnalysed"] += len(analysed_pages)
            totals["chunks"] += len(doc.chunk_indices)
            totals["chunksAnalysed"] += analysed_chunks
            totals["chunksUnreached"] += len(unreached)

            documents.append(
                {
                    "documentId": doc.id,
                    "name": doc.name,
                    "kind": doc.kind,
                    "pages": doc.page_count,
                    "state": UNREACHED if unreached else SCANNED,
                    "pagesAnalysed": len(analysed_pages),
                    "chunks": len(doc.chunk_indices),
                    "chunksAnalysed": analysed_chunks,
                    "chunksUnreached": len(unreached),
                    "unreachedPages": _spans(unreached_pages),
                }
            )

        totals["chunksScanned"] = totals["chunks"] - totals["chunksUnreached"]

        by_agent: dict[str, int] = {}
        for agents in self.analysed_by.values():
            for agent in agents:
                by_agent[agent] = by_agent.get(agent, 0) + 1

        ledger = {
            "at": datetime.now(UTC).isoformat(),
            "totals": totals,
            "documents": documents,
            "byAgent": dict(sorted(by_agent.items())),
            "complete": totals["chunksUnreached"] == 0 and totals["emptyDocuments"] == 0,
        }

        logger.info(
            "coverage_ledger",
            documents=totals["documents"],
            pages=totals["pages"],
            pages_scanned=totals["pagesScanned"],
            pages_analysed=totals["pagesAnalysed"],
            chunks_unreached=totals["chunksUnreached"],
            empty_documents=totals["emptyDocuments"],
        )
        return ledger


def _spans(pages: list[int]) -> list[list[int]]:
    """Contiguous page runs. `[3, 4, 5, 9]` reads better as `3–5, 9`."""
    if not pages:
        return []
    spans: list[list[int]] = [[pages[0], pages[0]]]
    for page in pages[1:]:
        if page == spans[-1][1] + 1:
            spans[-1][1] = page
        else:
            spans.append([page, page])
    return spans


def summarise(ledger: dict) -> str:
    """One sentence for the analysis summary, stated the way it should be read."""
    totals = ledger.get("totals", {})
    pages = totals.get("pages", 0)
    scanned = totals.get("pagesScanned", 0)
    analysed = totals.get("pagesAnalysed", 0)
    docs = totals.get("documents", 0)
    empty = totals.get("emptyDocuments", 0)

    parts = [
        f"{scanned} of {pages} pages scanned across {docs} document{'' if docs == 1 else 's'}, "
        f"{analysed} analysed in depth."
    ]
    if empty:
        parts.append(
            f"{empty} document{'' if empty == 1 else 's'} produced no readable text and "
            "nothing in them was read."
        )
    if totals.get("chunksUnreached"):
        parts.append(f"{totals['chunksUnreached']} passages were not reached by any pass.")
    return " ".join(parts)
