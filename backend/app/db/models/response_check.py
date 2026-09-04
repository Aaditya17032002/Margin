"""One requirement, checked against one version of the response.

Rows are keyed by requirement *and* response version, so a second draft is a
second set of checks rather than an overwrite: "was this gap there last week?"
is a question a proposal manager asks constantly, and a table that only holds
the newest answer cannot answer it.

`decided_by` is not decoration. A row decided by `rule` was counted, a row
decided by `model` was read, and a row decided by `human` was signed. A reader
must never have to guess which kind of claim they are looking at.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class ResponseCheck(UUIDMixin, Base):
    __tablename__ = "response_checks"
    __table_args__ = (
        Index("uq_response_checks_req_version", "requirement_id", "response_version", unique=True),
        Index("ix_response_checks_analysis_version", "analysis_id", "response_version"),
    )

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: The response draft this check was made against, and the file it read.
    response_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    response_document_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    status: Mapped[str] = mapped_column(
        value_enum(
            "satisfied", "partial", "failed", "not_found", "unverifiable",
            name="response_check_status",
        ),
        nullable=False,
        default="unverifiable",
    )
    #: `mechanical` was counted; `substantive` was read.
    verification: Mapped[str] = mapped_column(
        value_enum("mechanical", "substantive", name="requirement_verification"),
        nullable=False,
        default="substantive",
    )
    decided_by: Mapped[str] = mapped_column(
        value_enum("rule", "model", "human", name="response_check_decider"),
        nullable=False,
        default="rule",
    )
    #: Which mechanical rule fired, so a disputed result traces to the code
    #: that produced it rather than to a prompt nobody kept.
    rule: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gap: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk: Mapped[str] = mapped_column(
        value_enum("low", "medium", "high", name="response_check_risk"),
        nullable=False,
        default="low",
    )
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Where in the response this was answered: {documentId, page, section,
    #: quote, located}. `located: false` means the quote could not be found in
    #: the response and the claim resting on it was downgraded.
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: A model calling a mandatory requirement satisfied is a recommendation.
    #: It stays one until a person signs it here.
    needs_confirmation: Mapped[bool] = mapped_column(nullable=False, default=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: What a person said when they overruled or accepted the check.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
