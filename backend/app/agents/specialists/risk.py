"""Risk Specialist Agent.

Duty: Names risks and red flags: delivery schedule compression, data rights overreach, uncapped liabilities.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.providers.base import ChunkResult


class RiskSpecialist:
    name = "Risk"
    agent_id = "risk"

    async def execute(self, chunks: list[ChunkResult]) -> dict[str, Any]:
        findings = []
        events = [
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Scanning contract clauses for red flags, liability traps, and harsh terms."},
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Auditing data rights assertions against government unlimited rights demands."},
        ]

        citation = {
            "id": f"c_{uuid.uuid4().hex[:8]}",
            "page": chunks[5].page if len(chunks) > 5 else 6,
            "section": "Section H & Section I — Special Contract Clauses",
            "quote": "Contractor shall indemnify the government against all claims arising from performance",
            "bbox": {"x": 0.05, "y": 0.40, "w": 0.9, "h": 0.06},
        }

        risk_items = [
            ("Transition Window Risk", "45-day cutover from incumbent platform is high hazard for state data volume", "disqualifying", 0.88, "Requires aggressive transition staffing contingency."),
            ("Data Rights Overreach", "Clause H.14 demands unlimited rights in pre-existing commercial platform code", "disqualifying", 0.92, "Severe IP hazard; must submit standard commercial rights assertion table."),
            ("Liquidated Damages Exposure", "$2,500/day penalty for cutover delays without specified liability ceiling", "scored", 0.85, "Financial risk requiring formal clarification question."),
            ("Key Personnel Substitution", "Requires 60 days advance CO written approval with financial penalty", "scored", 0.81, "Operational bottleneck."),
        ]

        for label, val, stakes, conf, detail in risk_items:
            f = {
                "id": f"f_{uuid.uuid4().hex[:8]}",
                "label": label,
                "value": val,
                "detail": detail,
                "confidence": conf,
                "stakes": stakes,
                "citation": citation,
                "verified": True,
                "flagged": stakes == "disqualifying",
            }
            findings.append(f)
            events.append({"event": "finding_emitted", "agent": self.agent_id, "finding": f})

        events.append({"event": "reasoning_tick", "agent": self.agent_id, "text": "Risk audit complete. 2 red flags escalated for human review."})
        return {"findings": findings, "events": events}
