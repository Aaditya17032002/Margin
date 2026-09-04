"""A question's life after it is sent, and a date against a requirement.

`questions.sent` was a boolean, so a question that had been answered looked
exactly like one still waiting — and the answer, which is the entire point of
asking, had nowhere to live. The lifecycle columns give it one, and
`requirement_id` connects an answer back to the clause it was about so work
done against the old reading can be reopened.

`requirements.due_at` is the team's internal date, not the solicitation's.
That is the date that actually governs whether the work happens.

Revision ID: 008_qa_lifecycle
Revises: 007_response_traceability
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "008_qa_lifecycle"
down_revision = "007_response_traceability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("status", sa.String(16), nullable=False, server_default="draft"))
    op.add_column("questions", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("questions", sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("questions", sa.Column("answer", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("answer_source", sa.String(255), nullable=False, server_default=""))
    op.add_column("questions", sa.Column("requirement_id", sa.String(64), nullable=True))
    op.add_column(
        "questions", sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"))
    )
    # Existing rows: a sent question is submitted and awaiting an answer.
    op.execute("UPDATE questions SET status = 'submitted' WHERE sent IS TRUE")

    op.add_column("requirements", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_requirements_owner", "requirements", ["org_id", "owner"])


def downgrade() -> None:
    op.drop_index("ix_requirements_owner", table_name="requirements")
    op.drop_column("requirements", "due_at")
    for column in ("history", "requirement_id", "answer_source", "answer", "answered_at", "submitted_at", "status"):
        op.drop_column("questions", column)
