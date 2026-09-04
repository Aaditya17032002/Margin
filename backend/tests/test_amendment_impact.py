"""An amendment's only interesting question: which of our answers is now wrong?"""

from __future__ import annotations

from app.db.models.requirement import Requirement
from app.pipeline import amendments
from app.pipeline.requirements import stable_key

OLD_LIMIT = "Proposals shall not exceed 40 pages, excluding the cover letter and tabs."
NEW_LIMIT = "Proposals shall not exceed 50 pages, excluding the cover letter and tabs."
UNRELATED = "The Contractor shall maintain a Quality Control Plan throughout performance."


def _row(text: str, *, reference: str, status: str = "unassigned", owner=None, location: str = ""):
    return Requirement(
        id=f"req_{abs(hash(text)) % 10**8}",
        analysis_id="an_test",
        org_id="org_test",
        key=stable_key(text),
        text=text,
        reference=reference,
        stakes="disqualifying",
        status=status,
        owner=owner,
        response_location=location,
        state="open",
        history=[],
    )


def test_a_reworded_requirement_is_one_change_not_two():
    """Identity comes from the words, so an amendment that edits a clause shows
    up as a removal and an addition. Left like that it is true and useless."""
    old = _row(OLD_LIMIT, reference="L.3.2")
    new = _row(NEW_LIMIT, reference="L.3.2")

    pairs = amendments.pair([old], [new])

    assert len(pairs) == 1
    assert pairs[0].old_key == old.key and pairs[0].new_key == new.key
    # The number that moved is what a proposal manager is reading for.
    assert "40 → 50" in pairs[0].summary


def test_two_different_requirements_are_never_paired():
    old = _row(OLD_LIMIT, reference="L.3.2")
    new = _row(UNRELATED, reference="C.4")
    assert amendments.pair([old], [new]) == []


def test_a_drafted_answer_is_reopened_when_its_requirement_changes():
    """The expensive failure this prevents: a green tick against wording that
    no longer exists."""
    old = _row(OLD_LIMIT, reference="L.3.2", status="complete", owner="Dana", location="Volume I, §1")
    new = _row(NEW_LIMIT, reference="L.3.2")
    rows = {old.key: old, new.key: new}

    invalidated = amendments.apply(amendments.pair([old], [new]), rows)

    assert old.state == "superseded" and old.superseded_by_id == new.id
    assert new.supersedes_id == old.id
    # The work moves to the new row, but not the claim that it is finished.
    assert new.owner == "Dana" and new.response_location == "Volume I, §1"
    assert new.status == "assigned"
    assert new.confirmed_by is None
    assert invalidated == ["L.3.2 was complete in Volume I, §1"]
    assert any(e["event"] == "reopened" for e in new.history)


def test_untouched_work_is_carried_over_without_a_warning():
    old = _row(OLD_LIMIT, reference="L.3.2", status="assigned", owner="Dana")
    new = _row(NEW_LIMIT, reference="L.3.2")
    rows = {old.key: old, new.key: new}

    invalidated = amendments.apply(amendments.pair([old], [new]), rows)

    assert invalidated == []
    assert new.owner == "Dana" and new.status == "unassigned"
    assert any(e["event"] == "supersedes" for e in new.history)


def test_a_moved_deadline_is_always_critical():
    before = [{"label": "Proposals due", "date": "2026-06-01"}, {"label": "Questions due", "date": "2026-05-14"}]
    after = [{"label": "Proposals due", "date": "2026-06-15"}, {"label": "Questions due", "date": "2026-05-14"}]

    moved = amendments.date_diff(before, after)
    assert moved == [{"label": "Proposals due", "before": "2026-06-01", "after": "2026-06-15"}]

    record = amendments.record(
        label="Amendment 0001",
        issued="2026-05-01T00:00:00Z",
        pairs=[],
        added_keys=[],
        removed_keys=[],
        rows_by_key={},
        date_changes=moved,
    )
    assert record["changes"][0]["critical"] is True
    assert "Proposals due" in record["summary"]


def test_the_record_separates_changed_from_added_and_withdrawn():
    old = _row(OLD_LIMIT, reference="L.3.2")
    new = _row(NEW_LIMIT, reference="L.3.2")
    fresh = _row(UNRELATED, reference="C.4")
    gone = _row("The Offeror shall provide three references for similar work.", reference="L.5")
    rows = {r.key: r for r in (old, new, fresh, gone)}

    pairs = amendments.pair([old, gone], [new, fresh])
    record = amendments.record(
        label="Amendment 0002",
        issued="2026-05-01T00:00:00Z",
        pairs=pairs,
        added_keys=[new.key, fresh.key],
        removed_keys=[old.key, gone.key],
        rows_by_key=rows,
        date_changes=[],
    )

    kinds = sorted(change["kind"] for change in record["changes"])
    assert kinds == ["added", "changed", "removed"]
    changed = next(c for c in record["changes"] if c["kind"] == "changed")
    assert changed["before"] == OLD_LIMIT and changed["after"] == NEW_LIMIT


