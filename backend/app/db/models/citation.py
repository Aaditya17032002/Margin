"""Citation model — precise source references for findings."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class Citation(UUIDMixin, Base):
    __tablename__ = "citations"

    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        value_enum("solicitation", "web", name="citation_source"),
        nullable=False,
        default="solicitation",
    )
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    page: Mapped[int] = mapped_column(Integer, nullable=True)
    section_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quote: Mapped[str | None] = mapped_column(String(200), nullable=True)  # ≤15 words
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
