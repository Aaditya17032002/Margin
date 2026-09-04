"""The machinery around the model, checked without one.

The adjudication corpus measures a model's judgement. These check the things
that must hold whatever the model says — and each of them is a way a wrong
`satisfied` could reach a proposal manager.
"""

from __future__ import annotations

import json

import pytest

from evals.adjudication.runner import (
    ScriptedModel,
    check,
    load_cases,
    load_thresholds,
    score,
    scripted_model_for,
)
from app.pipeline.traceability import FAILED, SATISFIED, UNVERIFIABLE


def _fixed(reply: str):
    model = ScriptedModel(reply)
    return lambda _case: model


@pytest.mark.asyncio
async def test_a_right_answer_survives_the_journey_to_a_verdict():
    """The offline run answers every case correctly by construction, so
    anything less than perfect means parsing, retrieval or grounding altered a
    verdict on the way through."""
    cases = load_cases()
    summary = await score(cases, scripted_model_for)

    assert summary.correct == summary.total, [
        (r.id, r.expected, r.actual) for r in summary.results if not r.correct
    ]
    assert check(summary, load_thresholds()["scripted"]) == []


@pytest.mark.asyncio
async def test_a_verdict_outside_the_rubric_never_becomes_a_clearance():
    """A model that answers "yes" or invents a status has not adjudicated
    anything, and treating that as agreement is the cheapest possible way to
    ship a gap."""
    cases = load_cases()[:4]
    for reply in (
        '{"status": "compliant", "detail": "looks fine", "gap": "", "quote": ""}',
        '{"status": true}',
        "Yes, this looks satisfied to me.",
        "",
    ):
        summary = await score(cases, _fixed(reply))
        assert {r.actual for r in summary.results} <= {UNVERIFIABLE, "not_found"}, reply
        assert summary.false_satisfied == []


@pytest.mark.asyncio
async def test_a_quote_that_is_not_in_the_response_downgrades_the_claim():
    """The same grounding rule citations are held to. A verdict resting on an
    invented passage is not a verdict."""
    cases = [c for c in load_cases() if c["id"] == "plain-answer"]
    summary = await score(
        cases,
        _fixed(
            json.dumps(
                {
                    "status": "satisfied",
                    "detail": "fully addressed",
                    "gap": "",
                    "quote": "We hold ISO 9001 certification, which the response never claims.",
                }
            )
        ),
    )
    assert summary.results[0].actual == UNVERIFIABLE
    assert summary.false_satisfied == []


@pytest.mark.asyncio
async def test_a_model_that_clears_everything_is_caught_by_the_score_that_matters():
    """Accuracy alone would call this a bad run. The point of scoring
    false-satisfied separately is that this is not a bad run — it is an unsafe
    one, and no number of correct verdicts elsewhere compensates."""
    cases = load_cases()
    summary = await score(
        cases,
        _fixed(json.dumps({"status": "satisfied", "detail": "yes", "gap": "", "quote": ""})),
    )

    assert summary.false_satisfied, "a model that clears everything scored clean"
    failures = check(summary, load_thresholds()["live"])
    assert any("false-satisfied" in failure for failure in failures)


@pytest.mark.asyncio
async def test_a_model_that_refuses_everything_is_not_flagged_as_dangerous():
    """The cautious failure mode. It is bad, and it is bad in the direction
    that costs five minutes rather than the bid."""
    cases = load_cases()
    summary = await score(
        cases,
        _fixed(json.dumps({"status": "unverifiable", "detail": "cannot tell", "gap": "", "quote": ""})),
    )

    assert summary.false_satisfied == []
    failures = check(summary, load_thresholds()["live"])
    assert not any("false-satisfied" in failure for failure in failures)
    # It still fails, on the floors that measure usefulness rather than safety.
    assert any("accuracy" in failure or "safe rate" in failure for failure in failures)


@pytest.mark.asyncio
async def test_a_mandatory_requirement_is_never_reported_as_settled():
    """An invariant, not a score. A build where this fails is broken."""
    cases = load_cases()
    summary = await score(
        cases,
        _fixed(json.dumps({"status": "satisfied", "detail": "yes", "gap": "", "quote": ""})),
    )

    mandatory = [r for r in summary.results if r.stakes == "disqualifying"]
    assert mandatory
    assert summary.mandatory_cleared == []
    assert all(r.needs_confirmation for r in mandatory if r.actual == SATISFIED)


@pytest.mark.asyncio
async def test_a_contradiction_is_reported_as_a_failure_not_as_doubt():
    """A response saying Secret against a Top Secret requirement is a rewrite;
    one that says nothing is a blank page. Collapsing both into "could not
    tell" buries a hard failure in the pile of things to check."""
    cases = [c for c in load_cases() if c["id"] == "answered-for-the-wrong-thing"]
    summary = await score(
        cases,
        _fixed(
            json.dumps(
                {
                    "status": "failed",
                    "detail": "The response offers Secret; the requirement is Top Secret.",
                    "gap": "Top Secret clearances are not evidenced.",
                    "quote": "All Acme staff assigned to this programme hold an active Secret clearance",
                }
            )
        ),
    )
    assert summary.results[0].actual == FAILED


def test_every_case_states_why_it_is_in_the_corpus():
    """A case nobody can explain is a case nobody will maintain, and an
    adversarial corpus is only useful while its adversaries are understood."""
    for case in load_cases():
        assert case.get("why"), case["id"]
        assert case["expected"] in {SATISFIED, "partial", FAILED, "not_found", UNVERIFIABLE}
        assert case["passages"], case["id"]


def test_the_corpus_covers_both_directions_of_error():
    """A corpus of only-answerable cases measures nothing about caution, and a
    corpus of only-unanswerable ones rewards refusing to answer."""
    expected = {case["expected"] for case in load_cases()}
    assert SATISFIED in expected
    assert {"not_found", "unverifiable"} <= expected
    assert any(case["stakes"] == "disqualifying" for case in load_cases())
