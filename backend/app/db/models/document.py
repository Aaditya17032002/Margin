"""Document model — base documents, attachments, and amendments."""

from __future__ import annotations

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Document(UUIDMixin, Base):
    __tablename__ = "documents"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    doc_kind: Mapped[str] = mapped_column(
        Enum("base", "attachment", "amendment", name="doc_kind"),
        nullable=False,
        default="base",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
