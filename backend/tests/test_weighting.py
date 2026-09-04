"""Where the score is, and whether the response is there.

A compliance matrix treats every requirement as equally worth answering.
Evaluators do not, and a team with four days left should spend them on the
forty-percent factor rather than on whatever happens to be red.
"""

from __future__ import annotations

from types import SimpleNamespace as N

import pytest

from app.pipeline.weighting import MATCH_FLOOR, build, match, summarise


def _factor(id: str, name: str, weight: float, method: str = "") -> dict:
    return {"id": id, "name": name, "weight": weight, "method": method, "citation": {}}


def _req(id: str, reference: str, text: str, *, stakes: str = "scored", state: str = "open"):
    return N(id=id, reference=reference, text=text, stakes=stakes, state=state, owner=None)


def _check(requirement_id: str, status: str):
    return N(requirement_id=requirement_id, status=status)


TECHNICAL = _factor(
    "f1", "Factor 1: Technical Approach", 40,
    "Architecture, modernization roadmap and service level commitments.",
)
PAST = _factor("f2", "Factor 2: Past Performance", 10, "Relevance of recent contracts.")

ARCHITECTURE = _req(
    "r1", "L.4.1", "The Offeror shall describe its system architecture and modernization roadmap."
)
CLEARANCE = _req("r2", "H.2", "Personnel shall hold a Secret facility clearance.", stakes="disqualifying")


# ── Which requirements sit under which factor ────────────────────────────


def test_a_factor_that_names_a_clause_claims_it_outright():
    """The strongest possible signal: the solicitation is telling you directly
    which requirements this factor scores."""
    factor = _factor("f1", "Factor 1", 40, "Evaluated on the plan required by Section L.4.")
    strength, why = match(factor, _req("r1", "L.4.1", "Something entirely unrelated to the words."))
    assert strength == 1.0
    assert "names this clause" in why


def test_shared_vocabulary_maps_a_requirement_to_a_factor():
    strength, why = match(TECHNICAL, ARCHITECTURE)
    assert strength >= MATCH_FLOOR
    assert "architecture" in why


def test_an_unrelated_requirement_is_not_dragged_in():
    """Every solicitation says "the Offeror shall" everywhere. Without a floor
    every factor claims every requirement and the lens says nothing."""
    assert match(TECHNICAL, CLEARANCE)[0] < MATCH_FLOOR


def test_a_superseded_requirement_is_not_counted_under_a_factor():
    stale = _req("r9", "L.4.1", ARCHITECTURE.text, state="superseded")
    coverage = build([TECHNICAL], [stale], [])
    assert coverage[0].requirement_ids == []


# ── Weight against weakness ──────────────────────────────────────────────


def test_the_lens_orders_by_where_the_most_points_are_least_defended():
    """Not by weight, and not by how red something is. A ten-percent factor
    with nothing answered matters less than a forty-percent factor half
    answered."""
    big_gap = _req("r1", "L.4.1", "The Offeror shall describe its architecture and roadmap.")
    small_gap = _req("r2", "L.6", "The Offeror shall describe recent contracts and relevance.")
    coverage = build(
        [TECHNICAL, PAST],
        [big_gap, small_gap],
        [_check("r1", "not_found"), _check("r2", "not_found")],
    )
    assert coverage[0].name.startswith("Factor 1")
    assert coverage[0].exposure > coverage[1].exposure


def test_a_fully_answered_factor_carries_no_exposure():
    coverage = build([TECHNICAL], [ARCHITECTURE], [_check("r1", "satisfied")])
    assert coverage[0].weakness == 0.0
    assert coverage[0].exposure == 0.0


def test_unverifiable_sits_between_a_gap_and_an_answer():
    """It is genuinely unknown. Treating it as either would be a guess inside a
    number people act on."""
    answered = build([TECHNICAL], [ARCHITECTURE], [_check("r1", "satisfied")])[0]
    unknown = build([TECHNICAL], [ARCHITECTURE], [_check("r1", "unverifiable")])[0]
    missing = build([TECHNICAL], [ARCHITECTURE], [_check("r1", "not_found")])[0]
    assert answered.weakness < unknown.weakness < missing.weakness


def test_an_unchecked_requirement_is_not_scored_as_either():
    """No response is bound. Calling that a gap or an answer would put a number
    in front of somebody that means nothing."""
    coverage = build([TECHNICAL], [ARCHITECTURE], [])
    # It is counted, so the factor does not look empty, and it does not move
    # the weakness, so the number stays honest.
    assert coverage[0].counts == {"unchecked": 1}
    assert coverage[0].weakness == 0.0
    assert coverage[0].exposure == 0.0


def test_a_mandatory_gap_under_a_factor_is_named():
    mandatory = _req(
        "r1", "L.4.1", "The Offeror shall describe its architecture and roadmap.",
        stakes="disqualifying",
    )
    coverage = build([TECHNICAL], [mandatory], [_check("r1", "not_found")])
    assert coverage[0].blocking == ["L.4.1"]


# ── What it refuses to claim ─────────────────────────────────────────────


def test_shares_are_computed_from_stated_weights_only():
    """A factor with no weight is not worth nothing — "Basis for Award" is not
    a scored factor at all."""
    basis = _factor("f3", "Basis of Award", 0, "Best value trade-off.")
    coverage = {c.name: c for c in build([TECHNICAL, PAST, basis], [ARCHITECTURE], [])}
    assert coverage["Basis of Award"].share == 0.0
    assert coverage["Factor 1: Technical Approach"].share == pytest.approx(0.8)


def test_a_solicitation_with_no_weights_says_so_rather_than_inventing_them():
    """Showing every factor as equally important would be inventing the thing
    the lens exists to reveal."""
    coverage = build(
        [_factor("f1", "Technical", 0), _factor("f2", "Price", 0)], [ARCHITECTURE], []
    )
    report = summarise(coverage)
    assert report["weighted"] == 0 and report["unweighted"] == 2
    assert report["weightAtRisk"] == 0.0


def test_factors_no_requirement_maps_to_are_reported():
    """A factor with nothing under it means either the extraction missed the
    requirements or the factor is not about requirements at all — and both are
    worth knowing."""
    report = summarise(build([TECHNICAL, PAST], [ARCHITECTURE], []))
    assert "Factor 2: Past Performance" in report["unmapped"]


def test_the_summary_names_the_most_exposed_factors():
    coverage = build([TECHNICAL, PAST], [ARCHITECTURE], [_check("r1", "not_found")])
    report = summarise(coverage)
    assert report["mostExposed"][0]["name"] == "Factor 1: Technical Approach"
    assert 0 < report["weightAtRisk"] <= 1
