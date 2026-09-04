"""What the organisation already knows, in a form a requirement can query.

Two tables, and the distinction between them is the point.

``PastPerformance`` is *what we have done*: contracts, their agency, scope,
value and period, and the reference who will speak to them. A solicitation asks
for three references of similar scope and recent relevance; the answer is in
here or it is nowhere, and today it is in somebody's head.

``ContentBlock`` is *what we have written*: a paragraph that answered a
particular requirement on a particular bid. The reason this is not a snippet
library is the provenance. A block carries where it came from, which
requirement it answered, whether anyone verified it, and whether that bid was
won — because "this paragraph answered L.4.2 on the FNS award and Dana signed
it off" and "here is some old text about quality control" are completely
different things to hand somebody at 2am.

Suggesting old text without that context is how a proposal ends up describing a
staffing model the company no longer uses, in a paragraph that lost the last
three bids it was in.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class PastPerformance(UUIDMixin, Base):
    """A contract the organisation has delivered."""

    __tablename__ = "past_performance"
    __table_args__ = (Index("ix_past_performance_org_agency", "org_id", "agency"),)

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    customer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    agency: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    contract_number: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    #: What was actually delivered, in the words a proposal would use.
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="")
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    started_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Whether the work is still running. A current contract is stronger
    #: evidence of capability than one that ended four years ago.
    ongoing: Mapped[bool] = mapped_column(nullable=False, default=False)

    naics: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    #: The capabilities this contract demonstrates, as a proposal would claim
    #: them. Free tags rather than a taxonomy: every organisation's vocabulary
    #: is its own, and a fixed list would be filled in wrongly or not at all.
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String(120)), nullable=False, default=list)
    place_of_performance: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    #: The person who will answer a past performance questionnaire.
    reference_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reference_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reference_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reference_phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    #: When somebody last confirmed the reference is still willing and still
    #: there. A stale reference is worse than none: it fails at the worst time.
    reference_checked_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    #: CPARS or equivalent, in whatever words the customer used.
    rating: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ContentBlock(UUIDMixin, Base):
    """A passage that answered a requirement on a previous bid."""

    __tablename__ = "content_blocks"
    __table_args__ = (
        Index("ix_content_blocks_org_kind", "org_id", "requirement_kind"),
    )

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    #: The kind of requirement this answers — obligation, certification, form,
    #: limit, volume — so a page-limit block is never offered for a narrative
    #: requirement.
    requirement_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="obligation")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(120)), nullable=False, default=list)

    # ── Where it came from ───────────────────────────────────────────────
    #: The pursuit it was written for. A soft reference: the analysis may be
    #: deleted and the block still has a history worth stating.
    source_analysis_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_solicitation: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    source_agency: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    #: The clause it answered, as that solicitation numbered it.
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    source_requirement: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── What happened to it ──────────────────────────────────────────────
    #: Whether the bid it was written for was won. Text from a losing proposal
    #: is not disqualified — most losses have nothing to do with any one
    #: paragraph — but it is different evidence, and hiding which is which is
    #: how a library slowly fills with text that has never worked.
    outcome: Mapped[str] = mapped_column(
        value_enum("won", "lost", "no_award", "withdrawn", "unknown", name="content_outcome"),
        nullable=False,
        default="unknown",
    )
    #: The verdict the response check reached on it, if it was ever checked.
    last_verdict: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Set when somebody marks a block as no longer true — a staffing model
    #: that changed, a certification that lapsed. Retired rather than deleted,
    #: so a proposal that used it can still be explained.
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
