"""run_analysis worker — full pipeline: ingest → agents → verify → persist."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import orjson
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import AgentEvent, EventType
from app.agents.orchestrator import MODE_AGENTS, run_orchestration
from app.core.logging import get_logger
from app.db.base import async_session_factory
from app.db.models.activity import ActivityLog
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.db.models.matrix_row import MatrixRow
from app.db.models.notification import Notification
from app.db.models.question import Question
from app.db.models.user import User
from app.pipeline.ingest import full_pipeline
from app.providers.base import ChunkResult
from app.workers import derive

logger = get_logger()

PLACEHOLDER_TEXT = (
    "No readable text was extracted from this document.\n"
    "The reading pass still ran, but every finding should be treated as unconfirmed."
)


async def _document_text(db: AsyncSession, analysis: Analysis) -> tuple[str, str]:
    """The base document's extracted text, plus the filename to report."""
    result = await db.execute(
        select(Document)
        .where(Document.analysis_id == analysis.id, Document.doc_kind == "base")
        .order_by(Document.version.desc())
    )
    document = result.scalars().first()
    if document and document.raw_text:
        return document.raw_text, document.file_name
    filename = (document.file_name if document else analysis.file_name) or "document.pdf"
    return PLACEHOLDER_TEXT, filename


async def run_analysis_task(ctx: dict, analysis_id: str) -> dict:
    """Arq task: run the full analysis pipeline and persist everything it produced."""
    redis: Redis = ctx.get("redis", ctx.get("job_ctx", {}).get("redis"))
    channel = f"analysis:{analysis_id}:events"

    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if not analysis:
                logger.error("analysis_not_found", analysis_id=analysis_id)
                return {"error": "Analysis not found"}

            logger.info("run_analysis_start", analysis_id=analysis_id, mode=analysis.mode)
            analysis.stage = "analyzing"
            await db.commit()

            # ── Step 1: the document itself ──────────────────────────────
            raw_text, filename = await _document_text(db, analysis)
            layout, _embeddings = await full_pipeline(raw_text.encode("utf-8"), filename)

            chunks = layout.chunks or [
                ChunkResult(text=raw_text[:400], page=1, section_path="Section A")
            ]

            # ── Step 2: the agent roster ─────────────────────────────────
            orchestration = await run_orchestration(
                analysis_id=analysis_id,
                mode=analysis.mode,
                chunks=chunks,
                redis=redis,
            )

            findings = orchestration.get("findings", {})
            roster = MODE_AGENTS.get(analysis.mode, MODE_AGENTS["standard"])

            # ── Step 3: persist ──────────────────────────────────────────
            analysis.identity = findings.get("identity", [])
            analysis.scope = findings.get("scope", [])
            analysis.legal = findings.get("legal", [])
            analysis.eligibility = findings.get("eligibility", [])
            analysis.pricing = findings.get("pricing", [])
            analysis.post_award = findings.get("postAward", [])

            gate_list = derive.gates(analysis.eligibility)
            analysis.gates = gate_list
            analysis.evaluation = derive.evaluation_factors(findings.get("evaluation", []))
            analysis.risks = derive.risk_items(findings.get("risks", []))
            analysis.summary = derive.summary(analysis.title, findings, gate_list)
            analysis.page_count = layout.page_count
            analysis.pages = layout.pages
            analysis.stage = "review"
            analysis.updated_at = datetime.now(UTC)

            version_id = f"{analysis_id}_v{len(analysis.versions or []) + 1}"
            analysis.versions = [
                *(analysis.versions or []),
                {
                    "id": version_id,
                    "label": f"{analysis.mode.replace('-', ' ').title()} pass",
                    "at": datetime.now(UTC).isoformat(),
                    "author": "Margin",
                    "note": analysis.summary,
                },
            ]

            if "compliance" in roster:
                await _write_matrix_rows(db, analysis, derive.matrix_rows(analysis.legal))
            if "qa" in roster:
                await _write_questions(db, analysis, derive.questions(orchestration.get("questions", [])))

            await _announce(db, redis, analysis, gate_list)
            await db.commit()

            await redis.publish(
                channel,
                AgentEvent(
                    EventType.RUN_COMPLETED,
                    "orchestrator",
                    {
                        "analysisId": analysis_id,
                        "findingCount": sum(len(v) for v in findings.values()),
                    },
                ).to_json(),
            )

            logger.info("run_analysis_complete", analysis_id=analysis_id)
            return {"status": "completed", "analysis_id": analysis_id}

    except Exception as e:
        logger.exception("run_analysis_error", analysis_id=analysis_id, error=str(e))
        await _mark_failed(analysis_id)
        await redis.publish(channel, AgentEvent(EventType.RUN_ERROR, "orchestrator", {"error": str(e)}).to_json())
        return {"error": str(e)}


