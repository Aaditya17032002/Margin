"""The Requirement Ledger — one row per thing the solicitation demands.

This table replaces `matrix_rows` as the source of truth. The compliance
matrix is now a projection of it: the same rows, shown as a worksheet.

Three columns carry the weight:

``key``
    Derived from the requirement's own words, so the same requirement keeps
    the same row across every re-read of the package. Ownership and status
    used to be attached to ids that a re-run threw away.

``verification``
    `mechanical` or `substantive`, decided in code and never by a model.
    Page counts, fonts, margins, file names, forms and signatures are counted;
    everything else is read.

``state``
    A requirement is `open` until an amendment supersedes it or removes it.
    Nothing is deleted by a run — a requirement that disappears is recorded as
    having disappeared, which is a finding rather than an absence.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class Requirement(UUIDMixin, Base):
    __tablename__ = "requirements"
    __table_args__ = (
        # Identity is per analysis: the same clause in two solicitations is two
        # requirements, and the same clause read twice is one.
        Index("uq_requirements_analysis_key", "analysis_id", "key", unique=True),
        Index("ix_requirements_analysis_state", "analysis_id", "state"),
    )

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    # ── Identity ─────────────────────────────────────────────────────────
    key: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── What it says ─────────────────────────────────────────────────────
    reference: Mapped[str] = mapped_column(String(255), nullable=False, default="Unreferenced")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    #: The sweep category it came from: obligation, instruction, limit, form,
    #: certification, volume.
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="obligation")
    type: Mapped[str] = mapped_column(
        value_enum("shall", "should", "may", name="requirement_type"),
        nullable=False,
        default="shall",
    )
    stakes: Mapped[str] = mapped_column(
        value_enum("disqualifying", "scored", "informational", name="matrix_stakes"),
        nullable=False,
        default="scored",
    )
    verification: Mapped[str] = mapped_column(
        value_enum("mechanical", "substantive", name="requirement_verification"),
        nullable=False,
        default="substantive",
    )
    citation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── How it was found ─────────────────────────────────────────────────
    #: "sweep", "model", "manual" — a requirement both passes found is stronger
    #: evidence than one only a model saw, and the ledger says which.
    sources: Mapped[list[str]] = mapped_column(ARRAY(String(16)), nullable=False, default=list)

    # ── Lifecycle ────────────────────────────────────────────────────────
    state: Mapped[str] = mapped_column(
        value_enum("open", "superseded", "removed", name="requirement_state"),
        nullable=False,
        default="open",
    )
    #: The requirement this one replaces, and the one that replaced it. Set by
    #: amendment analysis; empty on a first read.
    supersedes_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: The document that introduced it — the base solicitation, or an amendment.
    introduced_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Runs in which this requirement was present. A requirement missing from
    #: the newest run is not deleted; the gap is the signal.
    last_seen_run: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    # ── Human state — never touched by a run ─────────────────────────────
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_location: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    status: Mapped[str] = mapped_column(
        value_enum("unassigned", "assigned", "drafted", "in-review", "complete", name="matrix_status"),
        nullable=False,
        default="unassigned",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: When this requirement's answer has to be written by. Not the
    #: solicitation's deadline — the team's internal one, which is the date
    #: that actually governs whether the work happens.
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: A mandatory requirement marked satisfied by a model is not cleared until
    #: a person says so. This is that signature.
    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: Append-only record of what changed and when: {at, event, detail}.
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
