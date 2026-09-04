"""The two questions a capture manager has on the same morning: should we bid
this, and can we still finish it.

Neither is answered by the product. The first is recorded with the evidence as
it stood; the second walks the deadline backwards and says what is already too
late.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace as N

from app.db.models.requirement import Requirement
from app.pipeline import decision
from app.pipeline.critical_path import AT_RISK, CLEAR, PAST, build


def _analysis(**overrides):
    base = dict(
        id="an_test", title="T", solicitation_number="R", agency="Agency",
        estimated_value=5_000_000, gates=[], dates=[], evaluation=[],
        coverage={"totals": {"pages": 60, "pagesScanned": 60, "emptyDocuments": 0}},
        ledger={}, amendments=[], response={},
        identity=[], scope=[], legal=[], eligibility=[], pricing=[], post_award=[],
    )
    base.update(overrides)
    return N(**base)


def _due(days: int) -> list[dict]:
    at = datetime.now(UTC) + timedelta(days=days)
    return [{"id": "kd1", "kind": "proposal-due", "label": "Proposals due", "at": at.isoformat()}]


def _requirement(id: str, reference: str, **overrides) -> Requirement:
    fields = dict(
        id=id, analysis_id="an_test", org_id="org", key=f"k_{id}", reference=reference,
        text=f"Requirement {reference}.", stakes="scored", verification="substantive",
        state="open", status="unassigned", owner=None, due_at=None, history=[],
    )
    fields.update(overrides)
    return Requirement(**fields)


def _round(colour: str = "red", status: str = "open"):
    return N(colour=colour, status=status)


# ── Critical path ────────────────────────────────────────────────────────


def test_without_a_submission_date_nothing_can_be_scheduled():
    """Said plainly rather than shown as a path with invented dates."""
    path = build(analysis=_analysis(), requirements=[_requirement("r1", "L.1")])
    assert path.submission is None
    assert path.items == []
    assert any("No submission date" in note for note in path.notes)


def test_review_rounds_push_the_start_date_back():
    """A Red Team cannot review a section nobody has drafted."""
    without = build(analysis=_analysis(dates=_due(20)), requirements=[])
    with_review = build(analysis=_analysis(dates=_due(20)), requirements=[], rounds=[_round("red")])

    earliest_without = min(s.due for s in without.steps if s.due)
    earliest_with = min(s.due for s in with_review.steps if s.due)
    assert earliest_with < earliest_without


def test_only_rounds_the_team_actually_opened_count():
    """Inventing a Red Team nobody planned would produce a deadline nobody
    agreed to."""
    path = build(
        analysis=_analysis(dates=_due(20)), requirements=[], rounds=[_round("red", status="closed")]
    )
    assert not [s for s in path.steps if s.kind == "review"]
    assert any("No review round is open" in note for note in path.notes)


def test_unstarted_work_past_its_start_date_is_a_decision_not_a_task():
    """Either scope comes out or the deadline moves, and both of those are
    conversations rather than to-dos."""
    path = build(
        analysis=_analysis(dates=_due(1)),
        requirements=[_requirement("r1", "L.1", stakes="disqualifying")],
        rounds=[_round("red"), _round("gold")],
    )
    item = path.items[0]
    assert item.state == PAST
    assert "decisions rather than tasks" in item.reason
    assert path.as_dict()["summary"]["blockingPastThePoint"] == 1


def test_work_under_way_past_the_date_is_recoverable():
    """A different situation from nothing having been started, and the wrong
    call either way costs somebody a night."""
    path = build(
        analysis=_analysis(dates=_due(1)),
        requirements=[_requirement("r1", "L.1", status="drafted", owner="Dana")],
        rounds=[_round("red"), _round("gold")],
    )
    assert path.items[0].state == AT_RISK
    assert "can still make it" in path.items[0].reason


def test_a_completed_requirement_is_off_the_path():
    path = build(
        analysis=_analysis(dates=_due(1)),
        requirements=[_requirement("r1", "L.1", status="complete", owner="Dana")],
    )
    assert path.items == []


def test_an_unowned_mandatory_requirement_cannot_be_scheduled_at_all():
    path = build(
        analysis=_analysis(dates=_due(60)),
        requirements=[_requirement("r1", "L.1", stakes="disqualifying")],
    )
    assert path.items[0].state == AT_RISK
    assert "cannot be scheduled" in path.items[0].reason


def test_plenty_of_time_and_an_owner_is_clear():
    path = build(
        analysis=_analysis(dates=_due(60)),
        requirements=[_requirement("r1", "L.1", owner="Dana", status="drafted")],
    )
    assert path.items[0].state == CLEAR
    assert "slack" in path.items[0].reason


def test_a_requirements_own_due_date_wins_when_it_is_earlier():
    """The team's internal date is the one that governs whether the work
    happens."""
    early = datetime.now(UTC) + timedelta(days=2)
    path = build(
        analysis=_analysis(dates=_due(60)),
        requirements=[_requirement("r1", "L.1", owner="Dana", due_at=early)],
    )
    assert path.items[0].latest_start == early.date()


def test_the_worst_items_come_first():
    """The top of this list is the next conversation somebody has to have."""
    path = build(
        analysis=_analysis(dates=_due(1)),
        requirements=[
            _requirement("r1", "L.9", owner="Dana", status="drafted"),
            _requirement("r2", "L.1", stakes="disqualifying"),
        ],
        rounds=[_round("red"), _round("gold")],
    )
    assert path.items[0].reference == "L.1"
    assert path.items[0].state == PAST


# ── Decision record ──────────────────────────────────────────────────────


def test_the_evidence_is_the_uncomfortable_half():
    """A record that only carried the reasons to bid would be a marketing
    document. The value of one is that it is what you read when it went
    wrong."""
    evidence = decision.assemble(
        analysis=_analysis(
            gates=[
                {"question": "Do you hold a facility clearance?", "weight": "hard", "met": False},
                {"question": "Are you SAM registered?", "weight": "hard", "met": None},
            ]
        ),
        requirements=[_requirement("r1", "L.1", stakes="disqualifying")],
    )
    kinds = {c.kind for c in evidence.considerations}
    assert "gate" in kinds and "ownership" in kinds
    assert any(c.weight == "against" for c in evidence.considerations)
    assert any(c.weight == "unknown" for c in evidence.considerations)


def test_an_unread_document_is_recorded_as_unknown_not_as_a_reason_against():
    """It is not an argument either way. It is a hole in what the decision
    could have been based on."""
    evidence = decision.assemble(
        analysis=_analysis(
            coverage={"totals": {"pages": 60, "pagesScanned": 40, "emptyDocuments": 1}}
        ),
        requirements=[],
    )
    coverage = next(c for c in evidence.considerations if c.kind == "coverage")
    assert coverage.weight == "unknown"


def test_open_contradictions_are_carried_into_the_record():
    conflict = N(state="open", summary="Two different page limits: L.1 says 40, L-2 says 50.")
    evidence = decision.assemble(
        analysis=_analysis(), requirements=[], contradictions=[conflict]
    )
    assert any(c.kind == "contradiction" for c in evidence.considerations)


def test_weight_sitting_on_unanswered_factors_argues_against():
    evidence = decision.assemble(
        analysis=_analysis(),
        requirements=[],
        weighting={"weightAtRisk": 0.6, "mostExposed": [{"name": "Technical Approach"}]},
    )
    item = next(c for c in evidence.considerations if c.kind == "evaluation")
    assert item.weight == "against"
    assert "Technical Approach" in item.detail


def test_readiness_is_not_a_recommendation():
    """A number that said "72% — bid" would be believed, and nothing here knows
    whether the company wants this customer."""
    evidence = decision.assemble(
        analysis=_analysis(gates=[{"question": "?", "weight": "hard", "met": None}]),
        requirements=[],
    )
    report = decision.readiness(evidence)
    assert set(report) == {"against", "unknown", "settled", "headline"}
    assert report["settled"] is False
    assert "still unknown" in report["headline"]


def test_a_clean_analysis_says_everything_checkable_was_settled():
    report = decision.readiness(decision.assemble(analysis=_analysis(), requirements=[]))
    assert report["settled"] is True
    assert "Everything Margin can check" in report["headline"]
