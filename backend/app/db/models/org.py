"""Org model."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class Org(UUIDMixin, Base):
    __tablename__ = "orgs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Deliberately not unique. Two companies can share a mail domain, and more
    # to the point, a second signup from a domain must not be able to land in
    # an existing tenant's workspace — each signup gets its own org, and people
    # join a colleague's workspace by invitation.
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="Trial")
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    seats_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duns: Mapped[str] = mapped_column(String(20), nullable=True)
    cage: Mapped[str] = mapped_column(String(10), nullable=True)

    # Relationships
    users = relationship("User", back_populates="org", lazy="selectin")
