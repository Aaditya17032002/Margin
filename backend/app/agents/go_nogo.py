"""Go/No-Go Synthesizer Agent.

Duty: Synthesizes hard eligibility gates, risk items, and evaluation factors into a grounded Bid / No-Bid recommendation.
"""

from __future__ import annotations

from typing import Any


class GoNoGoSynthesizer:
    """Synthesizes gate pass/fail status and risk findings into a Go/No-Go proposal verdict."""

    @staticmethod
    def synthesize(
        findings_by_section: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        disqualifying_findings = []
        high_risks = []

        for section_name, findings in findings_by_section.items():
            for f in findings:
                if f.get("stakes") == "disqualifying":
                    # Check if flag or low confidence or unmet
                    if f.get("flagged") or f.get("confidence", 1.0) < 0.85:
                        disqualifying_findings.append(f)
                if section_name == "risks" or f.get("stakes") == "disqualifying":
                    if "risk" in f.get("label", "").lower() or "overreach" in f.get("label", "").lower():
                        high_risks.append(f)

        # Decision heuristics
        if len(disqualifying_findings) >= 2:
            decision = "no-bid"
            justification = (
                f"No-Bid recommended: {len(disqualifying_findings)} critical disqualifying issues "
                f"identified, including {disqualifying_findings[0].get('label')}."
            )
            confidence = 0.92
        elif len(disqualifying_findings) == 1 or len(high_risks) >= 2:
            decision = "watch"
            justification = (
                f"Watch list: 1 disqualifying item requires executive legal review "
                f"({disqualifying_findings[0].get('label') if disqualifying_findings else 'high risk items'})."
            )
            confidence = 0.84
        else:
            decision = "bid"
            justification = "Bid recommended: All mandatory eligibility gates passed; risk exposure manageable."
            confidence = 0.95

        return {
            "decision": decision,
            "justification": justification,
            "confidence": confidence,
            "disqualifying_count": len(disqualifying_findings),
            "high_risk_count": len(high_risks),
        }
