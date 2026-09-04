"""An answer that reaches the clause, work that has a date, a record of both."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

import pytest

from app.api.v1.matrix import _EXPORT_COLUMNS, _parse_date
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck


def _requirement(**overrides):
    fields = dict(
        id="req_1",
        analysis_id="an_test",
        org_id="org",
        key="k1",
        reference="L.1",
        text="Proposals shall not exceed 40 pages.",
        type="shall",
        stakes="disqualifying",
        verification="mechanical",
        sources=["sweep", "model"],
        state="open",
        owner="Dana",
        response_location="Volume I, §1",
        status="drafted",
        citation={"documentName": "base.pdf", "page": 12, "quote": "Proposals shall not exceed 40 pages."},
        note="",
        history=[],
    )
    fields.update(overrides)
    return Requirement(**fields)


def test_the_export_carries_the_citation_on_every_row():
    """A matrix that leaves the product without its citations becomes a list of
    assertions the moment it is opened somewhere else."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([name for name, _ in _EXPORT_COLUMNS])
    writer.writerow([extract(_requirement()) for _, extract in _EXPORT_COLUMNS])

    buffer.seek(0)
    header, row = list(csv.reader(buffer))
    record = dict(zip(header, row))

    assert record["Document"] == "base.pdf"
    assert record["Page"] == "12"
    assert record["Quote"].startswith("Proposals shall not exceed")
    # How it is settled travels with the row: it decides who should own it.
    assert record["Check"] == "counted"
    assert record["Found by"] == "sweep, model"
    assert record["Owner"] == "Dana"


def test_the_export_says_how_a_requirement_was_found():
    assert dict(
        zip(
            [n for n, _ in _EXPORT_COLUMNS],
            [extract(_requirement(sources=["model"], verification="substantive")) for _, extract in _EXPORT_COLUMNS],
        )
    )["Check"] == "read"


def test_an_unparseable_due_date_clears_the_field_rather_than_failing_the_edit():
    """A due date is a convenience. Failing an edit that also changed the owner
    would lose the part that mattered."""
    assert _parse_date("2026-06-01") == datetime(2026, 6, 1)
    assert _parse_date("2026-06-01T09:00:00Z") == datetime(2026, 6, 1, 9, tzinfo=UTC)
    assert _parse_date("next Tuesday") is None
    assert _parse_date("") is None
    assert _parse_date(None) is None


# ── The answer reaching the clause ───────────────────────────────────────


def _check(**overrides):
    fields = dict(
        id="chk_1",
        analysis_id="an_test",
        org_id="org",
        requirement_id="req_1",
        response_version=1,
        status="satisfied",
        verification="substantive",
        decided_by="model",
        rule="",
        detail="Addressed on page 4.",
        gap="",
        risk="low",
        needs_confirmation=False,
        confirmed_by="u_dana",
        confirmed_at=datetime(2026, 5, 1, tzinfo=UTC),
        evidence={},
        history=[],
    )
    fields.update(overrides)
    return ResponseCheck(**fields)


def _fold_answer(requirement, checks, *, answer: str, source: str, now=None):
    """The behaviour `record_answer` implements, exercised without a database.

    Kept in step with the router by the assertions below rather than by
    sharing code: the point of the test is that the *rule* holds, not that two
    functions call the same helper.
    """
    now = now or datetime.now(UTC)
    requirement.history = [
        *(requirement.history or []),
        {"at": now.isoformat(), "event": "clarified", "detail": f"Answered by the agency ({source}): {answer}"},
    ]
    reopened = []
    for check in checks:
        if check.status != "satisfied":
            continue
        check.status = "unverifiable"
        check.confirmed_by = None
        check.confirmed_at = None
        check.risk = "high" if requirement.stakes == "disqualifying" else "medium"
        check.history = [*(check.history or []), {"at": now.isoformat(), "event": "reopened", "detail": source}]
        reopened.append(requirement.reference)
    return reopened


def test_an_agency_answer_reopens_work_done_against_the_old_reading():
    """An answer that only lands in a list has changed nothing. A section
    written before the clarification is not an answer to the clarified clause."""
    requirement = _requirement()
    check = _check()

    reopened = _fold_answer(
        requirement,
        [check],
        answer="The 40-page limit excludes resumes.",
        source="Q&A set 1",
    )

    assert reopened == ["L.1"]
    assert check.status == "unverifiable"
    assert check.confirmed_by is None, "a signature survived the thing it was signing"
    assert check.risk == "high"
    assert any(e["event"] == "clarified" for e in requirement.history)
    assert any(e["event"] == "reopened" for e in check.history)


def test_an_answer_leaves_a_check_that_was_already_a_gap_alone():
    """Reopening something that was never closed is noise, and noise in a
    change log is how people stop reading it."""
    requirement = _requirement()
    gap = _check(status="not_found", confirmed_by=None, confirmed_at=None, risk="high")

    reopened = _fold_answer(requirement, [gap], answer="Clarified.", source="Q&A set 1")

    assert reopened == []
    assert gap.history == []


@pytest.mark.parametrize("stakes,expected", [("disqualifying", "high"), ("scored", "medium")])
def test_reopened_risk_follows_what_the_requirement_costs(stakes, expected):
    requirement = _requirement(stakes=stakes)
    check = _check()
    _fold_answer(requirement, [check], answer="Clarified.", source="Q&A")
    assert check.risk == expected
