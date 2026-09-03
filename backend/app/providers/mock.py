"""Mock provider — deterministic canned results for dev, demos, and CI.

Runs the full agentic workflow offline without Azure keys.
Findings match the frontend seed data shapes.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from app.providers.base import (
    AgentProvider,
    AgentResult,
    ChunkResult,
    DocIntelProvider,
    EmbeddingResult,
    LLMProvider,
    LayoutResult,
    ResearchProvider,
    ResearchResult,
    RetrievalResult,
    SearchProvider,
)


class MockDocIntelProvider(DocIntelProvider):
    """Returns a simple text extraction without real layout analysis."""

    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        text = content.decode("utf-8", errors="replace") if content else "Mock document content."
        lines = text.split("\n")
        page_size = max(1, len(lines) // 10)  # ~10 pages

        pages = []
        chunks = []
        for i in range(0, len(lines), page_size):
            page_num = (i // page_size) + 1
            page_lines = lines[i : i + page_size]
            pages.append({
                "page": page_num,
                "heading": page_lines[0][:80] if page_lines else None,
                "lines": page_lines,
            })
            for j, line in enumerate(page_lines):
                if line.strip():
                    chunks.append(ChunkResult(
                        text=line.strip(),
                        page=page_num,
                        section_path=f"Section {page_num}",
                        bbox={"x": 0.05, "y": round(0.05 + (j * 0.08), 2), "w": 0.9, "h": 0.06},
                        chunk_index=len(chunks),
                    ))

        return LayoutResult(
            pages=pages,
            chunks=chunks,
            page_count=len(pages),
            raw_text=text,
        )


class MockLLMProvider(LLMProvider):
    """Returns deterministic responses and hash-based embeddings."""

    async def complete(self, messages: list[dict], *, model: str | None = None, **kwargs: Any) -> str:
        # Return the last user message as a mock "analysis"
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return f"Mock analysis of: {msg['content'][:200]}"
        return "Mock LLM response."

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Deterministic embeddings via SHA-256 hash → 1536-dim vector."""
        results = []
        for text in texts:
            h = hashlib.sha256(text.encode()).hexdigest()
            # Convert hex to floats, repeating to fill 1536 dimensions
            base = [int(h[i : i + 2], 16) / 255.0 for i in range(0, len(h), 2)]
            vec = (base * (1536 // len(base) + 1))[:1536]
            results.append(vec)
        return results


class MockAgentProvider(AgentProvider):
    """Returns canned findings that match the frontend's expected shape."""

    async def run_specialist(
        self, agent_id: str, schema_slice: dict, chunks: list[ChunkResult], **kwargs: Any
    ) -> AgentResult:
        try:
            from app.agents.specialists.intake import IntakeSpecialist
            from app.agents.specialists.scope import ScopeSpecialist
            from app.agents.specialists.compliance import ComplianceSpecialist
            from app.agents.specialists.eligibility import EligibilitySpecialist
            from app.agents.specialists.evaluation import EvaluationSpecialist
            from app.agents.specialists.risk import RiskSpecialist
            from app.agents.specialists.pricing_post_award import PricingPostAwardSpecialist
            from app.agents.specialists.qa_strategy import QAStrategySpecialist

            specialist_map = {
                "intake": IntakeSpecialist(),
                "scope": ScopeSpecialist(),
                "compliance": ComplianceSpecialist(),
                "eligibility": EligibilitySpecialist(),
                "evaluation": EvaluationSpecialist(),
                "risk": RiskSpecialist(),
                "pricing": PricingPostAwardSpecialist(),
                "qa": QAStrategySpecialist(),
            }
            if agent_id in specialist_map:
                res = await specialist_map[agent_id].execute(chunks)
                return AgentResult(findings=res["findings"], events=res["events"])
        except Exception:
            pass

        findings = []
        events = []
        events.append({"event": "agent_started", "agent": agent_id})
        mock_findings = _get_mock_findings(agent_id, chunks)
        for f in mock_findings:
            findings.append(f)
            events.append({"event": "finding_emitted", "agent": agent_id, "finding": f})
            events.append({"event": "reasoning_tick", "agent": agent_id, "text": f"Analysed: {f['label']}"})
        events.append({"event": "agent_completed", "agent": agent_id})
        return AgentResult(findings=findings, events=events)

    async def verify(self, findings: list[dict], chunks: list[ChunkResult]) -> list[dict]:
        """Runs the CitationVerifier re-reading each finding against its cited span."""
        try:
            from app.agents.verifier import CitationVerifier
            return await CitationVerifier().verify_findings(findings, chunks)
        except Exception:
            verified = []
            for f in findings:
                f_copy = dict(f)
                if f_copy.get("confidence", 0) < 0.4:
                    f_copy["verified"] = False
                    f_copy["flagged"] = True
                else:
                    f_copy["verified"] = True
                verified.append(f_copy)
            return verified


class MockSearchProvider(SearchProvider):
    """Returns mock retrieval results."""

    async def search(self, query: str, analysis_id: str, top_k: int = 10) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                text=f"Mock relevant passage for: {query[:50]}",
                page=1,
                section_path="Section C.1",
                bbox={"x": 0.05, "y": 0.15, "w": 0.9, "h": 0.06},
                score=0.95,
            ),
        ]


