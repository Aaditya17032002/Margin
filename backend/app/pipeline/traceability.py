"""Checking a response against the solicitation, requirement by requirement.

This is not "upload a document and check it". A response is bound to a
solicitation Margin has already read, and every row of the result names one
requirement from that solicitation's ledger, where in the response it is
answered, and what is missing. The output is a trace:

    solicitation clause / page → response section / page → status → evidence
    → gap → risk → owner

Two rules decide how each row is produced, and they are not negotiable.

**Mechanical rules are never judged by a model.** Page counts, fonts, margins,
file names, forms, signatures and volume structure go to
`app.pipeline.mechanical`, which is a set of rules you can read. A model that
miscounts pages produces a confident, wrong, green tick — the most expensive
output this product could generate.

**Substantive rules are judged by a model, biased toward not knowing.** The
model is asked whether the response addresses the requirement, and the rubric
pushes every ambiguous case to `unverifiable`. "We could not tell" sends a
person to look; "satisfied" does not. Given that asymmetry, the only safe
default is doubt.

On top of both: a mandatory requirement is never *cleared* by this engine. A
`satisfied` result on a disqualifying requirement is a recommendation awaiting
a human signature, and the schema keeps the two apart.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.pipeline import mechanical
from app.pipeline.anchor import normalize
from app.pipeline.corpus import Corpus
from app.pipeline.retrieval import CorpusRetriever

logger = get_logger()

SATISFIED = "satisfied"
PARTIAL = "partial"
FAILED = "failed"
NOT_FOUND = "not_found"
UNVERIFIABLE = "unverifiable"

MECHANICAL = "mechanical"
SUBSTANTIVE = "substantive"

#: Below this, the best passage the response offers has nothing to do with the
#: requirement, and there is nothing for a model to read. Saying `not_found` is
#: both cheaper and more useful than asking a model to confirm an absence.
RELEVANCE_FLOOR = 0.02

#: How much of the response one requirement is judged against. Small on
#: purpose: a model given twenty passages will find something that sounds like
#: an answer in one of them.
EVIDENCE_PASSAGES = 4

_RISK = {
    # (stakes, status) → risk. A disqualifying requirement with no answer is
    # the only combination that can end a bid on its own.
    ("disqualifying", NOT_FOUND): "high",
    ("disqualifying", FAILED): "high",
    ("disqualifying", PARTIAL): "high",
    ("disqualifying", UNVERIFIABLE): "medium",
    ("disqualifying", SATISFIED): "low",
    ("scored", NOT_FOUND): "medium",
    ("scored", FAILED): "medium",
    ("scored", PARTIAL): "medium",
    ("scored", UNVERIFIABLE): "low",
    ("scored", SATISFIED): "low",
}


@dataclass
class Trace:
    """One requirement, traced into the response."""

    requirement_id: str
    requirement_key: str
    reference: str
    requirement: str
    stakes: str
    verification: str
    status: str
    #: "rule" when a mechanical rule decided it, "model" when a specialist did,
    #: "human" once a person has confirmed. Never omitted: a reader has to know
    #: what kind of thing made the claim.
    decided_by: str
    detail: str
    gap: str = ""
    risk: str = "low"
    owner: str | None = None
    rule: str = ""
    evidence: dict | None = None
    #: A `satisfied` result on a mandatory requirement is a recommendation, not
    #: a clearance, until a person signs it — however it was decided.
    needs_confirmation: bool = False
    history: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "requirementKey": self.requirement_key,
            "reference": self.reference,
            "requirement": self.requirement,
            "stakes": self.stakes,
            "verification": self.verification,
            "status": self.status,
            "decidedBy": self.decided_by,
            "detail": self.detail,
            "gap": self.gap,
            "risk": self.risk,
            "owner": self.owner,
            "rule": self.rule,
            "evidence": self.evidence,
            "needsConfirmation": self.needs_confirmation,
        }


async def trace_response(
    requirements: list,
    response: Corpus,
    *,
    file_names: list[str] | None = None,
    llm=None,
) -> list[Trace]:
    """Every open requirement, checked against the response."""
    retriever = CorpusRetriever(response)
    traces: list[Trace] = []

    for requirement in requirements:
        if requirement.state != "open":
            continue
        rule = mechanical.check(requirement.text, response, file_names=file_names)
        if rule is not None:
            traces.append(_from_rule(requirement, rule))
            continue
        traces.append(await _from_model(requirement, retriever, llm))

    counts: dict[str, int] = {}
    for trace in traces:
        counts[trace.status] = counts.get(trace.status, 0) + 1
    logger.info("response_traced", requirements=len(traces), **{f"status_{k}": v for k, v in counts.items()})
    return traces


# ── Mechanical ───────────────────────────────────────────────────────────


def _from_rule(requirement, result: mechanical.Check) -> Trace:
    status = {
        mechanical.SATISFIED: SATISFIED,
        mechanical.FAILED: FAILED,
        mechanical.NOT_FOUND: NOT_FOUND,
        mechanical.UNVERIFIABLE: UNVERIFIABLE,
    }[result.status]
    gap = ""
    if status == FAILED:
        gap = f"Required {result.expected}; the response has {result.actual or 'no answer'}."
    elif status == NOT_FOUND:
        gap = f"Nothing in the response addresses {result.expected or 'this requirement'}."
    elif status == UNVERIFIABLE:
        gap = "Not checkable from what was supplied — confirm before submission."

    return Trace(
        requirement_id=requirement.id,
        requirement_key=requirement.key,
        reference=requirement.reference,
        requirement=requirement.text,
        stakes=requirement.stakes,
        verification=MECHANICAL,
        status=status,
        decided_by="rule",
        detail=result.detail,
        gap=gap,
        risk=_risk(requirement.stakes, status),
        owner=requirement.owner,
        rule=result.rule,
        evidence=result.evidence,
        # Even a counted rule does not clear a mandatory requirement on its
        # own. The count is strong evidence and the signature is cheap; a
        # disqualifying requirement going out marked satisfied because a
        # regular expression said so is not a trade worth making. The trace
        # still shows *how* it was decided, so a reviewer signing off a page
        # count is doing something quicker than signing off an opinion.
        needs_confirmation=status == SATISFIED and requirement.stakes == "disqualifying",
    )


# ── Substantive ──────────────────────────────────────────────────────────

_RUBRIC = """You are checking one requirement from a government solicitation against a draft response.

