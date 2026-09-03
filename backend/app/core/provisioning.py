"""Provisioning for a brand-new org.

A fresh account starts empty by design — no analyses, no notifications, no
knowledge base. Two things still have to exist before the workspace is usable:
the owner has to appear on their own team roster, and the integration hub needs
rows to offer, since connecting is an update to an existing row rather than a
create.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.integration import Integration
from app.db.models.team_member import TeamMember
from app.db.models.user import User

INTEGRATION_DEFAULTS: list[dict] = [
    {
        "provider": "outlook",
        "name": "Outlook",
        "blurb": "Solicitations arrive as mail. Read them without leaving the thread.",
        "scopes": ["Mail.Read", "Mail.ReadBasic"],
    },
    {
        "provider": "sharepoint",
        "name": "SharePoint",
        "blurb": "Pull the capture library straight from the team site.",
        "scopes": ["Sites.Read.All", "Files.Read.All"],
    },
    {
        "provider": "onedrive",
        "name": "OneDrive",
        "blurb": "Anything already saved to your own drive is one click away.",
        "scopes": ["Files.Read", "Files.ReadWrite"],
    },
]


async def ensure_org_provisioned(db: AsyncSession, user: User) -> None:
    """Idempotently give an org its owner roster entry and integration rows."""
    await _ensure_team_member(db, user)
    await _ensure_integrations(db, user.org_id)


async def _ensure_team_member(db: AsyncSession, user: User) -> None:
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.org_id == user.org_id, TeamMember.email == user.email
        )
    )
    if existing.scalar_one_or_none():
        return

    db.add(
        TeamMember(
            id=f"u_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            org_id=user.org_id,
            name=user.name,
            email=user.email,
            role=user.role,
            title=user.title or "",
            status="active",
            last_active=datetime.now(UTC).isoformat(),
            initials_color=user.avatar_tone or "patina",
        )
    )


async def _ensure_integrations(db: AsyncSession, org_id: str) -> None:
    existing = await db.execute(
        select(Integration.provider).where(Integration.org_id == org_id)
    )
    present = set(existing.scalars().all())

    for spec in INTEGRATION_DEFAULTS:
        if spec["provider"] in present:
            continue
        db.add(
            Integration(
                id=str(uuid.uuid4()),
                org_id=org_id,
                provider=spec["provider"],
                name=spec["name"],
                blurb=spec["blurb"],
                connected=False,
                scopes=spec["scopes"],
                tree=[],
            )
        )
