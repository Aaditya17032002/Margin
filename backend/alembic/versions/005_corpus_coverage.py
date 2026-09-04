"""Coverage ledger and sweep totals on the analysis.

Margin's central claim is that nothing gets missed. A claim like that is only
worth making if it can be shown false, so a run now records what it actually
read — counted from chunk records rather than estimated.

Revision ID: 005_corpus_coverage
Revises: 004_analysis_research
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "005_corpus_coverage"
down_revision = "004_analysis_research"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("coverage", "sweep"):
        op.add_column(
            "analyses",
            sa.Column(column, JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )
    # Chunks are rewritten on every run and always read back by analysis; the
    # composite index is what that access pattern actually needs.
    op.create_index(
        "ix_doc_chunks_analysis_chunk",
        "doc_chunks",
        ["analysis_id", "chunk_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_doc_chunks_analysis_chunk", table_name="doc_chunks")
    for column in ("sweep", "coverage"):
        op.drop_column("analyses", column)
