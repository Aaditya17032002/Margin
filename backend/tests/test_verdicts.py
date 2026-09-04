"""A judgement is a labelled example, and it used to be thrown away.

Every confirmation and correction is produced by somebody holding the document
who knows the answer. These check that the record survives the thing it
describes, and that the aggregate points somewhere a fix can be aimed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models.verdict import CONFIRMED, CORRECTED, FLAGGED, Verdict
from app.pipeline.verdicts import disagreement, outcome_of, record
from evals.verdicts import exportable, to_adjudication_case


class FakeSession:
    def __init__(self):
        self.added: list[Verdict] = []

    def add(self, row):
        self.added.append(row)


def _verdict(**overrides) -> Verdict:
    fields = dict(
        id="vd_1",
        org_id="org",
        analysis_id="an_1",
        subject_kind="response_check",
        subject_id="chk_1",
        outcome=CORRECTED,
        machine_status="satisfied",
        machine_decided_by="model",
        machine_rule="",
        machine_detail="Addressed on page 4.",
        machine_evidence={},
        human_status="not_found",
        note=None,
        reference="L.4.2",
        requirement_text="The Offeror shall describe its approach to quality control.",
        stakes="scored",
        verification="substantive",
        response_excerpt="Quality is central to everything we do.",
        actor="u_dana",
        at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    fields.update(overrides)
    return Verdict(**fields)


# ── What kind of judgement was it ────────────────────────────────────────


def test_agreeing_is_a_confirmation():
    assert outcome_of("satisfied", "satisfied", None) == CONFIRMED


def test_disagreeing_is_a_correction():
    assert outcome_of("satisfied", "not_found", None) == CORRECTED


def test_a_note_without_a_change_is_a_flag():
    """"Right, but for the wrong reason" is the most informative feedback there
    is and the easiest kind to lose."""
    assert outcome_of("satisfied", "satisfied", "Right answer, wrong clause.") == FLAGGED


def test_a_note_alongside_a_change_is_still_a_correction():
    assert outcome_of("satisfied", "failed", "The clearance level is wrong.") == CORRECTED


# ── The record survives the thing it describes ───────────────────────────


@pytest.mark.asyncio
async def test_the_context_is_frozen_not_referenced():
    """A label pointing at a requirement stops being a label the moment an
    amendment rewords that requirement."""
    session = FakeSession()
    await record(
        session,
        org_id="org",
        analysis_id="an_1",
        subject_kind="response_check",
        subject_id="chk_1",
        machine_status="satisfied",
        machine_decided_by="model",
        machine_detail="Addressed on page 4.",
        human_status="not_found",
        reference="L.4.2",
        requirement_text="The Offeror shall describe its approach to quality control.",
        response_excerpt="Quality is central to everything we do.",
        actor="u_dana",
    )
    row = session.added[0]

    assert row.outcome == CORRECTED
    assert row.requirement_text.startswith("The Offeror shall")
    assert row.response_excerpt.startswith("Quality is central")
    assert row.machine_status == "satisfied" and row.human_status == "not_found"
    assert row.at is not None


@pytest.mark.asyncio
async def test_a_confirmation_still_records_what_the_machine_said():
    """Confirmations are how "the page-limit rule is reliable" becomes a
    measured claim rather than an impression."""
    session = FakeSession()
    await record(
        session,
        org_id="org",
        analysis_id="an_1",
        subject_kind="response_check",
        subject_id="chk_1",
        machine_status="satisfied",
        machine_decided_by="rule",
        machine_rule="page_limit",
        human_status="satisfied",
        actor="u_dana",
    )
    row = session.added[0]
    assert row.outcome == CONFIRMED
    assert row.machine_rule == "page_limit"


# ── Where are we wrong ───────────────────────────────────────────────────


def test_the_report_points_at_something_a_fix_can_be_aimed_at():
    """A single accuracy figure says the product is 87% right and gives nobody
    anywhere to start."""
    rows = [
        _verdict(machine_rule="page_limit", verification="mechanical", outcome=CORRECTED,
                 machine_status="failed", human_status="satisfied"),
        _verdict(machine_rule="page_limit", verification="mechanical", outcome=CORRECTED,
                 machine_status="failed", human_status="satisfied"),
        _verdict(machine_rule="typography", verification="mechanical", outcome=CONFIRMED,
                 machine_status="unverifiable", human_status="unverifiable"),
        _verdict(machine_rule="", verification="substantive", outcome=CONFIRMED,
                 machine_status="satisfied", human_status="satisfied"),
    ]
    report = disagreement(rows)

    assert report["total"] == 4 and report["corrected"] == 2
    assert report["byRule"][0]["name"] == "page_limit"
    assert report["byRule"][0]["correctionRate"] == 1.0
    # The direction matters: this is the rule failing compliant responses.
    assert {"from": "failed", "to": "satisfied", "count": 2} in report["transitions"]


def test_corrections_out_of_satisfied_are_counted_apart():
    """These are the ones that would have gone out in a proposal. A correction
    the other way is the product being too cautious."""
    rows = [
        _verdict(machine_status="satisfied", human_status="failed", outcome=CORRECTED),
        _verdict(machine_status="unverifiable", human_status="satisfied", outcome=CORRECTED),
    ]
    report = disagreement(rows)
    assert report["corrected"] == 2
    assert report["wouldHaveShipped"] == 1


def test_an_empty_history_reports_nothing_rather_than_dividing_by_zero():
    report = disagreement([])
    assert report["total"] == 0 and report["correctionRate"] == 0.0


# ── Becoming an evaluation case ──────────────────────────────────────────


def test_a_correction_becomes_a_case_with_the_person_as_the_answer():
    case = to_adjudication_case(_verdict())

    assert case["expected"] == "not_found", "the machine's answer was used as the label"
    assert case["requirement"].startswith("The Offeror shall")
    assert case["passages"] == ["Quality is central to everything we do."]
    assert case["why"], "a case nobody can explain is a case nobody will maintain"
    assert case["provenance"]["verdictId"] == "vd_1"


def test_a_case_tolerates_the_cautious_answer():
    """A model saying it cannot tell where a person said `failed` is unhelpful,
    not dangerous. Scoring it as the same mistake pushes the rubric toward
    confident guessing."""
    assert to_adjudication_case(_verdict(human_status="failed"))["acceptable"] == ["unverifiable"]


def test_a_confirmation_is_not_exported_as_a_test():
    """It says the machine was right, which is worth measuring in aggregate and
    adds nothing as a case."""
    assert exportable([_verdict(outcome=CONFIRMED)]) == []


def test_a_correction_with_no_passage_cannot_be_replayed():
    """It would assert an answer with no question."""
    assert exportable([_verdict(response_excerpt="")]) == []
    assert exportable([_verdict(requirement_text="")]) == []


def test_a_flag_is_exported_because_it_carries_a_reason():
    rows = exportable([_verdict(outcome=FLAGGED, human_status="satisfied", note="Right clause, wrong reason.")])
    assert len(rows) == 1
    assert "Right clause, wrong reason." in to_adjudication_case(rows[0])["why"]
