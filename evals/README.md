# Greybeard evaluation harness

This harness measures whether the Greybeard skill stays **precise** as its prompts,
workflows, sub-agent instructions, and decision formats evolve. The product promise
is **precision over recall**, so the harness measures false alarms explicitly, not
just how many valid issues Greybeard catches.

Every tier exercises the **real shipped skill files** from `skills/greybeard/` —
never a paraphrased copy. If an eval used a shadow prompt it could pass while the
shipped skill regressed.

## Tiers (MVP)

| Tier | What it checks | How it runs | Headline signal |
| --- | --- | --- | --- |
| **Tier 0** | Format linter: `docs/greybeard/` banks against `decision-format.md` | Python (deterministic) | Structural drift / pass-fail |
| **Tier 1** | Candidate bar: one item → `accept`/`drop` + routing, per `decision-candidate.md` | **Your code harness** | False-alarm rate, then recall |
| **Tier 2** | Review classification: change → `VIOLATION`/`ADVISORY`/`SILENT` | **Your code harness** | False-alarm rate (firing on conformant/tombstoned) |

`remember` has no dedicated tier in the MVP: its acceptance gate shares the same
`decision-candidate.md` rules that Tier 1 exercises directly. Full `learn`
extraction eval is deferred (see `fixtures/learn/README.md`).

## How the LLM tiers run: bring your own harness

Tiers 1 and 2 are **harness-driven and harness-agnostic**. There is no built-in
model provider and no API key to configure — the coding harness you already use
(Claude Code, Copilot CLI, Cursor, Aider, a scripted model call, …) **is** the
judge. You point your harness at a runbook; it writes a results file; a small
deterministic Python scorer grades it.

1. **Run the runbook with any harness.** Open a task in your harness and have it
   follow `evals/tier1.md` (and/or `evals/tier2.md`). Each runbook tells the
   harness exactly which shipped files to read, how to judge each fixture case,
   and where to write its verdicts:
   - `evals/out/tier1-results.json`
   - `evals/out/tier2-results.json`

2. **Score the results deterministically.**

   ```bash
   python evals/runner/score.py            # Tier 1 + Tier 2 metrics
   python evals/runner/score.py --json     # full machine-readable results
   python evals/runner/score.py --update-baseline   # refresh baselines/metrics.json
   ```

   `score.py` reads the harness results, compares them against the `expect`
   answer keys already in the fixtures, and computes precision / recall /
   **false-alarm rate** / accuracy. A missing results file → that tier is
   reported `skipped`.

### Why a harness, not an API model

- **No extra spend.** You judge with the subscription harness you already pay for.
- **Avoid self-judging.** Each runbook makes the harness treat the skill files as
  **quoted input data** and judge "using ONLY the rules below", ideally in a
  clean sub-task with the Greybeard skill **not active** — otherwise a session
  that already loaded Greybeard would grade itself.
- **Advisory, not a gate.** Because a conversational harness is less deterministic
  than a fixed-temperature API call, Tiers 1/2 are advisory: a single-case wobble
  against the baseline is noise. Each results file is stamped with
  `harness` / `model` / `date` so two baselines are actually comparable.

## Tier 0 and CI

Tier 0 is the **CI gate** and needs no model or harness:

```bash
python evals/runner/run.py            # Tier 0 (gates) + scores any harness results present
python evals/runner/run.py --json     # full machine-readable results
python evals/runner/run.py --update-baseline   # refresh baselines/metrics.json
```

`run.py` exits non-zero if the valid fixture bank does not pass clean or the
broken bank does not produce exactly its expected error set. It also folds in the
Tier 1/2 scores for whatever harness results exist in `evals/out/`, but **only
Tier 0 affects the exit code** — CI is never blocked on a model judge or network.

## Layout

```text
evals/
  README.md
  tier1.md                            # Tier 1 runbook (run with any harness)
  tier2.md                            # Tier 2 runbook (run with any harness)
  out/                                # harness results land here (gitignored)
  fixtures/
    candidate/cases.jsonl              # Tier 1 cases (accept/drop + route)
    review/
      bank-a/docs/greybeard/...        # a VALID bank: Tier 0 must pass
      bank-broken/docs/greybeard/...   # an INVALID bank
      bank-broken/expected-errors.json # the exact error set Tier 0 must produce
      cases/00*.json                   # Tier 2 review classification cases
    learn/README.md                    # deferred extraction eval
  runner/                             # Tier 0 linter + scorer + metrics + run.py
  baselines/metrics.json              # last recorded metrics
```

## Adding cases

- **Tier 0**: add or edit a bank under `fixtures/review/`. A valid bank must lint
  clean; an invalid bank needs an `expected-errors.json` listing the error set
  (compared by `code` + `file` + `decisionId`).
- **Tier 1**: append a JSON line to `fixtures/candidate/cases.jsonl` with `item`,
  `context`, and `expect: {verdict, route}`. The harness ignores `expect` while
  judging; the scorer uses it as the answer key.
- **Tier 2**: add `fixtures/review/cases/NNN-*.json` with `bank`, `category`,
  `change`, and `expect: {type, decisionId?}`.
