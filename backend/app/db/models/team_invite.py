"""Team invite model."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class TeamInvite(UUIDMixin, Base):
    __tablename__ = "team_invites"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "reviewer", "writer", "viewer", name="invite_role", create_constraint=False),
        nullable=False,
        default="writer",
    )
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "expired", name="invite_status"),
        nullable=False,
        default="pending",
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
