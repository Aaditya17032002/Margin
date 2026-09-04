"""Amendment impact: what actually changed, and what that invalidates.

An amendment is not a new document to be read from scratch. It is a set of
edits to a document a team has already been working against for weeks, and the
only question that matters is *which of that work is now wrong*.

Answering it needs the Requirement Ledger. Because a requirement's identity is
derived from its words, a reworded clause arrives at the ledger as one removal
and one addition — true, but useless to a proposal manager. This module pairs
them back up:

* A removed requirement and a new one that are mostly the same sentence are one
  requirement that changed, and the old row is marked `superseded` rather than
  vanishing.
* The work recorded against the old row — owner, response location — moves to
  the new one, because the person who wrote that section is the person who has
  to revisit it.
* A section marked drafted or complete against the *old* wording is **not**
  carried over as complete. It is reopened and named. A green tick against text
  that no longer exists is the single most expensive thing this product could
  get wrong.

There are two shapes of change, and only one of them is a removal.

Sometimes the base document is re-issued and the old wording is genuinely gone.
More often — and this is the case that matters — the amendment is a separate
document saying "L.1 is deleted and replaced with the following", while the
base still contains the original sentence word for word. The package then holds
two contradictory page limits, both perfectly extractable, and a reader who
only sees a list of requirements has no way to tell which one binds. So a
requirement introduced by an amendment supersedes the standing requirement it
most resembles: amendments win, which is the one rule of solicitation
precedence that is never in doubt.

Withdrawals are read directly from the amendment's own language — "Section L.5
is deleted", "Offerors are no longer required to" — because that sentence is
the only evidence a deletion happened at all. The clause it withdraws is still
sitting in the base document, looking exactly like a live requirement.

Pairing is deterministic — token overlap, no model — for the same reason the
sweep is: an amendment analysis that gives different answers on Tuesday and
Thursday cannot be the basis of a submission decision.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.pipeline.anchor import normalize

logger = get_logger()

#: Below this, two requirements are different requirements. Chosen to pair a
#: clause whose page limit or deadline moved (which changes a handful of tokens
#: in a long sentence) while refusing to pair two unrelated obligations that
#: happen to share boilerplate.
PAIR_THRESHOLD = 0.6

#: Statuses that represent work already done against the old wording. When a
#: requirement is superseded, these are the ones that stop being trustworthy.
_WORK_DONE = frozenset({"drafted", "in-review", "complete"})

#: A number as an amendment states one: 50, 2026-06-22, 14:00, 1.5. The
#: separator must sit between digits, so "12-point" yields 12 and not "12-".
_NUMBER = re.compile(r"\b\d+(?:[,./:-]\d+)*\b")

#: A section reference as solicitations write them: L.1, C.4.2, Section H,
#: Attachment J-1, Article 7.
_REFERENCE = r"(?:Section|Clause|Article|Paragraph|Attachment|Exhibit)?\s*[A-Z]{1,2}[.\-]?\d+(?:\.\d+)*"

#: An amendment announcing that something no longer applies. The clause it
#: withdraws is still in the base document and still looks live, so this
#: sentence is the only evidence the deletion happened.
_WITHDRAWAL = re.compile(
    rf"""(?ix)
    (?:
        ({_REFERENCE})\s+(?:is|are)\s+(?:hereby\s+)?
            (?:deleted|removed|withdrawn|struck|rescinded|cancelled|canceled)
      | (?:delete|remove|strike)\s+({_REFERENCE})
    )
    """
)


@dataclass
class Supersession:
    """One requirement replaced by another, with what moved between them."""

    old_key: str
    new_key: str
    similarity: float
    summary: str


#: The hinge of a replacement clause. Everything before it is the amendment
#: talking about the document; everything after it is the document's new text.
_REPLACEMENT = re.compile(
    r"""(?ix)
    \b(?:
        replaced\s+with\s+the\s+following
      | substituted\s+with\s+the\s+following
      | replaced\s+(?:in\s+its\s+entirety\s+)?(?:by|with)
      | (?:is|are)\s+(?:changed|revised|amended)\s+to\s+read(?:\s+as\s+follows)?
      | now\s+reads\s+as\s+follows
    )\b[:\s\u2014-]*
    """
)

#: A clause number where a solicitation puts one — at the head of the sentence,
#: or naming the section in the reference.
_LEADING_CLAUSE = re.compile(r"^\s*((?:[A-Z]{1,2}[.-])?\d+(?:\.\d+)*)\b")


def comparable(text: str) -> str:
    """The part of an amendment sentence that is the document's new wording.

    "L.1 is deleted in its entirety and replaced with the following: Proposals
    shall not exceed 65 pages" is two statements bolted together — an
    instruction to the reader, and a requirement. Only the second is comparable
    to the clause it replaces, and comparing the whole sentence buries the
    match under the boilerplate.
    """
    match = _REPLACEMENT.search(text)
    return text[match.end():].strip() if match else text


def similarity(a: str, b: str) -> float:
    """Token overlap on normalised text — Jaccard, and nothing cleverer.

    Deliberately blunt. A measure that is easy to reason about is worth more
    here than a measure that is slightly more accurate and impossible to
    explain when it pairs the wrong two clauses.
    """
    left = set(normalize(comparable(a)).split())
    right = set(normalize(comparable(b)).split())
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def describe_change(old: str, new: str) -> str:
    """What moved, in the terms a proposal manager reads amendments for.

    Numbers first: an amendment that changes "40 pages" to "50 pages" or moves
    a date is the common case, and burying that in a word-level diff helps
    nobody.
    """
    old, new = comparable(old), comparable(new)
    old_numbers = _NUMBER.findall(old)
    new_numbers = _NUMBER.findall(new)
    parts: list[str] = []

    if old_numbers != new_numbers:
        gone = [n for n in old_numbers if n not in new_numbers]
        arrived = [n for n in new_numbers if n not in old_numbers]
        if gone and arrived:
            parts.append(f"{', '.join(gone)} → {', '.join(arrived)}")
        elif arrived:
            parts.append(f"added {', '.join(arrived)}")
        elif gone:
            parts.append(f"dropped {', '.join(gone)}")

    # Words only, and only ones the numeric line did not already report —
    # repeating "50 → 65" as "no longer says 50" is noise in the one place a
    # reader is skimming for the actual change.
    old_words = normalize(old).split()
    new_words = normalize(new).split()
    added = [w for w in new_words if w not in set(old_words) and _carries_meaning(w)]
    removed = [w for w in old_words if w not in set(new_words) and _carries_meaning(w)]
    if added:
        parts.append(f"now says {' '.join(added[:8])}")
    if removed:
        parts.append(f"no longer says {' '.join(removed[:8])}")

    return "; ".join(parts) if parts else "reworded without changing its terms"


def withdrawn_references(text: str) -> list[str]:
    """Section references an amendment says no longer apply.

    A replacement — "L.1 is deleted in its entirety and replaced with the
    following" — is deliberately still reported here. The caller resolves the
    overlap: a reference that also has a replacement is a supersession, which
    is the more useful record, and only a reference with nothing taking its
    place is a withdrawal.
    """
    found: list[str] = []
    for match in _WITHDRAWAL.finditer(text):
        reference = (match.group(1) or match.group(2) or "").strip()
        reference = re.sub(r"(?i)^(?:section|clause|article|paragraph)\s+", "", reference).strip()
        if reference and reference not in found:
            found.append(reference)
    return found


def cited_reference(text: str) -> str:
    """The clause an amendment sentence is about.

    "A.2 Section L.1 is deleted in its entirety and replaced with the
    following…" is filed by extraction under whatever heading it sits beneath —
    usually the amendment's own title, which tells a reader nothing. The
    sentence names the clause it edits, so that is the reference the
    replacement should carry.
    """
    references = withdrawn_references(text)
    return references[0] if references else ""


def withdraw(references: list[str], standing: list, *, at: datetime | None = None) -> list:
    """Mark the standing requirements an amendment withdrew.

    Matching is on the reference the amendment names, because that is what an
    amendment actually cites — it says "L.5 is deleted", never the sentence.
    A requirement whose reference is unknown is left alone: guessing here would
    withdraw a live obligation, which is the worst outcome available.
    """
    at = at or datetime.now(UTC)
    wanted = {_normalise_reference(reference) for reference in references if reference}
    withdrawn = []
    for row in standing:
        if row.state != "open":
            continue
        if not (_clause_numbers(row) & wanted):
            continue
        row.state = "removed"
        row.history = [
            *(row.history or []),
            _event(at, "withdrawn", f"An amendment states that {row.reference} no longer applies."),
        ]
        withdrawn.append(row)
    return withdrawn


def _clause_numbers(row) -> set[str]:
    """Every clause number this requirement answers to.

    An extracted reference is often the section heading — "SECTION L —
    Instructions to Offerors" — while the amendment cites "L.1". The clause
    number the requirement's own text opens with is the one that matches, so
    both are collected.
    """
    numbers = {_normalise_reference(row.reference)}
    leading = _LEADING_CLAUSE.match((row.text or "").strip())
    if leading:
        numbers.add(_normalise_reference(leading.group(1)))
        # "L.1 Proposals shall…" often survives extraction as "1 Proposals…"
        # when the section letter was consumed by the heading above it.
        section = _LEADING_CLAUSE.match((row.reference or "").strip())
        if section:
            numbers.add(_normalise_reference(f"{section.group(1)}{leading.group(1)}"))
    return {n for n in numbers if n}


def _normalise_reference(reference: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (reference or "").lower())


def pair(removed: list, added: list, threshold: float = PAIR_THRESHOLD) -> list[Supersession]:
    """Match requirements that went away to requirements that arrived.

    Greedy on the best score first, so the strongest pair claims its partner
    before a weaker one can. Each requirement is used at most once: an
    amendment that splits one clause into two shows as one supersession and one
    genuinely new requirement, which is what it is.
    """
    scored = sorted(
        (
            (similarity(old.text, new.text), old, new)
            for old in removed
            for new in added
        ),
        key=lambda item: (-item[0], item[1].key, item[2].key),
    )

    used_old: set[str] = set()
    used_new: set[str] = set()
    pairs: list[Supersession] = []
    for score, old, new in scored:
        if score < threshold or old.key in used_old or new.key in used_new:
            continue
        used_old.add(old.key)
        used_new.add(new.key)
        pairs.append(
            Supersession(
                old_key=old.key,
                new_key=new.key,
                similarity=round(score, 3),
                summary=describe_change(old.text, new.text),
            )
        )
    return pairs


def apply(pairs: list[Supersession], rows_by_key: dict, *, at: datetime | None = None) -> list[str]:
    """Link the two rows, move the work, and reopen anything already answered.

    Returns the human-readable list of work this amendment invalidated.
    """
    at = at or datetime.now(UTC)
    invalidated: list[str] = []

    for link in pairs:
        old = rows_by_key.get(link.old_key)
        new = rows_by_key.get(link.new_key)
        if old is None or new is None:
            continue

        # The replacement adopts the clause number the amendment cites, so the
        # record reads "L.1 changed" rather than naming the amendment's cover
        # heading, which is where extraction filed the sentence.
        cited = cited_reference(new.text)
        if cited:
            new.reference = cited

        old.state = "superseded"
        old.superseded_by_id = new.id
        new.supersedes_id = old.id
        old.history = [
            *(old.history or []),
            _event(at, "superseded", f"Replaced by {new.reference}: {link.summary}."),
        ]

        # The work follows the requirement. Whoever wrote the old answer is the
        # person who has to decide whether it still holds.
        if old.owner and not new.owner:
            new.owner = old.owner
        if old.response_location and not new.response_location:
            new.response_location = old.response_location

        if old.status in _WORK_DONE:
            # Never inherited as done. The answer was written against wording
            # that no longer exists.
            new.status = "assigned" if new.owner else "unassigned"
            new.confirmed_by = None
            new.confirmed_at = None
            where = old.response_location or "an unrecorded location"
            invalidated.append(f"{new.reference} was {old.status} in {where}")
            new.history = [
                *(new.history or []),
                _event(
                    at,
                    "reopened",
                    f"Supersedes {old.reference}, which was {old.status}. "
                    f"The change ({link.summary}) has not been answered.",
                ),
            ]
        else:
            new.history = [
                *(new.history or []),
                _event(at, "supersedes", f"Replaces {old.reference}: {link.summary}."),
            ]

    return invalidated


def record(
    *,
    label: str,
    issued: str,
    pairs: list[Supersession],
    added_keys: list[str],
    removed_keys: list[str],
    rows_by_key: dict,
    date_changes: list[dict],
) -> dict:
    """The amendment record the workspace shows.

    Changed clauses first, then genuinely new obligations, then withdrawn ones.
    A record with no changes is still worth writing: "this amendment changed
    nothing we track" is an answer, and an absent record is not.
    """
    superseded_new = {link.new_key for link in pairs}
    changes: list[dict] = []

    for link in pairs:
        old = rows_by_key.get(link.old_key)
        new = rows_by_key.get(link.new_key)
        if old is None or new is None:
            continue
        changes.append(
            {
                "id": f"ch_{uuid.uuid4().hex[:8]}",
                "kind": "changed",
                "area": new.reference or old.reference,
                "before": old.text,
                "after": new.text,
                "critical": "disqualifying" in (old.stakes, new.stakes),
            }
        )

    for key in added_keys:
        if key in superseded_new:
            continue
        row = rows_by_key.get(key)
        if row is None:
            continue
        changes.append(
            {
                "id": f"ch_{uuid.uuid4().hex[:8]}",
                "kind": "added",
                "area": row.reference,
                "before": None,
                "after": row.text,
                "critical": row.stakes == "disqualifying",
            }
        )

    superseded_old = {link.old_key for link in pairs}
    for key in removed_keys:
        if key in superseded_old:
            continue
        row = rows_by_key.get(key)
        if row is None:
            continue
        changes.append(
            {
                "id": f"ch_{uuid.uuid4().hex[:8]}",
                "kind": "removed",
                "area": row.reference,
                "before": row.text,
                "after": None,
                "critical": row.stakes == "disqualifying",
            }
        )

    for change in date_changes:
        changes.append(
            {
                "id": f"ch_{uuid.uuid4().hex[:8]}",
                "kind": "changed",
                "area": change["label"],
                "before": change["before"],
                "after": change["after"],
                # A deadline that moves is always critical: it is the one
                # change that can cost the bid on its own.
                "critical": True,
            }
        )

    counts = {kind: sum(1 for c in changes if c["kind"] == kind) for kind in ("changed", "added", "removed")}
    logger.info(
        "amendment_impact",
        label=label,
        changed=len(pairs),
        added=counts["added"],
        removed=counts["removed"],
        dates=len(date_changes),
    )
    return {
        "id": f"am_{uuid.uuid4().hex[:8]}",
        "label": label,
        "issued": issued,
        "summary": _summary(pairs, counts, date_changes),
        "changes": changes,
    }


def date_diff(before: list[dict], after: list[dict]) -> list[dict]:
    """Deadlines that moved between two reads of the package.

    Matched by label rather than by id, because a re-read assigns new ids to
    the same milestone.
    """
    old_by_label = {str(d.get("label", "")).strip().lower(): d for d in before}
    moved: list[dict] = []
    for entry in after:
        label = str(entry.get("label", "")).strip().lower()
        previous = old_by_label.get(label)
        if not previous:
            continue
        if str(previous.get("date")) != str(entry.get("date")):
            moved.append(
                {
                    "label": entry.get("label", ""),
                    "before": str(previous.get("date")),
                    "after": str(entry.get("date")),
                }
            )
    return moved


def _summary(pairs, counts: dict, date_changes) -> str:
    """Counted from the changes actually recorded.

    Deriving these by subtracting key lists was wrong: a requirement an
    amendment supersedes need never have been *removed* — the base document
    still contains it — so the arithmetic could report a negative withdrawal.
    """
    added = counts["added"]
    removed = counts["removed"]
    parts: list[str] = []
    if pairs:
        parts.append(f"{len(pairs)} requirement{'' if len(pairs) == 1 else 's'} changed")
    if added:
        parts.append(f"{added} added")
    if removed:
        parts.append(f"{removed} withdrawn")
    if date_changes:
        labels = ", ".join(change["label"] for change in date_changes[:3])
        parts.append(f"{len(date_changes)} date{'' if len(date_changes) == 1 else 's'} moved ({labels})")
    if not parts:
        return "Nothing this analysis tracks changed."
    return f"{'; '.join(parts)}."


def _carries_meaning(word: str) -> bool:
    """Drop what a diff should not bother a reader with: bare numbers, already
    reported above, and the single letters clause numbers leave behind when
    "L.1" is normalised to "l 1"."""
    return len(word) > 1 and not word.isdigit()


def _event(at: datetime, event: str, detail: str) -> dict:
    return {"at": at.isoformat(), "event": event, "detail": detail}
