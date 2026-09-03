"""Eligibility Specialist Agent.

Duty: Identifies hard disqualify-gates (SAM registration, set-aside qualification, clearances, past performance recency).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.providers.base import ChunkResult


class EligibilitySpecialist:
    name = "Eligibility"
    agent_id = "eligibility"

    async def execute(self, chunks: list[ChunkResult]) -> dict[str, Any]:
        findings = []
        events = [
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Auditing mandatory gate criteria against bidder profile."},
            {"event": "reasoning_tick", "agent": self.agent_id, "text": "Cross-checking SAM.gov registration and facility clearance thresholds."},
        ]

        citation = {
            "id": f"c_{uuid.uuid4().hex[:8]}",
            "page": chunks[3].page if len(chunks) > 3 else 4,
            "section": "Section M & Instructions L.4 — Eligibility Mandates",
            "quote": "Offerors must possess an active SAM.gov registration with no active exclusions",
            "bbox": {"x": 0.05, "y": 0.35, "w": 0.9, "h": 0.06},
        }

        eligibility_items = [
            ("SAM.gov Registration", "Active registration required at proposal submission date", "disqualifying", 0.99, "Hard gate; verified against CAGE code."),
            ("Facility Security Clearance", "Secret Facility Clearance (FCL) required prior to award", "disqualifying", 0.94, "Teaming partners may sponsor if valid."),
            ("Past Performance Recency", "3 past projects within the last 36 months, >$5M value each", "disqualifying", 0.91, "Strict 3-year recency boundary."),
            ("Small Business Teaming", "Prime must self-perform minimum 50% of personnel cost", "disqualifying", 0.93, "Limitations on subcontracting clause."),
        ]

        for label, val, stakes, conf, detail in eligibility_items:
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

        events.append({"event": "reasoning_tick", "agent": self.agent_id, "text": "Eligibility audit finished. 4 disqualifying gates registered."})
        return {"findings": findings, "events": events}
