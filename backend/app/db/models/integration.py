"""Integration model — external service connections."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Integration(UUIDMixin, Base):
    __tablename__ = "integrations"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # outlook, sharepoint, onedrive
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    blurb: Mapped[str] = mapped_column(Text, nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    account: Mapped[str | None] = mapped_column(String(320), nullable=True)
    connected_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tree: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
