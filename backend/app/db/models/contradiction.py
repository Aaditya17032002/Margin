"""Two requirements in the same package that cannot both be met.

Kept as its own record rather than as a flag on a requirement, because a
contradiction belongs to the *pair* and outlives both halves of it: when a
reviewer decides that the amendment governs, the losing requirement is
superseded and the reasoning has to survive that.

`state` is the whole lifecycle. A contradiction is `open` until somebody reads
both clauses; `resolved` when they have said which governs and why;
`disputed` when they have decided the document itself is wrong and a question
to the agency is the only way out — which is a different outcome from either,
and the one most likely to change a deadline.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class Contradiction(UUIDMixin, Base):
    __tablename__ = "contradictions"
    __table_args__ = (
        # Identity is the pair and the thing they disagree about, so a re-run
        # finds the same contradiction rather than raising it again.
        Index("uq_contradictions_analysis_key", "analysis_id", "key", unique=True),
        Index("ix_contradictions_analysis_state", "analysis_id", "state"),
    )

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)

    #: What they disagree about: page_limit, deadline, permission, and so on.
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    left_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    right_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    left_value: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    right_value: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    #: Which one probably governs, and why. A recommendation the product makes
    #: and never acts on: choosing for the team would be choosing which
    #: requirement they write to.
    recommended_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(
        value_enum("blocking", "important", name="contradiction_severity"),
        nullable=False,
        default="blocking",
    )

    state: Mapped[str] = mapped_column(
        value_enum("open", "resolved", "disputed", "dismissed", name="contradiction_state"),
        nullable=False,
        default="open",
    )
    #: The requirement the reviewer decided governs.
    governs_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Set when resolving raised a question to the agency, so the two records
    #: point at each other.
    question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_run: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
