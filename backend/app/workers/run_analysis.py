"""run_analysis worker — full pipeline: ingest → agents → verify → persist."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import orjson
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import AgentEvent, EventType
from app.agents.orchestrator import MODE_AGENTS, run_orchestration
from app.core.logging import get_logger
from app.db.base import async_session_factory
from app.db.models.activity import ActivityLog
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.db.models.matrix_row import MatrixRow
from app.db.models.doc_chunk import DocChunk
from app.db.models.notification import Notification
from app.db.models.question import Question
from app.db.models.user import User
from app.pipeline.corpus import Corpus, build_corpus
from app.pipeline.coverage import CoverageLedger, summarise as coverage_summary
from app.pipeline.ingest import embed_chunks
from app.pipeline.sweep import sweep_chunks
from app.providers.base import ChunkResult
from app.workers import derive
from app.workers.schedule import build_schedule

logger = get_logger()

RESEARCH_NOTES = {
    "rate_limited": "External research was unavailable on this pass — the deep-research deployment was rate limited. Every finding above comes from the document itself.",
    "timeout": "External research did not return in time on this pass. Every finding above comes from the document itself.",
    "skipped": "External research is not configured for this workspace.",
    "failed": "External research could not be completed on this pass.",
}


def _research_note(research: dict) -> str:
    status = str(research.get("status") or "")
    if status in ("completed", "not_requested", ""):
        return ""
    return RESEARCH_NOTES.get(status, RESEARCH_NOTES["failed"])


PLACEHOLDER_TEXT = (
    "No readable text was extracted from this document.\n"
    "The reading pass still ran, but every finding should be treated as unconfirmed."
)


async def _package(db: AsyncSession, analysis: Analysis) -> Corpus:
    """Every document in the pursuit, not just the base one.

    The previous version filtered to ``doc_kind == "base"``, so a package of a
    base RFP and twelve attachments was read as one document and the other
    twelve were stored and ignored.
    """
    result = await db.execute(
        select(Document)
        .where(Document.analysis_id == analysis.id)
        .order_by(Document.created_at.asc())
    )
    documents = list(result.scalars().all())
    corpus = build_corpus(documents)

    if not corpus.chunks:
        # Nothing readable anywhere. The run still happens — the reader is told
        # plainly rather than shown an empty analysis with no explanation.
        placeholder = SimpleNamespace(
            id="",
            file_name=(analysis.file_name or "document.pdf"),
            doc_kind="base",
            version=1,
            raw_text=PLACEHOLDER_TEXT,
        )
        corpus = build_corpus([placeholder])
    return corpus


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

            # ── Step 1: the whole package ────────────────────────────────
            corpus = await _package(db, analysis)
            embeddings = await embed_chunks(
                [ChunkResult(text=c.text, page=c.page, section_path=c.section_path) for c in corpus.chunks]
            )
            await _persist_chunks(db, analysis, corpus, embeddings)

            # ── Step 2: the deterministic sweep ──────────────────────────
            # Before any model runs, and over every chunk. This is what makes
            # coverage a fact rather than an estimate.
            sweep_result = sweep_chunks(corpus.chunks)
            ledger = CoverageLedger(corpus=corpus)
            ledger.record_scanned(sweep_result.visited)

            # ── Step 3: the agent roster ─────────────────────────────────
            orchestration = await run_orchestration(
                analysis_id=analysis_id,
                mode=analysis.mode,
                corpus=corpus,
                embeddings=embeddings,
                sweep=sweep_result,
                ledger=ledger,
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
            # The calendar is built on every run, whatever the bid decision:
            # a team decides *because* they can see the dates.
            # The ledger closes here: every pass that could record what it read
            # has run by now.
            coverage = ledger.build()
            analysis.coverage = coverage

            analysis.dates = build_schedule(orchestration.get("dates") or [])
            analysis.summary = derive.summary(analysis.title, findings, gate_list)

            # A deep-research pass that could not reach the research service is
            # still a valid read of the document, but the analysis must not
            # imply research happened. The note travels on the summary and the
            # version entry, which is where a reviewer looks weeks later.
            research = orchestration.get("research") or {}
            analysis.research = research
            research_note = _research_note(research)
            if research_note:
                analysis.summary = f"{analysis.summary} {research_note}"
            # Coverage leads the summary: what was read is the precondition for
            # trusting anything that follows it.
            analysis.summary = f"{coverage_summary(coverage)} {analysis.summary}".strip()
            analysis.page_count = corpus.page_count
            analysis.pages = corpus.pages_for_anchor()
            analysis.sweep = {
                "at": coverage["at"],
                "counts": sweep_result.by_kind(),
                "total": len(sweep_result.hits),
            }
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


async def _persist_chunks(
    db: AsyncSession, analysis: Analysis, corpus: Corpus, embeddings: list[list[float]]
) -> None:
    """Store the corpus so later passes do not have to re-read the package.

    Embeddings were previously computed on every run and discarded — the
    variable was assigned and never used, while `doc_chunks`, the pgvector
    column and the retriever all sat written and uncalled.
    """
    await db.execute(delete(DocChunk).where(DocChunk.analysis_id == analysis.id))
    for index, chunk in enumerate(corpus.chunks):
        if not chunk.document_id:
            continue  # the placeholder corpus has no document behind it
        db.add(
            DocChunk(
                id=f"dc_{uuid.uuid4().hex[:12]}",
                document_id=chunk.document_id,
                analysis_id=analysis.id,
                org_id=analysis.org_id,
                text=chunk.text,
                page=chunk.page,
                section_path=chunk.section_path[:500],
                bbox=chunk.bbox,
                chunk_index=chunk.chunk_index,
                embedding=embeddings[index] if index < len(embeddings) else None,
            )
        )
    await db.flush()
    logger.info("chunks_persisted", analysis_id=analysis.id, chunks=len(corpus.chunks))


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
