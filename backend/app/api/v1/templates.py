"""Templates router — full CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.template import Template
from app.schemas.resources import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


def _to_response(t: Template) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "kind": t.kind,
        "description": t.description or "",
        "sections": t.sections or [],
        "updatedAt": t.updated_at.isoformat() if isinstance(t.updated_at, datetime) else str(t.updated_at),
        "usageCount": t.usage_count,
        "format": t.format,
    }


@router.get("", response_model=list[TemplateResponse])
async def list_templates(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Template).where(Template.org_id == user.org_id)
    )
    return [_to_response(t) for t in result.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateCreate, user: CurrentUser, db: DbSession):
    t = Template(
        id=f"t_{uuid.uuid4().hex[:8]}",
        org_id=user.org_id,
        name=body.name,
        kind=body.kind,
        description=body.description,
        sections=body.sections,
        format=body.format,
    )
    db.add(t)
    await db.flush()
    return _to_response(t)


@router.patch("/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.org_id == user.org_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(t, key):
            setattr(t, key, value)
    t.updated_at = datetime.now(UTC)
    await db.flush()
    return _to_response(t)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.org_id == user.org_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.delete(t)
