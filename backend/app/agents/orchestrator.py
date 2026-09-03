"""Agent orchestrator — runs the agent roster based on analysis mode.

Selects which specialists run, coordinates them, streams events to Redis pub/sub,
and merges results into the analysis.
"""

from __future__ import annotations

import asyncio
from typing import Any

from redis.asyncio import Redis

from app.agents.events import AgentEvent, EventType
from app.providers.base import AgentProvider, ChunkResult
from app.providers.factory import get_agent_provider, get_research_provider

# Mode → agent roster mapping (from §8.8)
MODE_AGENTS: dict[str, list[str]] = {
    "quick-triage": ["intake", "eligibility", "verifier"],
    "standard": ["intake", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
    "deep-research": ["intake", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
    "matrix-only": ["intake", "compliance", "verifier"],
    "qa-only": ["intake", "scope", "qa", "verifier"],
    "amendment-refresh": ["intake", "compliance", "evaluation", "verifier"],
    "recompete-compare": ["intake", "scope", "compliance", "evaluation", "risk", "verifier"],
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


async def run_orchestration(
    *,
    analysis_id: str,
    mode: str,
    chunks: list[ChunkResult],
    redis: Redis,
    agent_provider: AgentProvider | None = None,
) -> dict[str, Any]:
    """Run the full agent roster for an analysis, streaming events."""

    if agent_provider is None:
        agent_provider = get_agent_provider()

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
    specialists = [a for a in roster if a not in ("verifier", "qa")]
    for agent_id in specialists:
        # Publish agent started
        event = AgentEvent(EventType.AGENT_STARTED, agent_id)
        await redis.publish(channel, event.to_json())

        # Run the specialist
        result = await agent_provider.run_specialist(agent_id, {}, chunks)

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

    # ── External research (only for deep-research mode) ──────────────────
    if mode == "deep-research":
        try:
            research_provider = get_research_provider()
            # Generate a generic query (never raw document text!)
            generic_query = "federal procurement compliance requirements 2026"
            research_result = await research_provider.research(generic_query)
            # Merge research findings into legal section
            for f in research_result.findings:
                all_findings["legal"].append({
                    "id": f.get("id", ""),
                    "label": f.get("title", ""),
                    "value": f.get("summary", ""),
                    "confidence": 0.7,
                    "stakes": "informational",
                    "citation": {"id": "", "page": 0, "section": "External", "quote": "", "bbox": {}},
                })
        except Exception:
            pass  # Research is best-effort

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

        qa_result = await agent_provider.run_specialist("qa", {}, chunks)
        questions = qa_result.findings

        await redis.publish(channel, AgentEvent(EventType.AGENT_COMPLETED, "qa").to_json())

    # ── Run completed ────────────────────────────────────────────────────
    await redis.publish(channel, AgentEvent(EventType.RUN_COMPLETED, "orchestrator", {
        "findingCount": sum(len(v) for v in all_findings.values()),
    }).to_json())

    return {
        "findings": all_findings,
        "gates": gates,
        "silent": silent_items,
        "questions": questions,
    }
