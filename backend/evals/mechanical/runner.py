"""Measuring the rules that decide compliance without a model.

These rules are the reason mechanical compliance is trustworthy, and they are
also the easiest part of the system to break by accident: a pattern widened to
catch one phrasing starts firing on a sentence that merely mentions pages, and
a compliance matrix fills with checks nobody asked for.

So each case names one requirement, one response, and the verdict the rule
should reach — including the cases where the right answer is *no rule at all*.
Two failure modes are gated separately, because they are not the same mistake:

**Wrong verdicts** are a rule that got the answer wrong. A `satisfied` on a
response that does not comply is the worst of them.

**Spurious rules** are a rule firing on a requirement it has no business
judging. Every one of those is a row in somebody's compliance matrix that
wastes their afternoon, and enough of them make the mechanical layer something
people learn to ignore.

    python -m evals.mechanical.runner
    python -m evals.mechanical.runner --gate
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from app.pipeline.corpus import build_corpus
from app.pipeline.mechanical import check, check_all

CASES_PATH = Path(__file__).parent / "cases.json"


@dataclass
class Result:
    id: str
    why: str
    expected: str | None
    actual: str | None
    expected_rule: str | None
    actual_rule: str | None
    also: list[str] = field(default_factory=list)
    missing_also: list[str] = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return self.actual == self.expected and not self.missing_also

    @property
    def spurious(self) -> bool:
        """A rule fired on a requirement it should have left alone."""
        return self.expected is None and self.actual is not None

    @property
    def silent(self) -> bool:
        """No rule fired on a requirement that carries one."""
        return self.expected is not None and self.actual is None

    @property
    def wrong_rule(self) -> bool:
        return (
            self.expected is not None
            and self.actual is not None
            and self.expected_rule is not None
            and self.actual_rule != self.expected_rule
        )


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text())["cases"]


def _response(case: dict):
    """The response as the case describes it: page texts, or filler pages."""
    texts = case.get("pageTexts")
    if not texts:
        texts = [f"Section {i}. Narrative content." for i in range(1, int(case.get("pages", 1)) + 1)]
    return build_corpus(
        [
            SimpleNamespace(
                id="d_case",
                file_name=(case.get("files") or ["response.pdf"])[0],
                doc_kind="response",
                version=1,
                raw_text="\f".join(texts),
            )
        ],
        include_response=True,
    )


def score(cases: list[dict]) -> list[Result]:
    results: list[Result] = []
    for case in cases:
        response = _response(case)
        files = case.get("files") or []
        verdict = check(case["requirement"], response, file_names=files)
        every = check_all(case["requirement"], response, file_names=files)
        fired = [c.rule for c in every]

        expected_also = case.get("alsoRules") or []
        results.append(
            Result(
                id=case["id"],
                why=case.get("why", ""),
                expected=case.get("expected"),
                actual=verdict.status if verdict else None,
                expected_rule=case.get("rule"),
                actual_rule=verdict.rule if verdict else None,
                also=fired,
                missing_also=[rule for rule in expected_also if rule not in fired],
            )
        )
    return results


def check_results(results: list[Result]) -> list[str]:
    failures: list[str] = []

    wrong = [r for r in results if not r.correct and not r.spurious and not r.silent]
    for result in wrong:
        failures.append(f"{result.id}: expected {result.expected}, got {result.actual}")

    for result in [r for r in results if r.spurious]:
        failures.append(
            f"{result.id}: the {result.actual_rule} rule fired on a requirement it should not "
            "judge — every one of these is a row that wastes somebody's afternoon"
        )
    for result in [r for r in results if r.silent]:
        failures.append(
            f"{result.id}: no rule fired, so this went to the model — a countable rule judged "
            "by a model is a countable rule that can be wrong"
        )
    for result in [r for r in results if r.wrong_rule]:
        failures.append(
            f"{result.id}: right verdict from the wrong rule ({result.actual_rule}, "
            f"expected {result.expected_rule})"
        )
    for result in [r for r in results if r.missing_also]:
        failures.append(
            f"{result.id}: a compound requirement did not produce {', '.join(result.missing_also)} — "
            "reporting only the first rule is how a response passes a page count and fails on a font"
        )
    return failures


def report(results: list[Result]) -> str:
    lines = ["", "Mechanical rules", "=" * 74, f"{'case':<46}{'expected':>13}{'actual':>13}"]
    for result in results:
        mark = "" if result.correct else "  !!"
        lines.append(
            f"{result.id:<46}{str(result.expected):>13}{str(result.actual):>13}{mark}"
        )
    lines.append("-" * 74)
    correct = sum(1 for r in results if r.correct)
    lines.append(f"{correct}/{len(results)} correct")
    if any(r.spurious for r in results):
        lines.append(f"{sum(1 for r in results if r.spurious)} rule(s) fired where none should")
    if any(r.silent for r in results):
        lines.append(f"{sum(1 for r in results if r.silent)} requirement(s) fell through to the model")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args(argv)

    cases = load_cases()
    results = score(cases)
    print(report(results))

    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps([r.__dict__ for r in results], indent=2, default=str)
        )

    failures = check_results(results)
    if failures:
        print("\nMechanical rule regression:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        if args.gate:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
