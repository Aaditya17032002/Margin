"""Knowledge item model — past bids / institutional memory."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[assignment, misc]


class KnowledgeItem(UUIDMixin, Base):
    __tablename__ = "knowledge_items"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    agency: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_at: Mapped[str] = mapped_column(String(50), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    value: Mapped[float] = mapped_column(Float, nullable=True, default=0)
    debrief: Mapped[str] = mapped_column(Text, nullable=True, default="")
    lessons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    incumbent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score_gap: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Embedding for KB vector search
    embedding = mapped_column(Vector(1536) if Vector else Text, nullable=True)
