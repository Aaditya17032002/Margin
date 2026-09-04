"""A judgement, recorded as data rather than as prose.

Every time a person confirms, overrules or flags something Margin decided, two
useful things happen at once. The immediate one is governance: a name against a
conclusion. The other is that a labelled example has just been produced by
somebody who knows the answer — and until now it was written into a history
string and lost.

This table keeps it. One row per judgement, carrying **what the machine said,
what the person said, and the text both were looking at**.

The context is frozen into the row rather than referenced. A label that points
at a requirement is not a label once an amendment rewords that requirement: the
verdict would then describe text nobody judged. So the requirement, the
evidence and the machine's reasoning are copied in at the moment of the
decision, the way a signed document copies in what was signed.

What that buys, in order of how soon it pays:

* *Where are we wrong?* — corrections grouped by rule, by category, by whether
  a rule or a model decided, so the next change is aimed at a measured weakness
  instead of a guess.
* *Are we getting better?* — the same measurement over time.
* *Prove it.* — corrections export as evaluation cases, which is the only kind
  of eval corpus that grows on its own.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum

#: What the person did to the machine's answer.
CONFIRMED = "confirmed"
CORRECTED = "corrected"
FLAGGED = "flagged"


class Verdict(UUIDMixin, Base):
    __tablename__ = "verdicts"
    __table_args__ = (
        Index("ix_verdicts_org_outcome", "org_id", "outcome"),
        Index("ix_verdicts_subject", "subject_kind", "subject_id"),
    )

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    #: What was being judged. `subject_id` is a soft reference on purpose: the
    #: row it names may be superseded or deleted, and the verdict still stands.
    subject_kind: Mapped[str] = mapped_column(
        value_enum("response_check", "requirement", "citation", name="verdict_subject"),
        nullable=False,
        default="response_check",
    )
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    outcome: Mapped[str] = mapped_column(
        value_enum("confirmed", "corrected", "flagged", name="verdict_outcome"),
        nullable=False,
        default="confirmed",
    )

    # ── What the machine said ────────────────────────────────────────────
    machine_status: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    #: `rule`, `model`, or empty when nothing decided it yet.
    machine_decided_by: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    #: Which mechanical rule fired, when one did. This is the field that turns
    #: a pile of corrections into "the page-limit rule is wrong about
    #: exclusions".
    machine_rule: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    machine_detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    machine_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── What the person said ─────────────────────────────────────────────
    human_status: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── The text both were looking at, frozen ────────────────────────────
    reference: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stakes: Mapped[str] = mapped_column(String(20), nullable=False, default="scored")
    verification: Mapped[str] = mapped_column(String(16), nullable=False, default="substantive")
    #: The passage the machine was reasoning over. Without it a correction says
    #: someone disagreed and not what about.
    response_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
