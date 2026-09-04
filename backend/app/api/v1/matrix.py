"""The compliance matrix — a projection of the Requirement Ledger.

There is no separate matrix table any more. A matrix row *is* a requirement,
shown as a worksheet: the extracted half (reference, text, stakes, citation) is
owned by the run and read-only here, and the working half (owner, status,
response location, note) is owned by whoever is answering the solicitation and
is never touched by a run.

That split is the point. Assignments used to be attached to rows a re-read
deleted, so re-running an analysis quietly reset the team's work.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.requirement import Requirement
from app.pipeline.requirements import classify_stakes, classify_type, classify_verification, stable_key
from app.schemas.resources import (
    BulkMatrixRequest,
    MatrixRowCreate,
    MatrixRowResponse,
    MatrixRowUpdate,
)

router = APIRouter(tags=["matrix"])

#: A mandatory requirement is not cleared on a model's say-so. Moving one to
#: `complete` records who did it, because "satisfied" is a claim someone has to
#: own.
_CLEARED = "complete"


def _to_response(r: Requirement) -> dict:
    return {
        "id": r.id,
        "analysisId": r.analysis_id,
        "key": r.key,
        "reference": r.reference,
        "requirement": r.text,
        "type": r.type,
        "stakes": r.stakes,
        "kind": r.kind,
        "verification": r.verification,
        "state": r.state,
        "sources": list(r.sources or []),
        "owner": r.owner,
        "responseLocation": r.response_location or "",
        "status": r.status,
        "citation": r.citation or {},
        "note": r.note,
        "confirmedBy": r.confirmed_by,
        "confirmedAt": r.confirmed_at.isoformat() if r.confirmed_at else None,
        "history": r.history or [],
    }


@router.get("/analyses/{analysis_id}/matrix", response_model=list[MatrixRowResponse])
async def list_matrix(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    include_removed: bool = Query(
        False,
        alias="includeRemoved",
        description="Include requirements the latest run stopped finding. They are never deleted.",
    ),
):
    query = select(Requirement).where(
        Requirement.analysis_id == analysis_id, Requirement.org_id == user.org_id
    )
    if not include_removed:
        query = query.where(Requirement.state != "removed")
    result = await db.execute(query.order_by(Requirement.document_id, Requirement.page, Requirement.reference))
    return [_to_response(r) for r in result.scalars().all()]


@router.post("/analyses/{analysis_id}/matrix", status_code=status.HTTP_201_CREATED)
async def create_matrix_row(analysis_id: str, body: MatrixRowCreate, user: CurrentUser, db: DbSession):
    """A requirement a person found that the run did not.

    It gets the same identity as any other, so a later run that *does* find it
    merges into this row rather than duplicating it — and it is marked
    `manual`, which stops a run that misses it from marking it removed.
    """
    key = stable_key(body.requirement, body.reference)
    existing = (
        await db.execute(
            select(Requirement).where(
                Requirement.analysis_id == analysis_id,
                Requirement.org_id == user.org_id,
                Requirement.key == key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        # Already known. Adopting it is more useful than a duplicate row or an
        # error the person cannot act on.
        existing.sources = sorted({*(existing.sources or []), "manual"})
        if existing.state == "removed":
            existing.state = "open"
        await db.flush()
        return _to_response(existing)

    citation = body.citation.model_dump() if body.citation else {}
    now = datetime.now(UTC)
    row = Requirement(
        id=f"req_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        org_id=user.org_id,
        key=key,
        reference=body.reference,
        text=body.requirement,
        kind="obligation",
        type=body.type.value,
        stakes=body.stakes.value,
        verification=classify_verification("obligation", body.requirement),
        citation=citation,
        document_id=str(citation.get("documentId") or ""),
        page=int(citation.get("page") or 0),
        sources=["manual"],
        state="open",
        owner=body.owner,
        response_location=body.response_location,
        status=body.status.value,
        note=body.note,
        first_seen_at=now,
        last_seen_at=now,
        history=[{"at": now.isoformat(), "event": "added", "detail": "Added by hand."}],
    )
    db.add(row)
    await db.flush()
    return _to_response(row)


@router.patch("/analyses/{analysis_id}/matrix/{row_id}")
async def update_matrix_row(analysis_id: str, row_id: str, body: MatrixRowUpdate, user: CurrentUser, db: DbSession):
    row = await _row(db, analysis_id, row_id, user.org_id)

    update = body.model_dump(exclude_unset=True, by_alias=False)
    now = datetime.now(UTC)
    events: list[str] = []

    for key, value in update.items():
        value = value.value if hasattr(value, "value") else value
        if key == "requirement":
            # Editing the words changes the requirement's identity, so the key
            # moves with it. Without this the row would keep answering to text
            # it no longer contains.
            if value != row.text:
                row.text = value
                row.key = stable_key(value, row.reference)
                row.type = classify_type(value)
                row.verification = classify_verification(row.kind, value)
                row.stakes = classify_stakes(row.kind, value)
                row.sources = sorted({*(row.sources or []), "manual"})
                events.append("requirement text edited by hand")
            continue
        column = "response_location" if key == "response_location" else key
        if hasattr(row, column) and getattr(row, column) != value:
            setattr(row, column, value)
            events.append(f"{key} set to {value!r}" if value is not None else f"{key} cleared")

    if update.get("status") == _CLEARED:
        # Marking a requirement complete is a claim with a name on it.
        row.confirmed_by = user.id
        row.confirmed_at = now
        events.append(f"marked complete by {user.id}")
    elif "status" in update and row.status != _CLEARED:
        row.confirmed_by = None
        row.confirmed_at = None

    if events:
        row.history = [*(row.history or []), {"at": now.isoformat(), "event": "edited", "detail": "; ".join(events)}]
    await db.flush()
    return _to_response(row)


@router.delete("/analyses/{analysis_id}/matrix/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_matrix_row(analysis_id: str, row_id: str, user: CurrentUser, db: DbSession):
    """Dismissing a requirement, not erasing it.

    A row a person removes is marked `removed` and kept, so the ledger can
    still answer "what happened to L.3.2?" — which a deleted row cannot.
    """
    row = await _row(db, analysis_id, row_id, user.org_id)
    row.state = "removed"
    row.history = [
        *(row.history or []),
        {
            "at": datetime.now(UTC).isoformat(),
            "event": "dismissed",
            "detail": f"Dismissed by {user.id}.",
        },
    ]
    await db.flush()


@router.post("/analyses/{analysis_id}/matrix/bulk")
async def bulk_matrix(analysis_id: str, body: BulkMatrixRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Requirement).where(
            Requirement.analysis_id == analysis_id,
            Requirement.org_id == user.org_id,
            Requirement.id.in_(body.ids),
        )
    )
    rows = result.scalars().all()
    now = datetime.now(UTC)
    for row in rows:
        detail: list[str] = []
        if body.owner is not None:
            row.owner = body.owner
            detail.append(f"owner set to {body.owner!r}" if body.owner else "owner cleared")
            if body.owner and row.status == "unassigned":
                row.status = "assigned"
            elif not body.owner:
                row.status = "unassigned"
        if body.status is not None:
            row.status = body.status.value
            detail.append(f"status set to {row.status!r}")
            if row.status == _CLEARED:
                row.confirmed_by = user.id
                row.confirmed_at = now
            else:
                row.confirmed_by = None
                row.confirmed_at = None
        if detail:
            row.history = [*(row.history or []), {"at": now.isoformat(), "event": "edited", "detail": "; ".join(detail)}]
    await db.flush()
    return {"updated": len(rows)}


async def _row(db, analysis_id: str, row_id: str, org_id: str) -> Requirement:
    result = await db.execute(
        select(Requirement).where(
            Requirement.id == row_id,
            Requirement.analysis_id == analysis_id,
            Requirement.org_id == org_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    return row
