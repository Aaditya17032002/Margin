"""Response Match Analysis report blocks."""

from __future__ import annotations

from types import SimpleNamespace

from app.reports.response_match import build


def test_response_match_empty_unbound():
    analysis = SimpleNamespace(
        title="Test RFP",
        solicitation_number="R-1",
        agency="Agency",
        response={},
    )
    blocks = build(analysis=analysis, requirements=[], checks=[])
    assert blocks[0] == ("heading", 1, "Response Match Analysis")
    assert any(b[0] == "heading" and b[2] == "No response bound" for b in blocks)


def test_response_match_with_checks():
    analysis = SimpleNamespace(
        title="Test RFP",
        solicitation_number="R-1",
        agency="Agency",
        response={
            "fileName": "draft.docx",
            "label": "Draft A",
            "version": 1,
            "summary": {
                "total": 2,
                "cleared": 0,
                "awaitingConfirmation": 1,
                "blocking": 1,
                "counts": {"satisfied": 1, "not_found": 1},
            },
        },
    )
    requirements = [
        SimpleNamespace(
            id="req_1",
            reference="L.1",
            text="Must include a cover letter.",
            stakes="mandatory",
        ),
        SimpleNamespace(
            id="req_2",
            reference="L.2",
            text="Page limit 50.",
            stakes="mandatory",
        ),
    ]
    checks = [
        SimpleNamespace(
            id="chk_1",
            requirement_id="req_1",
            status="not_found",
            decided_by="model",
            rule=None,
            detail="",
            gap="No cover letter section.",
            risk="high",
            owner="capture",
            evidence={},
            needs_confirmation=False,
            confirmed_by=None,
            confirmed_at=None,
            note=None,
            carried_verdict=None,
            supersedes_id=None,
        ),
        SimpleNamespace(
            id="chk_2",
            requirement_id="req_2",
            status="satisfied",
            decided_by="rule",
            rule="page_count",
            detail="",
            gap="",
            risk="low",
            owner="",
            evidence={"documentName": "draft.docx", "page": 1, "quote": "50 pages", "located": True},
            needs_confirmation=True,
            confirmed_by=None,
            confirmed_at=None,
            note=None,
            carried_verdict=True,
            supersedes_id="chk_old",
        ),
    ]
    blocks = build(analysis=analysis, requirements=requirements, checks=checks)
    headings = [b[2] for b in blocks if b[0] == "heading"]
    assert "Match summary" in headings
    assert "Could lose the bid" in headings
    assert "Gaps, by risk" in headings
    assert "Requirement by requirement" in headings
    assert "Carried across drafts" in headings
    tables = [b for b in blocks if b[0] == "table"]
    assert tables  # at least the summary / gaps tables
