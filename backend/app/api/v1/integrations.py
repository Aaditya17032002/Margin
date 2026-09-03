"""Integrations router — connect, disconnect, browse files, import."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.integration import Integration
from app.schemas.resources import ConnectRequest, ImportRequest, IntegrationResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _to_response(i: Integration) -> dict:
    return {
        "id": i.provider,
        "name": i.name,
        "blurb": i.blurb or "",
        "connected": i.connected,
        "account": i.account,
        "connectedAt": i.connected_at,
        "scopes": i.scopes or [],
        "tree": i.tree or [],
    }


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Integration).where(Integration.org_id == user.org_id)
    )
    return [_to_response(i) for i in result.scalars().all()]


@router.post("/{provider}/connect")
async def connect_integration(provider: str, body: ConnectRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Integration).where(Integration.provider == provider, Integration.org_id == user.org_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{provider}' not found")

    integration.connected = True
    integration.connected_at = datetime.now(UTC).isoformat()
    if body.account:
        integration.account = body.account
    await db.flush()
    return _to_response(integration)


@router.delete("/{provider}/disconnect")
async def disconnect_integration(provider: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Integration).where(Integration.provider == provider, Integration.org_id == user.org_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{provider}' not found")

    integration.connected = False
    integration.connected_at = None
    await db.flush()
    return _to_response(integration)


@router.get("/{provider}/files")
async def list_files(provider: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Integration).where(Integration.provider == provider, Integration.org_id == user.org_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{provider}' not found")
    return integration.tree or []


@router.post("/{provider}/import")
async def import_files(provider: str, body: ImportRequest, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Integration).where(Integration.provider == provider, Integration.org_id == user.org_id)
    )
    integration = result.scalar_one_or_none()
    if not integration or not integration.connected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Integration '{provider}' not connected")

    # In production, this would trigger actual file import from the provider.
    # For now, return acknowledgement.
    return {"imported": len(body.file_ids), "analysisId": body.analysis_id}
