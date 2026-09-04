"""Human judgements, recorded as data rather than as prose.

Confirmations and corrections were written into `history` strings — enough for
an audit trail, useless as labelled data. Each one is an example produced by
somebody who knows the answer, and they were being thrown away.

The context is copied into the row rather than referenced. A label pointing at
a requirement stops being a label the moment an amendment rewords that
requirement, so the requirement text, the evidence and the machine's reasoning
are frozen at the moment of the decision.

Revision ID: 009_verdicts
Revises: 008_qa_lifecycle
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "009_verdicts"
down_revision = "008_qa_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verdicts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_kind", sa.String(20), nullable=False, server_default="response_check"),
        sa.Column("subject_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("machine_status", sa.String(20), nullable=False, server_default=""),
        sa.Column("machine_decided_by", sa.String(16), nullable=False, server_default=""),
        sa.Column("machine_rule", sa.String(64), nullable=False, server_default=""),
        sa.Column("machine_detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("machine_evidence", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("human_status", sa.String(20), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(255), nullable=False, server_default=""),
        sa.Column("requirement_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("stakes", sa.String(20), nullable=False, server_default="scored"),
        sa.Column("verification", sa.String(16), nullable=False, server_default="substantive"),
        sa.Column("response_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor", sa.String(255), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_verdicts_org_id", "verdicts", ["org_id"])
    op.create_index("ix_verdicts_analysis_id", "verdicts", ["analysis_id"])
    op.create_index("ix_verdicts_org_outcome", "verdicts", ["org_id", "outcome"])
    op.create_index("ix_verdicts_subject", "verdicts", ["subject_kind", "subject_id"])


def downgrade() -> None:
    op.drop_table("verdicts")
