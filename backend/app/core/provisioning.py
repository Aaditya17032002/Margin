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
from app.db.models.template import Template
from app.db.models.user import User

# The scopes shown on a connector card must be the scopes the consent screen
# will actually ask for, so they come from the connector itself rather than
# from a second list that can drift. `offline_access` is left off the card: it
# is plumbing, not access to anything.
INTEGRATION_DEFAULTS: list[dict] = [
    {
        "provider": "outlook",
        "name": "Outlook",
        "blurb": "Solicitations arrive as mail. Read them without leaving the thread.",
    },
    {
        "provider": "sharepoint",
        "name": "SharePoint",
        "blurb": "Pull the capture library straight from the team site.",
    },
    {
        "provider": "onedrive",
        "name": "OneDrive",
        "blurb": "Anything already saved to your own drive is one click away.",
    },
]


def default_scopes(provider: str) -> list[str]:
    from app.integrations.graph import PROVIDER_SCOPES

    return [s for s in PROVIDER_SCOPES.get(provider, []) if s != "offline_access"]


# A workspace starts empty of *findings*, not of the tools to work with. Without
# a template there is nothing to pick in the export picker, so the Generate
# button is permanently disabled and a report can never be produced at all.
TEMPLATE_DEFAULTS: list[dict] = [
    {
        "name": "Go/no-go brief",
        "kind": "report",
        "description": "The decision, the gates behind it, the risks, and the calendar — one page a principal can read before a stand-up.",
        "sections": ["Summary", "Go / no-go", "Key dates", "Risks"],
        "format": "DOCX",
    },
    {
        "name": "Full reading",
        "kind": "report",
        "description": "Everything the pass produced: every finding with its clause, the compliance matrix, and the questions for the agency.",
        "sections": [
            "Summary",
            "Go / no-go",
            "Key dates",
            "Evaluation factors",
            "Risks",
            "Findings",
            "Compliance matrix",
            "Questions",
        ],
        "format": "DOCX",
    },
]


async def ensure_org_provisioned(db: AsyncSession, user: User) -> None:
    """Idempotently give an org its owner roster entry, integrations, templates."""
    await _ensure_team_member(db, user)
    await _ensure_integrations(db, user.org_id)
    await _ensure_templates(db, user.org_id)


async def _ensure_templates(db: AsyncSession, org_id: str) -> None:
    existing = await db.execute(select(Template.name).where(Template.org_id == org_id))
    present = set(existing.scalars().all())
    for spec in TEMPLATE_DEFAULTS:
        if spec["name"] in present:
            continue
        db.add(
            Template(
                id=f"tpl_{uuid.uuid4().hex[:8]}",
                org_id=org_id,
                name=spec["name"],
                kind=spec["kind"],
                description=spec["description"],
                sections=spec["sections"],
                format=spec["format"],
                usage_count=0,
            )
        )


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
    existing = await db.execute(select(Integration).where(Integration.org_id == org_id))
    rows = {row.provider: row for row in existing.scalars().all()}

    for spec in INTEGRATION_DEFAULTS:
        row = rows.get(spec["provider"])
        if row is not None:
            # A card that advertises scopes the consent screen will not ask for
            # is a promise Margin cannot keep. A live connection keeps the
            # scopes it was actually granted.
            if not row.connected:
                row.scopes = default_scopes(spec["provider"])
            continue
        db.add(
            Integration(
                id=str(uuid.uuid4()),
                org_id=org_id,
                provider=spec["provider"],
                name=spec["name"],
                blurb=spec["blurb"],
                connected=False,
                scopes=default_scopes(spec["provider"]),
                tree=[],
            )
        )
