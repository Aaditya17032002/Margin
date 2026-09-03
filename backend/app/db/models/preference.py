"""User preferences model — stored as JSONB for flexibility."""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

DEFAULT_PREFS = {
    "appearance": "paper",
    "density": "comfortable",
    "defaultMode": "standard",
    "shortcutsEnabled": True,
    "reduceMotion": False,
    "marginRailPinned": False,
    "sidebarCollapsed": False,
    "coachDismissed": False,
    "notify": {
        "deadlines": True,
        "lowConfidence": True,
        "mentions": True,
        "amendments": True,
        "weeklyDigest": False,
    },
}


class Preference(UUIDMixin, Base):
    __tablename__ = "preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: dict(DEFAULT_PREFS))
