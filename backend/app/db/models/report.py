"""Report / export record model."""

from __future__ import annotations

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Report(UUIDMixin, Base):
    __tablename__ = "reports"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_title: Mapped[str] = mapped_column(String(500), nullable=False)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(
        Enum("DOCX", "PDF", name="report_format"),
        nullable=False,
        default="DOCX",
    )
    size: Mapped[int] = mapped_column(BigInteger, nullable=True, default=0)
    destination: Mapped[str] = mapped_column(
        Enum("download", "onedrive", "outlook", name="report_destination"),
        nullable=False,
        default="download",
    )
    status: Mapped[str] = mapped_column(
        Enum("ready", "generating", "failed", name="report_status"),
        nullable=False,
        default="generating",
    )
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
