"""Colour-team rounds, and the sign-off that closes one.

The discipline being encoded is that a round ends with a named person saying a
bid can proceed — and that closing a round over its own unresolved must-fix
findings is allowed but never quiet.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.db.models.review import CHARTERS, ReviewFinding, ReviewRound
from app.pipeline import review_report, verification
from app.pipeline.verification import BLOCKING, IMPORTANT, ROUTINE
from app.reports import evidence


def _analysis(version: int = 2, **overrides):
    base = dict(
        id="an_test",
        title="Test",
        solicitation_number="RFP-1",
        agency="Agency",
        coverage={"totals": {}, "documents": []},
        ledger={},
        amendments=[],
        response={"version": version},
        gates=[],
        dates=[],
        identity=[], scope=[], legal=[], eligibility=[], pricing=[], post_award=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _round(**overrides) -> ReviewRound:
    base = dict(
        id="rev_1",
        analysis_id="an_test",
        org_id="org",
        colour="red",
        response_version=2,
        charter=CHARTERS["red"],
        reviewers=["Dana", "Ade"],
        status="closed",
        verdict="proceed",
        note=None,
        override_reason=None,
        opened_by="u_dana",
        opened_at=datetime(2026, 5, 1, tzinfo=UTC),
        closed_by="u_ade",
        closed_at=datetime(2026, 5, 3, tzinfo=UTC),
        history=[],
    )
    base.update(overrides)
    return ReviewRound(**base)


def _finding(**overrides) -> ReviewFinding:
    base = dict(
        id="rf_1",
        round_id="rev_1",
        analysis_id="an_test",
        org_id="org",
        requirement_id="req_1",
        severity="must_fix",
        text="Volume II does not price the option years.",
        location="Volume II, §4",
        state="open",
        resolution=None,
        raised_by="Dana",
        raised_at=datetime(2026, 5, 2, tzinfo=UTC),
        resolved_by=None,
        resolved_at=None,
    )
    base.update(overrides)
    return ReviewFinding(**base)


# ── What a round leaves in the worklist ──────────────────────────────────


def test_an_unresolved_must_fix_blocks():
    items = verification.build(
        analysis=_analysis(),
        requirements=[],
        checks=[],
        reviews=[_round()],
        review_findings=[_finding()],
    )
    item = next(i for i in items if i.id == "review:finding:rf_1")
    assert item.severity == BLOCKING
    assert item.tab == "reviews"
    assert "Volume II, §4" == item.reference


def test_a_resolved_finding_leaves_the_worklist():
    items = verification.build(
        analysis=_analysis(),
        requirements=[],
        checks=[],
        reviews=[_round()],
        review_findings=[_finding(state="fixed")],
    )
    assert not [i for i in items if i.id.startswith("review:finding")]


def test_a_lesser_finding_does_not_block():
    """A queue is only useful while everything in it is real work. A "consider"
    is a suggestion, and treating it like a blocker teaches people to ignore
    the blockers."""
    items = verification.build(
        analysis=_analysis(),
        requirements=[],
        checks=[],
        reviews=[_round()],
        review_findings=[_finding(severity="consider")],
    )
    assert not [i for i in items if i.id.startswith("review:finding")]


def test_a_round_that_reviewed_an_earlier_draft_is_stale():
    """A Red Team on draft 2 is not a Red Team on draft 4, and a closed round
    quietly ageing out is how a team believes it has been reviewed."""
    items = verification.build(
        analysis=_analysis(version=4),
        requirements=[],
        checks=[],
        reviews=[_round(response_version=2)],
        review_findings=[],
    )
    item = next(i for i in items if i.id == "review:stale:rev_1")
    assert item.severity == IMPORTANT
    assert "covered draft 2" in item.title and "current draft is 4" in item.title


def test_a_round_on_the_current_draft_is_not_stale():
    items = verification.build(
        analysis=_analysis(version=2),
        requirements=[],
        checks=[],
        reviews=[_round(response_version=2)],
        review_findings=[],
    )
    assert not [i for i in items if i.id.startswith("review:stale")]


def test_an_unsigned_round_is_not_a_review_that_happened():
    items = verification.build(
        analysis=_analysis(),
        requirements=[],
        checks=[],
        reviews=[_round(status="open", verdict=None, closed_by=None, closed_at=None)],
        review_findings=[_finding(severity="should_fix")],
    )
    item = next(i for i in items if i.id == "review:open:rev_1")
    assert item.severity == ROUTINE
    assert "1 finding(s) unresolved" in item.why


def test_an_analysis_with_no_rounds_says_nothing_about_reviews():
    assert verification.build(analysis=_analysis(), requirements=[], checks=[], reviews=[]) == []


# ── The record ───────────────────────────────────────────────────────────


def _flatten(blocks) -> str:
    parts: list[str] = []
    for block in blocks:
        if block[0] == "table":
            parts += [str(cell) for row in block[2] for cell in row]
            parts += [str(header) for header in block[1]]
        else:
            parts.append(str(block[-1]))
    return "\n".join(parts)


def test_the_pack_names_who_signed_each_round():
    flat = _flatten(
        evidence.build(
            analysis=_analysis(),
            requirements=[],
            checks=[],
            queue=[],
            reviews=[_round()],
            review_findings=[_finding(state="fixed")],
        )
    )
    assert "Review rounds" in flat
    assert "u_ade" in flat and "proceed" in flat
    assert "Dana, Ade" in flat


def test_an_overridden_close_is_never_recorded_as_a_clean_pass():
    """The point of an override is that somebody accepted a known risk. A
    record that hides the decision hides the risk with it."""
    flat = _flatten(
        evidence.build(
            analysis=_analysis(),
            requirements=[],
            checks=[],
            queue=[],
            reviews=[_round(override_reason="Submission is in six hours; PM accepts the risk.")],
            review_findings=[_finding()],
        )
    )
    assert "Closed over unresolved must-fix findings" in flat
    assert "PM accepts the risk" in flat


def test_a_rejected_finding_carries_the_reason_it_was_rejected():
    """Otherwise the reviewer who raised it cannot tell it was considered, and
    the next round raises it again."""
    flat = _flatten(
        evidence.build(
            analysis=_analysis(),
            requirements=[],
            checks=[],
            queue=[],
            reviews=[_round()],
            review_findings=[
                _finding(state="rejected", resolution="The RFP does not ask for option pricing.")
            ],
        )
    )
    assert "considered and rejected" in flat
    assert "does not ask for option pricing" in flat


def test_open_findings_are_listed_worst_first():
    blocks = evidence.build(
        analysis=_analysis(),
        requirements=[],
        checks=[],
        queue=[],
        reviews=[_round()],
        review_findings=[
            _finding(id="rf_2", severity="consider", text="Consider a graphic here."),
            _finding(id="rf_1", severity="must_fix", text="Option years are unpriced."),
        ],
    )
    table = next(b for b in blocks if b[0] == "table" and "Severity" in b[1])
    assert table[2][0][0] == "must fix"


def test_every_colour_has_a_charter():
    """A round whose reviewers disagree about its purpose produces findings
    nobody can act on."""
    assert set(CHARTERS) == {"pink", "red", "gold", "white_glove"}
    for colour, charter in CHARTERS.items():
        assert len(charter) > 60, colour


# ── Reading the rounds against each other ────────────────────────────────


def test_a_finding_that_comes_back_is_reported_as_a_regression():
    """Raised in Pink, marked fixed, raised again in Red. The single most
    useful signal a review programme produces, and invisible per-round."""
    pink = _round(id="rev_pink", colour="pink", response_version=1, opened_at=datetime(2026, 4, 1, tzinfo=UTC))
    red = _round(id="rev_red", colour="red", response_version=2, opened_at=datetime(2026, 5, 1, tzinfo=UTC))
    findings = [
        _finding(id="rf_a", round_id="rev_pink", state="fixed", requirement_id="req_7"),
        _finding(id="rf_b", round_id="rev_red", state="open", requirement_id="req_7"),
    ]
    result = review_report.build([red, pink], findings, current_version=2)
    assert len(result["recurring"]) == 1
    again = result["recurring"][0]
    assert again["firstColour"] == "pink" and again["againColour"] == "red"
    assert "did not hold" in again["why"]


def test_findings_with_no_requirement_are_never_matched_across_rounds():
    """Guessing at which prose comment is "the same" as another produces a
    list nobody trusts."""
    pink = _round(id="rev_pink", colour="pink", response_version=1, opened_at=datetime(2026, 4, 1, tzinfo=UTC))
    red = _round(id="rev_red", colour="red", response_version=2, opened_at=datetime(2026, 5, 1, tzinfo=UTC))
    findings = [
        _finding(id="rf_a", round_id="rev_pink", state="fixed", requirement_id=None),
        _finding(id="rf_b", round_id="rev_red", state="open", requirement_id=None),
    ]
    assert review_report.build([pink, red], findings)["recurring"] == []


def test_a_must_fix_left_open_by_a_closed_round_is_surfaced():
    """A closed round stops being looked at, so nothing raises it again."""
    row = _round(status="closed", verdict="proceed")
    result = review_report.build([row], [_finding(state="open", severity="must_fix")])
    assert len(result["carried"]) == 1
    assert "stops being looked at" in result["carried"][0]["why"]


def test_accepted_must_fixes_are_called_deferrals_not_a_pass():
    row = _round(status="closed", verdict="proceed")
    result = review_report.build([row], [_finding(state="accepted", severity="must_fix")])
    note = result["rounds"][0]["note"]
    assert "deferrals" in note


def test_a_sign_off_against_an_older_draft_is_stale_not_wrong():
    row = _round(status="closed", verdict="proceed", response_version=2)
    result = review_report.build([row], [], current_version=4)
    assert result["rounds"][0]["stale"] is True
    assert "no longer covers" in result["rounds"][0]["note"]


def test_an_override_is_never_reported_as_a_clean_pass():
    row = _round(status="closed", verdict="proceed", override_reason="Deadline is tomorrow.")
    result = review_report.build([row], [_finding(state="open", severity="must_fix")])
    assert result["rounds"][0]["overridden"] is True
    assert "override, not as a pass" in result["rounds"][0]["note"]


def test_the_trend_reads_two_closed_rounds_against_each_other():
    pink = _round(
        id="rev_pink", colour="pink", response_version=1, status="closed", verdict="proceed_with_fixes",
        opened_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    red = _round(
        id="rev_red", colour="red", response_version=2, status="closed", verdict="proceed",
        opened_at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    findings = [
        _finding(id="rf_1", round_id="rev_pink", state="fixed", requirement_id="req_1"),
        _finding(id="rf_2", round_id="rev_pink", state="fixed", requirement_id="req_2"),
        _finding(id="rf_3", round_id="rev_red", state="fixed", requirement_id="req_3"),
    ]
    trend = review_report.build([pink, red], findings, current_version=2)["trend"]
    assert trend["direction"] == "improving"
    assert trend["roundsClosed"] == 2


def test_a_single_round_is_not_a_trend():
    trend = review_report.build([_round(status="closed", verdict="proceed")], [])["trend"]
    assert trend["direction"] == "single"
    assert "second round" in trend["detail"]


def test_a_reviewer_who_raised_nothing_is_still_counted():
    """A round nobody actually read is a sign-off with nothing behind it."""
    row = _round(reviewers=["Dana", "Ade"])
    reviewers = review_report.build([row], [_finding(raised_by="Dana")])["reviewers"]
    by_name = {r["reviewer"]: r for r in reviewers}
    assert by_name["Ade"]["rounds"] == 1 and by_name["Ade"]["raised"] == 0
    assert by_name["Dana"]["raised"] == 1
