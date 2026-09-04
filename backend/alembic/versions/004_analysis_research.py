"""Give external research a home of its own.

A deep-research pass reads the open web. Those claims were being appended to the
`legal` findings array with the source URL stuffed into `citation.quote` — the
field that holds a verbatim clause from the solicitation — and `page: 0`. The
result read as a document finding, which is the one thing it is not.

Revision ID: 004_analysis_research
Revises: 003_org_domain_not_unique
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "004_analysis_research"
down_revision = "003_org_domain_not_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("research", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("analyses", "research")
