"""Close the gap between the models and the initial schema.

Three tables the models declare were never created — `team_invites` (which the
invite endpoint writes to on every invitation), `findings`, and `citations` —
and `knowledge_items` was missing the embedding column every read of it
selects.

Revision ID: 002_schema_drift
Revises: 001_initial_schema
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_schema_drift"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

TIMESTAMPS = (
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
)


def upgrade() -> None:
    op.execute("ALTER TABLE knowledge_items ADD COLUMN IF NOT EXISTS embedding vector(1536)")

    op.create_table(
        "team_invites",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="writer"),
        sa.Column("invited_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        *TIMESTAMPS,
    )
    op.create_index("ix_team_invites_org_id", "team_invites", ["org_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="ANSWERED"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stakes", sa.String(length=20), nullable=False, server_default="informational"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        *TIMESTAMPS,
    )
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])
    op.create_index("ix_findings_org_id", "findings", ["org_id"])

    op.create_table(
        "citations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("finding_id", sa.String(length=64), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="solicitation"),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section_path", sa.String(length=500), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("quote", sa.String(length=200), nullable=True),
        sa.Column("url", sa.String(length=2000), nullable=True),
        *TIMESTAMPS,
    )
    op.create_index("ix_citations_finding_id", "citations", ["finding_id"])


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("findings")
    op.drop_table("team_invites")
    op.execute("ALTER TABLE knowledge_items DROP COLUMN IF EXISTS embedding")
