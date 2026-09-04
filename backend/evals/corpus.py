"""The evaluation corpus: what is in it, where it came from, and is it sound.

A recall number is only as trustworthy as the labels behind it, and labels are
the part of an evaluation that rots quietly. A quote that is not verbatim fails
the extraction rather than testing it; a page number off by one turns a hit into
a miss; the same requirement labelled twice inflates a denominator nobody
checks. Each of those was found by hand while this corpus was being written,
which is why they are checked by code now.

Provenance matters as much. A case with no source cannot be re-derived when the
parser changes, cannot be shared without a licence question, and cannot be
distinguished from one somebody invented — and a corpus of invented documents
that reports 100% recall is worse than no corpus, because it is believed.

    python -m evals.corpus validate     # labels sound? provenance recorded?
    python -m evals.corpus stats        # what the corpus actually covers
    python -m evals.corpus propose <case>   # candidate labels from the sweep
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.anchor import normalize
from app.pipeline.extract import pages_from_text
from app.pipeline.layout import LayoutExtractor
from app.pipeline.sweep import KINDS, sweep_chunks

CASES_DIR = Path(__file__).parent / "cases"

#: A case is either written by hand against the conventions of real
#: solicitations, or extracted from an actual one. The distinction is the whole
#: reason this field exists: a floor held up entirely by documents we invented
#: is not a floor.
SYNTHETIC = "synthetic"
REAL = "real"


@dataclass
class Problem:
    case: str
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.case}] {self.kind}: {self.detail}"


@dataclass
class CaseFiles:
    directory: Path
    text: str
    spec: dict

    @property
    def name(self) -> str:
        return str(self.spec.get("name") or self.directory.name)

    @property
    def source(self) -> str:
        return str(self.spec.get("source") or "unknown")

    @property
    def is_real(self) -> bool:
        return self.source == REAL

    @property
    def pages(self) -> list[str]:
        return pages_from_text(self.text)

    def checksum(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


def load(directory: Path = CASES_DIR) -> list[CaseFiles]:
    cases: list[CaseFiles] = []
    if not directory.exists():
        return cases
    for case_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
        document = case_dir / "document.txt"
        labels = case_dir / "labels.json"
        if not document.exists() or not labels.exists():
            continue
        cases.append(
            CaseFiles(
                directory=case_dir,
                text=document.read_text(),
                spec=json.loads(labels.read_text()),
            )
        )
    return cases


# ── Validation ───────────────────────────────────────────────────────────


def validate(cases: list[CaseFiles]) -> list[Problem]:
    """Everything that would make a recall number mean less than it appears to."""
    problems: list[Problem] = []
    for case in cases:
        problems += _validate_provenance(case)
        problems += _validate_labels(case)
        pending = unreviewed(case)
        if pending:
            problems.append(
                Problem(
                    case.name,
                    "label",
                    f"{pending} labels are still flagged `candidate` — the sweep proposed them "
                    "and nobody has reviewed them. Scoring against these measures the sweep "
                    "against itself.",
                )
            )
    return problems


def _validate_provenance(case: CaseFiles) -> list[Problem]:
    problems: list[Problem] = []
    source = case.source
    if source not in (SYNTHETIC, REAL):
        problems.append(
            Problem(case.name, "provenance", f"`source` is {source!r}; expected 'real' or 'synthetic'")
        )
        return problems

    if source == SYNTHETIC:
        return problems

    # A real case has to be traceable. Without this it cannot be re-derived
    # when the parser changes, and nobody can answer the licence question.
    provenance = case.spec.get("provenance") or {}
    for field_name in ("solicitationNumber", "agency", "retrievedFrom", "retrievedAt"):
        if not str(provenance.get(field_name) or "").strip():
            problems.append(
                Problem(case.name, "provenance", f"real case is missing provenance.{field_name}")
            )
    recorded = str(provenance.get("checksum") or "")
    if not recorded:
        problems.append(
            Problem(case.name, "provenance", "real case is missing provenance.checksum")
        )
    elif recorded != case.checksum():
        # The document changed after it was labelled. Every page number in the
        # label file is now a guess.
        problems.append(
            Problem(
                case.name,
                "provenance",
                f"document has changed since labelling (recorded {recorded}, now {case.checksum()}). "
                "Re-check the page numbers before trusting this case.",
            )
        )
    return problems


def _validate_labels(case: CaseFiles) -> list[Problem]:
    problems: list[Problem] = []
    pages = case.pages
    normalised_pages = [normalize(page) for page in pages]
    expected = case.spec.get("expected") or {}
    seen: set[tuple[str, int, str]] = set()

    for kind, items in expected.items():
        if kind not in KINDS:
            problems.append(Problem(case.name, "label", f"unknown category {kind!r}"))
            continue
        for item in items:
            quote = str(item.get("quote") or "")
            page = int(item.get("page") or 0)

            if not quote.strip():
                problems.append(Problem(case.name, "label", f"{kind}: empty quote"))
                continue
            if page < 1 or page > len(pages):
                problems.append(
                    Problem(case.name, "label", f"{kind} p.{page}: no such page (document has {len(pages)})")
                )
                continue

            needle = normalize(quote)
            if needle not in normalised_pages[page - 1]:
                # The single most common way a label goes wrong, and the one
                # that looks exactly like an extraction failure.
                where = [i + 1 for i, text in enumerate(normalised_pages) if needle in text]
                detail = f"{kind} p.{page}: {quote[:60]!r} is not on that page"
                if where:
                    detail += f" — it is on p.{', p.'.join(str(p) for p in where)}"
                else:
                    detail += " and not anywhere in the document"
                problems.append(Problem(case.name, "label", detail))
                continue

            identity = (kind, page, needle)
            if identity in seen:
                problems.append(
                    Problem(case.name, "label", f"{kind} p.{page}: {quote[:60]!r} is labelled twice")
                )
            seen.add(identity)

    for kind in case.spec.get("exhaustive") or []:
        if kind not in expected:
            problems.append(
                Problem(
                    case.name,
                    "label",
                    f"{kind} is marked exhaustive but has no labels — precision would be measured "
                    "against an empty list",
                )
            )
    return problems


# ── What the corpus covers ───────────────────────────────────────────────


@dataclass
class Stats:
    cases: int = 0
    real: int = 0
    synthetic: int = 0
    pages: int = 0
    labels: int = 0
    by_kind: dict = field(default_factory=dict)
    by_kind_real: dict = field(default_factory=dict)

    @property
    def real_share(self) -> float:
        return self.real / self.cases if self.cases else 0.0


def stats(cases: list[CaseFiles]) -> Stats:
    result = Stats(cases=len(cases))
    for case in cases:
        if case.is_real:
            result.real += 1
        else:
            result.synthetic += 1
        result.pages += len(case.pages)
        for kind, items in (case.spec.get("expected") or {}).items():
            result.by_kind[kind] = result.by_kind.get(kind, 0) + len(items)
            result.labels += len(items)
            if case.is_real:
                result.by_kind_real[kind] = result.by_kind_real.get(kind, 0) + len(items)
    return result


def coverage_gaps(cases: list[CaseFiles]) -> list[str]:
    """Categories no *real* document exercises.

    A category measured only against text we wrote ourselves is measured
    against our own assumptions about how agencies write, which is exactly the
    assumption an evaluation exists to test.
    """
    numbers = stats(cases)
    if not numbers.real:
        return [f"no real cases at all — every category is measured against invented text"]
    return [kind for kind in KINDS if not numbers.by_kind_real.get(kind)]


# ── Labelling assistance ─────────────────────────────────────────────────


def propose(case: CaseFiles, limit_per_kind: int = 40) -> dict:
    """Candidate labels from the sweep, for a person to cut down.

    This is deliberately a *starting point a human edits*, never a label file.
    Labels generated by the thing being measured would make the harness score
    its own opinion — the value is only in what a person removes and adds.
    Every candidate carries the page and the verbatim text, so accepting one is
    a deletion of the `candidate` flag rather than retyping a quote and getting
    it subtly wrong.
    """
    layout = LayoutExtractor().extract_from_pages(case.pages, case.name)
    hits = sweep_chunks(layout.chunks).hits

    proposed: dict[str, list[dict]] = {}
    for hit in hits:
        bucket = proposed.setdefault(hit.kind, [])
        if len(bucket) >= limit_per_kind:
            continue
        quote = " ".join(hit.text.split())
        if any(entry["quote"] == quote for entry in bucket):
            continue
        bucket.append({"page": hit.page, "quote": quote, "candidate": True})

    return {
        "name": case.name,
        "source": case.source,
        "notes": (
            "CANDIDATES ONLY — generated by the sweep and not yet reviewed. Delete what is "
            "not a real requirement, add what the sweep missed (that is the part that "
            "matters), and remove the \"candidate\" flag from what you keep. A label file "
            "that still contains candidates is rejected by `python -m evals.corpus validate`."
        ),
        "exhaustive": [],
        "expected": proposed,
    }


def unreviewed(case: CaseFiles) -> int:
    """Labels still flagged as machine-proposed.

    A corpus that accepted these would be scoring the sweep against itself.
    """
    return sum(
        1
        for items in (case.spec.get("expected") or {}).values()
        for item in items
        if item.get("candidate")
    )


# ── CLI ──────────────────────────────────────────────────────────────────


def _report_validate(cases: list[CaseFiles]) -> int:
    problems = validate(cases)
    numbers = stats(cases)
    print(f"{numbers.cases} cases · {numbers.real} real, {numbers.synthetic} synthetic · {numbers.labels} labels")
    if not problems:
        print("Labels are verbatim, on the right pages, unique, and provenance is recorded.")
        return 0
    print(f"\n{len(problems)} problem(s):", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    return 1


def _report_stats(cases: list[CaseFiles]) -> int:
    numbers = stats(cases)
    print(f"cases      {numbers.cases}  ({numbers.real} real, {numbers.synthetic} synthetic)")
    print(f"pages      {numbers.pages}")
    print(f"labels     {numbers.labels}")
    print()
    print(f"{'category':<16}{'labels':>8}{'from real':>11}")
    for kind in KINDS:
        total = numbers.by_kind.get(kind, 0)
        real = numbers.by_kind_real.get(kind, 0)
        print(f"{kind:<16}{total:>8}{real:>11}")

    gaps = coverage_gaps(cases)
    if gaps:
        print()
        print("Measured only against text we wrote ourselves:")
        for gap in gaps:
            print(f"  {gap}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "stats", "propose"])
    parser.add_argument("case", nargs="?", help="case directory name, for `propose`")
    args = parser.parse_args(argv)

    cases = load()
    if not cases:
        print("No cases found in evals/cases.", file=sys.stderr)
        return 1

    if args.command == "validate":
        return _report_validate(cases)
    if args.command == "stats":
        return _report_stats(cases)

    if not args.case:
        print("`propose` needs a case directory name.", file=sys.stderr)
        return 1
    match = next((c for c in cases if c.directory.name == args.case), None)
    if match is None:
        print(f"No case directory named {args.case!r}.", file=sys.stderr)
        return 1
    print(json.dumps(propose(match), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
