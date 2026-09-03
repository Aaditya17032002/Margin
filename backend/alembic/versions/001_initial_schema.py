"""Initial database schema migration creating all core tables and pgvector.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-03 12:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Orgs
    op.create_table(
        "orgs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False, unique=True),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="Trial"),
        sa.Column("seats", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("seats_used", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duns", sa.String(length=20), nullable=True),
        sa.Column("cage", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="writer"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("avatar_tone", sa.String(length=20), nullable=True, server_default="patina"),
        sa.Column("signature", sa.String(length=500), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True, server_default="America/Chicago"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_org_id", "users", ["org_id"])

    # 4. Analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("solicitation_number", sa.String(length=100), nullable=False, server_default="Pending assignment"),
        sa.Column("agency", sa.String(length=255), nullable=False),
        sa.Column("sub_agency", sa.String(length=255), nullable=True),
        sa.Column("doc_type", sa.String(length=50), nullable=False, server_default="RFP"),
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="standard"),
        sa.Column("stage", sa.String(length=50), nullable=False, server_default="triage"),
        sa.Column("go_no_go", sa.String(length=50), nullable=False, server_default="undecided"),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("spec_version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("collaborators", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("naics", sa.String(length=20), nullable=True, server_default="Not yet determined"),
        sa.Column("set_aside", sa.String(length=100), nullable=True, server_default="Not yet determined"),
        sa.Column("place_of_performance", sa.String(length=255), nullable=True, server_default="Not yet determined"),
        sa.Column("estimated_value", sa.Float(), nullable=True, server_default="0"),
        sa.Column("page_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("file_name", sa.String(length=500), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True, server_default="0"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="upload"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=True, server_default=""),
        sa.Column("identity", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scope", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("legal", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("eligibility", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pricing", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("post_award", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("gates", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("evaluation", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("risks", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("silent", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("dates", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("clins", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("amendments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("versions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analyses_org_id", "analyses", ["org_id"])

    # 5. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("storage_path", sa.String(length=1000), nullable=True),
        sa.Column("doc_kind", sa.String(length=50), nullable=False, server_default="base"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supersedes", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_analysis_id", "documents", ["analysis_id"])

    # 6. Doc Chunks with vector(1536)
    # asyncpg prepares every statement, and a prepared statement holds exactly
    # one command — so each of these is issued on its own.
    op.execute(
        """
        CREATE TABLE doc_chunks (
            id VARCHAR(36) PRIMARY KEY,
            document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            analysis_id VARCHAR(36) NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
            text TEXT NOT NULL,
            page INTEGER NOT NULL,
            section_path VARCHAR(500),
            bbox JSONB,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            embedding vector(1536),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX ix_doc_chunks_analysis_id ON doc_chunks(analysis_id)")
    op.execute("CREATE INDEX ix_doc_chunks_document_id ON doc_chunks(document_id)")

    # 7. Matrix Rows
    op.create_table(
        "matrix_rows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="shall"),
        sa.Column("stakes", sa.String(length=50), nullable=False, server_default="scored"),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("response_location", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="unassigned"),
        sa.Column("citation", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_matrix_rows_analysis_id", "matrix_rows", ["analysis_id"])

    # 8. Questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("go_no_go_impact", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("citation", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_questions_analysis_id", "questions", ["analysis_id"])

    # 9. Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id"), nullable=True),
        sa.Column("href", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # 10. Team Members
    op.create_table(
        "team_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_active", sa.String(length=50), nullable=True),
        sa.Column("initials_color", sa.String(length=20), nullable=True, server_default="patina"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_team_members_org_id", "team_members", ["org_id"])

    # 11. Integrations
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("blurb", sa.Text(), nullable=True),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("account", sa.String(length=320), nullable=True),
        sa.Column("connected_at", sa.String(length=50), nullable=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tree", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("token_ref", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_integrations_org_id", "integrations", ["org_id"])

    # 12. Templates
    op.create_table(
        "templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="report"),
        sa.Column("description", sa.Text(), nullable=True, server_default=""),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("format", sa.String(length=50), nullable=False, server_default="DOCX"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_templates_org_id", "templates", ["org_id"])

    # 13. Knowledge Items (Past Bids)
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("agency", sa.String(length=255), nullable=False),
        sa.Column("submitted_at", sa.String(length=50), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("value", sa.Float(), nullable=True, server_default="0"),
        sa.Column("debrief", sa.Text(), nullable=True, server_default=""),
        sa.Column("lessons", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("incumbent", sa.String(length=255), nullable=True),
        sa.Column("score_gap", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_items_org_id", "knowledge_items", ["org_id"])

    # 14. Reports
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_title", sa.String(length=500), nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False, server_default="DOCX"),
        sa.Column("size", sa.BigInteger(), nullable=True, server_default="0"),
        sa.Column("destination", sa.String(length=50), nullable=False, server_default="download"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="generating"),
        sa.Column("storage_path", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reports_org_id", "reports", ["org_id"])

    # 15. Activity Log
    op.create_table(
        "activity_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.String(length=500), nullable=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_log_org_id", "activity_log", ["org_id"])

    # 16. Preferences
    op.create_table(
        "preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("preferences")
    op.drop_table("activity_log")
    op.drop_table("reports")
    op.drop_table("knowledge_items")
    op.drop_table("templates")
    op.drop_table("integrations")
    op.drop_table("team_members")
    op.drop_table("notifications")
    op.drop_table("questions")
    op.drop_table("matrix_rows")
    op.drop_table("doc_chunks")
    op.drop_table("documents")
    op.drop_table("analyses")
    op.drop_table("users")
    op.drop_table("orgs")
    op.execute("DROP EXTENSION IF EXISTS vector")
