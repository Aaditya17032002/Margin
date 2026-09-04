"""Agent orchestrator — runs the agent roster based on analysis mode.

Selects which specialists run, coordinates them, streams events to Redis pub/sub,
and merges results into the analysis.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

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
    #
    # What comes back is not a finding about the solicitation — it is what the
    # open web says about the rules the solicitation sits inside. It is kept in
    # its own record, with every source that produced it, so the workspace can
    # show a reader where each claim came from and never present a web page as
    # a clause in their document.
    research: dict = {"status": "not_requested", "detail": "", "query": "", "summary": "", "sources": []}
    if mode == "deep-research":
        try:
            research_provider = get_research_provider()
            generic_query = _generic_research_query(all_findings)
            logger.info("deep_research_query", query=generic_query)
            result = await research_provider.research(generic_query)
            sources = _dedupe_sources(result.sources)
            research = {
                "status": result.status,
                "detail": result.detail,
                "query": result.query_used,
                "summary": "\n\n".join(str(f.get("summary") or "") for f in result.findings).strip(),
                "sources": sources,
                "claims": _attributed_claims(result.claims, sources),
                "at": datetime.now(UTC).isoformat(),
            }
            await redis.publish(channel, AgentEvent(
                EventType.REASONING_TICK,
                "research",
                {
                    "text": (
                        f"Read {len(research['sources'])} sources on the open web."
                        if result.status == "completed"
                        else _research_note(result.status, result.detail)
                    )
                },
            ).to_json())
        except Exception as exc:  # noqa: BLE001 — research is additive, never fatal
            logger.exception("deep_research_failed")
            research = {**research, "status": "failed", "detail": str(exc)[:300]}

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
        "research": research,
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


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    """One entry per URL, carrying the host so a reader can judge it at a glance.

    Whose site a claim came from is most of what makes it worth trusting —
    acquisition.gov and a consultancy blog are not the same evidence.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for source in sources:
        url = str(source.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(
            {
                "url": url,
                "title": str(source.get("title") or url)[:300],
                "site": urlparse(url).netloc.removeprefix("www."),
            }
        )
    return out[:40]


def _attributed_claims(claims: list[dict], sources: list[dict]) -> list[dict]:
    """Keep each paragraph with the sources that actually survived into the list.

    A claim pointing at a URL the panel does not show is worse than an
    unattributed one: the reader sees a citation marker and cannot follow it.
    """
    kept = {source["url"] for source in sources}
    out: list[dict] = []
    for claim in claims:
        text = str(claim.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "sources": [url for url in (claim.get("sources") or []) if url in kept],
            }
        )
    return out


def _research_note(status: str, detail: str) -> str:
    note = RESEARCH_NOTES.get(status, RESEARCH_NOTES["failed"])
    return f"{note} ({detail})" if detail else note
