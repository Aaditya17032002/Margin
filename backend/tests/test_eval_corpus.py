"""The corpus that holds up the recall number has to be checkable itself.

Every failure mode here was found by hand while the first three cases were
written: a label quoting words the document does not carry, a page number off
by one, the same requirement labelled twice. Each looks exactly like an
extraction failure from the outside, which is why they are checked by code.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals import corpus
from evals.corpus import CaseFiles, Problem

DOCUMENT = (
    "SECTION L — Instructions\n"
    "Proposals shall not exceed 40 pages, excluding the cover letter.\n"
    "\f"
    "SECTION M — Evaluation\n"
    "Technical approach is weighted 60 percent.\n"
)


def _case(spec: dict, text: str = DOCUMENT) -> CaseFiles:
    return CaseFiles(directory=Path("/tmp/case"), text=text, spec=spec)


def _spec(**overrides) -> dict:
    base = {
        "name": "Test case",
        "source": "synthetic",
        "expected": {"limit": [{"page": 1, "quote": "shall not exceed 40 pages"}]},
    }
    base.update(overrides)
    return base


def _kinds(problems: list[Problem]) -> list[str]:
    return [f"{p.kind}: {p.detail}" for p in problems]


def test_a_sound_case_produces_no_problems():
    assert corpus.validate([_case(_spec())]) == []


def test_a_quote_the_document_does_not_carry_is_caught():
    """The failure that looks exactly like an extraction miss. One of these was
    in the first corpus, and it cost an afternoon of chasing the matcher."""
    problems = corpus.validate(
        [_case(_spec(expected={"limit": [{"page": 1, "quote": "as a separate PDF"}]}))]
    )
    assert any("not anywhere in the document" in detail for detail in _kinds(problems))


def test_a_quote_on_the_wrong_page_names_the_right_one():
    problems = corpus.validate(
        [_case(_spec(expected={"evaluation": [{"page": 1, "quote": "weighted 60 percent"}]}))]
    )
    assert any("it is on p.2" in detail for detail in _kinds(problems))


def test_a_page_that_does_not_exist_is_caught():
    problems = corpus.validate(
        [_case(_spec(expected={"limit": [{"page": 9, "quote": "shall not exceed 40 pages"}]}))]
    )
    assert any("no such page" in detail for detail in _kinds(problems))


def test_the_same_label_twice_inflates_a_denominator_nobody_checks():
    quote = {"page": 1, "quote": "shall not exceed 40 pages"}
    problems = corpus.validate([_case(_spec(expected={"limit": [quote, dict(quote)]}))])
    assert any("labelled twice" in detail for detail in _kinds(problems))


def test_an_unknown_category_is_rejected_rather_than_ignored():
    problems = corpus.validate([_case(_spec(expected={"deadlines": [{"page": 1, "quote": "x"}]}))])
    assert any("unknown category" in detail for detail in _kinds(problems))


def test_exhaustive_without_labels_would_measure_precision_against_nothing():
    problems = corpus.validate([_case(_spec(exhaustive=["form"]))])
    assert any("marked exhaustive but has no labels" in detail for detail in _kinds(problems))


# ── Provenance ───────────────────────────────────────────────────────────


def _real_spec(**overrides) -> dict:
    spec = _spec(source="real")
    spec["provenance"] = {
        "solicitationNumber": "RFP-2026-0041",
        "agency": "NYC DOT",
        "retrievedFrom": "https://example.gov/opp/1",
        "retrievedAt": "2026-05-01",
        "checksum": _case(_spec()).checksum(),
    }
    spec.update(overrides)
    return spec


def test_a_real_case_must_say_where_it_came_from():
    """Without this it cannot be re-derived when the parser changes, and nobody
    can answer the licence question."""
    spec = _real_spec()
    del spec["provenance"]["retrievedFrom"]
    problems = corpus.validate([_case(spec)])
    assert any("provenance.retrievedFrom" in detail for detail in _kinds(problems))


def test_a_synthetic_case_needs_no_provenance():
    assert corpus.validate([_case(_spec())]) == []


def test_a_document_that_changed_after_labelling_invalidates_its_page_numbers():
    spec = _real_spec()
    spec["provenance"]["checksum"] = "0000000000000000"
    problems = corpus.validate([_case(spec)])
    assert any("has changed since labelling" in detail for detail in _kinds(problems))


def test_an_unknown_source_is_not_quietly_treated_as_synthetic():
    problems = corpus.validate([_case(_spec(source="probably real"))])
    assert any("expected 'real' or 'synthetic'" in detail for detail in _kinds(problems))


# ── Candidates ───────────────────────────────────────────────────────────


def test_machine_proposed_labels_cannot_be_scored_against():
    """Candidates come from the sweep. Accepting them wholesale would score the
    sweep against its own output and report 100% forever."""
    spec = _spec(
        expected={"limit": [{"page": 1, "quote": "shall not exceed 40 pages", "candidate": True}]}
    )
    problems = corpus.validate([_case(spec)])
    assert any("still flagged `candidate`" in detail for detail in _kinds(problems))


def test_proposals_are_verbatim_so_accepting_one_is_a_deletion_not_a_retype():
    case = _case(_spec())
    proposed = corpus.propose(case)

    assert proposed["expected"], "the sweep proposed nothing at all"
    for kind, items in proposed["expected"].items():
        for item in items:
            assert item["candidate"] is True
            page = case.pages[item["page"] - 1]
            assert " ".join(item["quote"].split()) in " ".join(page.split())


# ── What the corpus covers ───────────────────────────────────────────────


def test_a_corpus_of_invented_documents_says_so():
    """A recall figure held up entirely by text we wrote ourselves measures our
    own assumptions about how agencies write."""
    gaps = corpus.coverage_gaps([_case(_spec())])
    assert gaps == ["no real cases at all — every category is measured against invented text"]


def test_categories_no_real_document_exercises_are_named():
    cases = [_case(_real_spec()), _case(_spec())]
    gaps = corpus.coverage_gaps(cases)
    assert "limit" not in gaps
    assert "certification" in gaps


def test_stats_keep_real_and_synthetic_apart():
    numbers = corpus.stats([_case(_real_spec()), _case(_spec()), _case(_spec())])
    assert (numbers.real, numbers.synthetic) == (1, 2)
    assert numbers.by_kind_real == {"limit": 1}
    assert numbers.by_kind == {"limit": 3}


def test_the_shipped_corpus_is_sound():
    """The corpus in the repository, checked on every run. A recall number
    computed over unsound labels is worse than no number."""
    assert corpus.validate(corpus.load()) == []