def test_one_requirement_split_in_two_claims_only_its_best_match():
    """An amendment that splits a clause is one supersession and one genuinely
    new requirement — not two supersessions of the same row."""
    old = _row(OLD_LIMIT, reference="L.3.2")
    new_a = _row(NEW_LIMIT, reference="L.3.2")
    new_b = _row(
        "Proposals shall not exceed 50 pages, excluding the cover letter, tabs and dividers.",
        reference="L.3.3",
    )
    pairs = amendments.pair([old], [new_a, new_b])
    assert len(pairs) == 1


def test_an_amendment_that_changes_nothing_says_so_rather_than_nothing():
    record = amendments.record(
        label="Amendment 0003",
        issued="2026-05-01T00:00:00Z",
        pairs=[],
        added_keys=[],
        removed_keys=[],
        rows_by_key={},
        date_changes=[],
    )
    assert record["changes"] == []
    assert record["summary"] == "Nothing this analysis tracks changed."


def test_a_replacement_is_compared_to_its_new_wording_not_its_preamble():
    """An amendment clause is two statements welded together: an instruction to
    the reader and the requirement itself. Comparing the whole sentence buries
    the match under the boilerplate and the change is reported as a brand new
    requirement sitting beside the one it replaces."""
    standing = _row(OLD_LIMIT, reference="SECTION L — Instructions to Offerors")
    replacement = _row(
        "A.2 Section L.1 is deleted in its entirety and replaced with the following: "
        + NEW_LIMIT,
        reference="AMENDMENT 0001",
    )

    assert amendments.similarity(standing.text, replacement.text) >= amendments.PAIR_THRESHOLD
    pairs = amendments.pair([standing], [replacement])
    assert len(pairs) == 1
    assert pairs[0].summary == "40 → 50"


def test_a_withdrawal_matches_the_clause_number_the_amendment_cites():
    """Amendments cite "L.5", never the sentence. The extracted reference is
    often the section heading, so the clause number at the head of the
    requirement's own text is what has to match."""
    text = "A.4 Section L.5 is deleted. Offerors are no longer required to provide references."
    assert amendments.withdrawn_references(text) == ["L.5"]

    row = _row("L.5 Offerors shall provide three references.", reference="SECTION L — Instructions")
    other = _row(UNRELATED, reference="C.4")
    withdrawn = amendments.withdraw(["L.5"], [row, other])

    assert withdrawn == [row]
    assert row.state == "removed" and other.state == "open"
    assert any(e["event"] == "withdrawn" for e in row.history)


def test_a_withdrawal_never_guesses():
    """Withdrawing a live obligation is the worst outcome available, so a
    reference that matches nothing withdraws nothing."""
    row = _row(UNRELATED, reference="C.4")
    assert amendments.withdraw(["L.9"], [row]) == []
    assert row.state == "open"


def test_a_superseded_requirement_is_never_counted_as_withdrawn():
    """The base document still contains the wording an amendment replaced, so
    nothing was removed. Subtracting key lists used to report -1 withdrawn."""
    old = _row(OLD_LIMIT, reference="L.3.2")
    new = _row(NEW_LIMIT, reference="L.3.2")
    rows = {old.key: old, new.key: new}
    pairs = amendments.pair([old], [new])

    record = amendments.record(
        label="Amendment 0001",
        issued="2026-05-01T00:00:00Z",
        pairs=pairs,
        added_keys=[new.key],
        removed_keys=[],
        rows_by_key=rows,
        date_changes=[],
    )
    assert record["summary"] == "1 requirement changed."
    assert [c["kind"] for c in record["changes"]] == ["changed"]


def test_a_package_uploaded_with_its_amendment_still_pairs_the_replacement():
    """There is no earlier run to have "added" anything, but the base document
    still carries the wording the amendment replaced. Pairing only fresh
    additions would leave two contradictory page limits both reading as live."""
    standing = _row(OLD_LIMIT, reference="SECTION L")
    replacement = _row(
        "A.2 Section L.1 is deleted in its entirety and replaced with the following: " + NEW_LIMIT,
        reference="AMENDMENT 0001",
    )
    rows = {standing.key: standing, replacement.key: replacement}

    # Both were found on the same first read — the pairing input is every open
    # requirement, not only the ones a reconciliation reported as new.
    amendments.apply(amendments.pair([standing], [replacement]), rows)

    assert standing.state == "superseded"
    assert replacement.reference == "L.1"
    assert standing.superseded_by_id == replacement.id
