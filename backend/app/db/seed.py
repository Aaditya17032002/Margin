"""Seed script — populates the database with demo data matching the frontend's seed fixtures.

Run: `python -m app.db.seed`
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base, get_engine, async_session_factory
from app.db.models import *  # noqa: F403 — import all models for table creation


def _offset_hours(h: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=h)).isoformat()


def _offset_days(d: int, hour: int = 12, minute: int = 0) -> str:
    dt = datetime.now(UTC) - timedelta(days=d)
    dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.isoformat()


async def seed() -> None:
    engine = get_engine()

    # Create all tables (for dev — in prod, use Alembic migrations)
    async with engine.begin() as conn:
        try:
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass  # pgvector might not be available in all dev setups
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if already seeded
        existing = await db.execute(select(Org).where(Org.id == "org_thornfield"))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # ── Org ──────────────────────────────────────────────────────────
        org = Org(
            id="org_thornfield",
            name="Thornfield Group",
            domain="thornfield.co",
            plan="Practice",
            seats=12,
            seats_used=6,
            duns="84-772-1190",
            cage="7BQK4",
        )
        db.add(org)
        await db.flush()

        # ── Users ────────────────────────────────────────────────────────
        users_data = [
            ("u_amara", "Amara Osei", "a.osei@thornfield.co", "admin", "Director of Capture", "patina"),
            ("u_priya", "Priya Raman", "p.raman@thornfield.co", "reviewer", "Compliance Counsel", "slate"),
            ("u_daniel", "Daniel Whitfield", "d.whitfield@thornfield.co", "writer", "Lead Proposal Writer", "ochre"),
            ("u_marcus", "Marcus Bell", "m.bell@thornfield.co", "writer", "Bid Coordinator", "leaf"),
            ("u_lena", "Lena Ford", "l.ford@thornfield.co", "reviewer", "Technical Reviewer", "seal"),
            ("u_javier", "Javier Mendes", "j.mendes@thornfield.co", "viewer", "Finance Partner", "ink"),
        ]
        pw_hash = hash_password("margin2026")
        for uid, name, email, role, title, tone in users_data:
            user = User(
                id=uid, name=name, email=email, password_hash=pw_hash,
                role=role, title=title, avatar_tone=tone, org_id=org.id,
                signature=f"{name} · {title} · Thornfield Group",
                timezone="America/Chicago",
                status="active" if uid != "u_javier" else "invited",
            )
            db.add(user)
        await db.flush()

        # ── Team Members ─────────────────────────────────────────────────
        for uid, name, email, role, title, tone in users_data:
            tm = TeamMember(
                id=f"tm_{uid}", user_id=uid, org_id=org.id,
                name=name, email=email, role=role, title=title,
                status="active" if uid != "u_javier" else "invited",
                last_active=_offset_hours(2), initials_color=tone,
            )
            db.add(tm)
        await db.flush()

        # ── Preferences ──────────────────────────────────────────────────
        from app.db.models.preference import DEFAULT_PREFS
        pref = Preference(user_id="u_amara", org_id=org.id, data=dict(DEFAULT_PREFS))
        db.add(pref)

        # ── Integrations ─────────────────────────────────────────────────
        integrations_data = [
            ("outlook", "Microsoft Outlook", True, "a.osei@thornfield.co"),
            ("sharepoint", "SharePoint", True, "thornfield.sharepoint.com / Capture"),
            ("onedrive", "OneDrive", False, None),
        ]
        for provider, name, connected, account in integrations_data:
            integ = Integration(
                id=f"int_{provider}", provider=provider, name=name, org_id=org.id,
                blurb=f"{name} integration", connected=connected, account=account,
                connected_at=_offset_days(38) if connected else None,
                scopes=["Mail.Read"] if provider == "outlook" else ["Files.ReadWrite.All"],
                tree=[],
            )
            db.add(integ)

        # ── Templates ────────────────────────────────────────────────────
        templates = [
            ("t_1", "Capture Brief — Executive", "report", "DOCX", 34),
            ("t_2", "Full Solicitation Analysis", "report", "DOCX", 61),
            ("t_3", "Compliance Matrix Export", "report", "DOCX", 88),
            ("t_4", "Clarifying Questions — Agency Format", "report", "DOCX", 47),
            ("t_5", "Data Protection Addendum — Standard", "dpa", "DOCX", 19),
            ("t_6", "FERPA School Official Boilerplate", "boilerplate", "MD", 12),
            ("t_7", "Accessibility Conformance Narrative", "boilerplate", "MD", 26),
        ]
        for tid, name, kind, fmt, usage in templates:
            t = Template(
                id=tid, org_id=org.id, name=name, kind=kind, format=fmt,
                description=f"Template: {name}", sections=[], usage_count=usage,
            )
            db.add(t)

        # ── Knowledge (Past Bids) ────────────────────────────────────────
        knowledge = [
            ("k_1", "Ohio Statewide Learning Platform", "Ohio Department of Education", "won", 27400000),
            ("k_2", "Federal Health Information Exchange Modernization", "HHS / ASPE", "lost", 9800000),
            ("k_3", "State Broadband Middle-Mile Program", "Kentucky Communications Authority", "lost", 15200000),
            ("k_4", "Naval Sensor Processing SBIR Phase II", "Office of Naval Research", "won", 1650000),
            ("k_5", "County Bridge Preservation Program", "Indiana Department of Transportation", "no-bid", 4100000),
            ("k_6", "Municipal Crisis Line Data Pilot", "City of Austin", "pending", 780000),
        ]
        for kid, title, agency, outcome, value in knowledge:
            k = KnowledgeItem(
                id=kid, org_id=org.id, title=title, agency=agency,
                outcome=outcome, value=value, submitted_at=_offset_days(300),
                debrief=f"Debrief for {title}", lessons=[],
            )
            db.add(k)

        # ── Notifications ────────────────────────────────────────────────
        notifications = [
            ("n_1", "amendment", "Amendment 0002 changed a hard gate", False),
            ("n_2", "deadline", "Questions due in four days", False),
            ("n_3", "review", "Six findings need review", False),
            ("n_4", "mention", "Priya Raman mentioned you", True),
            ("n_5", "export", "Capture brief exported", True),
        ]
        for nid, kind, title, read in notifications:
            n = Notification(
                id=nid, user_id="u_amara", org_id=org.id,
                kind=kind, title=title, body=f"Body for: {title}", read=read,
            )
            db.add(n)

        # ── Activity Log ─────────────────────────────────────────────────
        activities = [
            ("a_1", "Amara Osei", "opened the compliance matrix", "TEA-2026-DLP-114"),
            ("a_2", "Margin", "detected three critical changes in", "Amendment 0002"),
            ("a_3", "Priya Raman", "verified 4 findings in", "Legal & Regulatory"),
        ]
        for aid, actor, action, target in activities:
            a = ActivityLog(
                id=aid, org_id=org.id, actor=actor, action=action, target=target,
            )
            db.add(a)

        await db.commit()
        print("Database seeded successfully!")
        print("Demo login: a.osei@thornfield.co / margin2026")


if __name__ == "__main__":
    asyncio.run(seed())
