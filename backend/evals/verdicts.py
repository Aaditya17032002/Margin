"""Turning recorded corrections into evaluation cases.

Every other corpus in `evals/` was written by hand, which is why there is so
little of it. This one grows on its own: each time somebody overrules Margin,
they produce an example with a known right answer, on a real document, in the
place the product is actually wrong.

    python -m evals.verdicts report                    # where are we wrong?
    python -m evals.verdicts export --out adjudication.json

**These cases contain real solicitation and response text.** They come out of a
customer's database and they carry the clause and the passage verbatim, because
a case without them is not a case. Nothing here uploads anything; the export
writes a file and stops. Where it goes afterwards is a decision somebody has to
make deliberately.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.base import async_session_factory, dispose_db
from app.db.models.verdict import CORRECTED, FLAGGED, Verdict
from app.pipeline.verdicts import disagreement


async def _load(analysis_id: str | None, org_id: str | None) -> list[Verdict]:
    async with async_session_factory() as db:
        query = select(Verdict)
        if analysis_id:
            query = query.where(Verdict.analysis_id == analysis_id)
        if org_id:
            query = query.where(Verdict.org_id == org_id)
        rows = list((await db.execute(query.order_by(Verdict.at.asc()))).scalars().all())
    await dispose_db()
    return rows


def to_adjudication_case(row: Verdict) -> dict:
    """One correction, in the shape `evals/adjudication` reads.

    The human verdict is `expected`, because they were the one holding the
    document. `acceptable` carries `unverifiable`: a model that says it cannot
    tell where a person said `failed` is unhelpful, not dangerous, and scoring
    it as the same mistake would push the rubric toward confident guessing.
    """
    return {
        "id": f"field-{row.id}",
        "why": (
            f"A reviewer overruled {row.machine_status or 'the machine'} → {row.human_status}"
            + (f" on {row.reference}" if row.reference else "")
            + (f". They said: {row.note}" if row.note else ".")
        ),
        "requirement": row.requirement_text,
        "reference": row.reference or "—",
        "stakes": row.stakes or "scored",
        "passages": [row.response_excerpt] if row.response_excerpt else [],
        "expected": row.human_status,
        "acceptable": ["unverifiable"] if row.human_status != "unverifiable" else [],
        "provenance": {
            "source": "field correction",
            "verdictId": row.id,
            "analysisId": row.analysis_id,
            "decidedBy": row.machine_decided_by,
            "rule": row.machine_rule,
            "at": row.at.isoformat() if row.at else None,
        },
    }


def exportable(rows: list[Verdict]) -> list[Verdict]:
    """Corrections and flags with enough context to be a case.

    A confirmation says the machine was right, which is worth measuring in the
    aggregate and adds nothing as a test. A correction with no passage recorded
    cannot be replayed — it would assert an answer with no question.
    """
    return [
        row
        for row in rows
        if row.outcome in (CORRECTED, FLAGGED)
        and row.requirement_text.strip()
        and row.response_excerpt.strip()
    ]


def _report(rows: list[Verdict]) -> int:
    if not rows:
        print("No verdicts recorded yet. They appear as people confirm and overrule checks.")
        return 0

    report = disagreement(rows)
    print(f"{report['total']} judgement(s): {report['confirmed']} confirmed, "
          f"{report['corrected']} corrected, {report['flagged']} flagged")
    print(f"correction rate {report['correctionRate']:.1%}")
    print(
        f"would have shipped: {report['wouldHaveShipped']}  "
        "(the machine said answered and a person said it was not)"
    )

    for label, key in (
        ("by rule", "byRule"),
        ("by decider", "byDecider"),
        ("mechanical vs substantive", "byVerification"),
        ("by stakes", "byStakes"),
    ):
        buckets = [b for b in report[key] if b["total"]]
        if not buckets:
            continue
        print(f"\n{label}")
        print(f"  {'':<28}{'seen':>6}{'wrong':>7}{'rate':>8}")
        for bucket in buckets[:10]:
            print(
                f"  {bucket['name'][:26]:<28}{bucket['total']:>6}{bucket['corrected']:>7}"
                f"{bucket['correctionRate']:>8.0%}"
            )

    if report["transitions"]:
        print("\nwhich way corrections go")
        for move in report["transitions"][:10]:
            print(f"  {move['from'] or '—':>14} → {move['to']:<14} {move['count']}")

    ready = len(exportable(rows))
    print(f"\n{ready} correction(s) carry enough context to become evaluation cases.")
    print("  python -m evals.verdicts export --out evals/adjudication/field.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["report", "export"])
    parser.add_argument("--analysis", help="limit to one analysis")
    parser.add_argument("--org", help="limit to one organisation")
    parser.add_argument("--out", help="where to write the exported cases")
    args = parser.parse_args(argv)

    rows = asyncio.run(_load(args.analysis, args.org))

    if args.command == "report":
        return _report(rows)

    if not args.out:
        print("`export` needs --out. It writes a file and does nothing else.", file=sys.stderr)
        return 1

    cases = [to_adjudication_case(row) for row in exportable(rows)]
    if not cases:
        print("No corrections carry enough context to export yet.", file=sys.stderr)
        return 1

    Path(args.out).write_text(
        json.dumps(
            {
                "_note": (
                    "Exported from recorded corrections. These carry real solicitation and "
                    "response text — check what they contain before they leave the machine "
                    "they were written on."
                ),
                "cases": cases,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {len(cases)} case(s) to {args.out}")
    print("Read them before adding them to a gated corpus: a reviewer can be wrong too, and a")
    print("bad label fails the extraction rather than testing it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
