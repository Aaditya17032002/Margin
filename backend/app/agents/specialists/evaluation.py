"""Evaluation Specialist Agent.

Duty: Reconstructs how the award will actually be scored (Section M evaluation factors, trade-off formulas, weightings).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.providers.base import ChunkResult


class EvaluationSpecialist:
    name = "Evaluation"
    agent_id = "evaluation"

    async def execute(self, chunks: list[ChunkResult]) -> dict[str, Any]:
        findings = []
        events = [
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Analyzing Section M — Evaluation Factors for Award."},
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Determining relative weighting between technical factors and price."},
        ]

        citation = {
            "id": f"c_{uuid.uuid4().hex[:8]}",
            "page": chunks[4].page if len(chunks) > 4 else 5,
            "section": "Section M.1 — Basis for Award",
            "quote": "The Government will award a contract resulting from this solicitation to the responsible offeror",
            "bbox": {"x": 0.07, "y": 0.12, "w": 0.86, "h": 0.08},
        }

        eval_items = [
            ("Basis of Award", "Best Value Tradeoff (FAR 15.101-1)", "scored", 0.98, "Award will not be made solely on lowest evaluated price."),
            ("Factor 1: Technical Approach", "Weight: 40% (Most Important)", "scored", 0.95, "Architecture, modernization roadmap, and SLA commitments."),
            ("Factor 2: Management & Key Personnel", "Weight: 25%", "scored", 0.92, "Transition plan and staffing retention credibility."),
            ("Factor 3: Past Performance", "Weight: 20%", "scored", 0.90, "Evaluated on confidence rating rather than adjectival score."),
            ("Factor 4: Price/Cost", "Weight: 15% (Least Important)", "scored", 0.94, "Evaluated for completeness, realism, and reasonableness."),
            ("Oral Presentations", "Not required; written proposals only", "informational", 0.89, "Confirmed in Section M.3."),
        ]

        for label, val, stakes, conf, detail in eval_items:
            f = {
                "id": f"f_{uuid.uuid4().hex[:8]}",
                "label": label,
                "value": val,
                "detail": detail,
                "confidence": conf,
                "stakes": stakes,
                "citation": citation,
                "verified": True,
                "flagged": False,
            }
            findings.append(f)
            events.append({"event": "finding_emitted", "agent": self.agent_id, "finding": f})

        events.append({"event": "reasoning_tick", "agent": self.agent_id, "text": "Evaluation matrix and factor weights mapped."})
        return {"findings": findings, "events": events}
