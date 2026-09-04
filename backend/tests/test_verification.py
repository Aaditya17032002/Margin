"""One queue for everything a machine could not settle, and a record of it."""

from __future__ import annotations

from types import SimpleNamespace

from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import verification
from app.pipeline.verification import BLOCKING, IMPORTANT, ROUTINE
from app.reports import evidence


def _analysis(**overrides):
    base = dict(
        id="an_test",
        title="ARTS 311 CRM",
        solicitation_number="RFP-2026-0041",
        agency="NYC DOT",
        coverage={
            "totals": {"documents": 2, "pages": 40, "pagesScanned": 40, "pagesAnalysed": 30, "chunksUnreached": 0, "emptyDocuments": 0},
            "documents": [
                {"documentId": "d1", "name": "base.pdf", "kind": "base", "pages": 40, "state": "scanned", "pagesAnalysed": 30, "chunksUnreached": 0, "unreachedPages": []}
            ],
        },
        ledger={},
        amendments=[],
        response={},
        gates=[],
        identity=[], scope=[], legal=[], eligibility=[], pricing=[], post_award=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _requirement(reference="L.1", *, stakes="disqualifying", owner=None, state="open"):
    return Requirement(
        id=f"req_{reference}",
        analysis_id="an_test",
        org_id="org",
        key=f"k_{reference}",
        reference=reference,
        text="Proposals shall not exceed 40 pages.",
        stakes=stakes,
        owner=owner,
        state=state,
        verification="mechanical",
        sources=["sweep"],
        history=[],
    )


def _check(requirement, **overrides):
    fields = dict(
        id=f"chk_{requirement.id}",
        analysis_id="an_test",
        org_id="org",
        requirement_id=requirement.id,
        response_version=1,
        status="satisfied",
        verification="mechanical",
        decided_by="rule",
        rule="page_limit",
        detail="The response is 11 pages against a limit of 40.",
        gap="",
        risk="low",
        needs_confirmation=False,
        evidence={},
        history=[],
    )
    fields.update(overrides)
    return ResponseCheck(**fields)


def test_a_document_with_no_text_is_the_first_thing_anyone_sees():
    """Nothing in it was read, so no requirement in it exists anywhere. That
    outranks every other kind of doubt the product can produce."""
    analysis = _analysis(
        coverage={
            "totals": {"documents": 2, "pages": 40, "emptyDocuments": 1, "chunksUnreached": 0},
            "documents": [
                {"documentId": "d2", "name": "Attachment J-1.pdf", "kind": "attachment", "state": "no_text", "pages": 0, "chunksUnreached": 0, "unreachedPages": []}
            ],
        }
    )
    items = verification.build(analysis=analysis, requirements=[], checks=[])

    assert items[0].severity == BLOCKING
    assert "no readable text" in items[0].title
    assert "no requirement in it exists" in items[0].consequence


def test_a_mandatory_requirement_the_draft_does_not_answer_blocks():
    requirement = _requirement()
    check = _check(requirement, status="not_found", risk="high", gap="Nothing addresses this.")
    items = verification.build(analysis=_analysis(), requirements=[requirement], checks=[check])

    gap = next(item for item in items if item.kind == "response")
    assert gap.severity == BLOCKING
    assert gap.reference == "L.1"
    assert gap.tab == "response"


def test_an_answer_awaiting_a_signature_says_which_kind_of_claim_it_is():
    """Signing off a counted page limit is a quicker job than signing off a
    model's reading, and the queue should not make them look the same."""
    requirement = _requirement()
    counted = _check(requirement, needs_confirmation=True)
    items = verification.build(analysis=_analysis(), requirements=[requirement], checks=[counted])
    assert "counted by a rule" in next(i for i in items if i.kind == "response").why

    read = _check(requirement, needs_confirmation=True, decided_by="model", rule="")
    items = verification.build(analysis=_analysis(), requirements=[requirement], checks=[read])
    assert "a model read the response" in next(i for i in items if i.kind == "response").why.lower()


def test_a_signed_off_check_leaves_the_queue():
    """The queue is derived, never stored, so settling something removes it
    instead of leaving a row to be reconciled later."""
    requirement = _requirement(owner="Dana")
    check = _check(requirement, needs_confirmation=True, confirmed_by="u_dana")
    items = verification.build(analysis=_analysis(), requirements=[requirement], checks=[check])
    assert [item for item in items if item.kind == "response"] == []


def test_an_invalidated_answer_outranks_an_unowned_requirement():
    analysis = _analysis(ledger={"invalidated": ["L.1 was complete in Volume I, §1"]})
    items = verification.build(analysis=analysis, requirements=[_requirement("C.4")], checks=[])

    assert items[0].kind == "amendment" and items[0].severity == BLOCKING
    assert any(item.kind == "requirement" and item.severity == IMPORTANT for item in items)


def test_a_claim_whose_quote_was_never_found_is_raised():
    analysis = _analysis(
        legal=[
            {
                "id": "f1",
                "label": "Cybersecurity compliance",
                "value": "FedRAMP Moderate required",
                "stakes": "disqualifying",
                "citation": {"quote": "The Contractor shall maintain FedRAMP Moderate", "located": False},
            },
            {
                "id": "f2",
                "label": "Grounded finding",
                "value": "Something else",
                "citation": {"quote": "A quote that was found", "located": True},
            },
        ]
    )
    items = verification.build(analysis=analysis, requirements=[], checks=[])
    citations = [item for item in items if item.kind == "citation"]

    assert len(citations) == 1
    assert citations[0].severity == IMPORTANT
    assert "not found anywhere in the package" in citations[0].why


def test_an_unanswered_hard_gate_blocks_and_a_soft_one_does_not():
    analysis = _analysis(
        gates=[
            {"id": "g1", "question": "Do you hold a Secret facility clearance?", "weight": "hard", "answer": ""},
            {"id": "g2", "question": "Have you bid this agency before?", "weight": "soft", "answer": ""},
            {"id": "g3", "question": "Are you SAM registered?", "weight": "hard", "answer": "Yes"},
        ]
    )
    items = {item.id: item for item in verification.build(analysis=analysis, requirements=[], checks=[])}

    assert items["gate:g1"].severity == BLOCKING
    assert items["gate:g2"].severity == ROUTINE
    assert "gate:g3" not in items, "an answered gate stayed in the queue"


def test_every_item_says_what_happens_if_nobody_acts():
    """An item nobody can act on, or that does not say why it matters, is
    noise in a list whose whole value is that everything in it is real work."""
    requirement = _requirement()
    analysis = _analysis(ledger={"removedWithWork": ["L.9"]}, gates=[{"id": "g1", "question": "?", "weight": "hard", "answer": ""}])
    items = verification.build(
        analysis=analysis,
        requirements=[requirement],
        checks=[_check(requirement, status="unverifiable", risk="medium")],
    )
    assert items
    for item in items:
        assert item.title and item.why and item.consequence and item.tab


# ── Evidence pack ────────────────────────────────────────────────────────


def test_the_pack_records_the_pages_nothing_reached():
    analysis = _analysis(
        coverage={
            "totals": {"documents": 2, "pages": 40, "pagesScanned": 36, "pagesAnalysed": 20, "chunksUnreached": 3, "emptyDocuments": 1},
            "documents": [
                {"documentId": "d1", "name": "base.pdf", "kind": "base", "pages": 40, "state": "unreached", "pagesAnalysed": 20, "chunksUnreached": 3, "unreachedPages": [[12, 15]]},
                {"documentId": "d2", "name": "Scan.pdf", "kind": "attachment", "pages": 0, "state": "no_text", "pagesAnalysed": 0, "chunksUnreached": 0, "unreachedPages": []},
            ],
        }
    )
    blocks = evidence.build(analysis=analysis, requirements=[], checks=[], queue=[])
    flat = _flatten(blocks)

    assert "12–15" in flat
    assert "no readable text" in flat
    assert "36 of 40 pages" in flat


def test_the_pack_names_every_signature():
    requirement = _requirement()
    from datetime import UTC, datetime

    check = _check(
        requirement,
        needs_confirmation=False,
        confirmed_by="u_dana",
        confirmed_at=datetime(2026, 5, 1, tzinfo=UTC),
        note="Checked the rendered PDF.",
    )
    blocks = evidence.build(
        analysis=_analysis(), requirements=[requirement], checks=[check], queue=[]
    )
    flat = _flatten(blocks)

    assert "Who signed what" in flat
    assert "u_dana" in flat and "Checked the rendered PDF." in flat


def test_the_pack_keeps_claims_it_could_not_ground_rather_than_hiding_them():
    analysis = _analysis(
        legal=[
            {
                "label": "Cybersecurity compliance",
                "value": "FedRAMP Moderate required",
                "citation": {"quote": "a quote that is not in the document", "located": False},
            }
        ]
    )
    flat = _flatten(evidence.build(analysis=analysis, requirements=[], checks=[], queue=[]))
    assert "could not be grounded" in flat
    assert "a quote that is not in the document" in flat


def test_a_clean_analysis_says_so_rather_than_omitting_the_section():
    """An absent section reads as an oversight. "None" is a finding."""
    flat = _flatten(evidence.build(analysis=_analysis(), requirements=[], checks=[], queue=[]))
    assert "None. Every claim in this analysis quotes text found in the package." in flat


def _flatten(blocks) -> str:
    parts: list[str] = []
    for block in blocks:
        if block[0] == "table":
            parts += [str(cell) for row in block[2] for cell in row]
            parts += [str(header) for header in block[1]]
        else:
            parts.append(str(block[-1]))
    return "\n".join(parts)
