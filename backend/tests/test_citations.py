"""Citations must point at the clause they quote, or admit they cannot."""

from __future__ import annotations

from app.pipeline.anchor import MIN_SCORE, CitationAnchor, resolve_citation
from app.pipeline.extract import PAGE_SEP, extract_pages, pages_from_text
from app.pipeline.layout import LayoutExtractor, find_heading

PAGES = [
    "NEW YORK CITY DEPARTMENT OF TRANSPORTATION\nRequest for Expressions of Interest\n",
    (
        "8.3. Contractor Expertise Required\n"
        "The Systems Integrator shall demonstrate:\n"
        "The minimum of three (3) prior engagements involving data warehouse design,\n"
        "centralized reporting, or Extract, Transform, Load (ETL) pipeline development.\n"
        "Demonstrated experience implementing Microsoft Dynamics 365-based workflow\n"
        "solutions in a government or enterprise setting.\n"
    ),
    (
        "8.4.2 Location of Services\n"
        "The Contractor may not export, process, access or store City Data or provide\n"
        "services outside the United States except with express written permission.\n"
    ),
]


def _anchor() -> CitationAnchor:
    return CitationAnchor(LayoutExtractor().extract_from_pages(PAGES, "rfp.pdf").pages)


def test_two_clauses_on_one_page_get_different_anchors():
    """The bug this exists for: every eligibility gate cited the same place."""
    anchor = _anchor()
    first = resolve_citation(
        anchor,
        "The minimum of three (3) prior engagements involving data warehouse design, "
        "centralized reporting, or Extract, Transform, Load (ETL) pipeline development.",
        claimed_page=24,
    )
    second = resolve_citation(
        anchor,
        "Demonstrated experience implementing Microsoft Dynamics 365-based workflow "
        "solutions in a government or enterprise setting.",
        claimed_page=24,
    )
    assert first["located"] and second["located"]
    assert first["page"] == second["page"] == 2
    assert first["lines"] != second["lines"]
    assert first["bbox"]["y"] < second["bbox"]["y"]


def test_a_claimed_page_never_overrides_the_document():
    """The model said page 24; the clause is on page 3. The document wins."""
    resolved = resolve_citation(
        _anchor(),
        "The Contractor may not export, process, access or store City Data",
        claimed_page=24,
        claimed_section="8.3",
    )
    assert resolved["page"] == 3
    assert resolved["section"] == "8.4.2 Location of Services"


def test_a_quote_that_is_not_in_the_document_is_not_located():
    resolved = resolve_citation(
        _anchor(),
        "This sentence appears nowhere in the document whatsoever.",
        claimed_page=24,
    )
    assert resolved["located"] is False
    assert resolved["lines"] is None


def test_an_approximate_quote_still_anchors():
    """Models tidy quotes. A dropped word must not cost the citation."""
    resolved = resolve_citation(
        _anchor(),
        "The minimum of three prior engagements involving data warehouse design, "
        "centralized reporting, or ETL pipeline development.",
    )
    assert resolved["located"] is True
    assert resolved["page"] == 2
    assert resolved["matchScore"] >= MIN_SCORE


def test_headings_come_from_the_documents_own_numbering():
    assert find_heading("8.3. Contractor Expertise Required") == "8.3 Contractor Expertise Required"
    assert find_heading("SECTION L — Instructions to Offerors").startswith("SECTION L")
    assert find_heading("The Contractor shall provide 3 copies of the proposal.") is None


def test_page_breaks_survive_the_round_trip_through_raw_text():
    text = PAGE_SEP.join(PAGES)
    assert pages_from_text(text) == PAGES
    assert LayoutExtractor().extract_from_text(text, "rfp.pdf").page_count == 3


def test_plain_text_without_page_breaks_still_pages():
    pages = extract_pages(("line\n" * 200).encode(), "notes.txt")
    assert len(pages) > 1
    assert all(page.strip() for page in pages)
