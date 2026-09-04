"""Checking a draft response against the solicitation it is bound to.

The two rules under test are the ones the whole feature rests on: a countable
rule is never decided by a model, and an ambiguous substantive one resolves to
"we could not tell" rather than to "satisfied".
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db.models.requirement import Requirement
from app.pipeline import mechanical
from app.pipeline.corpus import build_corpus
from app.pipeline.requirements import stable_key
from app.pipeline.traceability import (
    NOT_FOUND,
    SATISFIED,
    UNVERIFIABLE,
    summarise,
    trace_response,
)


def _response(pages: list[str], name: str = "Acme_Volume_I.pdf"):
    return build_corpus(
        [SimpleNamespace(id="d_r", file_name=name, doc_kind="response", version=1, raw_text="\f".join(pages))],
        include_response=True,
    )


def _requirement(text: str, *, reference: str = "L.1", stakes: str = "scored", verification: str = "substantive"):
    return Requirement(
        id=f"req_{abs(hash(text)) % 10**8}",
        analysis_id="an_test",
        org_id="org_test",
        key=stable_key(text),
        text=text,
        reference=reference,
        stakes=stakes,
        verification=verification,
        state="open",
        status="unassigned",
        history=[],
    )


class Model:
    """A model that always claims the requirement is met."""

    def __init__(self, payload: str):
        self.payload = payload
        self.calls: list[str] = []

    async def complete(self, messages, **kwargs):
        self.calls.append(messages[-1]["content"])
        return self.payload


ELEVEN_PAGES = ["Volume I — Technical Approach\nOur approach is described below."] + [
    f"Section {i}. We will deliver the integration services described in the statement of work."
    for i in range(2, 12)
]


# ── Mechanical ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_page_limit_is_counted_and_never_asked_about():
    """A model that miscounts pages produces a confident, wrong, green tick.
    The rule layer exists so that cannot happen."""
    model = Model('{"status": "satisfied", "detail": "looks fine", "gap": "", "quote": ""}')
    requirement = _requirement("Proposals shall not exceed 5 pages, excluding the cover letter.")

    traces = await trace_response([requirement], _response(ELEVEN_PAGES), llm=model)

    assert model.calls == [], "a countable rule was sent to a model"
    assert traces[0].status == "failed"
    assert traces[0].decided_by == "rule"
    assert traces[0].rule == "page_limit"
    assert "11 pages against a limit of 5" in traces[0].detail
    assert traces[0].gap


@pytest.mark.asyncio
async def test_a_rule_that_cannot_be_checked_says_so_rather_than_passing():
    """Font, margins and spacing are properties of a rendered page. Extracted
    text cannot show them, and "nothing contradicted it" is not evidence."""
    requirement = _requirement("Text shall be 12-point Times New Roman with 1-inch margins.")
    traces = await trace_response([requirement], _response(ELEVEN_PAGES), llm=None)

    assert traces[0].status == UNVERIFIABLE
    assert traces[0].rule == "typography"
    assert "rendered document" in traces[0].detail


@pytest.mark.asyncio
async def test_a_missing_form_is_reported_against_the_response_that_omitted_it():
    requirement = _requirement(
        "Offerors must submit a completed Standard Form 33 with Volume I.",
        stakes="disqualifying",
    )
    traces = await trace_response([requirement], _response(ELEVEN_PAGES), llm=None)

    assert traces[0].status == NOT_FOUND
    assert traces[0].risk == "high", "a mandatory requirement with no answer is not a medium risk"


def test_a_volume_limit_is_not_counted_against_a_response_whose_volumes_are_unknown():
    """Counting every page of a multi-volume response against Volume I's limit
    would fail a response that complies, so a volume that cannot be located
    stops the check rather than guessing at it."""
    result = mechanical.check(
        "Volume I shall not exceed 5 pages.",
        _response([f"Section {i}. Narrative." for i in range(1, 13)]),
    )
    assert result.status == mechanical.UNVERIFIABLE
    assert result.rule == "page_limit.volume"
    assert "would fail a response that complies" in result.detail


def test_a_volume_limit_is_counted_from_the_volume_heading_when_there_is_one():
    result = mechanical.check(
        "Volume I shall not exceed 5 pages.",
        _response(["Cover page."] + ELEVEN_PAGES),
    )
    # The heading is on page 2 and nothing follows it, so Volume I is the rest
    # of the file: 11 pages against a limit of 5.
    assert result.status == mechanical.FAILED
    assert "11 pages against a limit of 5" in result.detail


# ── Substantive ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_requirement_the_response_never_touches_needs_no_model():
    requirement = _requirement(
        "The Contractor shall maintain a Facility Clearance at the Secret level throughout performance."
    )
    model = Model('{"status": "satisfied"}')

    traces = await trace_response([requirement], _response(["We propose a integration team."]), llm=model)

    assert traces[0].status == NOT_FOUND
    assert model.calls == [], "a model was asked to confirm an absence"


@pytest.mark.asyncio
async def test_a_quote_that_is_not_in_the_response_downgrades_the_claim():
    """The same grounding rule citations are held to. A satisfied verdict
    resting on an invented quote is not a verdict."""
    requirement = _requirement("The Offeror shall describe its quality control approach.")
    model = Model(
        '{"status": "satisfied", "detail": "fully addressed", "gap": "",'
        ' "quote": "We operate an ISO 9001 certified quality management system."}'
    )

    traces = await trace_response(
        [requirement],
        _response(["Quality control approach. Our team reviews every deliverable before release."]),
        llm=model,
    )

    assert traces[0].status == UNVERIFIABLE
    assert traces[0].evidence["located"] is False
    assert "could not be found" in traces[0].detail


@pytest.mark.asyncio
async def test_a_model_that_fails_leaves_the_requirement_unresolved():
    class Broken:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("service unavailable")

    requirement = _requirement("The Offeror shall describe its quality control approach.")
    traces = await trace_response(
        [requirement],
        _response(["Quality control approach. Our team reviews every deliverable."]),
        llm=Broken(),
    )

    assert traces[0].status == UNVERIFIABLE
    assert "unresolved" in traces[0].detail


@pytest.mark.asyncio
async def test_unparseable_output_is_never_read_as_agreement():
    requirement = _requirement("The Offeror shall describe its quality control approach.")
    traces = await trace_response(
        [requirement],
        _response(["Quality control approach. Our team reviews every deliverable."]),
        llm=Model("Yes, this looks satisfied to me."),
    )
    assert traces[0].status == UNVERIFIABLE


# ── Confirmation ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_mandatory_requirement_is_never_cleared_by_the_engine():
    """"Satisfied" on a disqualifying requirement is a recommendation. It stays
    one until a person signs it."""
    requirement = _requirement(
        "The Offeror shall describe its quality control approach.", stakes="disqualifying"
    )
    quote = "Quality control approach. Our team reviews every deliverable before release."
    model = Model(
        '{"status": "satisfied", "detail": "addressed on page 1", "gap": "", "quote": "%s"}' % quote
    )

    traces = await trace_response([requirement], _response([quote]), llm=model)

    assert traces[0].status == SATISFIED
    assert traces[0].needs_confirmation is True
    assert summarise(traces)["cleared"] == 0, "a mandatory requirement was counted as settled"
    assert summarise(traces)["awaitingConfirmation"] == 1


@pytest.mark.asyncio
async def test_a_counted_rule_still_does_not_clear_a_mandatory_requirement():
    """The count is strong evidence, not a clearance. A disqualifying
    requirement going out marked satisfied because a regular expression said so
    is not a trade worth making — and the trace still shows a reviewer that
    this one is a page count rather than an opinion."""
    requirement = _requirement(
        "Proposals shall not exceed 40 pages.", stakes="disqualifying"
    )
    traces = await trace_response([requirement], _response(ELEVEN_PAGES), llm=None)

    assert traces[0].status == SATISFIED
    assert traces[0].decided_by == "rule" and traces[0].rule == "page_limit"
    assert traces[0].needs_confirmation is True
    assert summarise(traces)["cleared"] == 0


@pytest.mark.asyncio
async def test_a_scored_requirement_needs_no_signature():
    quote = "Quality control approach. Our team reviews every deliverable before release."
    model = Model('{"status": "satisfied", "detail": "addressed", "gap": "", "quote": "%s"}' % quote)
    requirement = _requirement("The Offeror shall describe its quality control approach.")

    traces = await trace_response([requirement], _response([quote]), llm=model)

    assert traces[0].status == SATISFIED and traces[0].needs_confirmation is False
    assert summarise(traces)["cleared"] == 1
