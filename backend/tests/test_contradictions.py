"""Requirements in the same package that cannot both be met.

The failure this catches is one nothing else in the product can: every clause
is extracted correctly, coverage says the package was read, the matrix lists
them all as live work, and the team writes to whichever one they happened to
open.
"""

from __future__ import annotations

import pytest

from app.pipeline.contradictions import Candidate, claims_of, detect, scope_of


def _req(id: str, reference: str, text: str, *, kind: str = "limit",
         document_kind: str = "base", stakes: str = "scored", state: str = "open") -> Candidate:
    return Candidate(
        id=id, reference=reference, text=text, kind=kind,
        document_kind=document_kind, stakes=stakes, state=state,
    )


PAGE_40 = _req("r1", "L.1", "Proposals shall not exceed 40 pages.", stakes="disqualifying")
PAGE_50 = _req(
    "r2", "L-2.3", "The proposal shall not exceed 50 pages.",
    document_kind="attachment", stakes="disqualifying",
)


# ── The case it exists for ───────────────────────────────────────────────


def test_two_page_limits_in_one_package_is_a_contradiction():
    found = detect([PAGE_40, PAGE_50])
    assert len(found) == 1
    assert found[0].dimension == "page_limit"
    assert {found[0].left_value, found[0].right_value} == {"40", "50"}
    assert found[0].severity == "blocking"


def test_three_limits_are_reported_against_the_earliest_rather_than_pairwise():
    """Three page limits is one problem to resolve, not three. A list that
    grows quadratically is a list nobody works through."""
    amended = _req(
        "r3", "A.2", "Proposals shall not exceed 65 pages.",
        document_kind="amendment", stakes="disqualifying",
    )
    found = detect([PAGE_40, PAGE_50, amended])
    assert len(found) == 2
    assert all(c.left_id == "r1" for c in found), "the base document should anchor the comparison"


def test_the_same_limit_stated_twice_is_not_a_contradiction():
    restated = _req("r2", "L-2.3", "The proposal shall not exceed 40 pages.", document_kind="attachment")
    assert detect([PAGE_40, restated]) == []


def test_limits_on_different_parts_of_the_response_do_not_collide():
    """A limit on the executive summary and one on the proposal are both true.
    Treating them as a conflict is how a detector becomes noise."""
    summary = _req("r4", "L.5", "The executive summary shall not exceed 2 pages.")
    assert detect([PAGE_40, summary]) == []


def test_limits_on_different_volumes_do_not_collide():
    one = _req("r5", "L.3", "Volume I shall not exceed 30 pages.")
    two = _req("r6", "L.4", "Volume II shall not exceed 15 pages.")
    assert detect([one, two]) == []


# ── Other dimensions ─────────────────────────────────────────────────────


def test_two_deadlines_are_the_most_expensive_kind_of_disagreement():
    early = _req("d1", "A.1", "Proposals are due 2026-06-01.", kind="date")
    late = _req("d2", "L.7", "Proposals are due June 22, 2026.", kind="date")
    found = detect([early, late])
    assert len(found) == 1
    assert found[0].dimension == "deadline"
    # Both written forms normalise to the same shape so they can be compared.
    assert {found[0].left_value, found[0].right_value} == {"2026-06-01", "2026-06-22"}
    assert found[0].severity == "blocking"


@pytest.mark.parametrize(
    "left,right,dimension",
    [
        ("Text shall be 12-point Times New Roman.", "Text shall be 10-point Arial.", "font_size"),
        ("Use 1-inch margins.", "Use 0.5-inch margins.", "margin"),
        ("No file shall exceed 25 MB.", "No file shall exceed 10 MB.", "file_size"),
        (
            "Offerors shall deliver three hard copies.",
            "Offerors shall deliver five hard copies.",
            "copies",
        ),
        (
            "The summary shall not exceed 500 words.",
            "The summary shall not exceed 750 words.",
            "word_limit",
        ),
    ],
)
def test_each_countable_dimension_is_compared(left, right, dimension):
    found = detect([_req("a", "X.1", left), _req("b", "Y.2", right)])
    assert [c.dimension for c in found] == [dimension]


