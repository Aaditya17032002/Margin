"""Turn agent output into the shapes the workspace reads.

Specialists all speak the same Finding dialect. The workspace does not: an
evaluation factor carries a weight, a risk carries a severity, an eligibility
gate is a question with an answer. This module is the one place that
translation lives, so the API contract and the agents can move independently.
"""

from __future__ import annotations

import re
import uuid

SEVERITY_BY_STAKES = {
    "disqualifying": "critical",
    "scored": "elevated",
    "informational": "moderate",
}

WEIGHT_PATTERN = re.compile(r"(\d{1,3})\s*%")


def evaluation_factors(findings: list[dict]) -> list[dict]:
    """Section M factors, with the percentage lifted out of the stated weight."""
    factors = []
    for f in findings:
        match = WEIGHT_PATTERN.search(f.get("value", ""))
        factors.append(
            {
                "id": f.get("id") or f"ef_{uuid.uuid4().hex[:8]}",
                "name": f.get("label", ""),
                "weight": int(match.group(1)) if match else 0,
                "method": f.get("detail") or f.get("value", ""),
                "citation": f.get("citation", {}),
            }
        )
    return factors


def risk_items(findings: list[dict]) -> list[dict]:
    """Risks keep the agent's wording; severity follows the stakes it assigned."""
    return [
        {
            "id": f.get("id") or f"r_{uuid.uuid4().hex[:8]}",
            "title": f.get("label", ""),
            "narrative": f.get("value", ""),
            "severity": SEVERITY_BY_STAKES.get(f.get("stakes", "scored"), "moderate"),
            # Likelihood is not something the reading pass can honestly assert,
            # so every risk arrives as "possible" for a human to sharpen.
            "likelihood": "possible",
            "mitigation": f.get("detail", ""),
            "citation": f.get("citation", {}),
        }
        for f in findings
    ]


def gates(findings: list[dict]) -> list[dict]:
    """Eligibility gates. `met` stays null: whether the bidder clears a gate is a
    fact about the company, not about the document, so a person answers it."""
    return [
        {
            "id": f"g_{uuid.uuid4().hex[:8]}",
            "question": f.get("label", ""),
            "answer": f.get("value", ""),
            "met": None,
            "citation": f.get("citation", {}),
            "weight": "hard" if f.get("stakes") == "disqualifying" else "soft",
        }
        for f in findings
    ]


def questions(findings: list[dict]) -> list[dict]:
    """The Q&A agent already emits question-shaped records; normalise the keys."""
    normalised = []
    for index, q in enumerate(findings):
        normalised.append(
            {
                "text": q.get("text") or q.get("value", ""),
                "rationale": q.get("rationale") or q.get("detail", ""),
                "sourceKind": q.get("sourceKind", "manual"),
                "goNoGoImpact": bool(q.get("goNoGoImpact")),
                "order": q.get("order", index),
                "citation": q.get("citation"),
            }
        )
    return normalised


# The sections the workspace counts as findings. Evaluation factors and risks
# live in the same result but are shown separately, so a summary that counted
# them would disagree with the number on the analysis header.
FINDING_SECTIONS = ("identity", "scope", "legal", "eligibility", "pricing", "postAward")


def summary(analysis_title: str, findings: dict[str, list[dict]], gate_list: list[dict]) -> str:
    """A plain sentence about what the read produced — no invented conclusions."""
    sections = [findings.get(name, []) for name in FINDING_SECTIONS]
    total = sum(len(section) for section in sections)
    hard = sum(1 for g in gate_list if g.get("weight") == "hard")
    disqualifying = sum(
        1 for section in sections for f in section if f.get("stakes") == "disqualifying"
    )
    parts = [f"{total} findings extracted from {analysis_title}, each resolved to a cited clause."]
    if hard:
        parts.append(f"{hard} hard eligibility gates need a human answer.")
    if disqualifying:
        parts.append(f"{disqualifying} findings carry disqualifying stakes.")
    return " ".join(parts)
