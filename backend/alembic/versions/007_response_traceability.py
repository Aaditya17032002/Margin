"""Response checks: one requirement, one response version, one verdict.

Rows are keyed by requirement and response version rather than replaced in
place, because "was this gap there in the last draft?" is a question the
compliance lead asks on every revision, and a table holding only the newest
answer cannot answer it.

`analyses.response` carries the binding: which document is the current draft,
what version it is, and when it was last checked. A response is a separately
versioned corpus bound to a solicitation Margin has already read — never a
loose document dropped into a general-purpose checker.

Revision ID: 007_response_traceability
Revises: 006_requirement_ledger
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "007_response_traceability"
down_revision = "006_requirement_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "response_checks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column(
            "requirement_id",
            sa.String(64),
            sa.ForeignKey("requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("response_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("response_document_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverifiable"),
        sa.Column("verification", sa.String(16), nullable=False, server_default="substantive"),
        sa.Column("decided_by", sa.String(16), nullable=False, server_default="rule"),
        sa.Column("rule", sa.String(64), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("gap", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk", sa.String(10), nullable=False, server_default="low"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("evidence", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("needs_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_response_checks_analysis_id", "response_checks", ["analysis_id"])
    op.create_index("ix_response_checks_org_id", "response_checks", ["org_id"])
    op.create_index("ix_response_checks_requirement_id", "response_checks", ["requirement_id"])
    op.create_index(
        "ix_response_checks_analysis_version", "response_checks", ["analysis_id", "response_version"]
    )
    op.create_index(
        "uq_response_checks_req_version",
        "response_checks",
        ["requirement_id", "response_version"],
        unique=True,
    )

    op.add_column(
        "analyses",
        sa.Column("response", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("analyses", "response")
    op.drop_table("response_checks")
