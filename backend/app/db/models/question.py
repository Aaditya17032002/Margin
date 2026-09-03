"""QA Question model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class Question(UUIDMixin, Base):
    __tablename__ = "questions"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(
        value_enum("silent", "contradiction", "ambiguity", "manual", name="question_source"),
        nullable=False,
        default="manual",
    )
    go_no_go_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    citation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
