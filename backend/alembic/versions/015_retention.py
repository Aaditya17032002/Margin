"""Retention policy, and the hold that beats it.

The org owns the timer; the analysis owns the exemption. Both are needed: a
policy without a hold flag is one nobody dares turn on, because the first
protest makes it a liability.

Revision ID: 015_retention
Revises: 014_decision
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "015_retention"
down_revision = "014_decision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Off by default, and stored as one document rather than five columns: the
    # classes a policy governs will change, and a migration per class would
    # make that change expensive enough to avoid.
    op.add_column(
        "orgs",
        sa.Column("retention", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    # A hold is a fact about a pursuit, not a setting on a policy — it has to
    # survive the policy being edited, and it has to say who put it there.
    op.add_column("analyses", sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("analyses", sa.Column("legal_hold_reason", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("legal_hold_by", sa.String(255), nullable=True))
    op.add_column("analyses", sa.Column("legal_hold_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "legal_hold_at")
    op.drop_column("analyses", "legal_hold_by")
    op.drop_column("analyses", "legal_hold_reason")
    op.drop_column("analyses", "legal_hold")
    op.drop_column("orgs", "retention")
