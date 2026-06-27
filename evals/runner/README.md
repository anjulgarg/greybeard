# Eval runner

Smallest-footprint runner: Python 3 standard library only, no third-party
dependencies. The LLM judging is **harness-driven** (see `evals/tier1.md` /
`evals/tier2.md`); the Python here is just the deterministic Tier 0 gate plus the
scorer that grades whatever a harness wrote to `evals/out/`.

| File | Role |
| --- | --- |
| `run.py` | Orchestrator. Runs Tier 0, scores any harness results, gates CI on Tier 0. |
| `tier0_format_lint.py` | Deterministic decision-bank format linter (the CI gate). |
| `score.py` | Scores harness results in `evals/out/` against the fixture answer keys. |
| `load_skill_files.py` | Loads the REAL shipped files from `skills/greybeard/`. |
| `metrics.py` | Precision / recall / **false-alarm rate** / accuracy. |

Run from the repo root:

```bash
python evals/runner/run.py        # Tier 0 (gates) + score harness results if present
python evals/runner/score.py      # score the LLM tiers only
```

The modules are also importable directly (e.g. for unit-testing the linter or the
scorer):

```python
import sys; sys.path.insert(0, "evals/runner")
import tier0_format_lint as t0
print(t0.lint_bank("evals/fixtures/review/bank-a"))

import score
print(score.score_tier1())   # reads evals/out/tier1-results.json if present
```
