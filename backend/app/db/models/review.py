"""Colour-team reviews: the rounds a proposal is judged in before it is sent.

A capture team does not review a response once. It reviews it in rounds, each
asking a different question, and the discipline of the practice is that a round
ends with a named person saying it can proceed.

``pink``
    Early draft. Is the approach right, and is the structure compliant enough
    to be worth writing into?
``red``
    A full read as the evaluator will score it. The most valuable round and the
    one most often skipped when a deadline tightens.
``gold``
    Executive review before submission. Is this a bid we are prepared to make?
``white_glove``
    Production. Fonts, margins, forms, signatures, file names, volume
    structure — the rules Margin can count but cannot see in extracted text,
    which is exactly what this round exists to check in the rendered file.

Two things make this more than a checklist table.

**A round is against a version of the response.** A Red Team on draft 2 says
nothing about draft 4, and a round with no version attached reviews nothing in
particular.

**A round is not closed while its must-fix findings are open.** Closing one
anyway is allowed, because a real deadline sometimes wins — but it takes a
written reason and it is recorded as an override rather than as a clean pass.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum

COLOURS = ("pink", "red", "gold", "white_glove")

#: What each round is for, shown when one is opened. A round whose reviewers
#: disagree about its purpose produces findings nobody can act on.
CHARTERS: dict[str, str] = {
    "pink": (
        "Is the approach right, and is the structure compliant enough to be worth writing "
        "into? Findings here should be about direction and outline, not wording."
    ),
    "red": (
        "Read it as the evaluator will score it, against the evaluation factors and nothing "
        "else. Score what is on the page, not what the team meant."
    ),
    "gold": (
        "Is this a bid we are prepared to make? Price, risk, commitments, and whether the "
        "response we are about to send is one we can deliver."
    ),
    "white_glove": (
        "Production check against the rendered files: fonts, margins, spacing, page counts, "
        "file names, formats, required forms and signatures, volume structure. Margin can "
        "count these but cannot see them in extracted text — this round is where they are "
        "actually verified."
    ),
}


class ReviewRound(UUIDMixin, Base):
    __tablename__ = "review_rounds"
    __table_args__ = (Index("ix_review_rounds_analysis_status", "analysis_id", "status"),)

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    colour: Mapped[str] = mapped_column(
        value_enum(*COLOURS, name="review_colour"), nullable=False, default="red"
    )
    #: Which draft was reviewed. A round with no version attached reviews
    #: nothing in particular, and its findings cannot be aged.
    response_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    charter: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewers: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)

    status: Mapped[str] = mapped_column(
        value_enum("open", "closed", name="review_status"), nullable=False, default="open"
    )
    #: The round's answer, recorded when it closes.
    verdict: Mapped[str | None] = mapped_column(
        value_enum("proceed", "proceed_with_fixes", "do_not_proceed", name="review_verdict"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Set when a round was closed over its own unresolved must-fix findings.
    #: Kept apart from `note` so a clean pass and an overridden one can never
    #: be mistaken for each other in a report.
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    opened_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class ReviewFinding(UUIDMixin, Base):
    """One thing a reviewer found.

    A finding can name the requirement it is about, which is what connects a
    review round to the compliance matrix rather than leaving it as a parallel
    list of comments nobody reconciles.
    """

    __tablename__ = "review_findings"
    __table_args__ = (Index("ix_review_findings_round_state", "round_id", "state"),)

    round_id: Mapped[str] = mapped_column(
        ForeignKey("review_rounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    #: A soft reference: the requirement may be superseded later and the
    #: finding still stands against what was reviewed.
    requirement_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    severity: Mapped[str] = mapped_column(
        value_enum("must_fix", "should_fix", "consider", name="review_severity"),
        nullable=False,
        default="should_fix",
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    #: Where in the response — "Volume I, §3.2". Free text, because a reviewer
    #: reading a PDF describes a location the way they see it.
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    state: Mapped[str] = mapped_column(
        value_enum("open", "fixed", "accepted", "rejected", name="review_finding_state"),
        nullable=False,
        default="open",
    )
    #: Why it was rejected, or what was done about it. A finding closed with no
    #: word about it is a finding the next round will raise again.
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    raised_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    raised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
