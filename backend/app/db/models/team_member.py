"""Team member model."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class TeamMember(UUIDMixin, Base):
    __tablename__ = "team_members"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "reviewer", "writer", "viewer", name="team_role", create_constraint=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    status: Mapped[str] = mapped_column(
        Enum("active", "invited", "suspended", name="member_status", create_constraint=False),
        nullable=False,
        default="active",
    )
    last_active: Mapped[str] = mapped_column(String(50), nullable=True)
    initials_color: Mapped[str] = mapped_column(String(20), nullable=True, default="patina")
