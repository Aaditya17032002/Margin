"""Agent orchestrator — runs the agent roster based on analysis mode.

Selects which specialists run, coordinates them, streams events to Redis pub/sub,
and merges results into the analysis.
"""

from __future__ import annotations

import asyncio
from typing import Any

from redis.asyncio import Redis

from app.agents.events import AgentEvent, EventType
from app.core.logging import get_logger
from app.pipeline.anchor import CitationAnchor
from app.providers.base import AgentProvider, ChunkResult
from app.providers.factory import get_agent_provider, get_research_provider

logger = get_logger()

# Mode → agent roster mapping (from §8.8)
# `dates` runs in every mode. A team decides whether to bid *because* they can
# see the calendar, so the calendar cannot be something only a full read
# produces — a quick triage on the afternoon a document lands needs it most.
MODE_AGENTS: dict[str, list[str]] = {
    "quick-triage": ["intake", "dates", "eligibility", "verifier"],
    "standard": ["intake", "dates", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
    "deep-research": ["intake", "dates", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
    "matrix-only": ["intake", "dates", "compliance", "verifier"],
    "qa-only": ["intake", "dates", "scope", "qa", "verifier"],
    "amendment-refresh": ["intake", "dates", "compliance", "evaluation", "verifier"],
    "recompete-compare": ["intake", "dates", "scope", "compliance", "evaluation", "risk", "verifier"],
}

# Agent → finding section mapping
AGENT_SECTIONS: dict[str, str] = {
    "intake": "identity",
    "scope": "scope",
    "compliance": "legal",
    "eligibility": "eligibility",
    "evaluation": "evaluation",
    "risk": "risks",
    "qa": "questions",
}


def _generic_research_query(findings: dict[str, list[dict]]) -> str:
    """Build a Bing-safe query from extracted identity — never raw document text."""
    identity = findings.get("identity") or []
    bits: dict[str, str] = {}
    for item in identity:
        label = str(item.get("label") or "").lower()
        value = str(item.get("value") or "").strip()
        if not value or value.upper() == "SILENT":
            continue
        if "agency" in label or "issuing" in label:
            bits["agency"] = value[:120]
        elif "naics" in label:
            bits["naics"] = value.split("—")[0].split("-")[0].strip()[:20]
        elif "document type" in label:
            bits["type"] = value[:80]
    agency = bits.get("agency", "U.S. government")
    dtype = bits.get("type", "government solicitation")
    query = (
        f"Current public procurement rules, evaluation practices, and compliance "
        f"requirements relevant to a {dtype} issued by {agency}"
    )
    if bits.get("naics"):
        query += f" (NAICS {bits['naics']})"
    query += ". Concise report with sources. Do not include unpublished solicitation text."
    return query


async def run_orchestration(
    *,
    analysis_id: str,
    mode: str,
    chunks: list[ChunkResult],
    redis: Redis,
    pages: list[dict] | None = None,
    agent_provider: AgentProvider | None = None,
) -> dict[str, Any]:
    """Run the full agent roster for an analysis, streaming events."""

    if agent_provider is None:
        agent_provider = get_agent_provider()

    # Built once and shared by every specialist: resolving a quote is a search
    # over the whole document, and indexing it per agent would be wasteful.
    anchor = CitationAnchor(pages) if pages else None

    channel = f"analysis:{analysis_id}:events"
    roster = MODE_AGENTS.get(mode, MODE_AGENTS["standard"])

    all_findings: dict[str, list[dict]] = {
        "identity": [], "scope": [], "legal": [], "eligibility": [],
        "pricing": [], "postAward": [], "evaluation": [], "risks": [],
    }
    all_events: list[dict] = []
    gates: list[dict] = []
    silent_items: list[dict] = []
    questions: list[dict] = []

    # Run specialists (except verifier and qa)
    specialists = [a for a in roster if a not in ("verifier", "qa", "dates")]
    for agent_id in specialists:
        # Publish agent started
        event = AgentEvent(EventType.AGENT_STARTED, agent_id)
        await redis.publish(channel, event.to_json())

        # Run the specialist
        result = await agent_provider.run_specialist(agent_id, {}, chunks, anchor=anchor)

        # Map findings to the right section
        section = AGENT_SECTIONS.get(agent_id, "identity")
        if section in all_findings:
            all_findings[section].extend(result.findings)

        # Stream individual events
        for evt in result.events:
            await redis.publish(channel, AgentEvent(
                EventType(evt.get("event", "reasoning_tick")),
                agent_id,
                evt,
            ).to_json())

        # Publish agent completed
        event = AgentEvent(EventType.AGENT_COMPLETED, agent_id)
        await redis.publish(channel, event.to_json())

        # Brief pause to let the frontend process events
        await asyncio.sleep(0.1)

    # ── Key dates ────────────────────────────────────────────────────────
    key_dates: list[dict] = []
    if "dates" in roster:
        await redis.publish(channel, AgentEvent(EventType.AGENT_STARTED, "dates").to_json())
        try:
            dates_result = await agent_provider.run_specialist("dates", {}, chunks, anchor=anchor)
            key_dates = dates_result.findings
        except Exception:  # noqa: BLE001 — a missing calendar must not fail the read
            logger.exception("dates_agent_failed")
        await redis.publish(channel, AgentEvent(EventType.AGENT_COMPLETED, "dates").to_json())

    # ── External research (only for deep-research mode) ──────────────────
    research_status = {"status": "not_requested", "detail": ""}
    if mode == "deep-research":
        try:
            research_provider = get_research_provider()
            generic_query = _generic_research_query(all_findings)
            logger.info("deep_research_query", query=generic_query)
            research_result = await research_provider.research(generic_query)
            research_status = {
                "status": research_result.status,
                "detail": research_result.detail,
            }
            for f in research_result.findings:
                all_findings["legal"].append({
                    "id": f.get("id") or f"dr_{len(all_findings['legal'])}",
                    "label": f.get("title", "External research"),
                    "value": f.get("summary", ""),
                    "confidence": 0.7,
                    "stakes": "informational",
                    "citation": {
                        "id": f"c_{f.get('id') or len(all_findings['legal'])}",
                        "page": 0,
                        "section": "External research",
                        # An external finding is not in the solicitation, so it
                        # is never "located" — the source is the URL, and the
                        # workspace shows it as research rather than a clause.
                        "quote": (research_result.sources[0]["url"] if research_result.sources else ""),
                        "bbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0},
                        "lines": None,
                        "located": False,
                        "matchScore": 0.0,
                    },
                    "verified": None,
                    "flagged": False,
                })
            if research_result.status != "completed":
                # A deep-research run that produced no research must say so on
                # the analysis, not only in the worker log.
                await redis.publish(channel, AgentEvent(
                    EventType.REASONING_TICK,
                    "research",
                    {"text": _research_note(research_result.status, research_result.detail)},
                ).to_json())
        except Exception as exc:  # noqa: BLE001 — research is additive, never fatal
            logger.exception("deep_research_failed")
            research_status = {"status": "failed", "detail": str(exc)[:300]}

    # ── Verifier pass ────────────────────────────────────────────────────
    if "verifier" in roster:
        event = AgentEvent(EventType.AGENT_STARTED, "verifier")
        await redis.publish(channel, event.to_json())

        all_flat_findings = []
        for section_findings in all_findings.values():
            all_flat_findings.extend(section_findings)

        verified_findings = await agent_provider.verify(all_flat_findings, chunks)

        # Re-distribute verified findings back to sections
        verified_by_id = {f["id"]: f for f in verified_findings}
        for section in all_findings:
            all_findings[section] = [
                verified_by_id.get(f["id"], f) for f in all_findings[section]
            ]

        await redis.publish(channel, AgentEvent(EventType.VERIFICATION, "verifier", {
            "total": len(verified_findings),
            "downgraded": sum(1 for f in verified_findings if f.get("flagged")),
        }).to_json())

        await redis.publish(channel, AgentEvent(EventType.AGENT_COMPLETED, "verifier").to_json())

    # ── Q&A agent ────────────────────────────────────────────────────────
    if "qa" in roster:
        event = AgentEvent(EventType.AGENT_STARTED, "qa")
        await redis.publish(channel, event.to_json())

        qa_result = await agent_provider.run_specialist("qa", {}, chunks, anchor=anchor)
        questions = qa_result.findings

        await redis.publish(channel, AgentEvent(EventType.AGENT_COMPLETED, "qa").to_json())

    # `run_completed` is deliberately not published here. The caller persists
    # what this returned, and a listener that reloaded on the orchestrator's own
    # signal would race that write and read the analysis back unchanged.

    return {
        "findings": all_findings,
        "gates": gates,
        "silent": silent_items,
        "questions": questions,
        "dates": key_dates,
        "research": research_status,
    }


RESEARCH_NOTES = {
    "rate_limited": (
        "External research was skipped: the deep-research deployment is at its "
        "rate limit. Everything below still comes from the document itself."
    ),
    "timeout": (
        "External research did not return in time. Everything below still comes "
        "from the document itself."
    ),
    "skipped": "External research is not configured for this workspace.",
    "failed": "External research could not be completed.",
}


def _research_note(status: str, detail: str) -> str:
    note = RESEARCH_NOTES.get(status, RESEARCH_NOTES["failed"])
    return f"{note} ({detail})" if detail else note
