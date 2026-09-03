"""Template model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, value_enum


class Template(UUIDMixin, Base):
    __tablename__ = "templates"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(
        value_enum("report", "boilerplate", "dpa", name="template_kind"),
        nullable=False,
        default="report",
    )
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    format: Mapped[str] = mapped_column(
        value_enum("DOCX", "PDF", "MD", name="template_format"),
        nullable=False,
        default="DOCX",
    )
