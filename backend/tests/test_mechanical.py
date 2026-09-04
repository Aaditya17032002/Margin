"""The rules that settle compliance without a model.

Two failure modes, gated separately because they are not the same mistake: a
rule that gets the answer wrong, and a rule that fires on a requirement it has
no business judging. Enough of the second and the mechanical layer becomes
something people learn to scroll past.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.pipeline.corpus import build_corpus
from app.pipeline.mechanical import FAILED, SATISFIED, UNVERIFIABLE, check, check_all
from evals.mechanical.runner import check_results, load_cases, score


def _response(pages: list[str], name: str = "response.pdf"):
    return build_corpus(
        [SimpleNamespace(id="d", file_name=name, doc_kind="response", version=1, raw_text="\f".join(pages))],
        include_response=True,
    )


def test_every_rule_case_reaches_the_verdict_it_should():
    """The corpus in `evals/mechanical`, run as a test so a rule change fails
    here as well as in CI."""
    assert check_results(score(load_cases())) == []


def test_a_heading_only_page_still_counts_as_present():
    """A volume title page carries one line and produces no chunk. A presence
    check reading chunks reported "no heading found for Volume II" against a
    response that opens Volume II on its own page — failing exactly the
    properly structured proposals it exists to pass."""
    response = _response(["Volume I — Technical Approach", "Volume II — Price"])
    assert response.chunks == [] or len(response.chunks) < 2
    assert "Volume II" in response.full_text

    result = check(
        "Proposals shall be submitted in Volume I — Technical and Volume II — Price.", response
    )
    assert result.status == SATISFIED


def test_a_compound_requirement_produces_every_rule_it_carries():
    """Reporting only the first is how a response passes a page count and fails
    on a font."""
    checks = check_all(
        "Proposals shall not exceed 40 pages in 12-point Times New Roman, submitted as a "
        "single PDF named RFP-2026-0041_VendorName_VolumeX.pdf and not exceeding 25 MB.",
        _response([f"Page {i}." for i in range(1, 5)]),
        file_names=["RFP-2026-0041_Acme_VolumeI.pdf"],
    )
    rules = {c.rule for c in checks}
    assert {"page_limit", "typography", "file_name", "file_size"} <= rules


def test_the_worst_outcome_decides_a_compound_requirement():
    verdict = check(
        "Proposals shall not exceed 2 pages in 12-point Times New Roman.",
        _response([f"Page {i}." for i in range(1, 10)]),
    )
    assert verdict.status == FAILED
    assert verdict.rule == "page_limit"
    # The rule it beat still travels, so the detail can name both.
    assert any(other.rule == "typography" for other in verdict.also)


def test_an_exclusion_that_cannot_close_the_gap_does_not_excuse_it():
    """Refusing to decide when the response is four times over would be useless
    caution dressed as rigour."""
    verdict = check(
        "The technical volume shall not exceed 5 pages, excluding the cover letter and resumes.",
        _response([f"Page {i}." for i in range(1, 25)]),
    )
    assert verdict.status == FAILED


def test_an_exclusion_that_would_close_the_gap_stops_the_rule():
    """Over by exactly the front matter the requirement excludes. Reporting a
    failure would be the rule's fault, not the response's."""
    verdict = check(
        "Proposals shall not exceed 3 pages, excluding the cover letter and the table of contents.",
        _response(
            [
                "Cover Letter\nWe are pleased to submit this proposal.",
                "Table of Contents\n1. Approach 2. Experience 3. Price",
                "1. Approach\nOur approach.",
                "2. Experience\nOur experience.",
                "3. Price\nOur pricing.",
            ]
        ),
    )
    assert verdict.status == UNVERIFIABLE
    assert verdict.rule == "page_limit.exclusion"


@pytest.mark.parametrize(
    "requirement",
    [
        "The Contractor shall maintain a Quality Control Plan throughout performance.",
        "The Contractor shall maintain web pages describing the programme for public reference.",
        "The Offeror shall describe its approach to risk management.",
    ],
)
def test_a_substantive_requirement_gets_no_rule(requirement):
    """The boundary. A rule that fired here would be judging something it
    cannot count, and every spurious row wastes somebody's afternoon."""
    assert check(requirement, _response(["Some narrative."])) is None


def test_a_word_count_reads_pages_rather_than_chunks():
    """Same defect as the volume check: words on a heading-only page vanish
    from a chunk-based count."""
    verdict = check(
        "The executive summary shall not exceed 5 words.",
        _response(["Executive Summary", "One two three four five six seven."]),
    )
    assert verdict.status == FAILED


def test_the_right_extension_is_not_a_searchable_pdf():
    """Necessary and not sufficient, and saying so is more useful than a tick."""
    verdict = check(
        "Each volume shall be submitted as a searchable PDF.",
        _response(["Content."]),
        file_names=["Acme_Volume_I.pdf"],
    )
    assert verdict.status == UNVERIFIABLE
    assert verdict.rule == "file_format.variant"


def test_physical_requirements_are_named_rather_than_passed():
    """Copies, binding and the submission portal are real reasons a proposal is
    turned away, and none of them is a property of a file."""
    for requirement, rule in (
        ("Offerors shall deliver one original and three hard copies.", "copies"),
        ("Each volume shall be spiral-bound with tab dividers.", "binding"),
        ("Proposals shall be submitted through PASSPort.", "submission_method"),
    ):
        verdict = check(requirement, _response(["Content."]))
        assert verdict is not None and verdict.status == UNVERIFIABLE, requirement
        assert verdict.rule == rule
