"""Turning a real solicitation into an evaluation case.

Adding a case by hand means copying a file, writing a JSON skeleton,
remembering to record where the document came from, and then producing labels
without accidentally retyping a quote wrong. Every one of those steps has a way
to go quietly wrong, so they are one command.

    python -m evals.ingest add path/to/rfp.pdf \
        --name "USDA FNS — SNAP EBT modernisation" \
        --solicitation 12314424R0012 \
        --agency "USDA Food and Nutrition Service" \
        --from "https://sam.gov/opp/..." \
        --licence "US Government work, public domain"

It extracts the text, records the provenance and a checksum of exactly what was
extracted, and writes a labels file pre-filled with candidates from the sweep
for a person to cut down. Nothing it writes is a finished case: the labels
arrive flagged `candidate`, and `evals.corpus validate` refuses a corpus that
still contains them.

**The labels are the work, and they cannot be automated.** Candidates come from
the sweep, so accepting them wholesale would score the sweep against its own
output and report 100% forever. The value of a case is in what a person deletes
and — far more importantly — in what they *add* that the sweep never found.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.pipeline.extract import PAGE_SEP, extract_text

CASES_DIR = Path(__file__).parent / "cases"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "case"


def add(
    source_path: Path,
    *,
    name: str,
    solicitation: str,
    agency: str,
    retrieved_from: str,
    licence: str = "",
    slug: str = "",
    notes: str = "",
    keep_original: bool = True,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    content = source_path.read_bytes()
    text = extract_text(content, source_path.name)
    if not text.strip():
        # A scanned PDF with no text layer produces an empty case that reads as
        # a total extraction failure on every category. Better to refuse it and
        # say why.
        raise ValueError(
            f"No text could be extracted from {source_path.name}. It is probably a scan with no "
            "text layer — run it through OCR first, or the case will report zero recall on a "
            "document nothing could read."
        )

    directory = CASES_DIR / (slug or slugify(name))
    directory.mkdir(parents=True, exist_ok=True)
    document = directory / "document.txt"
    document.write_text(text)

    if keep_original:
        # Kept beside the extract so a later parser change can be diffed
        # against the same input rather than against a memory of it.
        shutil.copy2(source_path, directory / f"original{source_path.suffix}")

    from evals.corpus import CaseFiles, propose

    case = CaseFiles(directory=directory, text=text, spec={"name": name, "source": "real"})
    labels = propose(case)
    labels["provenance"] = {
        "solicitationNumber": solicitation,
        "agency": agency,
        "retrievedFrom": retrieved_from,
        "retrievedAt": datetime.now(UTC).date().isoformat(),
        "originalFile": source_path.name,
        "licence": licence,
        # Of the extracted text, not of the original file: the labels carry
        # page numbers, and pages come from extraction. If that output changes,
        # every page number in the file is a guess and validation says so.
        "checksum": case.checksum(),
    }
    if notes:
        labels["notes"] = f"{notes}\n\n{labels['notes']}"

    (directory / "labels.json").write_text(json.dumps(labels, indent=2) + "\n")

    pages = text.count(PAGE_SEP) + 1
    candidates = sum(len(items) for items in labels["expected"].values())
    print(f"Wrote {directory}")
    print(f"  {pages} pages, {candidates} candidate labels across {len(labels['expected'])} categories")
    print()
    print("Next, and this is the part that matters:")
    print(f"  1. Open {directory / 'labels.json'}")
    print("  2. Delete every candidate that is not really a requirement of that category.")
    print("  3. Add what the sweep missed. This is the only part that tests anything —")
    print("     candidates come from the sweep, so a case built only from them scores")
    print("     the sweep against its own output.")
    print("  4. Remove the \"candidate\": true flag from each label you keep.")
    print("  5. List any category where you labelled *every* instance in \"exhaustive\".")
    print("  6. Run: python -m evals.corpus validate")
    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="add a real solicitation as an evaluation case")
    add_parser.add_argument("path", type=Path)
    add_parser.add_argument("--name", required=True, help="how the case is described in reports")
    add_parser.add_argument("--solicitation", required=True, help="the solicitation number")
    add_parser.add_argument("--agency", required=True)
    add_parser.add_argument("--from", dest="retrieved_from", required=True, help="URL or system it came from")
    add_parser.add_argument("--licence", default="", help="redistribution status, if it is not a US Government work")
    add_parser.add_argument("--slug", default="", help="directory name; derived from --name otherwise")
    add_parser.add_argument("--notes", default="", help="what this case is for, and anything unusual about it")
    add_parser.add_argument(
        "--no-original",
        action="store_true",
        help="do not keep a copy of the source file (use when it cannot be redistributed)",
    )

    args = parser.parse_args(argv)
    try:
        add(
            args.path,
            name=args.name,
            solicitation=args.solicitation,
            agency=args.agency,
            retrieved_from=args.retrieved_from,
            licence=args.licence,
            slug=args.slug,
            notes=args.notes,
            keep_original=not args.no_original,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
