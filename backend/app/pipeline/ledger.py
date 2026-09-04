"""Reconciling a run against the standing Requirement Ledger.

A run does not *create* the ledger. It reports what it found, and the ledger
works out what that means for what it already knew:

* A requirement it has seen before keeps its row, its id, its owner, its
  status and its notes. Only the extracted half — the words, the reference,
  the citation, the stakes — is refreshed.
* A requirement it has not seen before is added, with the run that found it
  recorded against it.
* A requirement that was there last time and is not there now is **not
  deleted**. It is marked `removed`, with the run that stopped seeing it. An
  obligation quietly vanishing is a finding; an obligation quietly vanishing
  from the database is a bug that looks like nothing at all.

The last rule is the reason this module exists. The previous behaviour deleted
every agent-authored row and rebuilt it, which meant a re-read silently reset
work and an amendment that dropped a requirement was indistinguishable from a
parser that missed it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.requirement import Requirement
from app.pipeline.requirements import RequirementDraft

logger = get_logger()


@dataclass
class Reconciliation:
    """What the run changed. Shown to the user, not just logged."""

    added: list[str]
    updated: list[str]
    unchanged: list[str]
    removed: list[str]
    #: Requirements a person had already assigned or drafted that this run
    #: stopped seeing. These are the ones that need eyes.
    removed_with_work: list[str]

    def as_dict(self) -> dict:
        return {
            "added": len(self.added),
            "updated": len(self.updated),
            "unchanged": len(self.unchanged),
            "removed": len(self.removed),
            "removedWithWork": self.removed_with_work,
        }


#: Fields a run owns. Everything not listed here belongs to whoever is working
#: the response, and a run must never write it.
_EXTRACTED = ("reference", "text", "kind", "type", "stakes", "verification", "citation", "document_id", "page")


async def reconcile(
    db: AsyncSession,
    *,
    analysis_id: str,
    org_id: str,
    drafts: list[RequirementDraft],
    run_id: str,
    introduced_by: str = "",
) -> Reconciliation:
    existing_rows = (
        await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
    ).scalars().all()
    by_key = {row.key: row for row in existing_rows}
    now = datetime.now(UTC)

    added: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []

    for draft in drafts:
        row = by_key.get(draft.key)
        if row is None:
            row = Requirement(
                id=f"req_{uuid.uuid4().hex[:12]}",
                analysis_id=analysis_id,
                org_id=org_id,
                key=draft.key,
                state="open",
                introduced_by=introduced_by or draft.document_id,
                first_seen_at=now,
                history=[_event(now, "identified", f"Found by {_sources(draft)} in run {run_id}.")],
            )
            _apply(row, draft)
            row.sources = sorted(draft.sources)
            row.last_seen_at = now
            row.last_seen_run = run_id
            db.add(row)
            by_key[draft.key] = row
            added.append(draft.key)
            continue

        changes = _apply(row, draft)
        merged_sources = sorted(set(row.sources or []) | draft.sources)
        if merged_sources != sorted(row.sources or []):
            row.sources = merged_sources
        reinstated = row.state == "removed"
        if reinstated:
            # It came back. Usually a parser that stumbled last time, sometimes
            # an amendment reinstating a clause. Either way it is not silent —
            # and "reinstated" already says what happened, so it is not also
            # logged as an ordinary field change.
            row.state = "open"
            row.history = [*(row.history or []), _event(now, "reinstated", f"Seen again in run {run_id}.")]
        if changes:
            row.history = [
                *(row.history or []),
                _event(now, "updated", f"{', '.join(changes)} changed in run {run_id}."),
            ]
            updated.append(draft.key)
        elif reinstated:
            updated.append(draft.key)
        else:
            unchanged.append(draft.key)
        row.last_seen_at = now
        row.last_seen_run = run_id

    seen = {draft.key for draft in drafts}
    removed: list[str] = []
    removed_with_work: list[str] = []
    for row in existing_rows:
        if row.key in seen or row.state != "open":
            continue
        # A person's own row is never removed by a run that did not see it —
        # they wrote it because the document said something we did not catch.
        if "manual" in (row.sources or []):
            continue
        row.state = "removed"
        row.history = [
            *(row.history or []),
            _event(now, "removed", f"Not found in run {run_id}."),
        ]
        removed.append(row.key)
        if row.owner or row.status != "unassigned" or row.response_location:
            removed_with_work.append(row.reference or row.key)

    await db.flush()
    result = Reconciliation(added, updated, unchanged, removed, removed_with_work)
    logger.info(
        "ledger_reconciled",
        analysis_id=analysis_id,
        run=run_id,
        added=len(added),
        updated=len(updated),
        unchanged=len(unchanged),
        removed=len(removed),
    )
    return result


def _apply(row: Requirement, draft: RequirementDraft) -> list[str]:
    """Refresh the extracted half of a row. Returns the fields that moved."""
    changes: list[str] = []
    values = {
        "reference": draft.reference,
        "text": draft.text,
        "kind": draft.kind,
        "type": draft.type,
        "stakes": draft.stakes,
        "verification": draft.verification,
        "citation": draft.citation,
        "document_id": draft.document_id,
        "page": draft.page,
    }
    for field in _EXTRACTED:
        new = values[field]
        if getattr(row, field, None) != new:
            setattr(row, field, new)
            changes.append(field)
    if draft.note and not row.note:
        row.note = draft.note
    return changes


def _sources(draft: RequirementDraft) -> str:
    if draft.confirmed:
        return "both the pattern sweep and a specialist"
    return "the pattern sweep" if "sweep" in draft.sources else "a specialist"


def _event(at: datetime, event: str, detail: str) -> dict:
    return {"at": at.isoformat(), "event": event, "detail": detail}
