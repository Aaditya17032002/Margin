"""run_analysis worker — full pipeline: ingest → agents → verify → emit."""

from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import AgentEvent, EventType
from app.agents.orchestrator import run_orchestration
from app.core.logging import get_logger
from app.db.base import async_session_factory
from app.db.models.analysis import Analysis
from app.pipeline.ingest import full_pipeline
from app.providers.base import ChunkResult

logger = get_logger()


async def run_analysis_task(ctx: dict, analysis_id: str) -> dict:
    """Arq task: run the full analysis pipeline."""
    redis: Redis = ctx.get("redis", ctx.get("job_ctx", {}).get("redis"))
    channel = f"analysis:{analysis_id}:events"

    try:
        async with async_session_factory() as db:
            # Fetch analysis
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if not analysis:
                logger.error("analysis_not_found", analysis_id=analysis_id)
                return {"error": "Analysis not found"}

            logger.info("run_analysis_start", analysis_id=analysis_id, mode=analysis.mode)

            # Step 1: Document pipeline (mock: use empty content for now)
            # In production, this would read the uploaded document from storage
            mock_content = b"Mock document content for analysis.\nSection A: Identity\nSection B: Scope\n"
            layout, embeddings = await full_pipeline(mock_content, analysis.file_name or "document.pdf")

            # Step 2: Run agent orchestration
            chunks = layout.chunks if layout.chunks else [
                ChunkResult(text="Mock chunk", page=1, section_path="Section A")
            ]

            orchestration_result = await run_orchestration(
                analysis_id=analysis_id,
                mode=analysis.mode,
                chunks=chunks,
                redis=redis,
            )

            # Step 3: Write results back to the analysis
            findings = orchestration_result.get("findings", {})
            analysis.identity = findings.get("identity", [])
            analysis.scope = findings.get("scope", [])
            analysis.legal = findings.get("legal", [])
            analysis.eligibility = findings.get("eligibility", [])
            analysis.pricing = findings.get("pricing", [])
            analysis.post_award = findings.get("postAward", [])
            analysis.stage = "review"
            analysis.updated_at = datetime.now(UTC)
            analysis.page_count = layout.page_count
            analysis.pages = layout.pages

            await db.commit()

            logger.info("run_analysis_complete", analysis_id=analysis_id)
            return {"status": "completed", "analysis_id": analysis_id}

    except Exception as e:
        logger.exception("run_analysis_error", analysis_id=analysis_id, error=str(e))
        await redis.publish(channel, AgentEvent(EventType.RUN_ERROR, "orchestrator", {"error": str(e)}).to_json())
        return {"error": str(e)}
