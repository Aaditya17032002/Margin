# Evaluation

Margin claims that nothing gets missed. This is where that claim is measured,
and where it is kept honest about how much it currently proves.

```
python -m evals.harness                      # score and print
python -m evals.harness --gate               # non-zero exit on regression
python -m evals.harness --json recall.json   # machine-readable result

python -m evals.corpus validate              # are the labels sound?
python -m evals.corpus stats                 # what does the corpus cover?
python -m evals.corpus propose <case>        # candidate labels from the sweep

python -m evals.ingest add <file> ...        # add a real solicitation as a case
```

## The state of this corpus

**Every case here is synthetic.** They were written by hand against the
conventions of real solicitations — uniform contract format, a municipal RFP
with different vocabulary, an attachment package — not extracted from real
ones. The harness says so on every run, and it should keep saying so until that
changes.

This matters more than it sounds. A synthetic case is written by the same
people who wrote the patterns, to the same assumptions, which is the one thing
an evaluation cannot test. **Treat these numbers as a regression alarm, not as
evidence of real-world recall.** They will tell you when the sweep got worse.
They will not tell you how much it finds in a document nobody here wrote.

Real cases are the P0 gap. The tooling below exists so adding them is an
afternoon rather than a project.

## Adding a real solicitation

```
python -m evals.ingest add ~/downloads/12314424R0012.pdf \
    --name "USDA FNS — SNAP EBT modernisation" \
    --solicitation 12314424R0012 \
    --agency "USDA Food and Nutrition Service" \
    --from "https://sam.gov/opp/…" \
    --licence "US Government work, public domain"
```

That extracts the text, records provenance and a checksum, keeps the original
beside the extract, and writes a labels file pre-filled with candidates from
the sweep.

Then do the part that cannot be automated:

1. **Delete** every candidate that is not really a requirement of that
   category.
2. **Add what the sweep missed.** This is the only part that tests anything.
   Candidates come from the sweep, so a case built only from them scores the
   sweep against its own output and reports 100% forever.
3. Remove the `"candidate": true` flag from each label you keep. A corpus that
   still contains candidates is rejected — by `evals.corpus validate` and by
   `--gate`.
4. List any category where you labelled *every* instance in `exhaustive`, so
   precision is measured there too.
5. `python -m evals.corpus validate`

Budget roughly an hour per document for a careful pass, and label documents you
did not write the patterns against — that is where the interesting misses are.

### Where to get them

`sam.gov` publishes federal solicitations and their attachments; most are US
Government works and redistributable. State and municipal portals vary, and
`--licence` exists to record what you found out. Use `--no-original` when the
source file cannot be kept in the repository; the extracted text and the
checksum still make the case reproducible.

## Turning on the real-document floors

`thresholds.json` carries two floors that are `null` until there is something
to apply them to:

```json
"realRecall": null,
"minimumRealCases": null
```

Once real cases exist, set `minimumRealCases` first — so nobody can delete
them and keep a green build — then set `realRecall` from what the corpus
actually achieves. **Never above what it achieves, and never lowered
afterwards.** Until they are set, synthetic cases hold the gate up on their
own, which the harness warns about on every run.

## Why only the deterministic layer is gated

It is repeatable, so a change in the number is a real change rather than
sampling noise; it needs no API keys, so it runs on every pull request instead
of nightly and unwatched; and it is the floor the model layer sits on, so a
regression here moves everything above it.

The model layer is measured separately, in `evals/adjudication.py` — see
[`ADJUDICATION.md`](ADJUDICATION.md).

## Case format

```
cases/<name>/document.txt     # pages separated by form feed (\f)
cases/<name>/original.pdf     # the source file, when it can be kept
cases/<name>/labels.json
```

```json
{
  "name": "Federal RFP — Sections A through M",
  "source": "synthetic | real",
  "notes": "what this case is for, and anything unusual about it",
  "provenance": {
    "solicitationNumber": "12314424R0012",
    "agency": "USDA Food and Nutrition Service",
    "retrievedFrom": "https://sam.gov/opp/…",
    "retrievedAt": "2026-05-01",
    "licence": "US Government work, public domain",
    "checksum": "a1b2c3d4e5f60718"
  },
  "exhaustive": ["limit", "form"],
  "expected": {
    "limit": [{ "page": 3, "quote": "shall not exceed 40 pages" }]
  }
}
```

`provenance` is required on real cases and checked. The `checksum` is of the
*extracted text*, not the source file: labels carry page numbers, pages come
from extraction, and if that output changes then every page number in the file
is a guess. Validation says so rather than letting the case rot quietly.

**Label quotes must be verbatim.** Matching is containment either way, so a
label carrying words the document does not have fails the extraction rather
than testing it. `evals.corpus validate` checks every quote against the page it
claims, and names the page it actually appears on when it is somewhere else.

`exhaustive` lists categories where the labels record *every* instance, so
precision is meaningful there. Elsewhere only recall is measured: a sweep tuned
for recall will always fire on text nobody bothered to label, and counting that
as a false positive would push the patterns toward missing things.

## Thresholds

Floors, not targets. Set them from measured performance and raise them
deliberately. **Never lower a floor to make a build pass** — a drop means the
extraction got worse and the corpus is telling you so. The right response is to
fix the pattern or, if the label was wrong, fix the label and say so in `notes`.
