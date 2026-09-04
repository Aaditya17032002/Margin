"""What a change touches, and what it deliberately leaves alone.

The two easy answers are both wrong, and both are what tools in this category
actually do. Reopening everything is safe and useless: a hundred requirements
go amber because one clause moved, the team stops reading the amber, and the
next real change is invisible inside it. Reopening nothing is how a response
ships answering a clause that was withdrawn three weeks ago.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.db.models.review import ReviewFinding
from app.pipeline import propagation
from app.pipeline.propagation import build_graph, propagate, reachable, summarise


def _requirement(id: str, reference: str, **overrides) -> Requirement:
    fields = dict(
        id=id, analysis_id="an_test", org_id="org", key=f"k_{id}", reference=reference,
        text=f"Requirement {reference}.", stakes="disqualifying", verification="substantive",
        state="open", supersedes_id=None, superseded_by_id=None, history=[],
    )
    fields.update(overrides)
    return Requirement(**fields)


def _check(id: str, requirement_id: str, **overrides) -> ResponseCheck:
    fields = dict(
        id=id, analysis_id="an_test", org_id="org", requirement_id=requirement_id,
        response_version=1, status="satisfied", verification="substantive", decided_by="model",
        rule="", detail="Addressed.", gap="", risk="low", needs_confirmation=False,
        confirmed_by=None, evidence={}, history=[],
    )
    fields.update(overrides)
    return ResponseCheck(**fields)


def _finding(id: str, requirement_id: str, **overrides) -> ReviewFinding:
    fields = dict(
        id=id, round_id="rev_1", analysis_id="an_test", org_id="org",
        requirement_id=requirement_id, severity="must_fix", text="Option years unpriced.",
        location="Volume II", state="fixed", resolution="Priced in revision 2.",
        raised_by="Dana", raised_at=datetime(2026, 5, 1, tzinfo=UTC),
        resolved_by="Ade", resolved_at=datetime(2026, 5, 2, tzinfo=UTC),
    )
    fields.update(overrides)
    return ReviewFinding(**fields)


# ── What it reaches ──────────────────────────────────────────────────────


def test_a_change_reopens_the_answer_to_the_clause_it_moved():
    target = _requirement("r1", "L.1")
    check = _check("c1", "r1")
    graph = build_graph(requirements=[target], checks=[check])

    impacts = propagate(graph, ["r1"], cause="an amendment", detail="The page limit moved.")

    assert check.status == "unverifiable"
    assert check.risk == "high", "a mandatory requirement's reopened check is not a medium risk"
    assert any(e["event"] == "reopened" for e in check.history)
    assert [i.kind for i in impacts] == ["response_check"]


def test_it_leaves_every_other_requirement_alone():
    """The whole value of narrow propagation. A change that reopens twelve
    things is legible; one that reopens four hundred is noise."""
    target, other = _requirement("r1", "L.1"), _requirement("r2", "C.4")
    touched, untouched = _check("c1", "r1"), _check("c2", "r2")
    graph = build_graph(requirements=[target, other], checks=[touched, untouched])

    propagate(graph, ["r1"], cause="an amendment", detail="…")

    assert touched.status == "unverifiable"
    assert untouched.status == "satisfied", "a change reached a requirement it has no edge to"
    assert untouched.history == []


def test_lineage_is_followed_in_both_directions():
    """A superseding requirement's answer was written for its predecessor, so a
    change to either reaches both."""
    old = _requirement("r1", "L.1", state="superseded", superseded_by_id="r2")
    new = _requirement("r2", "L.1", supersedes_id="r1")
    graph = build_graph(requirements=[old, new])

    assert reachable(graph, ["r1"]) == {"r1", "r2"}
    assert reachable(graph, ["r2"]) == {"r1", "r2"}


def test_requirements_in_the_same_section_have_no_edge():
    """Sitting near each other in a document is not a dependency."""
    graph = build_graph(requirements=[_requirement("r1", "L.1"), _requirement("r2", "L.2")])
    assert reachable(graph, ["r1"]) == {"r1"}


# ── What it refuses to touch ─────────────────────────────────────────────


def test_something_that_was_never_settled_is_not_reopened():
    """A change log full of "reopened something that was never closed" is
    noise, and noise is what stops people reading it."""
    gap = _check("c1", "r1", status="not_found", risk="high")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], checks=[gap])

    impacts = propagate(graph, ["r1"], cause="an amendment", detail="…")

    assert gap.history == []
    assert impacts == []


def test_a_signed_off_check_is_reopened_even_when_it_was_not_satisfied():
    """Somebody put their name on a conclusion about wording that has moved.
    That is exactly the case worth reopening."""
    signed = _check("c1", "r1", status="partial", confirmed_by="u_dana")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], checks=[signed])

    propagate(graph, ["r1"], cause="an amendment", detail="…")

    assert signed.confirmed_by is None
    assert signed.status == "unverifiable"


def test_a_resolved_review_finding_is_reopened():
    """A Red Team finding resolved against wording that has since moved should
    not stay quietly closed."""
    finding = _finding("f1", "r1")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], findings=[finding])

    impacts = propagate(graph, ["r1"], cause="an amendment", detail="The clause changed.")

    assert finding.state == "open"
    assert finding.resolved_by is None
    assert "reopened by an amendment" in (finding.resolution or "")
    assert [i.kind for i in impacts] == ["review_finding"]


def test_an_open_finding_is_left_where_it_is():
    finding = _finding("f1", "r1", state="open", resolution=None, resolved_by=None, resolved_at=None)
    graph = build_graph(requirements=[_requirement("r1", "L.1")], findings=[finding])
    assert propagate(graph, ["r1"], cause="an amendment", detail="…") == []


def test_a_question_is_flagged_rather_than_reopened():
    """An answer already given stays given. The point is to show that the
    clause it was about has moved underneath it."""
    question = SimpleNamespace(id="q1", requirement_id="r1", status="answered")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], questions=[question])

    impacts = propagate(graph, ["r1"], cause="an amendment", detail="…")

    assert [i.kind for i in impacts] == ["question"]
    assert impacts[0].reopened is False


# ── What it reports ──────────────────────────────────────────────────────


def test_the_summary_says_how_much_was_left_alone():
    """"Reopened 4 things" and "reopened 4 of 300 things" read the same
    without it, and the second is the one that says the propagation worked."""
    requirements = [_requirement(f"r{i}", f"L.{i}") for i in range(1, 21)]
    checks = [_check(f"c{i}", f"r{i}") for i in range(1, 21)]
    graph = build_graph(requirements=requirements, checks=checks)

    impacts = propagate(graph, ["r1"], cause="an amendment", detail="…")
    summary = summarise(impacts, cause="an amendment", considered=len(requirements))

    assert summary["reopened"] == 1
    assert summary["untouched"] == 19
    assert summary["cause"] == "an amendment"


def test_the_reason_travels_with_the_reopening():
    """"This was reopened" is much less useful than "this was reopened by
    Amendment 0002"."""
    check = _check("c1", "r1")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], checks=[check])

    propagate(graph, ["r1"], cause="amendment 0002", detail="The page limit moved to 65.")

    assert "amendment 0002" in check.detail
    assert "The page limit moved to 65." in check.detail
    assert "amendment 0002" in check.history[-1]["detail"]


def test_propagation_is_idempotent():
    """Running it twice must not produce a second round of history nobody can
    tell apart from a second change."""
    check = _check("c1", "r1")
    graph = build_graph(requirements=[_requirement("r1", "L.1")], checks=[check])

    propagate(graph, ["r1"], cause="an amendment", detail="…")
    first = len(check.history)
    propagate(graph, ["r1"], cause="an amendment", detail="…")

    assert len(check.history) == first
