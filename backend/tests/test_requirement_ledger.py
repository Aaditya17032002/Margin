"""A requirement keeps its name across runs, and never disappears quietly."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.db.models.requirement import Requirement
from app.pipeline.ledger import reconcile
from app.pipeline.requirements import (
    MECHANICAL,
    SUBSTANTIVE,
    RequirementDraft,
    classify_verification,
    from_findings,
    from_sweep,
    merge,
    stable_key,
)
from app.pipeline.sweep import SweepHit


class FakeSession:
    """Enough of an AsyncSession for reconciliation.

    Reconciliation is a decision about identity, not a database exercise, and
    the CI runner has no PostgreSQL. Requirement rows are ordinary objects
    until they are flushed, so the rules can be tested exactly as written.
    """

    def __init__(self, rows: list[Requirement]):
        self.rows = list(rows)
        self.added: list[Requirement] = []

    async def execute(self, _query):
        rows = self.rows

        class Result:
            def scalars(self):
                return self

            def all(self):
                return rows

        return Result()

    def add(self, row):
        self.added.append(row)
        self.rows.append(row)

    async def flush(self):
        return None


def _draft(text: str, *, reference: str = "L.3", kind: str = "obligation", source: str = "sweep"):
    from app.pipeline.requirements import classify_stakes, classify_type

    return RequirementDraft(
        key=stable_key(text),
        text=text,
        reference=reference,
        kind=kind,
        type=classify_type(text),
        stakes=classify_stakes(kind, text),
        verification=classify_verification(kind, text),
        citation={"page": 3, "located": True},
        document_id="d_base",
        page=3,
        sources={source},
    )


PAGE_LIMIT = "Proposals shall not exceed 40 pages, excluding the cover letter."
QCP = "The Contractor shall maintain a Quality Control Plan throughout performance."


async def _run(session, drafts, run_id):
    return await reconcile(
        session,
        analysis_id="an_test",
        org_id="org_test",
        drafts=drafts,
        run_id=run_id,
    )


@pytest.mark.asyncio
async def test_a_second_run_keeps_the_row_and_the_work_on_it():
    """The regression this exists for: every run deleted the agent-authored
    rows and inserted new ones, so an assignment made on Tuesday pointed at a
    row that did not exist on Wednesday."""
    session = FakeSession([])
    await _run(session, [_draft(PAGE_LIMIT), _draft(QCP)], "run_1")
    assert len(session.added) == 2

    row = next(r for r in session.rows if r.text == PAGE_LIMIT)
    row_id = row.id
    row.owner = "Dana"
    row.status = "drafted"
    row.response_location = "Volume I, §2"

    # The same package, read again — the text is identical, the run is not.
    result = await _run(session, [_draft(PAGE_LIMIT), _draft(QCP)], "run_2")

    assert result.added == [] and result.removed == []
    assert row.id == row_id, "the requirement was given a new identity"
    assert (row.owner, row.status, row.response_location) == ("Dana", "drafted", "Volume I, §2")


@pytest.mark.asyncio
async def test_a_requirement_that_stops_being_found_is_reported_not_deleted():
    session = FakeSession([])
    await _run(session, [_draft(PAGE_LIMIT), _draft(QCP)], "run_1")
    assigned = next(r for r in session.rows if r.text == QCP)
    assigned.owner = "Dana"
    assigned.status = "assigned"

    result = await _run(session, [_draft(PAGE_LIMIT)], "run_2")

    assert result.removed == [stable_key(QCP)]
    assert assigned.state == "removed", "a requirement vanished instead of being reported"
    # The ones with work against them are named, because those need a person.
    assert assigned.reference in result.removed_with_work
    assert any(e["event"] == "removed" for e in assigned.history)


@pytest.mark.asyncio
async def test_a_requirement_that_comes_back_is_reinstated_loudly():
    session = FakeSession([])
    await _run(session, [_draft(QCP)], "run_1")
    await _run(session, [], "run_2")
    await _run(session, [_draft(QCP)], "run_3")

    row = session.rows[0]
    assert row.state == "open"
    assert [e["event"] for e in row.history] == ["identified", "removed", "reinstated"]


@pytest.mark.asyncio
async def test_a_run_never_removes_a_requirement_a_person_added():
    """Someone adds a requirement because the extraction missed it. A run that
    misses it again must not undo them."""
    session = FakeSession([])
    await _run(session, [], "run_0")
    manual = Requirement(
        id="req_manual",
        analysis_id="an_test",
        org_id="org_test",
        key=stable_key("The Offeror shall provide a transition plan."),
        text="The Offeror shall provide a transition plan.",
        reference="H.2",
        sources=["manual"],
        state="open",
        status="assigned",
        history=[],
    )
    session.rows.append(manual)

    result = await _run(session, [_draft(PAGE_LIMIT)], "run_1")

    assert manual.state == "open"
    assert manual.key not in result.removed


@pytest.mark.asyncio
async def test_a_changed_reference_moves_the_row_rather_than_replacing_it():
    """An amendment renumbering L.3.2 to L.3.3 is the same obligation. Keying
    on the reference would report it as one removal and one addition."""
    session = FakeSession([])
    await _run(session, [_draft(PAGE_LIMIT, reference="L.3.2")], "run_1")
    row = session.rows[0]
    row.owner = "Dana"

    result = await _run(session, [_draft(PAGE_LIMIT, reference="L.3.3")], "run_2")

    assert result.added == [] and result.removed == []
    assert row.reference == "L.3.3" and row.owner == "Dana"
    assert result.updated == [row.key]


# ── Classification ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "Proposals shall not exceed 40 pages.",
        "Text shall be 12-point Times New Roman with 1-inch margins.",
        "Each volume shall be submitted as a separate PDF not exceeding 25 MB.",
        "File names shall follow the convention RFP-Offeror-Volume.",
        "Offerors must submit a completed Standard Form 33, signed by an authorised official.",
    ],
)
def test_a_countable_rule_is_never_left_to_a_model(text):
    """Page counts, fonts, margins, naming, forms and signatures are checked by
    counting. A model deciding them is a page limit that can be wrong."""
    assert classify_verification("obligation", text) == MECHANICAL


@pytest.mark.parametrize(
    "text",
    [
        "The Contractor shall maintain a Quality Control Plan throughout performance.",
        "The Offeror shall demonstrate experience with comparable enterprise integrations.",
        "Key personnel shall not be replaced without the Contracting Officer's consent.",
    ],
)
def test_a_judgement_call_is_marked_as_one(text):
    assert classify_verification("obligation", text) == SUBSTANTIVE


def test_agreement_between_the_two_passes_is_recorded():
    """A requirement a pattern and a specialist both found is stronger evidence
    than either alone, and the ledger has to be able to say so."""
    hit = SweepHit(
        kind="obligation",
        text=QCP,
        document_id="d_base",
        page=4,
        section="C.2",
        chunk_index=7,
        start=0,
        end=len(QCP),
        pattern="modal.shall",
    )
    finding = {"label": "Quality control", "value": QCP, "citation": {"section": "C.2", "page": 4}}

    merged = merge(from_sweep([hit]), from_findings([finding]))
    # The model's paraphrase carries the label, so it is a different sentence
    # and a different requirement — both survive rather than one masking the
    # other.
    sweep_only = [d for d in merged if d.text == QCP]
    assert len(sweep_only) == 1
    assert sweep_only[0].sources == {"sweep"}

    # Identical text from both passes does merge, and is marked confirmed.
    both = merge(from_sweep([hit]), [_draft(QCP, source="model")])
    assert len(both) == 1 and both[0].confirmed


def test_stakes_never_soften_when_two_passes_disagree():
    high = _draft(PAGE_LIMIT)
    high.stakes = "disqualifying"
    low = _draft(PAGE_LIMIT, source="model")
    low.stakes = "informational"

    assert merge([low], [high])[0].stakes == "disqualifying"
    assert merge([high], [low])[0].stakes == "disqualifying"


def test_the_migration_computes_the_same_key_as_the_application():
    """The ledger's identity is written out longhand in migration 006 so it
    cannot drift when this module changes. If they disagree, every migrated row
    loses its history the next time an analysis runs."""
    path = Path(__file__).resolve().parents[1] / "alembic/versions/006_requirement_ledger.py"
    spec = importlib.util.spec_from_file_location("migration_006", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    for text in [
        PAGE_LIMIT,
        QCP,
        "The Offeror’s plan",       # curly apostrophe
        "ﬁle names shall follow",   # fi ligature
        "double spaced",            # non-breaking space
        "",
    ]:
        assert migration._key(text) == stable_key(text), text