async def _write_matrix_rows(db: AsyncSession, analysis: Analysis, rows: list[dict]) -> None:
    """Replace the rows this pass owns. Rows a person added by hand are kept:
    they carry an owner or a response location the agent never sets."""
    existing = await db.execute(
        select(MatrixRow).where(MatrixRow.analysis_id == analysis.id)
    )
    for row in existing.scalars().all():
        if row.owner is None and not row.response_location and row.status == "unassigned":
            await db.delete(row)

    for row in rows:
        db.add(
            MatrixRow(
                id=f"m_{uuid.uuid4().hex[:8]}",
                analysis_id=analysis.id,
                org_id=analysis.org_id,
                reference=row["reference"][:255],
                requirement=row["requirement"],
                type=row["type"],
                stakes=row["stakes"],
                owner=None,
                response_location="",
                status="unassigned",
                citation=row["citation"],
                note=row["note"],
            )
        )


async def _write_questions(db: AsyncSession, analysis: Analysis, questions: list[dict]) -> None:
    """Same rule as the matrix: an unsent, agent-authored question is replaced,
    anything a person touched stays."""
    existing = await db.execute(select(Question).where(Question.analysis_id == analysis.id))
    kept = 0
    for question in existing.scalars().all():
        if question.sent or question.source_kind == "manual":
            kept += 1
        else:
            await db.delete(question)

    for index, q in enumerate(questions):
        db.add(
            Question(
                id=f"q_{uuid.uuid4().hex[:8]}",
                analysis_id=analysis.id,
                org_id=analysis.org_id,
                text=q["text"],
                rationale=q["rationale"],
                source_kind=q["sourceKind"],
                go_no_go_impact=q["goNoGoImpact"],
                order=kept + index,
                sent=False,
                citation=q["citation"],
            )
        )


async def _announce(db: AsyncSession, redis: Redis, analysis: Analysis, gate_list: list[dict]) -> None:
    """Tell the org the read is done — a notification each, one audit entry."""
    hard_gates = sum(1 for g in gate_list if g.get("weight") == "hard")
    body = f"{analysis.title} has been read."
    if hard_gates:
        body += f" {hard_gates} hard {'gate needs' if hard_gates == 1 else 'gates need'} attention."

    db.add(
        ActivityLog(
            id=f"a_{uuid.uuid4().hex[:8]}",
            org_id=analysis.org_id,
            actor="Margin",
            action="completed the reading of",
            target=analysis.title,
            analysis_id=analysis.id,
        )
    )

    users = await db.execute(select(User).where(User.org_id == analysis.org_id))
    for user in users.scalars().all():
        notification = Notification(
            id=f"n_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            org_id=analysis.org_id,
            kind="review",
            title="Analysis complete",
            body=body,
            read=False,
            analysis_id=analysis.id,
            href=f"/app/analyses/{analysis.id}",
        )
        db.add(notification)
        await redis.publish(
            f"notifications:{user.id}",
            orjson.dumps(
                {
                    "id": notification.id,
                    "at": datetime.now(UTC).isoformat(),
                    "kind": notification.kind,
                    "title": notification.title,
                    "body": notification.body,
                    "read": False,
                    "analysisId": analysis.id,
                    "href": notification.href,
                }
            ).decode(),
        )


async def _mark_failed(analysis_id: str) -> None:
    """A failed run must not leave the board stuck on "analyzing"."""
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if analysis and analysis.stage == "analyzing":
                analysis.stage = "triage"
                analysis.updated_at = datetime.now(UTC)
                await db.commit()
    except Exception:  # noqa: BLE001 — already handling a failure
        logger.exception("run_analysis_rollback_failed", analysis_id=analysis_id)
