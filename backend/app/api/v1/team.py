"""Team router — CRUD + invites."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import RequireRole
from app.db.models.team_member import TeamMember
from app.db.models.team_invite import TeamInvite
from app.schemas.resources import InviteRequest, TeamMemberResponse, TeamMemberUpdate

router = APIRouter(prefix="/team", tags=["team"])

TONES = ["patina", "slate", "ochre", "leaf", "seal", "ink"]


def _to_response(m: TeamMember) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "email": m.email,
        "role": m.role,
        "title": m.title or "",
        "status": m.status,
        "lastActive": m.last_active or datetime.now(UTC).isoformat(),
        "initialsColor": m.initials_color or "patina",
    }


@router.get("/members", response_model=list[TeamMemberResponse])
async def list_members(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(TeamMember).where(TeamMember.org_id == user.org_id)
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.patch("/members/{member_id}")
async def update_member(member_id: str, body: TeamMemberUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(TeamMember).where(TeamMember.id == member_id, TeamMember.org_id == user.org_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(m, key):
            setattr(m, key, value)
    await db.flush()
    return _to_response(m)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: str,
    user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(TeamMember).where(TeamMember.id == member_id, TeamMember.org_id == user.org_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await db.delete(m)


@router.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(body: InviteRequest, user: CurrentUser, db: DbSession):
    # Create invite record
    invite = TeamInvite(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        email=body.email,
        role=body.role,
        invited_by=user.id,
        token=str(uuid.uuid4()),
    )
    db.add(invite)

    # Create team member entry with "invited" status
    count_result = await db.execute(select(TeamMember).where(TeamMember.org_id == user.org_id))
    count = len(count_result.scalars().all())

    member = TeamMember(
        id=f"u_{uuid.uuid4().hex[:8]}",
        user_id=user.id,  # Will be updated when invite is accepted
        org_id=user.org_id,
        name=body.name,
        email=body.email,
        role=body.role,
        title=body.title,
        status="invited",
        last_active=datetime.now(UTC).isoformat(),
        initials_color=TONES[count % len(TONES)],
    )
    db.add(member)
    await db.flush()
    return _to_response(member)
