# Adjudication evaluation

`evals/harness.py` measures whether the extraction *finds* a requirement.
This measures what happens next: given a requirement and the passages a
retriever put in front of it, does the model reach the verdict a careful
reviewer would?

```
python -m evals.adjudication.runner           # offline, deterministic
python -m evals.adjudication.runner --gate    # non-zero on regression
python -m evals.adjudication.runner --live    # against the configured model
```

## The two errors are not symmetric

A wrong `satisfied` ships a compliant-looking response with a hole in it. It is
invisible until a debrief, and no number of correct verdicts elsewhere
compensates for one. A wrong `unverifiable` costs a person five minutes.

So the score reports accuracy and then largely ignores it. The number that
gates is **false-satisfied**: cases the reviewer would not have cleared and the
model did. `maxFalseSatisfied` is `0`, because there is no defensible non-zero
value for shipping a gap — raise it only with a written reason.

A model can be wrong on half this corpus and still be safe to ship, if it is
wrong in the direction of asking for help. `minSafeRate` measures that: right,
or wrong toward caution.

## The corpus

Twelve cases in `cases.json`, chosen for the ways a plausible answer is wrong
rather than for coverage:

- a plain answer, so a rubric that is merely timid fails too;
- text *about* the right subject that answers none of it;
- half of a two-part requirement;
- "we will comply with Section C.9", which restates and answers nothing;
- a near-miss (Secret where the requirement says Top Secret);
- a prohibition the response describes violating;
- an answer that points at another volume the model cannot see;
- a commitment made conditional on something the agency has not agreed to;
- an answer split across two retrieved passages;
- reused boilerplate that names the wrong agency;
- a quantified requirement met with an unquantified claim.

Each carries a `why`. A case nobody can explain is a case nobody will maintain.

`expected` is the verdict a careful reviewer would reach. `acceptable` lists
verdicts that are wrong but not dangerous — nearly always `unverifiable`. A
case with an empty `acceptable` admits no second-best answer.

## The two runs

**Scripted** (`--gate` in CI) answers every case correctly by construction, so
it measures nothing about judgement and everything about the machinery: that a
verdict outside the rubric never becomes a clearance, that an ungrounded quote
downgrades the claim resting on it, that a mandatory requirement is never
reported as settled, and that retrieval actually put the passage in front of
the model. Its floors are 100%, because a failure there is a bug rather than a
bad day.

Writing it this way earned its keep immediately. The first scripted run failed
three cases, and both causes were real:

- a scripted answer keyed by prompt text let one case silently overwrite
  another that shared its requirement;
- **the rubric had no way to say `failed`.** A response contradicting a
  requirement — Secret against Top Secret, business hours against 24x7, storage
  abroad against a CONUS-only clause — came back as `unverifiable`, burying a
  hard failure in the pile of things to check. A contradiction is a rewrite; an
  absence is a blank page, and they are different work. The rubric now
  distinguishes them.

**Live** (`--live`) needs `PROVIDER_MODE=azure` and Azure OpenAI credentials.
It refuses to run without them rather than falling back to the scripted path
and calling the result live.

## Before trusting the live floors

`live.minSafeRate` and `live.minAccuracy` are placeholders set from judgement,
not from measurement. Run `--live --json` once against the model you intend to
ship, read the failures case by case, and set the floors from what it actually
achieves. `maxFalseSatisfied` is the exception: it is `0` on principle and not
derived from a run.

Nothing in this corpus is a real proposal. The passages are written to be
adversarial, which is the right shape for catching rubric failures and the
wrong shape for estimating field accuracy. Add real requirement/response pairs
as they become available — the format does not change.
