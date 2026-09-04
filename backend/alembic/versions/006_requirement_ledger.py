"""The Requirement Ledger replaces the compliance matrix table.

`matrix_rows` had no identity: every run deleted the agent-authored rows and
inserted new ones with new ids, so an assignment made between runs pointed at a
row that no longer existed, and a requirement an amendment removed was
indistinguishable from one the parser missed.

`requirements` carries a content-derived `key` instead, which is stable across
re-reads, plus the lifecycle state a run must never destroy. Existing rows are
migrated across rather than dropped — the work recorded against them (owner,
status, response location, notes) is the part that matters.

Revision ID: 006_requirement_ledger
Revises: 005_corpus_coverage
"""

from __future__ import annotations

import hashlib
import json
import re

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "006_requirement_ledger"
down_revision = "005_corpus_coverage"
branch_labels = None
depends_on = None

_NON_WORD = re.compile(r"[^a-z0-9]+")
# The same damage-repair the anchor does before comparing text: smart quotes,
# ligatures, soft hyphens, non-breaking spaces. Written out rather than
# imported — a migration that called into application code would silently
# change meaning the next time that code changed, and these keys have to match
# what the application computes *today*. A test asserts the two agree.
_TRANSLATE = str.maketrans(
    {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00ad": "",
        "\u00a0": " ", "\ufb01": "fi", "\ufb02": "fl",
    }
)


def _key(text: str) -> str:
    body = _NON_WORD.sub(" ", (text or "").translate(_TRANSLATE).lower()).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:20]


def upgrade() -> None:
    op.create_table(
        "requirements",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("reference", sa.String(255), nullable=False, server_default="Unreferenced"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="obligation"),
        sa.Column("type", sa.String(16), nullable=False, server_default="shall"),
        sa.Column("stakes", sa.String(20), nullable=False, server_default="scored"),
        sa.Column("verification", sa.String(16), nullable=False, server_default="substantive"),
        sa.Column("citation", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("document_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources", ARRAY(sa.String(16)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("state", sa.String(16), nullable=False, server_default="open"),
        sa.Column("supersedes_id", sa.String(64), nullable=True),
        sa.Column("superseded_by_id", sa.String(64), nullable=True),
        sa.Column("introduced_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_run", sa.String(64), nullable=False, server_default=""),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("response_location", sa.String(255), nullable=True, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="unassigned"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("history", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_requirements_analysis_id", "requirements", ["analysis_id"])
    op.create_index("ix_requirements_org_id", "requirements", ["org_id"])
    op.create_index("ix_requirements_analysis_state", "requirements", ["analysis_id", "state"])
    op.create_index("uq_requirements_analysis_key", "requirements", ["analysis_id", "key"], unique=True)

    _migrate_existing_rows()

    op.drop_table("matrix_rows")


def _migrate_existing_rows() -> None:
    """Carry the old rows over, keeping the first of any duplicates.

    Duplicates are expected: the old table had no identity, so re-running an
    analysis left several rows saying the same thing. The one kept is the one
    with work recorded against it, because that is the row a person will look
    for.
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, analysis_id, org_id, reference, requirement, type, stakes,
                   owner, response_location, status, citation, note, created_at
            FROM matrix_rows
            ORDER BY created_at ASC
            """
        )
    ).mappings().all()

    seen: set[tuple[str, str]] = set()
    keep: list[dict] = []
    for row in rows:
        key = _key(row["requirement"])
        identity = (row["analysis_id"], key)
        worked = bool(row["owner"] or row["response_location"] or row["status"] != "unassigned")
        if identity in seen:
            if not worked:
                continue
            # A worked row displaces the untouched one already kept.
            keep = [k for k in keep if (k["analysis_id"], k["key"]) != identity]
        seen.add(identity)
        keep.append(
            {
                "id": row["id"],
                "analysis_id": row["analysis_id"],
                "org_id": row["org_id"],
                "key": key,
                "reference": row["reference"] or "Unreferenced",
                "text": row["requirement"],
                "type": row["type"] or "shall",
                "stakes": row["stakes"] or "scored",
                # Bound as text and cast: the driver has no adapter for a dict.
                "citation": json.dumps(row["citation"] or {}),
                "owner": row["owner"],
                "response_location": row["response_location"] or "",
                "status": row["status"] or "unassigned",
                "note": row["note"],
                "created_at": row["created_at"],
            }
        )

    for row in keep:
        bind.execute(
            sa.text(
                """
                INSERT INTO requirements (
                    id, created_at, updated_at, analysis_id, org_id, key, reference, text,
                    kind, type, stakes, verification, citation, document_id, page, sources,
                    state, introduced_by, first_seen_at, last_seen_at, last_seen_run,
                    owner, response_location, status, note, history
                ) VALUES (
                    :id, :created_at, :created_at, :analysis_id, :org_id, :key, :reference, :text,
                    'obligation', :type, :stakes, 'substantive', CAST(:citation AS jsonb), '', 0, ARRAY['model']::varchar[],
                    'open', '', :created_at, :created_at, 'migrated',
                    :owner, :response_location, :status, :note,
                    '[{"event": "migrated", "detail": "Carried over from the compliance matrix table."}]'::jsonb
                )
                """
            ),
            row,
        )

    op.add_column("analyses", sa.Column("ledger", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade() -> None:
    op.drop_column("analyses", "ledger")
    op.create_table(
        "matrix_rows",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_id", sa.String(64), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(64), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("reference", sa.String(255), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("type", sa.String(16), nullable=False, server_default="shall"),
        sa.Column("stakes", sa.String(20), nullable=False, server_default="scored"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("response_location", sa.String(255), nullable=True, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="unassigned"),
        sa.Column("citation", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_matrix_rows_analysis_id", "matrix_rows", ["analysis_id"])
    op.create_index("ix_matrix_rows_org_id", "matrix_rows", ["org_id"])
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO matrix_rows (id, created_at, updated_at, analysis_id, org_id, reference,
                                     requirement, type, stakes, owner, response_location, status, citation, note)
            SELECT id, created_at, updated_at, analysis_id, org_id, reference,
                   text, type, stakes, owner, response_location, status, citation, note
            FROM requirements WHERE state <> 'removed'
            """
        )
    )
    op.drop_table("requirements")
