"""Matrix router — CRUD + bulk operations for compliance matrix rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.matrix_row import MatrixRow
from app.schemas.resources import (
    BulkMatrixRequest,
    MatrixRowCreate,
    MatrixRowResponse,
    MatrixRowUpdate,
)

router = APIRouter(tags=["matrix"])


def _to_response(r: MatrixRow) -> dict:
    return {
        "id": r.id,
        "analysisId": r.analysis_id,
        "reference": r.reference,
        "requirement": r.requirement,
        "type": r.type,
        "stakes": r.stakes,
        "owner": r.owner,
        "responseLocation": r.response_location or "",
        "status": r.status,
        "citation": r.citation or {},
        "note": r.note,
    }


@router.get("/analyses/{analysis_id}/matrix", response_model=list[MatrixRowResponse])
async def list_matrix(analysis_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(MatrixRow).where(MatrixRow.analysis_id == analysis_id, MatrixRow.org_id == user.org_id)
    )
    return [_to_response(r) for r in result.scalars().all()]


@router.post("/analyses/{analysis_id}/matrix", status_code=status.HTTP_201_CREATED)
async def create_matrix_row(analysis_id: str, body: MatrixRowCreate, user: CurrentUser, db: DbSession):
    row = MatrixRow(
        id=f"m_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        org_id=user.org_id,
        reference=body.reference,
        requirement=body.requirement,
        type=body.type.value,
        stakes=body.stakes.value,
        owner=body.owner,
        response_location=body.response_location,
        status=body.status.value,
        citation=body.citation.model_dump() if body.citation else {},
        note=body.note,
    )
    db.add(row)
    await db.flush()
    return _to_response(row)


@router.patch("/analyses/{analysis_id}/matrix/{row_id}")
async def update_matrix_row(analysis_id: str, row_id: str, body: MatrixRowUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(MatrixRow).where(MatrixRow.id == row_id, MatrixRow.analysis_id == analysis_id, MatrixRow.org_id == user.org_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrix row not found")

    update_data = body.model_dump(exclude_unset=True, by_alias=False)
    for key, value in update_data.items():
        col = "response_location" if key == "response_location" else key
        if hasattr(row, col):
            setattr(row, col, value.value if hasattr(value, "value") else value)
    await db.flush()
    return _to_response(row)


@router.delete("/analyses/{analysis_id}/matrix/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_matrix_row(analysis_id: str, row_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(MatrixRow).where(MatrixRow.id == row_id, MatrixRow.analysis_id == analysis_id, MatrixRow.org_id == user.org_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrix row not found")
    await db.delete(row)


@router.post("/analyses/{analysis_id}/matrix/bulk")
async def bulk_matrix(analysis_id: str, body: BulkMatrixRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(MatrixRow).where(
            MatrixRow.analysis_id == analysis_id,
            MatrixRow.org_id == user.org_id,
            MatrixRow.id.in_(body.ids),
        )
    )
    rows = result.scalars().all()
    for row in rows:
        if body.owner is not None:
            row.owner = body.owner
            if body.owner and row.status == "unassigned":
                row.status = "assigned"
            elif not body.owner:
                row.status = "unassigned"
        if body.status is not None:
            row.status = body.status.value
    await db.flush()
    return {"updated": len(rows)}
