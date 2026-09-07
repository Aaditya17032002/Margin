"""Response Match Analysis report.

When a draft response is bound and checked against the solicitation ledger,
this pack is the downloadable record of that match: summary counts, gaps that
could lose the bid, every requirement-by-requirement finding with evidence,
and who signed what.

It is assembled from stored ``ResponseCheck`` rows — nothing is re-inferred at
export time — so printing twice produces the same document.
"""

from __future__ import annotations

from datetime import datetime

# Block kinds: ("heading", level, text) | ("para", text) | ("note", text)
#              | ("table", [headers], [[cells]])
Block = tuple

_STATUS_WORDS = {
    "satisfied": "Answered",
    "partial": "Partly answered",
    "failed": "Does not comply",
    "not_found": "Not addressed",
    "unverifiable": "Could not be determined",
}

_DECIDER_WORDS = {
    "rule": "counted by a rule",
    "model": "read by a model",
    "human": "decided by a person",
}

_RISK_ORDER = {"high": 0, "medium": 1, "low": 2}


def build(*, analysis, requirements: list, checks: list) -> list[Block]:
    binding = analysis.response or {}
    summary = binding.get("summary") or {}
    draft_label = binding.get("label") or binding.get("fileName") or "Draft response"
    version = binding.get("version") or 0

    blocks: list[Block] = [("heading", 1, "Response Match Analysis")]
    blocks.append(
        (
            "para",
            f"{analysis.title} — {analysis.solicitation_number or 'no solicitation number'}, "
            f"{analysis.agency}. Generated {datetime.now().strftime('%d %B %Y, %H:%M')}.",
        )
    )
    blocks.append(
        (
            "note",
            "This report matches a response draft against the solicitation's requirement "
            "ledger. Statuses and evidence are taken from the last check that was stored; "
            "they are not regenerated when you export.",
        )
    )

    if not checks:
        if binding.get("fileName") or binding.get("documentId"):
            blocks.append(("heading", 2, "No checks yet"))
            blocks.append(
                (
                    "para",
                    f"{draft_label} is bound"
                    + (f" as draft {version}" if version else "")
                    + " but has not been checked against the ledger. Run a check, then export again.",
                )
            )
        else:
            blocks.append(("heading", 2, "No response bound"))
            blocks.append(
                (
                    "para",
                    "Upload a response draft on the Response Gap tab, wait for the check to finish, "
                    "then export this report.",
                )
            )
        return blocks

    blocks += _summary(draft_label, version, summary, checks)
    blocks += _blocking(checks, requirements)
    blocks += _gaps(checks, requirements)
    blocks += _requirement_table(checks, requirements)
    blocks += _signoffs(checks, requirements)
    blocks += _lineage(checks, requirements)
    return blocks


def _summary(draft_label: str, version: int, summary: dict, checks: list) -> list[Block]:
    total = int(summary.get("total") or len(checks))
    cleared = int(summary.get("cleared") or 0)
    awaiting = int(summary.get("awaitingConfirmation") or 0)
    blocking = int(summary.get("blocking") or 0)
    counts = summary.get("counts") or {}
    if not counts:
        for check in checks:
            counts[check.status] = counts.get(check.status, 0) + 1

    blocks: list[Block] = [("heading", 2, "Match summary")]
    blocks.append(
        (
            "para",
            f"{draft_label}"
            + (f" (draft {version})" if version else "")
            + f" was checked against {total} open requirements. "
            f"{cleared} are answered and signed off; {awaiting} are answered but still "
            f"awaiting a person's signature; {blocking} are mandatory and unanswered.",
        )
    )
    blocks.append(
        (
            "table",
            ["Outcome", "Count"],
            [
                [_STATUS_WORDS.get(status, status), str(counts.get(status, 0))]
                for status in ("satisfied", "partial", "failed", "not_found", "unverifiable")
                if counts.get(status)
            ]
            or [["—", "0"]],
        )
    )
    return blocks


def _blocking(checks: list, requirements: list) -> list[Block]:
    by_id = {r.id: r for r in requirements}
    blocking_refs = []
    for check in checks:
        requirement = by_id.get(check.requirement_id)
        stakes = (requirement.stakes if requirement else "") or ""
        if stakes == "mandatory" and check.status in {"failed", "not_found", "unverifiable", "partial"}:
            blocking_refs.append(check)
        elif check.risk == "high" and check.status in {"failed", "not_found"}:
            blocking_refs.append(check)

    # Prefer the summary's blocking list when present — it is what the UI shows.
    # Fall back to the heuristic above when summary was never written.
    if not blocking_refs:
        return []

    blocks: list[Block] = [("heading", 2, "Could lose the bid")]
    blocks.append(
        (
            "para",
            "Mandatory or high-risk requirements the draft does not fully answer. "
            "Fix these before anything else on this page matters.",
        )
    )
    rows = []
    for check in sorted(blocking_refs, key=lambda c: (_RISK_ORDER.get(c.risk, 3), c.id)):
        requirement = by_id.get(check.requirement_id)
        rows.append(
            [
                requirement.reference if requirement else check.requirement_id,
                ((requirement.text if requirement else "") or "")[:280],
                _STATUS_WORDS.get(check.status, check.status),
                (check.gap or check.detail or "")[:220],
                check.risk or "",
                check.owner or "",
            ]
        )
    blocks.append(
        ("table", ["Clause", "Requirement", "Status", "Gap", "Risk", "Owner"], rows)
    )
    return blocks


