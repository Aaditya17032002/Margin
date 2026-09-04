"""Richer verification records, and lineage that survives a revision.

Two gaps.

A verdict recorded *what* a person concluded and not what they concluded it
from. "Dana said this is satisfied" is a name against an outcome; "Dana said
this is satisfied because she opened the rendered PDF and counted 38 pages" is
evidence. The second is what a debrief needs, and it is also the only kind of
record that makes a useful evaluation label.

And a response check pointed at a requirement and a response version but had no
lineage: when draft 3 replaced draft 2, the verdicts on draft 2 were simply
older rows. Nothing said *this check is the successor of that one*, so nothing
could say what had changed, what had been re-verified, or what had quietly
stopped being true.

Revision ID: 012_lineage
Revises: 011_contradictions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "012_lineage"
down_revision = "011_contradictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── What a verification was based on ─────────────────────────────────
    op.add_column("verdicts", sa.Column("basis", sa.String(32), nullable=False, server_default=""))
    op.add_column("verdicts", sa.Column("basis_detail", sa.Text(), nullable=False, server_default=""))
    op.add_column("verdicts", sa.Column("previous_verdict_id", sa.String(64), nullable=True))
    op.add_column("verdicts", sa.Column("response_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("verdicts", sa.Column("supersedes_verdict", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_verdicts_previous", "verdicts", ["previous_verdict_id"])

    # ── Lineage across response revisions ────────────────────────────────
    op.add_column("response_checks", sa.Column("supersedes_id", sa.String(64), nullable=True))
    op.add_column("response_checks", sa.Column("carried_verdict", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "response_checks",
        sa.Column("lineage", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_response_checks_supersedes", "response_checks", ["supersedes_id"])


def downgrade() -> None:
    op.drop_index("ix_response_checks_supersedes", table_name="response_checks")
    for column in ("lineage", "carried_verdict", "supersedes_id"):
        op.drop_column("response_checks", column)
    op.drop_index("ix_verdicts_previous", table_name="verdicts")
    for column in ("supersedes_verdict", "response_version", "previous_verdict_id", "basis_detail", "basis"):
        op.drop_column("verdicts", column)
