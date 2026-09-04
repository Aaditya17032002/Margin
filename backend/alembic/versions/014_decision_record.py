"""The bid/no-bid decision, and what was known when it was made.

`go_no_go` and a note recorded the answer. Six months after a loss the question
is never "was the machine right" — it is "what did we know when we decided, and
did we look at it", and nothing held the answer.

Revision ID: 014_decision
Revises: 013_memory
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "014_decision"
down_revision = "013_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("participants", sa.dialects.postgresql.ARRAY(sa.String(255)), nullable=False,
                  server_default=sa.text("'{}'::varchar[]")),
        # Frozen, not joined. A record that reconstructs the evidence from live
        # rows describes today, and the question is always about the day it was
        # decided.
        sa.Column("evidence", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("acknowledged", sa.dialects.postgresql.ARRAY(sa.String(64)), nullable=False,
                  server_default=sa.text("'{}'::varchar[]")),
        sa.Column("supersedes_id", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("outcome_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_decision_records_analysis_id", "decision_records", ["analysis_id"])
    op.create_index("ix_decision_records_org_id", "decision_records", ["org_id"])


def downgrade() -> None:
    op.drop_table("decision_records")
