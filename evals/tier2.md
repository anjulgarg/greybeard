# Tier 2 runbook — review classification eval (harness-driven)

This runbook is **harness-agnostic**: any coding harness (Claude Code, Copilot
CLI, Cursor, Aider, a plain scripted model call, …) can execute it. It replaces
the old Python `model_provider.py` + `tier2_review_eval.py` driver — you are now
the model. Follow the steps literally and write a results file; the deterministic
scorer (`evals/runner/score.py`) does the grading.

Tier 2 exercises the **review sub-agent**: given a decision bank, an assigned
category file, and a supplied change, does the review return the right
classification?

- `VIOLATION` — a real, code-checkable break of a recorded decision.
- `ADVISORY` — the change touches a **human-attested** fact; flag to coordinate,
  never a hard violation.
- `SILENT` — no finding: conformant code, or a tombstoned/withdrawn rule.

The headline metric is the **false-alarm rate**: firing on conformant or
tombstoned cases is exactly the precision failure the product must avoid.

## Read-this-first: avoid self-judging (contamination)

If you are running inside the greybeard repo, the Greybeard skill may already be
active in your own context. That makes you a biased judge: you must classify each
case using **only** the quoted sub-agent instructions and decision text below,
**not** any Greybeard behaviour loaded into your session.

To stay honest:

- **Run each case in a clean sub-task / fresh sub-agent** with the Greybeard
  skill **not active**. Treat the instruction and decision files purely as
  **quoted input data**.
- Behave **exactly as** `subagents/review.md` dictates, using
  `references/decision-format.md` as the canonical schema and the assigned
  category file as the decisions in scope. Do not consult any other project
  knowledge.
- Decide **each case independently**. Do not let one case influence another.
- Emit **only** the findings JSON object that `subagents/review.md` specifies.
  No prose.

## Inputs (load the REAL shipped files — never a paraphrase)

| Role | Path |
| --- | --- |
| The review sub-agent instructions you follow | `skills/greybeard/subagents/review.md` |
| Canonical decision schema | `skills/greybeard/references/decision-format.md` |
| The cases | `evals/fixtures/review/cases/*.json` |
| The decision banks the cases reference | `evals/fixtures/review/<bank>/docs/greybeard/` |

Each case file looks like:

```json
{
  "id": "001",
  "bank": "bank-a",
  "category": "api-compat.md",
  "change": { "file": "...", "summary": "...", "contents": "..." },
  "expect": { "type": "VIOLATION", "decisionId": "A1" }
}
```

For a case, the **assigned category decisions** are the contents of
`evals/fixtures/review/<bank>/docs/greybeard/<category>`. **Ignore the `expect`
and `description` fields while judging** — they are the answer key for the
scorer. Judge only the `change` against the category decisions.

## Task

For **every** case file in `evals/fixtures/review/cases/`, acting as the review
sub-agent over the assigned category file and the supplied `change`, produce the
findings object exactly as `subagents/review.md` specifies.

## Output

Write the results to `evals/out/tier2-results.json` (create `evals/out/` if it
does not exist). Use exactly this shape — one entry per case, carrying the raw
`findings` array the sub-agent produced:

```json
{
  "harness": "<the harness you ran this with>",
  "model": "<the model identity>",
  "date": "<YYYY-MM-DD>",
  "results": [
    {"id": "001", "findings": [{"type": "VIOLATION", "decisionId": "A1"}]},
    {"id": "002", "findings": []},
    {"id": "003", "findings": []},
    {"id": "004", "findings": [{"type": "ADVISORY", "decisionId": "A2"}]}
  ]
}
```

- Include all cases, keyed by `id`. An empty `findings` array means `SILENT`.
- Keep the `findings` shape that `subagents/review.md` defines. The scorer
  collapses it to the highest-severity label (`VIOLATION` > `ADVISORY` >
  `SILENT`), so emitting the real sub-agent output keeps the eval faithful.
- The `harness` / `model` / `date` stamp is **required** — it records *what*
  produced this run so two baselines are comparable.

## Score it

```bash
python evals/runner/score.py            # prints Tier 1 + Tier 2 metrics
python evals/runner/score.py --update-baseline   # also refresh baselines/metrics.json
```

Tier 2 is **advisory**, not a CI gate: only Tier 0 gates CI. Because a
conversational harness is less deterministic than a fixed-temperature API call,
expect small run-to-run wobble — a single-case difference against the baseline is
noise, not a regression.
