#!/usr/bin/env python3
"""Greybeard eval harness runner.

Runs the MVP tiers:

* Tier 0 - format linter (deterministic; **gates CI**).
* Tier 1 / Tier 2 - LLM-backed, but **harness-driven** (advisory, never gate CI).

Tier 0 is the CI gate: ``bank-a`` must pass clean and ``bank-broken`` must
produce exactly the error set in its ``expected-errors.json``.

The LLM tiers are no longer scored by a model provider inside Python. A coding
harness runs the runbooks ``evals/tier1.md`` / ``evals/tier2.md`` and writes its
verdicts to ``evals/out/``; ``score.py`` grades them. This runner invokes that
scorer for whatever harness results are present (reporting ``skipped`` for any
tier with no results file), so CI is never blocked on a model judge or network.

Usage:
    python evals/runner/run.py [--update-baseline] [--json]

Exit code is non-zero when any Tier 0 assertion fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow importing sibling modules whether invoked as a script or a module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import score  # noqa: E402
import tier0_format_lint as tier0  # noqa: E402
from load_skill_files import load_skill_files  # noqa: E402

EVALS_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = EVALS_ROOT / "fixtures"
BASELINES = EVALS_ROOT / "baselines" / "metrics.json"

BANK_A = FIXTURES / "review" / "bank-a"
BANK_BROKEN = FIXTURES / "review" / "bank-broken"


def _error_key_set(errors):
    return sorted(
        [e.get("code"), e.get("file"), e.get("decisionId")] for e in errors
    )


def run_tier0():
    """Deterministic format-linter assertions. Returns (summary, ok)."""
    checks = []

    valid = tier0.lint_bank(BANK_A)
    checks.append(
        {
            "name": "bank-a passes clean",
            "ok": valid["passed"] is True,
            "detail": valid["errors"],
        }
    )

    broken = tier0.lint_bank(BANK_BROKEN)
    expected = json.loads((BANK_BROKEN / "expected-errors.json").read_text("utf-8"))
    got_keys = _error_key_set(broken["errors"])
    want_keys = _error_key_set(expected["errors"])
    checks.append(
        {
            "name": "bank-broken matches expected-errors.json",
            "ok": got_keys == want_keys,
            "detail": {
                "missing": [k for k in want_keys if k not in got_keys],
                "unexpected": [k for k in got_keys if k not in want_keys],
            },
        }
    )

    ok = all(c["ok"] for c in checks)
    return {
        "tier": "tier0-format-lint",
        "ok": ok,
        "checks": checks,
        "bankBrokenErrorCount": len(broken["errors"]),
    }, ok


def main(argv=None):
    parser = argparse.ArgumentParser(description="Greybeard eval harness")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="write the current metrics to baselines/metrics.json",
    )
    parser.add_argument("--json", action="store_true", help="emit full JSON results")
    args = parser.parse_args(argv)

    # Loading the real shipped skill files up front fails loudly if any moved.
    load_skill_files()

    tier0_summary, tier0_ok = run_tier0()
    tier1_summary = score.score_tier1()
    tier2_summary = score.score_tier2()

    results = {
        "tier0": tier0_summary,
        "tier1": tier1_summary,
        "tier2": tier2_summary,
    }

    # ---- human-readable summary ----
    print("Greybeard eval harness")
    print("=" * 40)
    print(f"[tier0] format lint: {'PASS' if tier0_ok else 'FAIL'}")
    for c in tier0_summary["checks"]:
        print(f"        - {'ok ' if c['ok'] else 'FAIL'} {c['name']}")
    score._print_tier("tier1", tier1_summary)
    score._print_tier("tier2", tier2_summary)
    if not (tier1_summary["ran"] and tier2_summary["ran"]):
        print(
            "        (LLM tiers are harness-driven: run evals/tier1.md and "
            "evals/tier2.md with any harness, then re-run to score)"
        )

    if args.json:
        print(json.dumps(results, indent=2))

    if args.update_baseline:
        baseline = {
            "tier0": {
                "ok": tier0_ok,
                "bankBrokenErrorCount": tier0_summary["bankBrokenErrorCount"],
            },
            "tier1": tier1_summary["metrics"],
            "tier1Provenance": tier1_summary["provenance"],
            "tier2": tier2_summary["metrics"],
            "tier2Provenance": tier2_summary["provenance"],
        }
        BASELINES.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline to {BASELINES.relative_to(EVALS_ROOT.parent)}")

    return 0 if tier0_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
