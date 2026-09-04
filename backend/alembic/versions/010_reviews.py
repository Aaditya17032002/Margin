"""Colour-team review rounds and their findings.

A capture team reviews a response in rounds — pink, red, gold, white glove —
and the discipline of the practice is that a round ends with a named person
saying it can proceed. None of that was recorded anywhere, so the sign-offs
that govern whether a proposal is sent lived in email.

Revision ID: 010_reviews
Revises: 009_verdicts
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "010_reviews"
down_revision = "009_verdicts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_rounds",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("colour", sa.String(16), nullable=False, server_default="red"),
        sa.Column("response_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("charter", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewers", ARRAY(sa.String(255)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("verdict", sa.String(24), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("opened_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(255), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_review_rounds_analysis_id", "review_rounds", ["analysis_id"])
    op.create_index("ix_review_rounds_org_id", "review_rounds", ["org_id"])
    op.create_index("ix_review_rounds_analysis_status", "review_rounds", ["analysis_id", "status"])

    op.create_table(
        "review_findings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("round_id", sa.String(64), sa.ForeignKey("review_rounds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("requirement_id", sa.String(64), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="should_fix"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(255), nullable=False, server_default=""),
        sa.Column("state", sa.String(16), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("raised_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_review_findings_round_id", "review_findings", ["round_id"])
    op.create_index("ix_review_findings_analysis_id", "review_findings", ["analysis_id"])
    op.create_index("ix_review_findings_org_id", "review_findings", ["org_id"])
    op.create_index("ix_review_findings_round_state", "review_findings", ["round_id", "state"])


def downgrade() -> None:
    op.drop_table("review_findings")
    op.drop_table("review_rounds")