def _gaps(checks: list, requirements: list) -> list[Block]:
    by_id = {r.id: r for r in requirements}
    open_gaps = [
        c
        for c in checks
        if c.status != "satisfied" or c.needs_confirmation
    ]
    if not open_gaps:
        return [
            ("heading", 2, "Gaps"),
            ("para", "Every requirement is answered and signed off for this draft."),
        ]

    blocks: list[Block] = [("heading", 2, "Gaps, by risk")]
    blocks.append(
        (
            "para",
            "Everything that still needs work or a signature, ordered by how costly "
            "it would be to leave wrong.",
        )
    )
    rows = []
    for check in sorted(open_gaps, key=lambda c: (_RISK_ORDER.get(c.risk, 3), c.id)):
        requirement = by_id.get(check.requirement_id)
        note = check.gap or check.detail or ""
        if check.needs_confirmation and check.status == "satisfied":
            note = (note + " — awaiting sign-off").strip(" —")
        rows.append(
            [
                requirement.reference if requirement else check.requirement_id,
                ((requirement.text if requirement else "") or "")[:220],
                _STATUS_WORDS.get(check.status, check.status),
                note[:220],
                check.risk or "",
                check.owner or "",
            ]
        )
    blocks.append(
        ("table", ["Clause", "Requirement", "Status", "What is missing", "Risk", "Owner"], rows)
    )
    return blocks


def _requirement_table(checks: list, requirements: list) -> list[Block]:
    by_id = {r.id: r for r in requirements}
    blocks: list[Block] = [("heading", 2, "Requirement by requirement")]
    blocks.append(
        (
            "para",
            "Full trace for this draft. Evidence names the passage in the response "
            "the status rests on, when one was found.",
        )
    )
    rows = []
    for check in sorted(checks, key=lambda c: (_RISK_ORDER.get(c.risk, 3), c.id)):
        requirement = by_id.get(check.requirement_id)
        evidence = check.evidence or {}
        where = "—"
        if evidence.get("quote") or evidence.get("page") is not None:
            where = (
                f"{evidence.get('documentName', 'response')} p.{evidence.get('page', '?')}"
                + ("" if evidence.get("located", True) else " (quote not located)")
            )
            if evidence.get("quote"):
                where += f' — "{str(evidence.get("quote"))[:120]}"'
        rows.append(
            [
                requirement.reference if requirement else check.requirement_id,
                ((requirement.text if requirement else "") or "")[:260],
                _STATUS_WORDS.get(check.status, check.status),
                _DECIDER_WORDS.get(check.decided_by, check.decided_by or "")
                + (f" ({check.rule})" if check.rule else ""),
                where,
                (check.gap or "")[:180],
                check.risk or "",
            ]
        )
    blocks.append(
        (
            "table",
            ["Clause", "Requirement", "Status", "Decided", "Evidence", "Gap", "Risk"],
            rows,
        )
    )
    return blocks


def _signoffs(checks: list, requirements: list) -> list[Block]:
    signed = [c for c in checks if c.confirmed_by]
    if not signed:
        return []
    by_id = {r.id: r for r in requirements}
    blocks: list[Block] = [("heading", 2, "Who signed what")]
    blocks.append(
        (
            "para",
            "A mandatory requirement is never cleared by a rule or a model alone. "
            "Each row is a person taking responsibility for a conclusion.",
        )
    )
    rows = [
        [
            (by_id[c.requirement_id].reference if c.requirement_id in by_id else c.requirement_id),
            _STATUS_WORDS.get(c.status, c.status),
            c.confirmed_by or "",
            c.confirmed_at.isoformat(timespec="minutes") if c.confirmed_at else "",
            (c.note or "")[:200],
        ]
        for c in signed
    ]
    blocks.append(("table", ["Clause", "Conclusion", "Signed by", "When", "Note"], rows))
    return blocks


def _lineage(checks: list, requirements: list) -> list[Block]:
    carried = [c for c in checks if getattr(c, "carried_verdict", None) or getattr(c, "supersedes_id", None)]
    if not carried:
        return []
    by_id = {r.id: r for r in requirements}
    blocks: list[Block] = [("heading", 2, "Carried across drafts")]
    blocks.append(
        (
            "para",
            "Verdicts that survived a new draft upload because the underlying evidence "
            "had not changed. A carried row is not a fresh reading.",
        )
    )
    rows = [
        [
            (by_id[c.requirement_id].reference if c.requirement_id in by_id else c.requirement_id),
            _STATUS_WORDS.get(c.status, c.status),
            "yes" if c.carried_verdict else "no",
            (c.supersedes_id or "")[:24] or "—",
        ]
        for c in carried
    ]
    blocks.append(
        ("table", ["Clause", "Status", "Carried verdict", "Supersedes"], rows)
    )
    return blocks
