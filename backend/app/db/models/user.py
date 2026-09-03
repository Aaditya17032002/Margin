"""User model with argon2 password hash and role enum."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class User(UUIDMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "reviewer", "writer", "viewer", name="user_role", create_constraint=True),
        nullable=False,
        default="writer",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    avatar_tone: Mapped[str] = mapped_column(String(20), nullable=True, default="patina")
    signature: Mapped[str] = mapped_column(String(500), nullable=True, default="")
    timezone: Mapped[str] = mapped_column(String(50), nullable=True, default="America/Chicago")
    status: Mapped[str] = mapped_column(
        Enum("active", "invited", "suspended", name="user_status", create_constraint=True),
        nullable=False,
        default="active",
    )

    # FK
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    # Relationships
    org = relationship("Org", back_populates="users", lazy="selectin")
