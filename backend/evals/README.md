# Extraction evaluation

Margin claims that nothing gets missed. This is where that claim is measured.

Every case here is a document whose contents are known, labelled by category.
The harness runs the deterministic sweep (`app/pipeline/sweep.py`) over each
one and reports recall per category. `--gate` makes it a build failure when
recall drops below the floors in `thresholds.json`.

```
python -m evals.harness                      # score and print
python -m evals.harness --gate               # non-zero exit on regression
python -m evals.harness --json recall.json   # machine-readable result
```

## Why only the deterministic layer is gated

It is repeatable, so a change in the number is a real change rather than
sampling noise; it needs no API keys, so it runs on every pull request instead
of nightly and unwatched; and it is the floor the model layer sits on, so a
regression here moves everything above it.

Model-based extraction needs measuring too and cannot be measured this way.
That belongs in a separate, non-gating online evaluation over the same cases —
`load_cases()` is shared so the corpus is written once.

## The corpus

The three cases shipped here are **synthetic**: written by hand against the
conventions of real solicitations (uniform contract format, municipal RFP,
attachment package), not extracted from real ones. They are a floor, not a
substitute. Real labelled solicitations should be added as they become
available, and the format does not change when they are.

Each case is a directory:

```
cases/<name>/document.txt    # pages separated by form feed (\f)
cases/<name>/labels.json
```

```json
{
  "name": "Federal RFP — Sections A through M",
  "source": "synthetic | real",
  "notes": "what this case is for, and anything unusual about it",
  "exhaustive": ["limit", "form"],
  "expected": {
    "limit": [{ "page": 3, "quote": "shall not exceed 40 pages" }]
  }
}
```

**Label quotes must be verbatim from the document.** Matching is containment
either way, so a label carrying words the document does not have fails the
extraction rather than testing it.

`exhaustive` lists categories where the labels record *every* instance, so
precision is meaningful there. Elsewhere only recall is measured: a sweep tuned
for recall will always fire on text nobody bothered to label, and counting that
as a false positive would push the patterns toward missing things.

## Thresholds

Floors, not targets. Set them from measured performance and raise them
deliberately. **Never lower a floor to make a build pass** — a drop means the
extraction got worse and the corpus is telling you so. The right response is to
fix the pattern or, if the label was wrong, fix the label and say so in `notes`.
