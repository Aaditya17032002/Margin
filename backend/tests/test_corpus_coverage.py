"""The package is the unit of reading, and coverage is a counted fact."""

from __future__ import annotations

from types import SimpleNamespace

from app.pipeline.anchor import CitationAnchor, resolve_citation
from app.pipeline.corpus import build_corpus
from app.pipeline.coverage import CoverageLedger, summarise
from app.pipeline.retrieval import CorpusRetriever
from app.pipeline.sweep import hits_for_agent, sweep_chunks


def _doc(doc_id: str, name: str, kind: str, pages: list[str], version: int = 1):
    return SimpleNamespace(
        id=doc_id, file_name=name, doc_kind=kind, version=version, raw_text="\f".join(pages)
    )


def _package():
    """A base document plus two attachments — the shape a run used to discard."""
    base = ["SECTION A — Cover\nSolicitation RFP-2026-0041."]
    base += [f"Section {i}. Administrative provisions of no consequence." for i in range(2, 30)]
    base.append(
        "SECTION L — Instructions\nProposals shall not exceed 50 pages, in 12-point Times New Roman."
    )
    return [
        _doc("d_base", "base.pdf", "base", base),
        _doc(
            "d_j1",
            "Attachment J-1.pdf",
            "attachment",
            ["J-1 Wage Determination\nThe Contractor shall pay prevailing wages under this determination."],
        ),
        _doc(
            "d_k1",
            "Attachment K-1.pdf",
            "attachment",
            ["K-1 Certifications\nThe Offeror must certify active SAM.gov registration with no exclusions."],
        ),
    ]


def test_the_whole_package_is_read_not_only_the_base_document():
    """The regression this exists for: `doc_kind == "base"` filtered every
    attachment out of the run, so a package was read as one document."""
    corpus = build_corpus(_package())
    assert len(corpus.documents) == 3
    assert {d.kind for d in corpus.documents} == {"base", "attachment"}
    assert corpus.page_count == 32
    # Chunks from every document, not just the first.
    assert {c.document_id for c in corpus.chunks} == {"d_base", "d_j1", "d_k1"}


def test_a_document_with_no_text_is_counted_not_dropped():
    """A scanned PDF that yields nothing is the single most important thing a
    coverage ledger can report. Silently omitting it is how completeness
    becomes a lie."""
    documents = _package() + [_doc("d_scan", "Scanned.pdf", "attachment", [])]
    corpus = build_corpus(documents)
    assert len(corpus.documents) == 4
    scanned = corpus.document("d_scan")
    assert scanned is not None and scanned.empty

    ledger = CoverageLedger(corpus=corpus)
    ledger.record_scanned(sweep_chunks(corpus.chunks).visited)
    report = ledger.build()
    assert report["totals"]["emptyDocuments"] == 1
    assert report["complete"] is False
    assert "no readable text" in summarise(report)


def test_coverage_separates_scanned_from_analysed():
    """One number would overstate the reading or understate it. The ledger
    reports both, because they are different claims."""
    corpus = build_corpus(_package())
    ledger = CoverageLedger(corpus=corpus)
    ledger.record_scanned(sweep_chunks(corpus.chunks).visited)
    ledger.record_analysed("compliance", [c.chunk_index for c in corpus.chunks[:4]])

    report = ledger.build()
    totals = report["totals"]
    assert totals["chunksUnreached"] == 0
    assert totals["pagesScanned"] == corpus.page_count
    assert 0 < totals["pagesAnalysed"] < totals["pagesScanned"]
    assert report["byAgent"] == {"compliance": 4}
    assert report["complete"] is True


def test_an_unreached_passage_is_reported_rather_than_assumed_away():
    corpus = build_corpus(_package())
    ledger = CoverageLedger(corpus=corpus)
    # Everything except the last chunk — as if a pass had failed part way.
    ledger.record_scanned({c.chunk_index for c in corpus.chunks[:-1]})

    report = ledger.build()
    assert report["totals"]["chunksUnreached"] == 1
    assert report["complete"] is False
    assert any(doc["unreachedPages"] for doc in report["documents"])


def test_citations_name_the_document_they_came_from():
    """Page numbers restart per document. Without the document, "p.1" is
    ambiguous across a package."""
    corpus = build_corpus(_package())
    anchor = CitationAnchor(corpus.pages_for_anchor())

    wage = resolve_citation(anchor, "The Contractor shall pay prevailing wages under this determination.")
    assert wage["located"] is True
    assert wage["documentName"] == "Attachment J-1.pdf"

    limit = resolve_citation(anchor, "Proposals shall not exceed 50 pages, in 12-point Times New Roman.")
    assert limit["located"] is True
    assert limit["documentName"] == "base.pdf"


def test_a_heading_is_never_inherited_across_a_document_boundary():
    corpus = build_corpus(_package())
    anchor = CitationAnchor(corpus.pages_for_anchor())
    resolved = resolve_citation(
        anchor, "The Offeror must certify active SAM.gov registration with no exclusions."
    )
    assert resolved["documentName"] == "Attachment K-1.pdf"
    # Not "SECTION L" from the document before it.
    assert "SECTION" not in resolved["section"].upper()


async def test_retrieval_reaches_past_the_old_ceiling():
    """The page-40 instruction and the attachments were unreachable when the
    excerpt stopped at 70,000 characters of the base document."""
    corpus = build_corpus(_package())
    retriever = CorpusRetriever(corpus)  # no embeddings → lexical path
    assert retriever.mode == "lexical"

    hits = await retriever.search("page limit font margins proposal format")
    assert hits, "retrieval returned nothing"
    assert any("shall not exceed 50 pages" in hit.chunk.text for hit in hits)

    wage = await retriever.search("prevailing wage determination certified payroll")
    assert any(hit.chunk.document_id == "d_j1" for hit in wage)


async def test_a_specialist_gets_its_own_slice_of_the_package():
    corpus = build_corpus(_package())
    retriever = CorpusRetriever(corpus)
    compliance = await retriever.for_agent("compliance")
    assert compliance
    # Reading order, so the model sees passages as the document states them.
    assert [r.chunk.chunk_index for r in compliance] == sorted(
        r.chunk.chunk_index for r in compliance
    )


def test_each_specialist_sees_the_scan_leads_it_is_responsible_for():
    """A compliance agent that never sees a page limit found on page 300
    cannot report it, however good its retrieval was."""
    corpus = build_corpus(_package())
    result = sweep_chunks(corpus.chunks)

    compliance = hits_for_agent(result, "compliance")
    assert any(hit.kind == "limit" for hit in compliance)

    evaluation = hits_for_agent(result, "evaluation")
    assert all(hit.kind in ("evaluation", "clause") for hit in evaluation)


def test_the_ledger_survives_the_api_shape():
    """The ledger is only useful if a reviewer can see it, so the response
    schema has to carry every field the pipeline counts — including the
    unreached page spans, which are the whole point."""
    from app.schemas.common import Coverage

    corpus = build_corpus(_package())
    ledger = CoverageLedger(corpus=corpus)
    ledger.record_scanned({c.chunk_index for c in corpus.chunks[:-1]})
    ledger.record_analysed("compliance", [c.chunk_index for c in corpus.chunks[:4]])

    payload = Coverage.model_validate(ledger.build()).model_dump(by_alias=True)
    assert payload["totals"]["chunksUnreached"] == 1
    assert payload["byAgent"] == {"compliance": 4}
    assert payload["complete"] is False
    spans = [span for doc in payload["documents"] for span in doc["unreachedPages"]]
    assert spans, "the pages nobody reached did not survive serialisation"