Requirement ({reference}): {requirement}

Passages from the response that most resemble it:
{passages}

Answer with JSON only: {{"status": "...", "detail": "...", "gap": "...", "quote": "..."}}

status must be exactly one of:
  "satisfied"    — a passage plainly and completely answers the requirement.
  "partial"      — a passage addresses it but leaves part of it unanswered.
  "failed"       — a passage addresses it and states something that does not
                   meet it: a smaller number than required, a narrower
                   commitment, or the very thing the requirement forbids.
  "not_found"    — no passage addresses it.
  "unverifiable" — you cannot tell from these passages.

Rules you must follow:
- Prefer "unverifiable" whenever you are unsure. A wrong "satisfied" causes a
  compliant-looking response to go out with a gap in it; a wrong
  "unverifiable" costs a person five minutes.
- "failed" is not a stronger "not_found". Use it only when the response says
  something specific that conflicts with the requirement — "Secret" where the
  requirement says "Top Secret", business hours where it says 24x7, storage
  abroad where it forbids it. A contradiction is a rewrite; an absence is a
  blank page, and they are different work.
- Never infer that a requirement is met because it would be reasonable, normal
  or implied. Only what the passages actually say counts.
- "quote" must be copied verbatim from a passage, or left empty. Do not
  paraphrase it, and do not write a quote for "not_found".
