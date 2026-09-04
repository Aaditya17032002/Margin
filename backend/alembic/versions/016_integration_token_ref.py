"""Widen integrations.token_ref for sealed Microsoft refresh tokens.

Fernet-encrypted refresh tokens exceed VARCHAR(500) and broke the OAuth callback.

Revision ID: 016_integration_token_ref
Revises: 015_retention
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "016_integration_token_ref"
down_revision = "015_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "integrations",
        "token_ref",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "integrations",
        "token_ref",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
