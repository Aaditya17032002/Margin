"""Measuring what the deterministic extraction actually finds.

Margin's claim is that nothing gets missed. A claim like that is not a slogan
to be defended in a meeting; it is a number to be measured against documents
where the right answer is known, and re-measured every time anything upstream
of it changes.

This harness scores the deterministic sweep — the pattern layer in
``app/pipeline/sweep.py`` — against a labelled corpus, per category, and fails
the build when recall drops. It is deliberately the *deterministic* layer that
is gated:

* It is repeatable. The same document gives the same answer today and in a
  year, so a regression is a real change and never sampling noise.
* It needs no API keys, so it runs on every pull request rather than nightly
  and out of sight.
* It is the floor the model layer is built on. If the floor moves, everything
  above it moves and nobody would otherwise notice.

Model-based extraction needs measuring too, and cannot be measured this way —
it is non-deterministic and needs credentials. That belongs in a separate,
non-gating online evaluation using the same labelled cases; the loader here is
shared so the corpus is written once.

    python -m evals.harness              # score and print
    python -m evals.harness --gate       # score, print, exit non-zero on regression
    python -m evals.harness --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.anchor import normalize
from app.pipeline.extract import pages_from_text
from app.pipeline.layout import LayoutExtractor
from app.pipeline.sweep import KINDS, sweep_chunks

CASES_DIR = Path(__file__).parent / "cases"
THRESHOLDS_PATH = Path(__file__).parent / "thresholds.json"


@dataclass
class Expected:
    kind: str
    page: int
    quote: str


@dataclass
class Case:
    name: str
    path: Path
    text: str
    source: str
    expected: list[Expected]
    #: Categories where the labels list *every* instance, so precision is
    #: meaningful. Elsewhere only recall is measured, because a sweep tuned for
    #: recall will always fire on text nobody bothered to label.
    exhaustive: set[str] = field(default_factory=set)


def load_cases(directory: Path = CASES_DIR) -> list[Case]:
    cases: list[Case] = []
    for case_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
        document = case_dir / "document.txt"
        labels = case_dir / "labels.json"
        if not document.exists() or not labels.exists():
            continue
        spec = json.loads(labels.read_text())
        expected = [
            Expected(kind=kind, page=int(item["page"]), quote=str(item["quote"]))
            for kind, items in spec.get("expected", {}).items()
            for item in items
        ]
        cases.append(
            Case(
                name=spec.get("name", case_dir.name),
                path=case_dir,
                text=document.read_text(),
                source=spec.get("source", "unknown"),
                expected=expected,
                exhaustive=set(spec.get("exhaustive", [])),
            )
        )
    return cases


def _found(expected: Expected, hits: list) -> bool:
    """A label counts as found when a hit of the same kind on the same page
    carries the labelled text.

    Containment either way: the sweep often captures a whole sentence around a
    short label, and sometimes a fragment of a long one. Requiring an exact
    match would measure the phrasing of the labels rather than the recall of
    the patterns.
    """
    needle = normalize(expected.quote)
    if not needle:
        return False
    for hit in hits:
        if hit.kind != expected.kind or hit.page != expected.page:
            continue
        haystack = normalize(hit.text)
        if needle in haystack or (len(haystack) > 12 and haystack in needle):
            return True
    return False


def score_case(case: Case) -> dict:
    layout = LayoutExtractor().extract_from_pages(pages_from_text(case.text), case.name)
    hits = sweep_chunks(layout.chunks).hits

    by_kind: dict[str, dict] = {}
    for kind in KINDS:
        gold = [e for e in case.expected if e.kind == kind]
        if not gold:
            continue
        found = [e for e in gold if _found(e, hits)]
        missed = [e for e in gold if e not in found]
        entry = {
            "expected": len(gold),
            "found": len(found),
            "recall": round(len(found) / len(gold), 4),
            "missed": [{"page": e.page, "quote": e.quote} for e in missed],
        }
        if kind in case.exhaustive:
            produced = [h for h in hits if h.kind == kind]
            entry["produced"] = len(produced)
            entry["precision"] = round(len(found) / len(produced), 4) if produced else 0.0
        by_kind[kind] = entry

    return {
        "case": case.name,
        "source": case.source,
        "pages": len(layout.pages),
        "chunks": len(layout.chunks),
        "hits": len(hits),
        "byKind": by_kind,
    }


def aggregate(results: list[dict]) -> dict:
    totals: dict[str, dict] = {}
    for result in results:
        for kind, entry in result["byKind"].items():
            bucket = totals.setdefault(kind, {"expected": 0, "found": 0, "missed": []})
            bucket["expected"] += entry["expected"]
            bucket["found"] += entry["found"]
            bucket["missed"].extend(
                {**m, "case": result["case"]} for m in entry["missed"]
            )
    for kind, bucket in totals.items():
        bucket["recall"] = round(bucket["found"] / bucket["expected"], 4) if bucket["expected"] else 1.0
    overall_expected = sum(b["expected"] for b in totals.values())
    overall_found = sum(b["found"] for b in totals.values())
    return {
        "byKind": totals,
        "overall": {
            "expected": overall_expected,
            "found": overall_found,
            "recall": round(overall_found / overall_expected, 4) if overall_expected else 1.0,
        },
    }


def load_thresholds() -> dict:
    if THRESHOLDS_PATH.exists():
        return json.loads(THRESHOLDS_PATH.read_text())
    return {}


def check(summary: dict, thresholds: dict) -> list[str]:
    """Categories that fell below their floor. Empty means the gate passes."""
    failures: list[str] = []
    minimums = thresholds.get("recall", {})
    for kind, minimum in sorted(minimums.items()):
        actual = summary["byKind"].get(kind, {}).get("recall")
        if actual is None:
            failures.append(f"{kind}: no labelled examples in the corpus (floor {minimum:.0%})")
        elif actual + 1e-9 < minimum:
            failures.append(f"{kind}: recall {actual:.1%} below floor {minimum:.0%}")
    overall_min = thresholds.get("overallRecall")
    if overall_min is not None and summary["overall"]["recall"] + 1e-9 < overall_min:
        failures.append(
            f"overall: recall {summary['overall']['recall']:.1%} below floor {overall_min:.0%}"
        )
    return failures


def report(results: list[dict], summary: dict, thresholds: dict) -> str:
    minimums = thresholds.get("recall", {})
    lines = ["", "Extraction recall — deterministic sweep", "=" * 62]
    for result in results:
        lines.append(
            f"{result['case']}  ({result['source']}, {result['pages']} pages, {result['hits']} hits)"
        )
    lines.append("-" * 62)
    lines.append(f"{'category':<16}{'recall':>9}{'found':>8}{'floor':>8}   status")
    for kind in KINDS:
        bucket = summary["byKind"].get(kind)
        if not bucket:
            continue
        floor = minimums.get(kind)
        ok = floor is None or bucket["recall"] + 1e-9 >= floor
        lines.append(
            f"{kind:<16}{bucket['recall']:>8.1%}"
            f"{bucket['found']:>5}/{bucket['expected']:<3}"
            f"{(f'{floor:.0%}' if floor is not None else '—'):>8}"
            f"   {'ok' if ok else 'BELOW FLOOR'}"
        )
    lines.append("-" * 62)
    overall = summary["overall"]
    lines.append(
        f"{'overall':<16}{overall['recall']:>8.1%}{overall['found']:>5}/{overall['expected']:<3}"
    )

    misses = [
        (kind, miss)
        for kind, bucket in summary["byKind"].items()
        for miss in bucket["missed"]
    ]
    if misses:
        lines += ["", f"Missed ({len(misses)}):"]
        for kind, miss in misses[:25]:
            lines.append(f"  [{kind}] p.{miss['page']} {miss['quote'][:70]}  ({miss['case']})")
        if len(misses) > 25:
            lines.append(f"  … and {len(misses) - 25} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true", help="exit non-zero when recall is below a floor")
    parser.add_argument("--json", dest="json_path", help="write the full result to this path")
    args = parser.parse_args(argv)

    cases = load_cases()
    if not cases:
        print("No labelled cases found in evals/cases.", file=sys.stderr)
        return 1

    results = [score_case(case) for case in cases]
    summary = aggregate(results)
    thresholds = load_thresholds()

    print(report(results, summary, thresholds))

    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps({"cases": results, "summary": summary, "thresholds": thresholds}, indent=2)
        )

    failures = check(summary, thresholds)
    if failures:
        print("\nRecall regression:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        if args.gate:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
