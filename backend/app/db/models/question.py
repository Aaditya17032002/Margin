"""QA Question model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    #: Kept in step with `status` for the API shape the workspace already
    #: reads. `status` is the truth; this is the old boolean it replaces.
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    citation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Lifecycle ────────────────────────────────────────────────────────
    #: A question is not finished when it is sent. The answer is the point,
    #: and an answer that never reaches the requirement it was about has
    #: changed nothing.
    status: Mapped[str] = mapped_column(
        value_enum("draft", "submitted", "answered", "withdrawn", name="question_status"),
        nullable=False,
        default="draft",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: What the agency said, verbatim. Never a paraphrase: a Q&A answer is a
    #: contract document and the wording is the whole of it.
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Where the answer came from — "Amendment 0002", "Q&A set 1", an email.
    answer_source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    #: The requirement this question is about, when it is about one. Answering
    #: it reopens work done against the old reading.
    requirement_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
