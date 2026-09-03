"""Activity log model — audit trail."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class ActivityLog(UUIDMixin, Base):
    __tablename__ = "activity_log"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str | None] = mapped_column(String(500), nullable=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id"), nullable=True, index=True)
