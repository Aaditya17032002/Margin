"""Who can do what, how long things are kept, and what leaves the building.

Three controls that are only worth having if they hold at the edges: a refusal
that names what is missing, a retention policy that cannot reach back into last
month, and a redaction pass that never destroys the original.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import permissions
from app.pipeline import redaction, retention


# ── Permissions ──────────────────────────────────────────────────────────


def test_a_writer_cannot_clear_a_mandatory_requirement():
    assert permissions.allowed("reviewer", "clear_requirement")
    assert not permissions.allowed("writer", "clear_requirement")


def test_a_viewer_can_read_and_nothing_else():
    can = [name for name in permissions.PERMISSIONS if permissions.allowed("viewer", name)]
    assert can == ["read"]


def test_an_unknown_permission_is_refused_rather_than_allowed():
    """A typo in a call site should close a door, not open one."""
    assert not permissions.allowed("admin", "clear_requirment")
    with pytest.raises(HTTPException) as exc:
        permissions.require("admin", "clear_requirment")
    assert exc.value.status_code == 403


def test_a_refusal_names_the_roles_that_have_it():
    """A 403 reading "forbidden" teaches somebody to file a ticket."""
    with pytest.raises(HTTPException) as exc:
        permissions.require("writer", "sign_off_review")
    detail = exc.value.detail
    assert "admin, reviewer" in detail
    assert "writer" in detail
    assert "admin can change that" in detail


def test_nobody_signs_off_a_round_they_opened_themselves():
    permissions.require_separation(actor_id="u_ade", opened_by="u_dana", action="Signing off")
    with pytest.raises(HTTPException) as exc:
        permissions.require_separation(actor_id="u_dana", opened_by="u_dana", action="Signing off")
    assert exc.value.status_code == 409


def test_an_admin_is_not_exempt_from_separation():
    """An admin can grant themselves any role. Letting them skip the second
    pair of eyes would make the control decorative."""
    with pytest.raises(HTTPException):
        permissions.require_separation(
            actor_id="u_admin", opened_by="u_admin", action="Signing off"
        )


def test_the_matrix_ships_as_data():
    model = permissions.matrix()
    assert {r["name"] for r in model["roles"]} == set(permissions.ROLES)
    assert model["separationOfDuties"]
    admin = next(r for r in model["roles"] if r["name"] == "admin")
    assert "manage_retention" in admin["permissions"]


# ── Retention ────────────────────────────────────────────────────────────


def _analysis(*, days_ago: int, stage: str = "decided", **overrides):
    now = datetime.now(UTC)
    base = dict(
        id="an_1",
        title="Recompete",
        stage=stage,
        go_no_go="bid",
        legal_hold=False,
        created_at=now - timedelta(days=days_ago + 30),
        updated_at=now - timedelta(days=days_ago),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_a_live_pursuit_is_never_disposed_of():
    policy = retention.Policy.from_dict({"enabled": True, "minimum_hold_days": 100})
    result = retention.preview([_analysis(days_ago=4000, stage="review")], policy)
    assert result["due"] == []
    assert "Still live" in result["skipped"][0]["reason"]


def test_a_legal_hold_beats_every_timer():
    policy = retention.Policy.from_dict({"enabled": True, "minimum_hold_days": 100})
    result = retention.preview([_analysis(days_ago=4000, legal_hold=True)], policy)
    assert result["due"] == []
    assert result["skipped"][0]["reason"] == "Under legal hold."


def test_the_minimum_hold_overrides_a_shorter_class_period():
    """A policy edited in a hurry cannot reach back into last month."""
    policy = retention.Policy.from_dict(
        {"enabled": True, "source_documents_days": 30, "minimum_hold_days": 365}
    )
    assert policy.effective_days("source_documents") == 365
    assert retention.preview([_analysis(days_ago=200)], policy)["due"] == []

    due = retention.preview([_analysis(days_ago=400)], policy)["due"]
    kinds = {item["class"] for item in due}
    assert "source_documents" in kinds
    detail = next(i for i in due if i["class"] == "source_documents")["detail"]
    assert "raised to the minimum hold" in detail


def test_the_clock_runs_from_the_last_thing_that_happened():
    """A pursuit somebody amended last week is not four hundred days old."""
    now = datetime.now(UTC)
    fresh = _analysis(days_ago=0, created_at=now - timedelta(days=4000))
    policy = retention.Policy.from_dict({"enabled": True, "minimum_hold_days": 365})
    assert retention.preview([fresh], policy)["due"] == []


def test_the_record_is_never_in_scope():
    """What is disposed of is documents. What was decided, and on what basis,
    is the thing an auditor asks for."""
    assert set(retention.CLASSES) == {"source_documents", "extracted_text", "response_drafts"}
    joined = " ".join(retention.NEVER_DISPOSED).lower()
    for survivor in ("verdict", "decision record", "audit trail", "sign-off"):
        assert survivor in joined


def test_a_policy_below_the_floor_is_rejected_with_a_reason():
    problems = retention.validate(retention.Policy.from_dict({"minimum_hold_days": 30}))
    assert any("protest" in problem for problem in problems)


def test_text_disposed_before_the_files_it_came_from_is_flagged():
    problems = retention.validate(
        retention.Policy.from_dict(
            {"source_documents_days": 1000, "extracted_text_days": 400, "minimum_hold_days": 365}
        )
    )
    assert any("worst of both" in problem for problem in problems)


# ── Personal data ────────────────────────────────────────────────────────


SAMPLE = (
    "Contracting Officer: Dana Reyes, dana.reyes@example.gov, (202) 555-0142.\n"
    "Contractor EIN 12-3456789. Key personnel SSN 123-45-6789.\n"
    "Date of Birth: 1979-04-02. Routing number: 021000021.\n"
)


def test_the_obvious_shapes_are_found():
    found = redaction.scan(SAMPLE)
    assert set(found.counts) >= {"ssn", "ein", "email", "phone", "dob", "bank"}


def test_a_value_is_never_returned_in_full():
    """Listing every SSN in a document in order to warn about them is absurd."""
    finding = next(f for f in redaction.scan(SAMPLE).findings if f.kind == "ssn")
    preview = finding.as_dict()["preview"]
    assert "123-45-6789" not in preview
    assert preview.startswith("12") and preview.endswith("89")


def test_redaction_never_edits_in_place():
    found = redaction.scan(SAMPLE)
    redacted, record = redaction.redact(SAMPLE, found.findings)
    assert SAMPLE.count("123-45-6789") == 1  # the original is untouched
    assert "123-45-6789" not in redacted
    assert len(record) == len(found.findings)


def test_a_redacted_span_says_what_it_was():
    """An auditor asking "what did you take out" deserves better than
    "something"."""
    found = redaction.scan("Reach me at dana.reyes@example.gov please.")
    redacted, _ = redaction.redact("Reach me at dana.reyes@example.gov please.", found.findings)
    assert redacted == "Reach me at [redacted: email address] please."


def test_a_clean_document_is_returned_unchanged():
    text = "Proposals shall not exceed 50 pages, excluding the cover letter."
    found = redaction.scan(text)
    assert found.findings == []
    assert redaction.redact(text, found.findings) == (text, [])


def test_overlapping_detectors_do_not_double_count():
    """A phone number inside a labelled field is one finding, not two."""
    found = redaction.scan("Routing number: 021000021")
    spans = [(f.start, f.end) for f in found.findings]
    assert len(spans) == len(set(spans))
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:], strict=False))


# ── At the edge, through the API ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_permission_matrix_says_what_the_caller_can_do(client, auth_headers: dict):
    response = await client.get("/api/v1/governance/permissions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["you"]["role"] == "admin"
    assert "manage_retention" in body["you"]["can"]
    assert body["you"]["cannot"] == []


@pytest.mark.asyncio
async def test_a_viewer_is_told_what_they_are_missing(client, viewer_headers: dict):
    response = await client.get("/api/v1/governance/permissions", headers=viewer_headers)
    body = response.json()
    assert body["you"]["can"] == ["read"]
    assert "manage_retention" in body["you"]["cannot"]


@pytest.mark.asyncio
async def test_a_viewer_cannot_change_retention(client, viewer_headers: dict):
    response = await client.put(
        "/api/v1/governance/retention", json={"enabled": True}, headers=viewer_headers
    )
    assert response.status_code == 403
    assert "admin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_a_viewer_cannot_export_the_matrix(client, viewer_headers: dict):
    """Whoever can export can hand the package to anybody, which is a
    different authority from being able to read it here."""
    response = await client.get(
        "/api/v1/analyses/an_test/matrix/export", headers=viewer_headers
    )
    assert response.status_code == 403
