"""Requirements in the same package that cannot both be met.

Section L says forty pages, an attachment says fifty, an amendment says
sixty-five. All three extracted correctly, all three in the ledger looking
equally authoritative, and the team writes to whichever one they read. Nothing
else in the product catches it: coverage says everything was read, the sweep
found all three, and the matrix lists all three as open requirements.

Revision ID: 011_contradictions
Revises: 010_reviews
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "011_contradictions"
down_revision = "010_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contradictions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False, server_default=""),
        sa.Column("left_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("right_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("left_value", sa.String(255), nullable=False, server_default=""),
        sa.Column("right_value", sa.String(255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(16), nullable=False, server_default="blocking"),
        sa.Column("state", sa.String(16), nullable=False, server_default="open"),
        sa.Column("governs_id", sa.String(64), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("question_id", sa.String(64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_run", sa.String(64), nullable=False, server_default=""),
        sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_contradictions_analysis_id", "contradictions", ["analysis_id"])
    op.create_index("ix_contradictions_org_id", "contradictions", ["org_id"])
    op.create_index("ix_contradictions_analysis_state", "contradictions", ["analysis_id", "state"])
    op.create_index(
        "uq_contradictions_analysis_key", "contradictions", ["analysis_id", "key"], unique=True
    )

    op.add_column(
        "analyses",
        sa.Column("contradictions", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("analyses", "contradictions")
    op.drop_table("contradictions")
