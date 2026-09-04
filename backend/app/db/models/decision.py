"""A bid/no-bid decision, and the evidence as it stood when it was made.

Margin does not decide — the things that settle a bid are whether the company
wants this customer and whether the team is free in March, none of which is in
the document. What it does is make the decision accountable.

The evidence is frozen into the row rather than joined. A record that
reconstructs what was known from live tables describes today, and the question
six months after a loss is always about the day it was decided.

`acknowledged` is the field that makes this more than a note: the ids of the
considerations the decision-maker explicitly saw and accepted. "We knew about
the two unresolved contradictions and bid anyway" is a defensible position. "We
did not notice them" is not, and the difference should be recorded at the time
rather than reconstructed afterwards.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class DecisionRecord(UUIDMixin, Base):
    __tablename__ = "decision_records"

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    decision: Mapped[str] = mapped_column(
        value_enum("bid", "no-bid", "watch", name="decision_value"), nullable=False
    )
    #: Why. The one field that cannot be derived and the only one that matters
    #: in a debrief.
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Everyone in the room. A bid decision is rarely one person's.
    participants: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)

    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    #: Which considerations were explicitly seen and accepted.
    acknowledged: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False, default=list)

    #: A decision that replaced an earlier one — a no-bid reversed after an
    #: amendment, a bid pulled after a debrief. Kept as a chain, because "we
    #: changed our minds and here is why" is the useful record.
    supersedes_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    outcome: Mapped[str] = mapped_column(
        value_enum("pending", "won", "lost", "no_award", "not_submitted", name="decision_outcome"),
        nullable=False,
        default="pending",
    )
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
