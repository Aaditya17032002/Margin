"""The bid/no-bid decision, and what was known when it was made.

Margin does not decide. It cannot: the things that settle a bid are whether the
company wants this customer, whether the team is free in March, and what the
principal thinks of the incumbent — none of which is in the document.

What it can do is make the decision *accountable*. Six months after a loss the
question is never "was the machine right"; it is "what did we know when we
decided, and did we look at it". So this assembles the evidence as it stood at
the moment of the decision, freezes it, and records the human answer beside it.

The evidence is deliberately the uncomfortable half. Hard gates that failed.
Requirements nobody owns. Coverage that was incomplete. Contradictions never
resolved. Weight sitting on factors the response does not answer. A decision
record that only carried the reasons to bid would be a marketing document, and
the whole value of one is that it is the thing you read when it went wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.logging import get_logger

logger = get_logger()


@dataclass
class Consideration:
    """One thing that was true when the decision was made."""

    kind: str
    weight: str  # "against" | "for" | "unknown"
    summary: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "weight": self.weight, "summary": self.summary, "detail": self.detail}


@dataclass
class Evidence:
    """Everything the decision could have been made on, frozen."""

    at: str
    considerations: list[Consideration] = field(default_factory=list)
    #: Counts a reader scans before the prose.
    facts: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "at": self.at,
            "facts": self.facts,
            "considerations": [c.as_dict() for c in self.considerations],
            "against": sum(1 for c in self.considerations if c.weight == "against"),
            "unknown": sum(1 for c in self.considerations if c.weight == "unknown"),
        }


def assemble(
    *,
    analysis,
    requirements: list,
    checks: list | None = None,
    contradictions: list | None = None,
    weighting: dict | None = None,
    queue_summary: dict | None = None,
) -> Evidence:
    """What was known, at the moment somebody decided."""
    evidence = Evidence(at=datetime.now(UTC).isoformat())
    open_requirements = [r for r in requirements if r.state == "open"]
    mandatory = [r for r in open_requirements if r.stakes == "disqualifying"]

    # ── Hard gates ───────────────────────────────────────────────────────
    gates = analysis.gates or []
    failed = [g for g in gates if g.get("weight") == "hard" and g.get("met") is False]
    unanswered = [g for g in gates if g.get("weight") == "hard" and g.get("met") is None]
    if failed:
        evidence.considerations.append(
            Consideration(
                "gate", "against",
                f"{len(failed)} hard eligibility gate(s) were not met.",
                "; ".join(str(g.get("question", ""))[:120] for g in failed[:4]),
            )
        )
    if unanswered:
        evidence.considerations.append(
            Consideration(
                "gate", "unknown",
                f"{len(unanswered)} hard gate(s) had no answer when this was decided.",
                "Only your organisation can answer these, and nobody had. "
                + "; ".join(str(g.get("question", ""))[:120] for g in unanswered[:4]),
            )
        )

    # ── What was read ────────────────────────────────────────────────────
    coverage = (analysis.coverage or {}).get("totals") or {}
    if coverage:
        pages, scanned = coverage.get("pages", 0), coverage.get("pagesScanned", 0)
        if coverage.get("emptyDocuments"):
            evidence.considerations.append(
                Consideration(
                    "coverage", "unknown",
                    f"{coverage['emptyDocuments']} document(s) produced no readable text.",
                    "Nothing in them was read, so no requirement they state appears anywhere in "
                    "this analysis.",
                )
            )
        elif pages and scanned < pages:
            evidence.considerations.append(
                Consideration(
                    "coverage", "unknown",
                    f"{pages - scanned} of {pages} pages were not reached by any pass.",
                    "Requirements stated on them are missing from the ledger.",
                )
            )

    # ── Ownership ────────────────────────────────────────────────────────
    unowned = [r for r in mandatory if not r.owner]
    if unowned:
        evidence.considerations.append(
            Consideration(
                "ownership", "against",
                f"{len(unowned)} mandatory requirement(s) had no owner.",
                "; ".join(r.reference for r in unowned[:6]),
            )
        )

    # ── Contradictions ───────────────────────────────────────────────────
    open_conflicts = [c for c in (contradictions or []) if c.state == "open"]
    if open_conflicts:
        evidence.considerations.append(
            Consideration(
                "contradiction", "unknown",
                f"{len(open_conflicts)} requirement pair(s) contradicted each other and were "
                "never resolved.",
                "; ".join(c.summary[:120] for c in open_conflicts[:3]),
            )
        )

    # ── The response, if there is one ────────────────────────────────────
    if checks:
        blocking = [c for c in checks if c.risk == "high" and c.status in ("failed", "not_found")]
        if blocking:
            evidence.considerations.append(
                Consideration(
                    "response", "against",
                    f"{len(blocking)} mandatory requirement(s) were unanswered in the draft.",
                    "These are the gaps a proposal is rejected for.",
                )
            )
        unverifiable = [c for c in checks if c.status == "unverifiable"]
        if unverifiable:
            evidence.considerations.append(
                Consideration(
                    "response", "unknown",
                    f"{len(unverifiable)} check(s) could not be settled automatically.",
                    "Unresolved is not the same as compliant.",
                )
            )

    # ── Where the score is ───────────────────────────────────────────────
    if weighting and weighting.get("weightAtRisk", 0) > 0.25:
        exposed = ", ".join(f["name"] for f in weighting.get("mostExposed", [])[:3])
        evidence.considerations.append(
            Consideration(
                "evaluation", "against",
                f"{round(weighting['weightAtRisk'] * 100)}% of the stated evaluation weight sat "
                "on factors the response did not answer.",
                exposed,
            )
        )

    # ── Anything left for a person ───────────────────────────────────────
    if queue_summary and queue_summary.get("blocking"):
        evidence.considerations.append(
            Consideration(
                "verification", "against",
                f"{queue_summary['blocking']} item(s) in the verification queue could lose the "
                "bid on their own.",
            )
        )

    evidence.facts = {
        "requirements": len(open_requirements),
        "mandatory": len(mandatory),
        "unowned": len(unowned),
        "hardGatesFailed": len(failed),
        "hardGatesUnanswered": len(unanswered),
        "openContradictions": len(open_conflicts),
        "pagesScanned": coverage.get("pagesScanned", 0),
        "pages": coverage.get("pages", 0),
        "estimatedValue": float(analysis.estimated_value or 0),
    }

    logger.info(
        "decision_evidence_assembled",
        analysis_id=analysis.id,
        against=sum(1 for c in evidence.considerations if c.weight == "against"),
        unknown=sum(1 for c in evidence.considerations if c.weight == "unknown"),
    )
    return evidence


def readiness(evidence: Evidence) -> dict:
    """How much of what a decision needs was actually known.

    Not a recommendation. A number that said "72% — bid" would be believed, and
    nothing here knows whether the company wants this customer or has the team
    free in March. What this says is narrower and true: how much was settled,
    and how much was still open when somebody decided anyway.
    """
    against = [c for c in evidence.considerations if c.weight == "against"]
    unknown = [c for c in evidence.considerations if c.weight == "unknown"]
    return {
        "against": len(against),
        "unknown": len(unknown),
        "settled": not unknown,
        "headline": (
            "Everything Margin can check was settled when this was decided."
            if not unknown and not against
            else f"{len(against)} thing(s) argued against it and {len(unknown)} were still "
            "unknown when it was decided."
        ),
    }