class MockResearchProvider(ResearchProvider):
    """Returns canned research results without making any external calls."""

    async def research(self, query: str) -> ResearchResult:
        return ResearchResult(
            findings=[
                {
                    "title": f"Research finding for: {query[:50]}",
                    "summary": "Mock research finding from external sources.",
                    "source": "mock",
                }
            ],
            sources=[{"url": "https://example.com/mock", "title": "Mock Source"}],
            query_used=query,
        )


def _get_mock_findings(agent_id: str, chunks: list[ChunkResult]) -> list[dict]:
    """Generate mock findings appropriate for each specialist agent."""
    base_citation = {
        "id": f"c_{uuid.uuid4().hex[:8]}",
        "page": chunks[0].page if chunks else 1,
        "section": chunks[0].section_path if chunks else "Section A",
        "quote": chunks[0].text[:60] if chunks else "Mock citation text",
        "bbox": chunks[0].bbox or {"x": 0.05, "y": 0.15, "w": 0.9, "h": 0.06},
    }

    templates = {
        "intake": [
            {"label": "Document Type", "value": "Request for Proposal", "stakes": "informational", "confidence": 0.98},
            {"label": "Solicitation Number", "value": "MOCK-2026-001", "stakes": "informational", "confidence": 0.99},
        ],
        "scope": [
            {"label": "Period of Performance", "value": "Base year plus four option years", "stakes": "scored", "confidence": 0.92},
            {"label": "Primary Deliverable", "value": "Platform deployment and support services", "stakes": "scored", "confidence": 0.88},
        ],
        "compliance": [
            {"label": "Page Limit", "value": "40 pages excluding resumes", "stakes": "disqualifying", "confidence": 0.95},
            {"label": "Submission Format", "value": "Separate technical and price volumes", "stakes": "disqualifying", "confidence": 0.97},
        ],
        "eligibility": [
            {"label": "Small Business Set-Aside", "value": "Full and Open Competition", "stakes": "disqualifying", "confidence": 0.94},
            {"label": "SAM Registration", "value": "Required at time of award", "stakes": "disqualifying", "confidence": 0.99},
        ],
        "evaluation": [
            {"label": "Evaluation Method", "value": "Best Value Tradeoff", "stakes": "scored", "confidence": 0.96},
            {"label": "Technical Weight", "value": "Significantly more important than price", "stakes": "scored", "confidence": 0.91},
        ],
        "risk": [
            {"label": "Transition Risk", "value": "30-day transition window is tight for enterprise deployment", "stakes": "scored", "confidence": 0.85},
            {"label": "Data Rights", "value": "Government seeks unlimited rights to deliverables", "stakes": "scored", "confidence": 0.78},
        ],
    }

    findings_template = templates.get(agent_id, [])
    findings = []
    for t in findings_template:
        findings.append({
            "id": f"f_{uuid.uuid4().hex[:8]}",
            "label": t["label"],
            "value": t["value"],
            "detail": None,
            "confidence": t["confidence"],
            "stakes": t["stakes"],
            "citation": base_citation,
            "verified": None,
            "flagged": False,
        })
    return findings
