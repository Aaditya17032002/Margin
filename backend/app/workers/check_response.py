"""Checking the bound draft response against the solicitation's requirements.

The response is read as its own corpus and compared to the Requirement Ledger
one requirement at a time. Mechanical rules are counted in code; substantive
ones are read by a model that is instructed to say it does not know rather than
to guess. Nothing here clears a mandatory requirement — a `satisfied` result on
one is stored with `needs_confirmation` set, waiting for a person.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import AgentEvent, EventType
from app.core.logging import get_logger
from app.db.base import async_session_factory
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline.corpus import build_corpus
from app.pipeline.traceability import Trace, summarise, trace_response

logger = get_logger()


async def check_response_task(ctx: dict, analysis_id: str) -> dict:
    redis: Redis | None = ctx.get("redis", ctx.get("job_ctx", {}).get("redis"))
    channel = f"analysis:{analysis_id}:events"

    try:
        async with async_session_factory() as db:
            analysis = (
                await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            ).scalar_one_or_none()
            if analysis is None:
                return {"error": "analysis not found"}

            binding = analysis.response or {}
            version = int(binding.get("version") or 1)

            documents = list(
                (
                    await db.execute(
                        select(Document).where(
                            Document.analysis_id == analysis_id, Document.doc_kind == "response"
                        )
                    )
                )
                .scalars()
                .all()
            )
            current = [d for d in documents if d.version == version] or documents
            if not current:
                return {"error": "no response bound to this analysis"}

            response = build_corpus(current, include_response=True)
            requirements = list(
                (
                    await db.execute(
                        select(Requirement).where(
                            Requirement.analysis_id == analysis_id, Requirement.state == "open"
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not requirements:
                return {"error": "this solicitation has no requirements to check against"}

            traces = await trace_response(
                requirements,
                response,
                file_names=[d.file_name for d in current],
                llm=_llm(),
            )
            await _persist(db, analysis, traces, version=version, document_id=current[0].id)

            summary = summarise(traces)
            analysis.response = {
                **binding,
                "version": version,
                "at": datetime.now(UTC).isoformat(),
                "summary": summary,
            }
            analysis.updated_at = datetime.now(UTC)
            await db.commit()

            if redis is not None:
                await redis.publish(
                    channel,
                    AgentEvent(
                        EventType.RUN_COMPLETED,
                        "traceability",
                        {"analysisId": analysis_id, "response": summary},
                    ).to_json(),
                )
            logger.info("response_check_complete", analysis_id=analysis_id, **summary["counts"])
            return {"status": "completed", "analysis_id": analysis_id, "summary": summary}

    except Exception as exc:  # noqa: BLE001
        logger.exception("response_check_error", analysis_id=analysis_id, error=str(exc))
        return {"error": str(exc)}


def _llm():
    """The model layer, or nothing.

    A missing provider is not an error here: every substantive check then comes
    back `unverifiable` with the reason attached, which is a worse result than
    a real check and a much better one than a guess.
    """
    try:
        from app.providers.factory import get_llm_provider

        return get_llm_provider()
    except Exception as exc:  # noqa: BLE001
        logger.warning("response_check_no_llm", error=str(exc))
        return None


async def _persist(
    db: AsyncSession,
    analysis: Analysis,
    traces: list[Trace],
    *,
    version: int,
    document_id: str,
) -> None:
    """Write this version's verdicts, keeping what a person has already said.

    A check a human confirmed or overruled is never overwritten by a re-run
    against the same draft: their decision is the most reliable thing in the
    table, and losing it to a background job would teach everyone to stop
    making decisions in the product.
    """
    existing = {
        row.requirement_id: row
        for row in (
            await db.execute(
                select(ResponseCheck).where(
                    ResponseCheck.analysis_id == analysis.id,
                    ResponseCheck.response_version == version,
                )
            )
        )
        .scalars()
        .all()
    }
    now = datetime.now(UTC)

    for trace in traces:
        row = existing.get(trace.requirement_id)
        if row is not None and row.decided_by == "human":
            continue
        if row is None:
            row = ResponseCheck(
                id=f"chk_{uuid.uuid4().hex[:12]}",
                analysis_id=analysis.id,
                org_id=analysis.org_id,
                requirement_id=trace.requirement_id,
                response_version=version,
                response_document_id=document_id,
                history=[],
            )
            db.add(row)

        previous = row.status
        row.status = trace.status
        row.verification = trace.verification
        row.decided_by = trace.decided_by
        row.rule = trace.rule
        row.detail = trace.detail
        row.gap = trace.gap
        row.risk = trace.risk
        row.owner = trace.owner
        row.evidence = trace.evidence or {}
        row.needs_confirmation = trace.needs_confirmation
        if previous and previous != trace.status:
            row.history = [
                *(row.history or []),
                {
                    "at": now.isoformat(),
                    "event": "rechecked",
                    "detail": f"{previous} → {trace.status}.",
                },
            ]

    await db.flush()
