#!/usr/bin/env python3
"""Greybeard eval harness runner.

Runs the MVP tiers:

* Tier 0 - format linter (deterministic; gates CI).
* Tier 1 - candidate-bar eval (LLM-backed; skipped without a provider).
* Tier 2 - review classification eval (LLM-backed; skipped without a provider).

Tier 0 is the CI gate: ``bank-a`` must pass clean and ``bank-broken`` must
produce exactly the error set in its ``expected-errors.json``. The LLM tiers run
only when ``GREYBEARD_EVAL_PROVIDER`` is configured; otherwise they report
``skipped`` so CI is never blocked on a model judge or on network access.

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

import tier0_format_lint as tier0  # noqa: E402
import tier1_candidate_eval as tier1  # noqa: E402
import tier2_review_eval as tier2  # noqa: E402
from load_skill_files import load_skill_files  # noqa: E402

EVALS_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = EVALS_ROOT / "fixtures"
BASELINES = EVALS_ROOT / "baselines" / "metrics.json"

BANK_A = FIXTURES / "review" / "bank-a"
BANK_BROKEN = FIXTURES / "review" / "bank-broken"
CANDIDATE_CASES = FIXTURES / "candidate" / "cases.jsonl"
REVIEW_CASES = FIXTURES / "review" / "cases"


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
    skill_files = load_skill_files()

    tier0_summary, tier0_ok = run_tier0()
    tier1_summary = tier1.evaluate(CANDIDATE_CASES, skill_files=skill_files)
    tier2_summary = tier2.evaluate(REVIEW_CASES, skill_files=skill_files)

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
    for key, summary in (("tier1", tier1_summary), ("tier2", tier2_summary)):
        m = summary["metrics"]
        if not summary["ran"]:
            print(
                f"[{key}] {summary['tier']}: SKIPPED "
                f"({m['total']} cases, no model provider configured)"
            )
        else:
            print(
                f"[{key}] {summary['tier']}: scored {m['scored']}/{m['total']} "
                f"accuracy={m['accuracy']} false_alarm_rate={m['falseAlarmRate']} "
                f"precision={m['precision']} recall={m['recall']}"
            )

    if args.json:
        print(json.dumps(results, indent=2))

    if args.update_baseline:
        baseline = {
            "tier0": {"ok": tier0_ok, "bankBrokenErrorCount": tier0_summary["bankBrokenErrorCount"]},
            "tier1": tier1_summary["metrics"],
            "tier2": tier2_summary["metrics"],
        }
        BASELINES.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline to {BASELINES.relative_to(EVALS_ROOT.parent)}")

    return 0 if tier0_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
