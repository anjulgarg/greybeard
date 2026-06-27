# Tier 1 runbook — candidate-bar eval (harness-driven)

This runbook is **harness-agnostic**: any coding harness (Claude Code, Copilot
CLI, Cursor, Aider, a plain scripted model call, …) can execute it. It replaces
the old Python `model_provider.py` + `tier1_candidate_eval.py` driver — you are
now the model. Follow the steps literally and write a results file; the
deterministic scorer (`evals/runner/score.py`) does the grading.

Tier 1 exercises the **shared candidate bar**: given one comment / PR-description
point / attested fact, does the skill correctly `accept` or `drop` it, and if
accepted, route it as `code-checkable` vs `human-attested`? The product promise
is **precision over recall** — prefer dropping a borderline item to accepting a
wrong one.

## Read-this-first: avoid self-judging (contamination)

If you are running inside the greybeard repo, the Greybeard skill may already be
active in your own context. That makes you a biased judge: you must classify each
case using **only** the quoted rule text below, **not** any Greybeard behaviour
loaded into your session.

To stay honest:

- **Run each case in a clean sub-task / fresh sub-agent** with the Greybeard
  skill **not active**. Treat the rule files purely as **quoted input data**.
- Judge **using ONLY** `references/decision-candidate.md` (the bar) and the
  routing vocabulary in `references/decision-format.md`. Do not consult any other
  project knowledge.
- Decide **each case independently**. Do not let one case's verdict influence
  another — no shared running commentary, no "as before".
- Emit **only** the verdict JSON for each case. No prose, no explanation.

## Inputs (load the REAL shipped files — never a paraphrase)

| Role | Path |
| --- | --- |
| The candidate bar (the rules you apply) | `skills/greybeard/references/decision-candidate.md` |
| Routing vocabulary (`code-checkable` / `human-attested`) | `skills/greybeard/references/decision-format.md` |
| The cases to classify | `evals/fixtures/candidate/cases.jsonl` |

`cases.jsonl` has one JSON object per line:

```json
{"id": "c01", "item": "<the candidate text>", "context": "<surrounding context>", "expect": {...}, "note": "..."}
```

**Ignore the `expect` and `note` fields while judging** — they are the answer key
for the scorer. Judge only from `item` + `context` against the rules.

## Task

For **every** line in `cases.jsonl`, applying the bar strictly:

1. Decide a `verdict`: `"accept"` or `"drop"`.
2. Decide a `route`:
   - if `verdict` is `"accept"`: `"code-checkable"` or `"human-attested"`
     (per the routing vocabulary in `decision-format.md`);
   - if `verdict` is `"drop"`: always `"none"`.

## Output

Write the results to `evals/out/tier1-results.json` (create `evals/out/` if it
does not exist). Use exactly this shape:

```json
{
  "harness": "<the harness you ran this with, e.g. claude-code / copilot-cli>",
  "model": "<the model identity, e.g. claude-sonnet-4.5>",
  "date": "<YYYY-MM-DD>",
  "results": [
    {"id": "c01", "verdict": "accept", "route": "code-checkable"},
    {"id": "c02", "verdict": "accept", "route": "human-attested"},
    {"id": "c03", "verdict": "drop", "route": "none"}
  ]
}
```

- One entry per case, keyed by the case `id`. Include all 12 cases.
- The `harness` / `model` / `date` stamp is **required** — it records *what*
  produced this run so two baselines are comparable.

## Score it

```bash
python evals/runner/score.py            # prints Tier 1 + Tier 2 metrics
python evals/runner/score.py --update-baseline   # also refresh baselines/metrics.json
```

The headline number is the **false-alarm rate** (accepting an item that should
have been dropped). Tier 1 is **advisory**, not a CI gate: only Tier 0 gates CI.
Because a conversational harness is less deterministic than a fixed-temperature
API call, expect small run-to-run wobble — a single-case difference against the
baseline is noise, not a regression.