def test_number_words_and_digits_compare_equal():
    assert detect([
        _req("a", "X.1", "Offerors shall deliver three hard copies."),
        _req("b", "Y.2", "Offerors shall deliver 3 hard copies."),
    ]) == []


# ── The non-numeric case ─────────────────────────────────────────────────


def test_a_prohibition_contradicted_by_a_permission():
    banned = _req(
        "p1", "H.11",
        "The Contractor may not store Government Data outside the continental United States.",
        kind="obligation", stakes="disqualifying",
    )
    allowed = _req(
        "p2", "J-4",
        "The Contractor may store Government Data in approved offshore facilities.",
        kind="obligation", document_kind="attachment",
    )
    found = detect([banned, allowed])
    assert len(found) == 1
    assert found[0].dimension == "permission"
    assert found[0].severity == "blocking"


def test_a_prohibition_does_not_contradict_itself():
    """"may not" contains "may". Without a lookahead every prohibition matched
    as its own permission."""
    banned = _req("p1", "H.11", "The Contractor may not store Government Data offshore.")
    assert detect([banned]) == []


def test_unrelated_permissions_and_prohibitions_are_left_alone():
    """A page of maybe-conflicts trains people to close the tab."""
    ask = _req("q1", "L.9", "Offerors may submit written questions until the date in Block 12.")
    late = _req("q2", "L.10", "Offerors may not submit a proposal after the closing time.")
    assert detect([ask, late]) == []


# ── Precedence is proposed, never applied ────────────────────────────────


def test_an_amendment_is_recommended_over_the_base_document():
    amended = _req(
        "r3", "A.2", "Proposals shall not exceed 65 pages.", document_kind="amendment"
    )
    found = detect([PAGE_40, amended])
    assert found[0].recommended_id == "r3"
    assert "supersedes what it amends" in found[0].rationale


def test_two_clauses_in_the_same_document_get_no_recommendation():
    """Neither obviously wins, and inventing a winner would be picking which
    requirement the team writes to."""
    other = _req("r7", "L.9", "Proposals shall not exceed 55 pages.")
    found = detect([PAGE_40, other])
    assert found[0].recommended_id == ""
    assert "needs a person" in found[0].rationale


def test_a_superseded_requirement_is_not_compared():
    """Otherwise resolving one contradiction raises it again on the next run."""
    stale = _req("r2", "L-2.3", "The proposal shall not exceed 50 pages.", state="superseded")
    assert detect([PAGE_40, stale]) == []


# ── The parts underneath ─────────────────────────────────────────────────


def test_claims_reads_every_countable_thing_in_one_sentence():
    claims = claims_of(
        "Proposals shall not exceed 40 pages in 12-point font with 1-inch margins, "
        "and no file shall exceed 25 MB."
    )
    assert {c.dimension for c in claims} == {"page_limit", "font_size", "margin", "file_size"}


def test_scope_recognises_a_volume_and_a_named_part():
    assert scope_of("Volume II shall not exceed 20 pages.") == "volume:II"
    assert scope_of("The executive summary shall not exceed 2 pages.") == "part:executive summary"
    assert scope_of("Proposals shall not exceed 40 pages.") == "whole"


def test_detection_is_stable_across_runs():
    """A re-run must not reshuffle a list somebody is working through."""
    first = [c.key for c in detect([PAGE_40, PAGE_50])]
    second = [c.key for c in detect([PAGE_50, PAGE_40])]
    assert first == second


def test_a_requirement_stating_a_rule_and_its_exception_does_not_contradict_itself():
    """"Minimum 12pt Times New Roman; tables 10pt" is one rule with an
    exception. Reporting it as a conflict is the fastest way to teach somebody
    to ignore this tab — and it was the first thing the detector did on a real
    package."""
    both = _req(
        "t1", "Section L",
        "Typography Restrictions: Minimum 12pt Times New Roman, 1-inch margins; tables 10pt",
    )
    assert detect([both]) == []


def test_a_font_size_for_tables_is_scoped_to_tables():
    body = _req("t2", "L.2", "Body text shall be 12-point.")
    tables = _req("t3", "L.3", "Tables may be 10-point.")
    assert detect([body, tables]) == []
