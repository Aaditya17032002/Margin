"""The Evidence Pack: a record of what was read, decided, and by whom.

Every other export answers "what does this solicitation say?". This one answers
the question asked afterwards — in a debrief, a protest, an internal review,
or by whoever inherits the pursuit: *on what basis did you conclude that?*

So it carries the parts of the analysis that are usually thrown away:

* the coverage ledger, including the pages nothing read;
* every requirement with the run that found it and which passes agreed;
* every response check, what decided it, and the passage it rested on;
* every claim whose quote could not be located in the package;
* what each amendment changed and which answers it invalidated;
* every sign-off, with the name against it.

It is built from stored facts. Nothing here is regenerated or re-inferred at
export time, because a record that changes when you print it is not a record.

The output is a list of blocks so the DOCX and Markdown renderers can walk the
same content. A pack that differed between formats would be two records.
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


def build(
    *, analysis, requirements: list, checks: list, queue: list, questions: list | None = None
) -> list[Block]:
    blocks: list[Block] = []
    blocks.append(("heading", 1, "Evidence pack"))
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
            "This pack records what Margin read, what it concluded, and what a person "
            "decided. It is assembled from stored facts rather than regenerated, so it "
            "says the same thing every time it is exported.",
        )
    )

    blocks += _coverage(analysis)
    blocks += _amendments(analysis)
    blocks += _requirements(requirements)
    blocks += _questions(questions or [])
    blocks += _response(analysis, checks, requirements)
    blocks += _signoffs(checks, requirements)
    blocks += _open(queue)
    blocks += _unlocated(analysis)
    return blocks


# ── Sections ─────────────────────────────────────────────────────────────


def _coverage(analysis) -> list[Block]:
    coverage = analysis.coverage or {}
    totals = coverage.get("totals") or {}
    if not totals:
        return [("heading", 2, "What was read"), ("para", "No coverage was recorded for this analysis.")]

    blocks: list[Block] = [("heading", 2, "What was read")]
    blocks.append(
        (
            "para",
            f"{totals.get('pagesScanned', 0)} of {totals.get('pages', 0)} pages were scanned "
            f"across {totals.get('documents', 0)} documents; {totals.get('pagesAnalysed', 0)} "
            "were analysed in depth by a specialist. Scanning matches every known extraction "
            "pattern and is complete; analysis is interpretive and selective. The two are "
            "reported separately because they are different claims.",
        )
    )
    rows = []
    for document in coverage.get("documents") or []:
        unreached = ", ".join(
            str(start) if start == end else f"{start}–{end}"
            for start, end in (document.get("unreachedPages") or [])
        )
        rows.append(
            [
                str(document.get("name", "")),
                str(document.get("kind", "")),
                str(document.get("pages", 0)),
                str(document.get("pagesAnalysed", 0)),
                "no readable text"
                if document.get("state") == "no_text"
                else (unreached or "none"),
            ]
        )
    if rows:
        blocks.append(("table", ["Document", "Kind", "Pages", "Analysed", "Not reached"], rows))
    if totals.get("emptyDocuments"):
        blocks.append(
            (
                "note",
                f"{totals['emptyDocuments']} document(s) produced no readable text. Nothing in "
                "them was read, and no requirement stated in them appears anywhere in this pack.",
            )
        )
    return blocks


def _amendments(analysis) -> list[Block]:
    amendments = analysis.amendments or []
    if not amendments:
        return []
    blocks: list[Block] = [("heading", 2, "What each amendment changed")]
    for record in amendments:
        blocks.append(("heading", 3, str(record.get("label", "Amendment"))))
        blocks.append(("para", str(record.get("summary", ""))))
        rows = [
            [
                str(change.get("kind", "")),
                str(change.get("area", "")),
                str(change.get("before") or "—")[:300],
                str(change.get("after") or "—")[:300],
                "critical" if change.get("critical") else "",
            ]
            for change in record.get("changes") or []
        ]
        if rows:
            blocks.append(("table", ["Change", "Clause", "Before", "After", ""], rows))

    invalidated = (analysis.ledger or {}).get("invalidated") or []
    if invalidated:
        blocks.append(
            (
                "note",
                "Answers written against wording an amendment has since replaced: "
                + "; ".join(str(entry) for entry in invalidated)
                + ". Each was reopened rather than carried over as complete.",
            )
        )
    return blocks


def _requirements(requirements: list) -> list[Block]:
    if not requirements:
        return []
    blocks: list[Block] = [("heading", 2, "Every requirement, and how it was found")]
    blocks.append(
        (
            "para",
            "A requirement found by both the deterministic sweep and a specialist is "
            "stronger evidence than one only a model reported. This table says which.",
        )
    )
    rows = []
    for requirement in sorted(requirements, key=lambda r: (r.document_id, r.page, r.reference)):
        rows.append(
            [
                requirement.reference or "",
                (requirement.text or "")[:400],
                requirement.stakes or "",
                "counted" if requirement.verification == "mechanical" else "read",
                ", ".join(requirement.sources or []) or "—",
                requirement.state or "open",
                requirement.owner or "unassigned",
            ]
        )
    blocks.append(
        (
            "table",
            ["Reference", "Requirement", "Stakes", "Check", "Found by", "State", "Owner"],
            rows,
        )
    )
    return blocks


def _questions(questions: list) -> list[Block]:
    """What was asked, what came back, and what it changed.

    An agency answer is a contract document. A pack that summarised one would
    be worth nothing in the dispute it exists for, so answers are reproduced as
    they were received — and the questions nobody answered are listed too,
    because a decision made without an answer is a decision somebody has to be
    able to account for.
    """
    if not questions:
        return []

    blocks: list[Block] = [("heading", 2, "Questions to the agency")]
    answered = [q for q in questions if (q.status or "draft") == "answered"]
    open_questions = [q for q in questions if (q.status or "draft") == "submitted"]
    drafts = [q for q in questions if (q.status or "draft") == "draft"]

    blocks.append(
        (
            "para",
            f"{len(questions)} question(s): {len(answered)} answered, {len(open_questions)} sent "
            f"and unanswered, {len(drafts)} never sent.",
        )
    )

    if answered:
        blocks.append(
            (
                "table",
                ["Clause", "Question", "The agency's answer", "Source", "When"],
                [
                    [
                        q.reference if hasattr(q, "reference") else "",
                        (q.text or "")[:300],
                        (q.answer or "")[:600],
                        q.answer_source or "",
                        q.answered_at.isoformat(timespec="minutes") if q.answered_at else "",
                    ]
                    for q in answered
                ],
            )
        )

    if open_questions or drafts:
        blocks.append(
            (
                "note",
                "Unanswered questions are recorded because a decision made without an answer is "
                "a decision somebody has to be able to account for.",
            )
        )
        blocks.append(
            (
                "table",
                ["State", "Question", "Why it was asked", "Affects the decision"],
                [
                    [
                        q.status or "draft",
                        (q.text or "")[:300],
                        (q.rationale or "")[:200],
                        "yes" if q.go_no_go_impact else "",
                    ]
                    for q in [*open_questions, *drafts]
                ],
            )
        )
    return blocks


def _response(analysis, checks: list, requirements: list) -> list[Block]:
    binding = analysis.response or {}
    if not checks:
        if binding.get("fileName"):
            return [
                ("heading", 2, "The response"),
                ("para", f"{binding['fileName']} is bound to this solicitation but has not been checked."),
            ]
        return []

    by_id = {r.id: r for r in requirements}
    summary = binding.get("summary") or {}
    blocks: list[Block] = [("heading", 2, "The response, requirement by requirement")]
    blocks.append(
        (
            "para",
            f"{binding.get('label') or binding.get('fileName', 'The draft')} "
            f"(draft {binding.get('version', 1)}), checked against {summary.get('total', len(checks))} "
            f"requirements. {summary.get('cleared', 0)} are answered and signed off; "
            f"{summary.get('awaitingConfirmation', 0)} are answered but awaiting a signature; "
            f"{summary.get('blocking', 0)} are mandatory and unanswered.",
        )
    )
    rows = []
    for check in sorted(checks, key=lambda c: ({"high": 0, "medium": 1, "low": 2}.get(c.risk, 3), c.id)):
        requirement = by_id.get(check.requirement_id)
        evidence = check.evidence or {}
        where = ""
        if evidence.get("quote"):
            where = (
                f"{evidence.get('documentName', 'response')} p.{evidence.get('page', '?')}"
                + ("" if evidence.get("located", True) else " (quote not located)")
            )
        rows.append(
            [
                requirement.reference if requirement else check.requirement_id,
                (requirement.text if requirement else "")[:300],
                _STATUS_WORDS.get(check.status, check.status),
                _DECIDER_WORDS.get(check.decided_by, check.decided_by)
                + (f" ({check.rule})" if check.rule else ""),
                where or "—",
                (check.gap or "")[:200],
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
    cleared = [r for r in requirements if r.confirmed_by]
    if not signed and not cleared:
        return []
    blocks: list[Block] = [("heading", 2, "Who signed what")]
    blocks.append(
        (
            "para",
            "A mandatory requirement is never cleared by a rule or a model. Each row below "
            "is a person taking responsibility for a conclusion.",
        )
    )
    by_id = {r.id: r for r in requirements}
    rows = []
    for check in signed:
        requirement = by_id.get(check.requirement_id)
        rows.append(
            [
                requirement.reference if requirement else check.requirement_id,
                _STATUS_WORDS.get(check.status, check.status),
                check.confirmed_by or "",
                check.confirmed_at.isoformat(timespec="minutes") if check.confirmed_at else "",
                (check.note or "")[:200],
            ]
        )
    for requirement in cleared:
        rows.append(
            [
                requirement.reference or "",
                f"matrix: {requirement.status}",
                requirement.confirmed_by or "",
                requirement.confirmed_at.isoformat(timespec="minutes") if requirement.confirmed_at else "",
                (requirement.note or "")[:200],
            ]
        )
    blocks.append(("table", ["Clause", "Conclusion", "Signed by", "When", "Note"], rows))
    return blocks


def _open(queue: list) -> list[Block]:
    if not queue:
        return []
    blocks: list[Block] = [("heading", 2, "What is still open")]
    blocks.append(
        (
            "para",
            "Everything the analysis could not settle on its own, in the order it would "
            "cost to be wrong about. An empty list here would mean nothing was left to a "
            "person, which is never true of a real solicitation.",
        )
    )
    rows = [
        [item.severity, item.reference or "—", item.title[:200], item.why[:200], item.consequence[:200]]
        for item in queue
    ]
    blocks.append(("table", ["Severity", "Clause", "What", "Why a machine could not settle it", "If nobody does"], rows))
    return blocks


_FINDING_SECTIONS = (
    ("Identity", "identity"),
    ("Scope", "scope"),
    ("Legal & regulatory", "legal"),
    ("Eligibility", "eligibility"),
    ("Pricing", "pricing"),
    ("Post-award", "post_award"),
)


def _unlocated(analysis) -> list[Block]:
    """Claims whose quote could not be found in the package.

    Kept in the pack rather than hidden. A finding nothing in the document was
    shown to support is exactly what an auditor asks about, and answering "we
    knew, and here is the list" is a much better position than being shown it.
    """
    rows = []
    for label, attr in _FINDING_SECTIONS:
        for finding in getattr(analysis, attr, None) or []:
            citation = finding.get("citation") or {}
            if not citation.get("quote") or citation.get("located") is not False:
                continue
            rows.append(
                [
                    label,
                    str(finding.get("label", ""))[:120],
                    str(finding.get("value", ""))[:200],
                    str(citation.get("quote", ""))[:200],
                ]
            )
    if not rows:
        return [
            ("heading", 2, "Claims that could not be grounded"),
            ("para", "None. Every claim in this analysis quotes text found in the package."),
        ]
    return [
        ("heading", 2, "Claims that could not be grounded"),
        (
            "para",
            "The quote behind each of these was not found anywhere in the package. The claim "
            "may still be correct, but nothing in the document has been shown to support it.",
        ),
        ("table", ["Section", "Finding", "Claim", "Quote that could not be located"], rows),
    ]
