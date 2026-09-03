"""Finding model — structured findings from the agentic pipeline."""

from __future__ import annotations

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Finding(UUIDMixin, Base):
    __tablename__ = "findings"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    state: Mapped[str] = mapped_column(
        Enum("ANSWERED", "SILENT", "NEEDS_HUMAN", name="finding_state"),
        nullable=False,
        default="ANSWERED",
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stakes: Mapped[str] = mapped_column(
        Enum("disqualifying", "scored", "informational", name="stakes_level"),
        nullable=False,
        default="informational",
    )
    verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    flagged: Mapped[bool] = mapped_column(nullable=False, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
