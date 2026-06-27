# Greybeard evaluation harness

This harness measures whether the Greybeard skill stays **precise** as its prompts,
workflows, sub-agent instructions, and decision formats evolve. The product promise
is **precision over recall**, so the harness measures false alarms explicitly, not
just how many valid issues Greybeard catches.

The runner loads the **real shipped skill files** from `skills/greybeard/` — never a
paraphrased copy. If an eval used a shadow prompt it could pass while the shipped
skill regressed.

## Tiers (MVP)

| Tier | What it checks | Needs a model? | Headline signal |
| --- | --- | --- | --- |
| **Tier 0** | Format linter: `docs/greybeard/` banks against `decision-format.md` | No (deterministic) | Structural drift / pass-fail |
| **Tier 1** | Candidate bar: one item → `accept`/`drop` + routing, per `decision-candidate.md` | Yes | False-alarm rate, then recall |
| **Tier 2** | Review classification: change → `VIOLATION`/`ADVISORY`/`SILENT` | Yes | False-alarm rate (firing on conformant/tombstoned) |

`remember` has no dedicated tier in the MVP: its acceptance gate shares the same
`decision-candidate.md` rules that Tier 1 exercises directly. Full `learn`
extraction eval is deferred (see `fixtures/learn/README.md`).

## Running

```bash
python evals/runner/run.py            # human-readable summary
python evals/runner/run.py --json     # full machine-readable results
python evals/runner/run.py --update-baseline   # refresh baselines/metrics.json
```

Tier 0 is the **CI gate**: the runner exits non-zero if the valid fixture bank does
not pass clean or the broken bank does not produce exactly its expected error set.

The LLM-backed tiers (1 and 2) **skip** unless a model provider is configured, so the
harness needs **no network access** and CI is **never blocked on an LLM judge**. To
score them locally:

```bash
export GREYBEARD_EVAL_PROVIDER=openai
export GREYBEARD_EVAL_MODEL=gpt-4o-mini
export OPENAI_API_KEY=...        # taken from the environment, never committed
python evals/runner/run.py
```

## Layout

```text
evals/
  README.md
  fixtures/
    candidate/cases.jsonl              # Tier 1 cases (accept/drop + route)
    review/
      bank-a/docs/greybeard/...        # a VALID bank: Tier 0 must pass
      bank-broken/docs/greybeard/...   # an INVALID bank
      bank-broken/expected-errors.json # the exact error set Tier 0 must produce
      cases/00*.json                   # Tier 2 review classification cases
    learn/README.md                    # deferred extraction eval
  runner/                              # loader + tiers + metrics + run.py
  baselines/metrics.json               # last recorded metrics
```

## Adding cases

- **Tier 0**: add or edit a bank under `fixtures/review/`. A valid bank must lint
  clean; an invalid bank needs an `expected-errors.json` listing the error set
  (compared by `code` + `file` + `decisionId`).
- **Tier 1**: append a JSON line to `fixtures/candidate/cases.jsonl` with `item`,
  `context`, and `expect: {verdict, route}`.
- **Tier 2**: add `fixtures/review/cases/NNN-*.json` with `bank`, `category`,
  `change`, and `expect: {type, decisionId?}`.
