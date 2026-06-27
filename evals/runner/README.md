# Eval runner

Smallest-footprint runner: Python 3 standard library only, no third-party
dependencies.

| File | Role |
| --- | --- |
| `run.py` | Orchestrator. Runs all tiers, prints a summary, gates CI on Tier 0. |
| `load_skill_files.py` | Loads the REAL shipped files from `skills/greybeard/`. |
| `tier0_format_lint.py` | Deterministic decision-bank format linter. |
| `tier1_candidate_eval.py` | Candidate-bar eval (LLM-backed). |
| `tier2_review_eval.py` | Review classification eval (LLM-backed). |
| `metrics.py` | Precision / recall / **false-alarm rate** / accuracy. |
| `model_provider.py` | Optional model provider; returns `None` (skip) by default. |

Run from the repo root:

```bash
python evals/runner/run.py
```

The tier modules are also importable directly (e.g. for unit-testing the linter or
injecting a stub classifier):

```python
import sys; sys.path.insert(0, "evals/runner")
import tier0_format_lint as t0
print(t0.lint_bank("evals/fixtures/review/bank-a"))
```
