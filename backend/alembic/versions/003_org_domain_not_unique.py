"""Let two orgs share a mail domain.

`orgs.domain` was unique, so the second person to sign up from a company hit an
opaque 409. Signing them into the existing workspace instead would be worse: a
mail domain is not proof of belonging, and it would hand a stranger another
tenant's documents. So each signup keeps its own org, and colleagues join by
invitation.

Revision ID: 003_org_domain_not_unique
Revises: 002_schema_drift
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "003_org_domain_not_unique"
down_revision = "002_schema_drift"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orgs DROP CONSTRAINT IF EXISTS uq_orgs_domain")
    op.create_index("ix_orgs_domain", "orgs", ["domain"])


def downgrade() -> None:
    op.drop_index("ix_orgs_domain", table_name="orgs")
    op.create_unique_constraint("uq_orgs_domain", "orgs", ["domain"])
