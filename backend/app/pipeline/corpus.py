"""The package corpus: every document in a pursuit, as one addressable body.

A solicitation is not a file. It is a base document, a dozen attachments, and
however many amendments have been issued — and the requirement that
disqualifies you is as likely to be in Attachment J-1 as in Section L. Margin
previously loaded only the document whose ``doc_kind`` was ``base`` and
filtered the rest out before a single agent saw them, which made every claim
about completeness untrue by construction.

This module assembles the whole package: ordered, paginated, chunked, and
indexed so that a chunk knows which document and which page it came from. Every
downstream primitive — retrieval, the sweep, the coverage ledger, citation
anchoring — reads from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.pipeline.extract import pages_from_text
from app.pipeline.layout import LayoutExtractor

logger = get_logger()

# Base first, then attachments, then amendments — the order a person reads them
# and the order a citation list should appear in.
KIND_ORDER = {"base": 0, "attachment": 1, "amendment": 2, "response": 3}


@dataclass
class CorpusChunk:
    """A chunk that knows where it lives.

    ``chunk_index`` is unique across the whole corpus so the coverage ledger and
    the sweep can address any chunk in the package by one number.
    """

    text: str
    page: int
    section_path: str
    chunk_index: int
    document_id: str
    document_name: str
    document_kind: str
    bbox: dict | None = None
    #: Index within this document only, for per-document reporting.
    doc_chunk_index: int = 0


@dataclass
class CorpusDocument:
    id: str
    name: str
    kind: str
    version: int
    pages: list[dict]
    chunk_indices: list[int] = field(default_factory=list)
    #: True when extraction produced no usable text — a scanned PDF, an empty
    #: upload. Recorded rather than hidden: a document nothing could be read
    #: from is the single most important thing a coverage ledger can say.
    empty: bool = False

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass
class Corpus:
    documents: list[CorpusDocument] = field(default_factory=list)
    chunks: list[CorpusChunk] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return sum(doc.page_count for doc in self.documents)

    @property
    def readable_documents(self) -> list[CorpusDocument]:
        return [doc for doc in self.documents if not doc.empty]

    def document(self, document_id: str) -> CorpusDocument | None:
        return next((doc for doc in self.documents if doc.id == document_id), None)

    def chunk(self, index: int) -> CorpusChunk | None:
        return self.chunks[index] if 0 <= index < len(self.chunks) else None

    @property
    def full_text(self) -> str:
        """Everything that was extracted, page by page.

        Not the chunk texts. A page carrying only a heading — a volume title
        page, a tab divider, a section break — produces no chunk at all, so a
        presence check reading chunks would report that "Volume II" is missing
        from a response that opens Volume II on its own page. Chunks are for
        retrieval; this is for asking whether the package contains something.
        """
        return "\n".join(
            line
            for doc in self.documents
            for page in doc.pages
            for line in page.get("lines", [])
        )

    def pages_for_anchor(self) -> list[dict]:
        """The shape ``CitationAnchor`` indexes: one entry per page of the
        package, carrying which document it belongs to."""
        out: list[dict] = []
        for doc in self.documents:
            for page in doc.pages:
                out.append(
                    {
                        **page,
                        "documentId": doc.id,
                        "documentName": doc.name,
                        "documentKind": doc.kind,
                    }
                )
        return out


def build_corpus(documents: list, *, include_response: bool = False) -> Corpus:
    """Assemble a package from stored documents.

    ``documents`` are ORM rows carrying ``id``, ``file_name``, ``doc_kind``,
    ``version`` and ``raw_text``. The response is excluded by default: it is a
    separately versioned corpus compared *against* the solicitation, never part
    of it.
    """
    corpus = Corpus()
    extractor = LayoutExtractor()
    ordered = sorted(
        documents,
        key=lambda d: (KIND_ORDER.get(getattr(d, "doc_kind", "base"), 9), getattr(d, "version", 1), str(getattr(d, "file_name", ""))),
    )

    for row in ordered:
        kind = getattr(row, "doc_kind", "base")
        if kind == "response" and not include_response:
            continue

        raw = getattr(row, "raw_text", None) or ""
        name = str(getattr(row, "file_name", "") or "document")
        doc_id = str(getattr(row, "id", ""))

        if not raw.strip():
            # No text at all. It still counts toward the denominator — a
            # document Margin could not read is exactly what a reader needs to
            # be told about, and quietly dropping it is how "we read
            # everything" becomes a lie.
            corpus.documents.append(
                CorpusDocument(id=doc_id, name=name, kind=kind, version=int(getattr(row, "version", 1) or 1), pages=[], empty=True)
            )
            logger.warning("corpus_document_empty", document_id=doc_id, file_name=name, kind=kind)
            continue

        layout = extractor.extract_from_pages(pages_from_text(raw), name, raw_text=raw)
        document = CorpusDocument(
            id=doc_id,
            name=name,
            kind=kind,
            version=int(getattr(row, "version", 1) or 1),
            pages=layout.pages,
        )

        for local_index, chunk in enumerate(layout.chunks):
            index = len(corpus.chunks)
            corpus.chunks.append(
                CorpusChunk(
                    text=chunk.text,
                    page=chunk.page,
                    section_path=chunk.section_path,
                    chunk_index=index,
                    document_id=doc_id,
                    document_name=name,
                    document_kind=kind,
                    bbox=chunk.bbox,
                    doc_chunk_index=local_index,
                )
            )
            document.chunk_indices.append(index)

        corpus.documents.append(document)

    logger.info(
        "corpus_built",
        documents=len(corpus.documents),
        empty_documents=sum(1 for d in corpus.documents if d.empty),
        pages=corpus.page_count,
        chunks=len(corpus.chunks),
    )
    return corpus
