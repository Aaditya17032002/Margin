"""What the organisation already knows, in a form a requirement can query.

Two tables. Past performance is what we have done — contracts, scope, value,
period, and the reference who will speak to them. A solicitation asking for
three references of similar scope and recent relevance is asking a question the
answer to which lives in somebody's head today.

Content blocks are what we have written, with the provenance that makes them
worth offering: which requirement a paragraph answered, on which bid, whether
anybody verified it, and whether that bid was won. Suggesting old text without
that is how a proposal ends up describing a staffing model the company no
longer uses.

Revision ID: 013_memory
Revises: 012_lineage
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "013_memory"
down_revision = "012_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "past_performance",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("customer", sa.String(255), nullable=False, server_default=""),
        sa.Column("agency", sa.String(255), nullable=False, server_default=""),
        sa.Column("contract_number", sa.String(120), nullable=False, server_default=""),
        sa.Column("scope", sa.Text(), nullable=False, server_default=""),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.Date(), nullable=True),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("ongoing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("naics", sa.String(20), nullable=False, server_default=""),
        sa.Column("capabilities", ARRAY(sa.String(120)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("place_of_performance", sa.String(255), nullable=False, server_default=""),
        sa.Column("reference_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("reference_title", sa.String(255), nullable=False, server_default=""),
        sa.Column("reference_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("reference_phone", sa.String(64), nullable=False, server_default=""),
        sa.Column("reference_checked_at", sa.Date(), nullable=True),
        sa.Column("rating", sa.String(120), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_past_performance_org_id", "past_performance", ["org_id"])
    op.create_index("ix_past_performance_org_agency", "past_performance", ["org_id", "agency"])

    op.create_table(
        "content_blocks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("requirement_kind", sa.String(32), nullable=False, server_default="obligation"),
        sa.Column("tags", ARRAY(sa.String(120)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("source_analysis_id", sa.String(64), nullable=True),
        sa.Column("source_solicitation", sa.String(255), nullable=False, server_default=""),
        sa.Column("source_agency", sa.String(255), nullable=False, server_default=""),
        sa.Column("source_reference", sa.String(255), nullable=False, server_default=""),
        sa.Column("source_requirement", sa.Text(), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("last_verdict", sa.String(20), nullable=False, server_default=""),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_reason", sa.Text(), nullable=True),
        sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_content_blocks_org_id", "content_blocks", ["org_id"])
    op.create_index("ix_content_blocks_org_kind", "content_blocks", ["org_id", "requirement_kind"])


def downgrade() -> None:
    op.drop_table("content_blocks")
    op.drop_table("past_performance")