- "gap" states what is missing, in one sentence, or is empty when nothing is.
"""


async def _from_model(requirement, retriever: CorpusRetriever, llm) -> Trace:
    hits = await retriever.search(requirement.text, top_k=EVIDENCE_PASSAGES)
    relevant = [hit for hit in hits if hit.score >= RELEVANCE_FLOOR]

    if not relevant:
        return _trace(
            requirement,
            status=NOT_FOUND,
            decided_by="rule",
            detail="No passage in the response resembles this requirement.",
            gap="The response does not appear to address this at all.",
        )

    if llm is None:
        return _trace(
            requirement,
            status=UNVERIFIABLE,
            decided_by="rule",
            detail="Passages that may address this were found, but no model was available to read them.",
            gap="Needs a person to read the passages below.",
            evidence=_evidence(relevant[0]),
        )

    passages = "\n\n".join(
        f"[{index + 1}] {hit.chunk.document_name} p.{hit.chunk.page}"
        f"{' — ' + hit.chunk.section_path if hit.chunk.section_path else ''}\n{hit.chunk.text}"
        for index, hit in enumerate(relevant)
    )
    prompt = _RUBRIC.format(
        reference=requirement.reference, requirement=requirement.text, passages=passages
    )

    try:
        raw = await llm.complete([{"role": "user", "content": prompt}])
        answer = _parse(raw)
    except Exception as exc:  # noqa: BLE001 — a failed check is unverifiable, never satisfied
        logger.warning("response_check_failed", requirement=requirement.key, error=str(exc))
        answer = None

    if answer is None:
        return _trace(
            requirement,
            status=UNVERIFIABLE,
            decided_by="model",
            detail="The check did not return a usable answer, so the requirement is unresolved.",
            gap="Needs a person to read the passages below.",
            evidence=_evidence(relevant[0]),
        )

    status = answer.get("status", UNVERIFIABLE)
    if status not in (SATISFIED, PARTIAL, FAILED, NOT_FOUND, UNVERIFIABLE):
        # Anything outside the rubric is not a verdict. Coercing to
        # `unverifiable` rather than guessing keeps a malformed answer from
        # becoming a clearance.
        status = UNVERIFIABLE

    # A quote the model produced that is not in the response is a fabrication,
    # and the claim resting on it cannot stand. This is the same grounding rule
    # citations are held to.
    evidence = _grounded(answer.get("quote", ""), relevant) or _evidence(relevant[0])
    if status == SATISFIED and evidence and not evidence.get("located"):
        status = UNVERIFIABLE
        answer["detail"] = (
            "Reported as satisfied, but the passage it cited could not be found in the "
            "response. Downgraded rather than trusted. "
        ) + str(answer.get("detail", ""))

    return _trace(
        requirement,
        status=status,
        decided_by="model",
        detail=str(answer.get("detail", "")).strip(),
        gap=str(answer.get("gap", "")).strip(),
        evidence=evidence,
    )


def _parse(raw: str) -> dict | None:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _grounded(quote: str, hits: list) -> dict | None:
    """Locate the model's quote in the response, or mark that it is not there."""
    if not quote or not quote.strip():
        return None
    needle = normalize(quote)
    for hit in hits:
        if needle and needle in normalize(hit.chunk.text):
            return {
                "documentId": hit.chunk.document_id,
                "documentName": hit.chunk.document_name,
                "page": hit.chunk.page,
                "section": hit.chunk.section_path,
                "quote": quote,
                "located": True,
            }
    return {
        "documentId": hits[0].chunk.document_id if hits else "",
        "documentName": hits[0].chunk.document_name if hits else "",
        "page": hits[0].chunk.page if hits else 0,
        "section": hits[0].chunk.section_path if hits else "",
        "quote": quote,
        "located": False,
    }


def _evidence(hit) -> dict:
    return {
        "documentId": hit.chunk.document_id,
        "documentName": hit.chunk.document_name,
        "page": hit.chunk.page,
        "section": hit.chunk.section_path,
        "quote": hit.chunk.text[:400],
        "located": True,
    }


def _trace(requirement, *, status: str, decided_by: str, detail: str, gap: str = "", evidence=None) -> Trace:
    return Trace(
        requirement_id=requirement.id,
        requirement_key=requirement.key,
        reference=requirement.reference,
        requirement=requirement.text,
        stakes=requirement.stakes,
        verification=SUBSTANTIVE,
        status=status,
        decided_by=decided_by,
        detail=detail,
        gap=gap,
        risk=_risk(requirement.stakes, status),
        owner=requirement.owner,
        evidence=evidence,
        # The rule the whole engine turns on: a model saying a mandatory
        # requirement is met is a recommendation, and stays one until signed.
        needs_confirmation=status == SATISFIED and requirement.stakes == "disqualifying",
    )


def _risk(stakes: str, status: str) -> str:
    if stakes == "informational":
        return "low"
    return _RISK.get((stakes, status), "medium")


def summarise(traces: list[Trace]) -> dict:
    """The counts a proposal manager reads first.

    `cleared` deliberately excludes anything awaiting a signature: the number
    of requirements that are actually settled is smaller than the number a
    model called satisfied, and conflating them is how a response ships with a
    gap in it.
    """
    counts: dict[str, int] = {}
    for trace in traces:
        counts[trace.status] = counts.get(trace.status, 0) + 1
    awaiting = [t for t in traces if t.needs_confirmation]
    blocking = [t for t in traces if t.risk == "high"]
    return {
        "total": len(traces),
        "counts": counts,
        "cleared": counts.get(SATISFIED, 0) - len(awaiting),
        "awaitingConfirmation": len(awaiting),
        "blocking": len(blocking),
        "blockingReferences": [t.reference for t in blocking][:20],
    }
