"""An answer is not finished when it is filed.

A Q&A answer can explain a clause, rewrite it, or withdraw it, and those call
for completely different work. These check that each one reaches the ledger,
the response checks, and the queue somebody actually reads.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import verification
from app.pipeline.verification import BLOCKING, IMPORTANT, ROUTINE


def _analysis(**overrides):
    base = dict(
        id="an_test",
        title="Test",
        solicitation_number="RFP-1",
        agency="Agency",
        coverage={"totals": {}, "documents": []},
        ledger={},
        amendments=[],
        response={},
        gates=[],
        dates=[],
        identity=[], scope=[], legal=[], eligibility=[], pricing=[], post_award=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _question(**overrides):
    base = dict(
        id="q_1",
        text="Does the 40-page limit exclude resumes?",
        rationale="L.3 is silent on whether resumes count.",
        status="submitted",
        go_no_go_impact=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _requirement(state: str = "open", reference: str = "L.3"):
    return Requirement(
        id="req_1",
        analysis_id="an_test",
        org_id="org",
        key="k1",
        reference=reference,
        text="Proposals shall not exceed 40 pages.",
        stakes="disqualifying",
        verification="mechanical",
        state=state,
        owner="Dana",
        history=[],
    )


def _check(**overrides):
    base = dict(
        id="chk_1",
        analysis_id="an_test",
        org_id="org",
        requirement_id="req_1",
        response_version=1,
        status="unverifiable",
        verification="mechanical",
        decided_by="rule",
        rule="",
        detail="The agency answered a question about this requirement after this was checked.",
        gap="Re-read the answer against what the response says.",
        risk="high",
        needs_confirmation=False,
        evidence={},
        history=[],
    )
    base.update(overrides)
    return ResponseCheck(**base)


def _dates(**kinds):
    return [
        {"id": f"kd_{kind}", "kind": kind, "label": kind, "at": at.isoformat()}
        for kind, at in kinds.items()
    ]


# ── The reopened answer reaches somebody ─────────────────────────────────


def test_a_reopened_answer_is_not_filed_with_the_never_checked():
    """Somebody wrote that section and it passed. Something since then made
    that verdict unreliable, which is a different thing from a check that could
    never reach a conclusion."""
    reopened = _check(history=[{"at": "2026-05-01", "event": "reopened", "detail": "Q&A set 1"}])
    never = _check(id="chk_2", risk="medium", history=[])

    items = {
        item.id: item
        for item in verification.build(
            analysis=_analysis(), requirements=[_requirement()], checks=[reopened, never]
        )
    }
    # High risk, because a mandatory requirement whose answer is no longer
    # trustworthy can lose the bid as surely as one never answered.
    assert items["check:reopened:chk_1"].severity == BLOCKING
    assert "reopened" in items["check:reopened:chk_1"].title
    assert items["check:unverifiable:chk_2"].severity == ROUTINE


def test_a_check_against_a_withdrawn_requirement_leaves_the_queue():
    """Sending somebody to answer a requirement the agency withdrew is worse
    than sending them nowhere."""
    items = verification.build(
        analysis=_analysis(),
        requirements=[_requirement(state="removed")],
        checks=[_check(status="not_found", risk="high")],
    )
    assert [item for item in items if item.kind == "response"] == []


def test_a_superseded_requirement_does_not_generate_work_either():
    items = verification.build(
        analysis=_analysis(),
        requirements=[_requirement(state="superseded")],
        checks=[_check(status="not_found", risk="high")],
    )
    assert [item for item in items if item.kind == "response"] == []


# ── Questions that never got answered ────────────────────────────────────


def test_an_unanswered_question_that_affects_the_decision_is_raised():
    items = verification.build(
        analysis=_analysis(), requirements=[], checks=[], questions=[_question()]
    )
    item = next(i for i in items if i.id == "question:unanswered:q_1")
    assert item.severity == IMPORTANT
    assert item.tab == "questions"


def test_the_same_question_blocks_once_the_window_has_closed():
    """Before the cut-off it can be chased. After it, the decision gets made
    without the answer."""
    past = datetime.now(UTC) - timedelta(days=3)
    items = verification.build(
        analysis=_analysis(dates=_dates(**{"questions-due": past})),
        requirements=[],
        checks=[],
        questions=[_question()],
    )
    item = next(i for i in items if i.id == "question:unanswered:q_1")
    assert item.severity == BLOCKING
    assert "will be made without it" in item.consequence


def test_a_question_that_does_not_affect_the_decision_is_not_chased():
    """The queue is only useful while everything in it is real work."""
    items = verification.build(
        analysis=_analysis(), requirements=[], checks=[], questions=[_question(go_no_go_impact=False)]
    )
    assert not [i for i in items if i.id.startswith("question:unanswered")]


def test_drafts_left_unsent_past_the_deadline_are_the_worst_case():
    """Nobody asked. Whatever those questions were going to resolve now has to
    be assumed, and the assumption cannot be checked."""
    past = datetime.now(UTC) - timedelta(days=1)
    items = verification.build(
        analysis=_analysis(dates=_dates(**{"questions-due": past})),
        requirements=[],
        checks=[],
        questions=[_question(status="draft")],
    )
    item = next(i for i in items if i.id == "question:missed_cutoff")
    assert item.severity == BLOCKING


def test_drafts_before_the_deadline_are_a_reminder_not_an_alarm():
    future = datetime.now(UTC) + timedelta(days=10)
    items = verification.build(
        analysis=_analysis(dates=_dates(**{"questions-due": future})),
        requirements=[],
        checks=[],
        questions=[_question(status="draft")],
    )
    item = next(i for i in items if i.id == "question:unsent")
    assert item.severity == IMPORTANT
    assert future.date().isoformat() in item.why


def test_an_amendment_landing_on_open_questions_prompts_a_look():
    """Agencies publish Q&A answers with amendments, and nothing here can tell
    which paragraph answers which question."""
    items = verification.build(
        analysis=_analysis(amendments=[{"label": "Amendment 0002", "changes": [], "summary": ""}]),
        requirements=[],
        checks=[],
        questions=[_question()],
    )
    item = next(i for i in items if i.id == "question:check_amendment")
    assert "Amendment 0002" in item.title
    assert "stays marked as done" in item.consequence


def test_an_answered_question_stops_generating_work():
    items = verification.build(
        analysis=_analysis(amendments=[{"label": "A1", "changes": [], "summary": ""}]),
        requirements=[],
        checks=[],
        questions=[_question(status="answered")],
    )
    assert not [i for i in items if i.kind == "question"]


def test_an_analysis_with_no_questions_asks_nothing_about_dates():
    """A guard, because the queue is built on every workspace load and an
    analysis that never had a Q&A pass has no dates to read."""
    assert verification.build(analysis=_analysis(), requirements=[], checks=[], questions=[]) == []
