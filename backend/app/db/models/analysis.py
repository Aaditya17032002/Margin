"""Analysis model — mirrors the frontend Analysis type field-for-field.

The complex nested arrays (findings, gates, evaluation, risks, etc.) are stored
as JSONB to match the frontend's flat object shape exactly.  The agentic pipeline
writes to structured `findings` + `citations` tables internally but merges the
result into these JSONB arrays before exposing via the API.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, UUIDMixin, value_enum


class Analysis(UUIDMixin, SoftDeleteMixin, Base):
    __tablename__ = "analyses"

    # ── Identity ─────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    solicitation_number: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending assignment")
    agency: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_agency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doc_type: Mapped[str] = mapped_column(
        value_enum("RFP", "RFI", "RFQ", "IFB", "Sources Sought", "BAA", "Task Order", name="doc_type"),
        nullable=False,
        default="RFP",
    )
    mode: Mapped[str] = mapped_column(
        value_enum(
            "quick-triage", "standard", "deep-research", "matrix-only",
            "qa-only", "amendment-refresh", "recompete-compare",
            name="analysis_mode",
        ),
        nullable=False,
        default="standard",
    )
    stage: Mapped[str] = mapped_column(
        value_enum("triage", "analyzing", "review", "decided", name="analysis_stage"),
        nullable=False,
        default="triage",
    )
    go_no_go: Mapped[str] = mapped_column(
        value_enum("bid", "no-bid", "watch", "undecided", name="go_no_go"),
        nullable=False,
        default="undecided",
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    spec_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # ── Ownership ────────────────────────────────────────────────────────
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    collaborators: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    # ── Document metadata ────────────────────────────────────────────────
    naics: Mapped[str] = mapped_column(String(20), nullable=True, default="Not yet determined")
    set_aside: Mapped[str] = mapped_column(String(100), nullable=True, default="Not yet determined")
    place_of_performance: Mapped[str] = mapped_column(String(255), nullable=True, default="Not yet determined")
    estimated_value: Mapped[float] = mapped_column(Float, nullable=True, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    file_name: Mapped[str] = mapped_column(String(500), nullable=True, default="")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    source: Mapped[str] = mapped_column(
        value_enum("upload", "sharepoint", "onedrive", "outlook", name="analysis_source"),
        nullable=False,
        default="upload",
    )
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # ── Analysis results (JSONB — matches frontend shape exactly) ────────
    summary: Mapped[str] = mapped_column(Text, nullable=True, default="")
    identity: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scope: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    legal: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    eligibility: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pricing: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    post_award: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    gates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evaluation: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    silent: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    dates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    clins: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    amendments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    versions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    #: What a deep-research pass read on the open web, kept apart from anything
    #: the solicitation says. Shape: {status, query, summary, sources: [...], at}.
    #: External claims and document clauses must never be shown as the same kind
    #: of thing, so they are not stored as the same kind of thing either.
    research: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    #: What was read, by what, and what was not. Counted from chunk records
    #: rather than estimated — the claim has to be falsifiable to be worth
    #: making. Shape: {at, totals, documents[], byAgent, complete}.
    coverage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    #: Deterministic sweep totals for this run, so a drop in what the rules
    #: find is visible without re-running the pass.
    sweep: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
