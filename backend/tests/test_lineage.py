"""One requirement, traced from the clause to the person who signed it off —
and what survives when the response is revised.

The two wrong answers this exists to avoid: re-checking a revision from
scratch, which throws away every signature and asks the team to re-verify a
hundred requirements because two sections changed; and carrying verdicts
forward wholesale, which quietly asserts that somebody checked text they never
saw.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import lineage, verification
from app.pipeline.lineage import CHANGED, LOST, NEW, UNCHANGED
from app.pipeline.verification import BLOCKING, ROUTINE

ANSWER = (
    "Quality Control. Every deliverable passes a two-stage review against the acceptance "
    "criteria in the statement of work before release."
)
REWRITTEN = (
    "Quality Assurance. We apply an ISO 9001 certified management system across all "
    "programmes, audited annually by an external body."
)


def _check(version: int, quote: str, **overrides) -> ResponseCheck:
    fields = dict(
        id=f"chk_v{version}",
        analysis_id="an_test",
        org_id="org",
        requirement_id="req_1",
        response_version=version,
        status="satisfied",
        verification="substantive",
        decided_by="model",
        rule="",
        detail="Addressed on page 4.",
        gap="",
        risk="low",
        needs_confirmation=False,
        evidence={"quote": quote, "page": 4, "documentName": "response.pdf", "located": True},
        history=[],
        lineage={},
        carried_verdict=False,
    )
    fields.update(overrides)
    return ResponseCheck(**fields)


def _requirement(**overrides) -> Requirement:
    fields = dict(
        id="req_1",
        analysis_id="an_test",
        org_id="org",
        key="k1",
        reference="L.4.2",
        text="The Offeror shall describe its approach to quality control.",
        stakes="disqualifying",
        verification="substantive",
        state="open",
        citation={"documentName": "base.pdf", "page": 12, "quote": "describe its approach"},
        history=[],
    )
    fields.update(overrides)
    return Requirement(**fields)


# ── What changed between drafts ──────────────────────────────────────────


def test_an_unchanged_passage_carries_a_human_verdict():
    """The text is the same text. Asking somebody to sign it again teaches them
    to sign without reading."""
    previous = _check(1, ANSWER, decided_by="human", confirmed_by="u_dana",
                      confirmed_at=datetime(2026, 5, 1, tzinfo=UTC))
    current = _check(2, ANSWER, decided_by="model", confirmed_by=None, status="unverifiable")

    links = lineage.compare([previous], [current])
    assert links[0].state == UNCHANGED and links[0].carry_verdict is True

    summary = lineage.apply(links, [previous], [current])
    assert current.confirmed_by == "u_dana"
    assert current.status == "satisfied"
    assert current.carried_verdict is True, "a carried signature must be visible as carried"
    assert summary["carried"] == 1


def test_a_machine_verdict_is_not_carried_because_it_is_recomputed_anyway():
    """Carrying it would only hide that the check ran again."""
    previous = _check(1, ANSWER, decided_by="model", confirmed_by=None)
    current = _check(2, ANSWER, decided_by="model")

    links = lineage.compare([previous], [current])
    assert links[0].state == UNCHANGED and links[0].carry_verdict is False
    lineage.apply(links, [previous], [current])
    assert current.carried_verdict is False


def test_a_rewritten_passage_drops_the_verdict():
    """Whatever was concluded about the old text is not a conclusion about the
    new text."""
    previous = _check(1, ANSWER, decided_by="human", confirmed_by="u_dana")
    current = _check(2, REWRITTEN, status="unverifiable", confirmed_by=None)

    links = lineage.compare([previous], [current])
    assert links[0].state == CHANGED

    summary = lineage.apply(links, [previous], [current])
    assert current.confirmed_by is None
    assert current.status == "unverifiable"
    assert summary["invalidated"] == 1
    assert any(e["event"] == "invalidated" for e in current.history)


def test_a_typo_fix_is_not_a_rewrite():
    """Otherwise every draft invalidates every signature and the feature is
    worse than not having it."""
    tweaked = ANSWER.replace("two-stage", "two stage")
    links = lineage.compare([_check(1, ANSWER, decided_by="human", confirmed_by="u_dana")],
                            [_check(2, tweaked)])
    assert links[0].state == UNCHANGED


def test_an_answer_that_disappeared_is_the_dangerous_case():
    """A section that used to be there and is not, on a requirement somebody
    had already signed off."""
    previous = _check(1, ANSWER, decided_by="human", confirmed_by="u_dana")
    current = _check(2, "", evidence={}, status="not_found", risk="high")

    links = lineage.compare([previous], [current])
    assert links[0].state == LOST
    lineage.apply(links, [previous], [current])
    assert any(e["event"] == "invalidated" for e in current.history)


def test_a_requirement_the_previous_draft_never_saw_is_new():
    current = _check(2, ANSWER, requirement_id="req_2")
    links = lineage.compare([], [current])
    assert links[0].state == NEW


def test_a_requirement_checked_before_and_absent_now_is_reported():
    """Usually because the requirement itself was superseded — but silence
    would be indistinguishable from the check having been dropped."""
    links = lineage.compare([_check(1, ANSWER)], [])
    assert links[0].state == LOST


# ── What reaches the worklist ────────────────────────────────────────────


def _analysis(**overrides):
    base = dict(
        id="an_test", title="T", solicitation_number="R", agency="A",
        coverage={"totals": {}, "documents": []}, ledger={}, amendments=[],
        response={"version": 2}, gates=[], dates=[],
        identity=[], scope=[], legal=[], eligibility=[], pricing=[], post_award=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_a_carried_signature_on_a_mandatory_requirement_gets_one_look():
    check = _check(2, ANSWER, carried_verdict=True, confirmed_by="u_dana",
                   lineage={"state": "unchanged", "detail": "The passage is unchanged."})
    items = verification.build(
        analysis=_analysis(), requirements=[_requirement()], checks=[check]
    )
    item = next(i for i in items if i.id == f"check:carried:{check.id}")
    assert item.severity == ROUTINE
    assert "Almost certainly fine" in item.consequence


def test_a_carried_signature_on_a_scored_requirement_is_left_alone():
    """A queue is only useful while everything in it is real work."""
    check = _check(2, ANSWER, carried_verdict=True, confirmed_by="u_dana")
    items = verification.build(
        analysis=_analysis(),
        requirements=[_requirement(stakes="scored")],
        checks=[check],
    )
    assert not [i for i in items if i.kind == "response"]


def test_a_lost_answer_blocks_and_says_what_happened():
    """Nothing else notices: the check reports a gap, as though the requirement
    had never been answered."""
    check = _check(
        2, "", evidence={}, status="not_found", risk="high",
        lineage={"state": "lost", "detail": "The previous draft had a passage and this one has none."},
    )
    items = verification.build(
        analysis=_analysis(), requirements=[_requirement()], checks=[check]
    )
    item = next(i for i in items if i.id == f"check:lost:{check.id}")
    assert item.severity == BLOCKING
    assert "existed in the previous draft" in item.consequence


# ── The trace itself ─────────────────────────────────────────────────────


def test_the_trace_carries_the_whole_chain():
    """requirement → clause → response section → claim → evidence →
    verification, frozen rather than joined: a lineage reconstructed from live
    rows describes the present, which is the one thing an audit does not need."""
    check = _check(2, ANSWER, decided_by="human", confirmed_by="u_dana",
                   confirmed_at=datetime(2026, 5, 1, tzinfo=UTC))
    trace = lineage.trace(check, _requirement())

    assert trace["clause"] == "L.4.2"
    assert trace["clauseDocument"] == "base.pdf" and trace["clausePage"] == 12
    assert trace["responseDocument"] == "response.pdf" and trace["responsePage"] == 4
    assert trace["claim"] == "Addressed on page 4."
    assert trace["evidenceQuote"].startswith("Quality Control.")
    assert trace["evidenceLocated"] is True
    assert trace["verifiedBy"] == "u_dana" and trace["verifiedAt"].startswith("2026-05-01")


def test_a_trace_with_no_requirement_still_describes_what_was_checked():
    """The requirement may have been superseded since. The trace is a record of
    a moment, not a join."""
    trace = lineage.trace(_check(2, ANSWER), None)
    assert trace["requirementId"] == "req_1"
    assert trace["evidenceQuote"].startswith("Quality Control.")
