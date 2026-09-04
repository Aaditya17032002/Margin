"""A report must be a real file, from any stage of the pursuit."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from app.workers.generate_report import render

docx = pytest.importorskip("docx")


def _analysis(**overrides):
    base = dict(
        title="RFE DOT SI ARTS 311 CRM",
        agency="NYC DOT",
        solicitation_number="RFE-2026-01",
        doc_type="rfp",
        # Deliberately not "decided": the reading is what a decision is made
        # from, so it has to be exportable before one exists.
        stage="review",
        go_no_go="undecided",
        summary="21 findings extracted.",
        decision_note=None,
        gates=[
            {
                "question": "Past performance",
                "answer": "Three prior engagements",
                "met": None,
                "weight": "hard",
                "citation": {
                    "quote": "minimum of three (3) prior engagements",
                    "page": 24,
                    "section": "8.3 Contractor Expertise Required",
                    "located": True,
                },
            }
        ],
        dates=[
            {"at": "2026-06-01T14:00:00+00:00", "label": "Proposal due", "source": "document"},
            {"at": "2026-05-14T14:00:00+00:00", "label": "Written questions due", "source": "derived"},
        ],
        evaluation=[{"name": "Technical approach", "weight": 40, "method": "Best value", "citation": None}],
        risks=[
            {
                "title": "Staffing mandates",
                "severity": "critical",
                "narrative": "Key personnel are locked.",
                "mitigation": "Bench depth.",
                "citation": {"quote": "shall not transfer or replace", "page": 28, "located": False},
            }
        ],
        identity=[{"label": "Agency", "value": "NYC DOT", "citation": None}],
        scope=[],
        legal=[],
        eligibility=[],
        pricing=[],
        post_award=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _render_to(tmp_path, analysis):
    report = SimpleNamespace(id="x_test", template_name="Go/no-go brief", format="DOCX")
    row = SimpleNamespace(
        reference="8.3",
        requirement="Three prior engagements",
        type="shall",
        owner=None,
        status="unassigned",
    )
    question = SimpleNamespace(
        text="Will the City accept equivalent ETL experience?",
        rationale="8.3 is silent on equivalence.",
        citation=None,
    )
    return render(str(tmp_path), report, analysis, [row], [question])


def _headings(path):
    document = docx.Document(path)
    return [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]


def test_an_undecided_analysis_still_renders_a_complete_report(tmp_path):
    path = _render_to(tmp_path, _analysis())
    assert os.path.getsize(path) > 0
    headings = _headings(path)
    for expected in ("Go / no-go", "Key dates", "Evaluation factors", "Risks", "Compliance matrix"):
        assert expected in headings
    assert len(docx.Document(path).tables) == 2


def test_an_unlocated_citation_is_marked_rather_than_quoted_as_fact(tmp_path):
    path = _render_to(tmp_path, _analysis())
    text = "\n".join(p.text for p in docx.Document(path).paragraphs)
    assert "source not located" in text
    assert "8.3 Contractor Expertise Required" in text


def test_a_derived_date_is_labelled_as_planned(tmp_path):
    path = _render_to(tmp_path, _analysis())
    rows = [
        [cell.text for cell in row.cells]
        for table in docx.Document(path).tables
        for row in table.rows
    ]
    sources = {r[2] for r in rows if len(r) == 3}
    assert "Planned by Margin" in sources
    assert "Stated in document" in sources


def test_an_empty_analysis_renders_without_raising(tmp_path):
    bare = _analysis(
        gates=[], dates=[], evaluation=[], risks=[], identity=[], summary="", decision_note=None
    )
    report = SimpleNamespace(id="x_bare", template_name="Brief", format="DOCX")
    path = render(str(tmp_path), report, bare, [], [])
    assert os.path.getsize(path) > 0


def test_markdown_export_is_markdown_and_not_a_renamed_docx(tmp_path):
    report = SimpleNamespace(id="x_md", template_name="Go/no-go brief", format="MD")
    path = render(str(tmp_path), report, _analysis(), [], [])
    assert path.endswith(".md")
    text = open(path, encoding="utf-8").read()
    assert text.startswith("# RFE DOT SI ARTS 311 CRM")
    assert "| Date | Milestone | Source |" in text
    assert "Planned by Margin" in text


def test_pdf_without_libreoffice_fails_loudly_rather_than_renaming(tmp_path, monkeypatch):
    """A DOCX called .pdf opens in nothing and explains nothing."""
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    report = SimpleNamespace(id="x_pdf", template_name="Brief", format="PDF")
    with pytest.raises(RuntimeError, match="LibreOffice"):
        render(str(tmp_path), report, _analysis(), [], [])
