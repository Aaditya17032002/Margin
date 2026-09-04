"""What the organisation already knows, in a form a requirement can query.

The rule both matchers obey: never hand somebody text or a claim without the
context that decides whether to use it. A score nobody can argue with is a
score nobody reads.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace as N

from app.pipeline.memory import RELEVANCE_FLOOR, match_past_performance, relevance, suggest


def _record(**overrides):
    base = dict(
        id="pp1",
        title="311 CRM modernisation for the City of Boston",
        customer="City of Boston",
        agency="City of Boston",
        scope="Replaced a legacy 311 customer relationship management platform, including data "
              "migration, integration with dispatch, and accessibility remediation.",
        value=4_000_000.0,
        started_at=date(2023, 1, 1),
        ended_at=date.today() - timedelta(days=240),
        ongoing=False,
        naics="541512",
        capabilities=["CRM", "data migration", "accessibility"],
        reference_name="J. Okafor",
        reference_checked_at=date.today() - timedelta(days=60),
    )
    base.update(overrides)
    return N(**base)


CRM_REQUIREMENT = (
    "The Offeror shall demonstrate experience modernising a 311 customer relationship "
    "management platform, including data migration and accessibility remediation."
)


# ── Past performance ─────────────────────────────────────────────────────


def test_a_relevant_contract_reports_every_signal_separately():
    """"This one matches" is an assertion. "Same agency, same NAICS, ended
    eight months ago" is a case somebody can make in a proposal."""
    item = relevance(
        _record(), requirement_text=CRM_REQUIREMENT, agency="City of Boston",
        naics="541512", value=5_000_000.0,
    )
    assert item.score >= RELEVANCE_FLOOR
    assert set(item.signals) >= {"scope", "agency", "naics", "recency", "value"}
    assert "migration" in item.signals["scope"]["shared"]
    assert item.signals["agency"]["score"] == 1.0


def test_an_unrelated_contract_is_not_offered():
    grounds = _record(
        title="Grounds maintenance", scope="Mowing, landscaping and snow removal.",
        capabilities=["landscaping"],
    )
    assert match_past_performance([grounds], requirement_text=CRM_REQUIREMENT) == []


def test_a_current_contract_scores_recency_outright():
    item = relevance(_record(ongoing=True, ended_at=None), requirement_text=CRM_REQUIREMENT)
    assert item.signals["recency"]["score"] == 1.0


def test_an_old_contract_is_offered_with_the_age_stated():
    """Not filtered out — the recency window varies and the team knows theirs —
    but the age is said out loud."""
    old = _record(ended_at=date.today() - timedelta(days=365 * 5))
    item = relevance(old, requirement_text=CRM_REQUIREMENT)
    assert any("outside the recency window" in concern for concern in item.concerns)


def test_an_order_of_magnitude_in_value_is_a_concern():
    """Evaluators read "comparable scope" as including size."""
    item = relevance(
        _record(value=50_000.0), requirement_text=CRM_REQUIREMENT, value=10_000_000.0
    )
    assert any("order of magnitude" in concern for concern in item.concerns)


def test_a_missing_reference_is_flagged():
    item = relevance(_record(reference_name=""), requirement_text=CRM_REQUIREMENT)
    assert any("No reference recorded" in concern for concern in item.concerns)


def test_a_stale_reference_is_flagged():
    """A reference who has moved on fails at the worst possible time."""
    item = relevance(
        _record(reference_checked_at=date.today() - timedelta(days=800)),
        requirement_text=CRM_REQUIREMENT,
    )
    assert any("last confirmed" in concern for concern in item.concerns)


def test_an_unconfirmed_reference_is_flagged():
    item = relevance(_record(reference_checked_at=None), requirement_text=CRM_REQUIREMENT)
    assert any("still willing" in concern for concern in item.concerns)


def test_matches_are_ordered_by_relevance():
    near = _record(id="pp1")
    far = _record(
        id="pp2", title="Helpdesk support", scope="Tier 1 helpdesk and accessibility support.",
        agency="Other", capabilities=["accessibility"], naics="561422",
    )
    matches = match_past_performance(
        [far, near], requirement_text=CRM_REQUIREMENT, agency="City of Boston", naics="541512"
    )
    assert matches[0].record_id == "pp1"


# ── Content blocks ───────────────────────────────────────────────────────


def _block(**overrides):
    base = dict(
        id="cb1",
        title="Quality control approach",
        text="Every deliverable passes a two-stage review before release.",
        requirement_kind="obligation",
        tags=["quality", "review"],
        source_analysis_id="an_old",
        source_solicitation="RFP-2025-0100",
        source_agency="USDA FNS",
        source_reference="L.4.2",
        source_requirement="The Offeror shall describe its approach to quality control for deliverables.",
        outcome="won",
        last_verdict="satisfied",
        verified_by="u_dana",
        verified_at=datetime(2025, 6, 1, tzinfo=UTC),
        times_used=3,
        last_used_at=datetime.now(UTC) - timedelta(days=90),
        retired_at=None,
        retired_reason=None,
    )
    base.update(overrides)
    return N(**base)


QUALITY = N(
    kind="obligation",
    text="The Offeror shall describe its approach to quality control for all deliverables.",
)


def test_a_block_is_never_offered_without_what_happened_to_it():
    """The whole difference between a library and a pile of paragraphs."""
    [item] = suggest([_block()], QUALITY)
    assert "L.4.2" in item.provenance
    assert "RFP-2025-0100" in item.provenance
    assert "that bid was won" in item.provenance
    assert "u_dana verified it" in item.provenance


def test_an_unverified_block_from_a_lost_bid_is_offered_with_both_facts():
    """Still offered — most losses have nothing to do with any one paragraph —
    and both facts are said."""
    [item] = suggest([_block(outcome="lost", verified_by=None, last_verdict="")], QUALITY)
    assert any("Nobody ever verified" in caution for caution in item.cautions)
    assert any("bid it was written for was lost" in caution for caution in item.cautions)


def test_a_retired_block_is_never_offered():
    """A block somebody marked as no longer true is exactly the text that must
    not resurface at 2am."""
    retired = _block(retired_at=datetime.now(UTC), retired_reason="Staffing model changed.")
    assert suggest([retired], QUALITY) == []


def test_a_block_of_the_wrong_kind_is_never_offered():
    """A page-limit block is not an answer to a narrative requirement, however
    much vocabulary they share."""
    limit_block = _block(requirement_kind="limit")
    assert suggest([limit_block], QUALITY) == []


def test_a_block_nobody_has_used_says_so():
    [item] = suggest([_block(times_used=0, last_used_at=None)], QUALITY)
    assert any("never been used" in caution for caution in item.cautions)


def test_a_block_nobody_has_touched_in_years_says_so():
    """Check that it still describes how the company actually works."""
    stale = _block(last_used_at=datetime.now(UTC) - timedelta(days=365 * 3))
    [item] = suggest([stale], QUALITY)
    assert any("Last used" in caution for caution in item.cautions)


def test_an_unrelated_block_is_not_offered():
    unrelated = _block(
        source_requirement="The Contractor shall provide snow removal within four hours.",
        tags=["snow"], title="Snow removal",
    )
    assert suggest([unrelated], QUALITY) == []


def test_a_verified_block_from_a_won_bid_carries_no_cautions():
    assert suggest([_block()], QUALITY)[0].cautions == []
