"""Measuring the substantive layer — the half a recall number cannot reach.

`evals/harness.py` scores the deterministic sweep: does the extraction find the
requirement at all. This scores what happens next, and it is a different
question with a different failure mode. Given a requirement and the passages a
retriever put in front of it, does the model reach the verdict a careful
reviewer would?

**The two errors are not symmetric, and the score must not treat them as if
they were.**

A wrong `satisfied` ships a compliant-looking response with a hole in it. It is
the single most expensive output this product can produce, it is invisible
until a debrief, and no amount of correct verdicts elsewhere compensates for
one. A wrong `unverifiable` costs a person five minutes.

So accuracy is reported, and then largely ignored. The number that gates is
**false-satisfied**: cases the reviewer would not have cleared and the model
did. A model can be wrong on half the corpus and still be safe to ship if it is
wrong in the direction of asking for help.

Alongside those, three properties of the plumbing are checked, and they hold
without any model at all:

* a verdict outside the allowed set becomes `unverifiable` rather than passing
  through;
* a quote the model produced that is not in the passages downgrades the claim
  resting on it;
* a mandatory requirement is never *cleared*, whatever the verdict.

    python -m evals.adjudication.runner              # offline, deterministic
    python -m evals.adjudication.runner --gate       # non-zero on regression
    python -m evals.adjudication.runner --live       # against the real model
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from app.pipeline.corpus import build_corpus
from app.pipeline.requirements import stable_key
from app.pipeline.traceability import SATISFIED, trace_response

CASES_PATH = Path(__file__).parent / "cases.json"
THRESHOLDS_PATH = Path(__file__).parent / "thresholds.json"

#: The verdicts that mean "this is answered". A wrong verdict *into* this set
#: is the dangerous direction; a wrong verdict out of it is the cheap one.
CLEARING = {SATISFIED}


@dataclass
class CaseResult:
    id: str
    why: str
    stakes: str
    expected: str
    acceptable: list[str]
    actual: str
    #: Exactly right.
    correct: bool
    #: Wrong, but wrong in a direction that sends a person to look.
    tolerable: bool
    #: Wrong in the direction that ships a gap. This is the number that matters.
    false_satisfied: bool
    detail: str = ""
    needs_confirmation: bool = False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "stakes": self.stakes,
            "expected": self.expected,
            "actual": self.actual,
            "correct": self.correct,
            "tolerable": self.tolerable,
            "falseSatisfied": self.false_satisfied,
            "needsConfirmation": self.needs_confirmation,
            "detail": self.detail[:200],
        }


@dataclass
class Summary:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def correct(self) -> int:
        return sum(1 for r in self.results if r.correct)

    @property
    def safe(self) -> int:
        """Right, or wrong in the direction that asks for help."""
        return sum(1 for r in self.results if r.correct or r.tolerable)

    @property
    def false_satisfied(self) -> list[CaseResult]:
        return [r for r in self.results if r.false_satisfied]

    @property
    def mandatory_cleared(self) -> list[CaseResult]:
        """Mandatory requirements the engine reported as settled.

        Should always be empty: a `satisfied` verdict on a disqualifying
        requirement is stored awaiting a signature, never as a clearance.
        """
        return [
            r
            for r in self.results
            if r.stakes == "disqualifying" and r.actual in CLEARING and not r.needs_confirmation
        ]

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.correct / self.total, 4) if self.total else 1.0,
            "safe": self.safe,
            "safeRate": round(self.safe / self.total, 4) if self.total else 1.0,
            "falseSatisfied": len(self.false_satisfied),
            "falseSatisfiedRate": round(len(self.false_satisfied) / self.total, 4) if self.total else 0.0,
            "mandatoryClearedWithoutSignature": len(self.mandatory_cleared),
            "cases": [r.as_dict() for r in self.results],
        }


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text())["cases"]


def load_thresholds() -> dict:
    if THRESHOLDS_PATH.exists():
        return json.loads(THRESHOLDS_PATH.read_text())
    return {}


class ScriptedModel:
    """A stand-in that answers with one fixed reply, for running in CI.

    It is not a model and does not pretend to be one. Its job is to prove the
    machinery around the model behaves — that the rubric's output is parsed,
    that an unknown verdict is refused, that an ungrounded quote downgrades the
    claim, that a mandatory requirement is never cleared. Those hold whatever
    the model says, and they are the parts that must never regress silently.

    One model per case rather than one keyed by prompt text: two cases in this
    corpus deliberately share a requirement and differ only in the response, so
    matching on the prompt let one answer silently overwrite the other.

    ``reply`` is the raw string the model would return, so a test can hand it
    malformed output and see what survives.
    """

    def __init__(self, reply: str):
        self.reply = reply
        self.seen: list[str] = []

    async def complete(self, messages, **kwargs) -> str:
        self.seen.append(messages[-1]["content"])
        return self.reply


def _requirement(case: dict):
    """A requirement-shaped object, without a database behind it."""
    return SimpleNamespace(
        id=f"req_{case['id']}",
        key=stable_key(case["requirement"]),
        reference=case["reference"],
        text=case["requirement"],
        stakes=case["stakes"],
        verification="substantive",
        state="open",
        owner=None,
    )


def _response(case: dict):
    return build_corpus(
        [
            SimpleNamespace(
                id=f"d_{case['id']}",
                file_name="response.pdf",
                doc_kind="response",
                version=1,
                raw_text="\f".join(case["passages"]),
            )
        ],
        include_response=True,
    )


async def score(cases: list[dict], model_for) -> Summary:
    """`model_for(case)` supplies the model for one case.

    A callable rather than a single model because the scripted run needs a
    different scripted answer per case, and the live run does not care.
    """
    summary = Summary()
    for case in cases:
        traces = await trace_response([_requirement(case)], _response(case), llm=model_for(case))
        trace = traces[0]

        expected = case["expected"]
        acceptable = set(case.get("acceptable") or [])
        correct = trace.status == expected
        tolerable = (not correct) and trace.status in acceptable

        # The error that matters: the reviewer would not have cleared it and
        # the model did. A verdict that merely disagrees in the cautious
        # direction is not this.
        false_satisfied = trace.status in CLEARING and expected not in CLEARING

        summary.results.append(
            CaseResult(
                id=case["id"],
                why=case.get("why", ""),
                stakes=case["stakes"],
                expected=expected,
                acceptable=sorted(acceptable),
                actual=trace.status,
                correct=correct,
                tolerable=tolerable,
                false_satisfied=false_satisfied,
                detail=trace.detail,
                needs_confirmation=trace.needs_confirmation,
            )
        )
    return summary


def check(summary: Summary, thresholds: dict) -> list[str]:
    failures: list[str] = []

    ceiling = thresholds.get("maxFalseSatisfied")
    if ceiling is not None and len(summary.false_satisfied) > ceiling:
        names = ", ".join(r.id for r in summary.false_satisfied)
        failures.append(
            f"false-satisfied: {len(summary.false_satisfied)} case(s) cleared that a reviewer "
            f"would not have ({names}); ceiling is {ceiling}"
        )

    floor = thresholds.get("minSafeRate")
    if floor is not None and summary.total:
        rate = summary.safe / summary.total
        if rate + 1e-9 < floor:
            failures.append(f"safe rate {rate:.1%} below floor {floor:.0%}")

    accuracy_floor = thresholds.get("minAccuracy")
    if accuracy_floor is not None and summary.total:
        accuracy = summary.correct / summary.total
        if accuracy + 1e-9 < accuracy_floor:
            failures.append(f"accuracy {accuracy:.1%} below floor {accuracy_floor:.0%}")

    if summary.mandatory_cleared:
        # Not a threshold. This is an invariant, and a build where it fails is
        # broken rather than underperforming.
        names = ", ".join(r.id for r in summary.mandatory_cleared)
        failures.append(
            f"a mandatory requirement was reported as settled without a signature ({names}). "
            "This is an invariant, not a score."
        )
    return failures


def report(summary: Summary, thresholds: dict, *, live: bool) -> str:
    lines = [
        "",
        f"Response adjudication — {'live model' if live else 'scripted, offline'}",
        "=" * 78,
        f"{'case':<38}{'expected':>13}{'actual':>14}{'':>4}",
    ]
    for result in summary.results:
        mark = "ok" if result.correct else ("~" if result.tolerable else "!!")
        lines.append(f"{result.id:<38}{result.expected:>13}{result.actual:>14}{mark:>4}")
    lines.append("-" * 78)
    lines.append(
        f"exactly right      {summary.correct}/{summary.total}"
        f"   ({summary.correct / summary.total:.0%})" if summary.total else "no cases"
    )
    lines.append(
        f"right or cautious  {summary.safe}/{summary.total}"
        f"   ({summary.safe / summary.total:.0%})" if summary.total else ""
    )
    lines.append(
        f"cleared wrongly    {len(summary.false_satisfied)}"
        f"   (ceiling {thresholds.get('maxFalseSatisfied', '—')})"
    )
    if summary.false_satisfied:
        lines += ["", "Cleared something a reviewer would not have:"]
        for result in summary.false_satisfied:
            lines.append(f"  {result.id} — expected {result.expected}")
            lines.append(f"    {result.why}")
    return "\n".join(lines)


def _live_model():
    from app.core.config import get_settings

    settings = get_settings()
    if settings.PROVIDER_MODE != "azure" or not settings.AZURE_OPENAI_API_KEY:
        raise RuntimeError(
            "--live needs PROVIDER_MODE=azure and Azure OpenAI credentials. Without them "
            "there is no model to measure, and running the scripted path and calling it "
            "live would be worse than not running it."
        )
    from app.providers.factory import get_llm_provider

    return get_llm_provider()


def scripted_model_for(case: dict) -> ScriptedModel:
    """The *correct* verdict for this case, returned verbatim.

    Deliberately correct: an offline run that failed on judgement would be
    testing this function rather than the product. What it measures is whether
    a right answer survives the journey through parsing, grounding and the
    confirmation rule — and whether the retrieval in front of the model ever
    let the model see the passage at all.
    """
    return ScriptedModel(
        json.dumps(
            {
                "status": case["expected"],
                "detail": "Scripted answer for the offline run.",
                "gap": "" if case["expected"] == SATISFIED else "Stated in the requirement.",
                "quote": case["passages"][0][:120],
            }
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true", help="exit non-zero when a floor is missed")
    parser.add_argument("--live", action="store_true", help="run against the configured model")
    parser.add_argument("--json", dest="json_path", help="write the full result to this path")
    args = parser.parse_args(argv)

    cases = load_cases()
    thresholds = load_thresholds()

    if args.live:
        try:
            live = _live_model()
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        model_for = lambda _case: live  # noqa: E731 — one line, one meaning
        floors = thresholds.get("live", {})
    else:
        model_for = scripted_model_for
        floors = thresholds.get("scripted", {})

    summary = asyncio.run(score(cases, model_for))
    print(report(summary, floors, live=args.live))

    if not args.live:
        print(
            "\nThis run used a scripted model. It proves the machinery around the model — "
            "\nparsing, grounding, the refusal to clear a mandatory requirement — and says "
            "\nnothing about how a real model judges. Run with --live for that.",
            file=sys.stderr,
        )

    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps({"live": args.live, "summary": summary.as_dict(), "thresholds": floors}, indent=2)
        )

    failures = check(summary, floors)
    if failures:
        print("\nAdjudication regression:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        if args.gate:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
