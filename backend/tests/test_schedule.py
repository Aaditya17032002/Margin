"""Every analysis gets a calendar, whether or not anyone has decided to bid."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.workers.schedule import build_schedule, normalise_extracted, parse_when

NOW = datetime(2026, 3, 1, tzinfo=UTC)


def _stated(kind: str, days: int, label: str = "") -> dict:
    return {
        "kind": kind,
        "label": label,
        "at": (NOW + timedelta(days=days)).isoformat(),
        "timezone": "America/New_York",
    }


def test_the_calendar_covers_the_whole_pursuit_from_one_stated_deadline():
    schedule = build_schedule([_stated("proposal-due", 40)], now=NOW)
    kinds = [d["kind"] for d in schedule]
    for expected in (
        "intent-due",
        "questions-due",
        "answers-expected",
        "solution-review",
        "draft-review",
        "final-review",
        "proposal-due",
        "orals",
        "award",
    ):
        assert expected in kinds, expected
    assert schedule == sorted(schedule, key=lambda d: d["at"])


def test_a_stated_date_is_never_replaced_by_a_derived_one():
    schedule = build_schedule(
        [_stated("proposal-due", 40), _stated("questions-due", 5, "Questions due 5pm")],
        now=NOW,
    )
    questions = [d for d in schedule if d["kind"] == "questions-due"]
    assert len(questions) == 1
    assert questions[0]["source"] == "document"
    assert questions[0]["label"] == "Questions due 5pm"


def test_derived_dates_are_labelled_as_derived_and_carry_no_citation():
    schedule = build_schedule([_stated("proposal-due", 40)], now=NOW)
    derived = [d for d in schedule if d["source"] == "derived"]
    assert derived
    assert all(d["citation"] is None for d in derived)
    stated = [d for d in schedule if d["source"] == "document"]
    assert len(stated) == 1


def test_a_stage_whose_window_has_already_closed_is_not_scheduled():
    """Anchored three days out, there is no point putting the intent notice
    three weeks in the past on someone's calendar."""
    schedule = build_schedule([_stated("proposal-due", 3)], now=NOW)
    kinds = [d["kind"] for d in schedule]
    assert "intent-due" not in kinds
    assert "final-review" in kinds
    assert "award" in kinds


def test_nothing_is_invented_without_a_date_to_anchor_to():
    assert build_schedule([], now=NOW) == []


def test_unreadable_dates_are_dropped_rather_than_guessed():
    dates = normalise_extracted(
        [
            {"kind": "proposal-due", "at": "as stated in Section L"},
            {"kind": "proposal-due", "at": "2026-06-01T14:00:00"},
            {"not": "a dict"},
        ]
    )
    assert len(dates) == 1
    assert dates[0]["at"].startswith("2026-06-01")


def test_a_kind_is_recovered_from_the_label_when_the_model_omits_it():
    dates = normalise_extracted(
        [
            {"label": "Oral presentations and demonstration", "at": "2026-06-10"},
            {"label": "Answers to written questions posted", "at": "2026-05-10"},
            {"label": "Anticipated award", "at": "2026-08-01"},
        ]
    )
    assert [d["kind"] for d in dates] == ["orals", "answers-expected", "award"]


def test_parse_when_accepts_the_shapes_a_model_actually_returns():
    assert parse_when("2026-06-01") == datetime(2026, 6, 1, tzinfo=UTC)
    assert parse_when("2026-06-01T14:30") == datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
    assert parse_when("due 2026-06-01 14:30:00 EST") == datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
    assert parse_when("2026-13-45") is None
    assert parse_when("") is None
