"""Matrix row model — compliance matrix entries."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class MatrixRow(UUIDMixin, Base):
    __tablename__ = "matrix_rows"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("shall", "should", "may", name="requirement_type"),
        nullable=False,
        default="shall",
    )
    stakes: Mapped[str] = mapped_column(
        Enum("disqualifying", "scored", "informational", name="matrix_stakes"),
        nullable=False,
        default="scored",
    )
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_location: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    status: Mapped[str] = mapped_column(
        Enum("unassigned", "assigned", "drafted", "in-review", "complete", name="matrix_status"),
        nullable=False,
        default="unassigned",
    )
    citation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
