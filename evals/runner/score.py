"""Deterministic scorer for the harness-driven LLM tiers (1 and 2).

The judging is no longer done by a model provider inside Python. A coding harness
runs the runbooks ``evals/tier1.md`` / ``evals/tier2.md`` and writes its verdicts
to ``evals/out/tier1-results.json`` / ``evals/out/tier2-results.json``. This
module is the only Python left for those tiers: it loads the harness results,
compares them against the ``expect`` answer keys baked into the fixtures, and
computes the same precision / recall / **false-alarm rate** metrics via
``metrics.py``.

If a results file is missing, that tier is reported as ``skipped`` (every case
counts toward ``total`` but none are scored) — exactly the shape the old
no-provider path produced, so ``baselines/metrics.json`` keeps its schema.

Usage:
    python evals/runner/score.py [--update-baseline] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics import compute_classification_metrics  # noqa: E402

EVALS_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = EVALS_ROOT / "fixtures"
OUT_DIR = EVALS_ROOT / "out"
BASELINES = EVALS_ROOT / "baselines" / "metrics.json"

CANDIDATE_CASES = FIXTURES / "candidate" / "cases.jsonl"
REVIEW_CASES = FIXTURES / "review" / "cases"

TIER1_RESULTS = OUT_DIR / "tier1-results.json"
TIER2_RESULTS = OUT_DIR / "tier2-results.json"

VERDICTS = {"accept", "drop"}
ROUTES = {"code-checkable", "human-attested", "none"}
LABELS = {"VIOLATION", "ADVISORY", "SILENT"}


def _load_jsonl(path):
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _load_results(path):
    """Return ``(provenance, {id: entry})`` from a harness results file, or
    ``(None, None)`` when the file is absent (tier not run)."""
    if not path.is_file():
        return None, None
    doc = json.loads(path.read_text(encoding="utf-8"))
    provenance = {
        "harness": doc.get("harness"),
        "model": doc.get("model"),
        "date": doc.get("date"),
    }
    by_id = {entry["id"]: entry for entry in doc.get("results", [])}
    return provenance, by_id


def _collapse_findings(findings):
    """Collapse a review sub-agent ``findings`` array to its highest-severity
    label (VIOLATION > ADVISORY > SILENT)."""
    types = {f.get("type") for f in (findings or [])}
    if "VIOLATION" in types:
        return "VIOLATION"
    if "ADVISORY" in types:
        return "ADVISORY"
    return "SILENT"


def score_tier1(results_path=TIER1_RESULTS, cases_path=CANDIDATE_CASES):
    provenance, by_id = _load_results(results_path)
    ran = by_id is not None
    cases = _load_jsonl(cases_path)

    results = []
    pairs = []
    for case in cases:
        expected = case["expect"]
        entry = by_id.get(case["id"]) if ran else None
        pred_verdict = None
        pred_route = None
        if entry is not None:
            v = entry.get("verdict")
            r = entry.get("route")
            pred_verdict = v if v in VERDICTS else None
            if pred_verdict is None:
                pred_route = None
            elif r in ROUTES:
                pred_route = r
            else:
                pred_route = "none" if pred_verdict == "drop" else None
        results.append(
            {
                "id": case["id"],
                "expectedVerdict": expected["verdict"],
                "expectedRoute": expected["route"],
                "predictedVerdict": pred_verdict,
                "predictedRoute": pred_route,
                "routeCorrect": (
                    None
                    if pred_verdict is None
                    else (
                        pred_verdict == expected["verdict"]
                        and pred_route == expected["route"]
                    )
                ),
            }
        )
        pairs.append((expected["verdict"], pred_verdict))

    metrics = compute_classification_metrics(pairs, positive_labels={"accept"})
    return {
        "tier": "tier1-candidate",
        "ran": ran,
        "provenance": provenance,
        "metrics": metrics,
        "cases": results,
    }


def score_tier2(results_path=TIER2_RESULTS, cases_dir=REVIEW_CASES):
    provenance, by_id = _load_results(results_path)
    ran = by_id is not None

    results = []
    pairs = []
    for case_path in sorted(Path(cases_dir).glob("*.json")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        expected = case["expect"]["type"]
        entry = by_id.get(case["id"]) if ran else None
        predicted = None
        if entry is not None:
            if "findings" in entry:
                predicted = _collapse_findings(entry.get("findings"))
            elif entry.get("type") in LABELS:
                # Tolerate a pre-collapsed label if a harness emits one.
                predicted = entry["type"]
        results.append(
            {
                "id": case["id"],
                "expected": expected,
                "predicted": predicted,
                "correct": None if predicted is None else predicted == expected,
            }
        )
        pairs.append((expected, predicted))

    metrics = compute_classification_metrics(
        pairs, positive_labels={"VIOLATION", "ADVISORY"}
    )
    return {
        "tier": "tier2-review",
        "ran": ran,
        "provenance": provenance,
        "metrics": metrics,
        "cases": results,
    }


def _print_tier(key, summary):
    m = summary["metrics"]
    if not summary["ran"]:
        print(
            f"[{key}] {summary['tier']}: SKIPPED "
            f"({m['total']} cases, no harness results at evals/out/)"
        )
        return
    prov = summary["provenance"] or {}
    stamp = f"{prov.get('harness') or '?'}/{prov.get('model') or '?'} ({prov.get('date') or '?'})"
    print(
        f"[{key}] {summary['tier']}: {stamp} scored {m['scored']}/{m['total']} "
        f"accuracy={m['accuracy']} false_alarm_rate={m['falseAlarmRate']} "
        f"precision={m['precision']} recall={m['recall']}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score harness-driven eval tiers")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="merge the current tier metrics into baselines/metrics.json",
    )
    parser.add_argument("--json", action="store_true", help="emit full JSON results")
    args = parser.parse_args(argv)

    tier1_summary = score_tier1()
    tier2_summary = score_tier2()

    print("Greybeard eval — LLM tier scoring (harness-driven)")
    print("=" * 40)
    _print_tier("tier1", tier1_summary)
    _print_tier("tier2", tier2_summary)

    if args.json:
        print(json.dumps({"tier1": tier1_summary, "tier2": tier2_summary}, indent=2))

    if args.update_baseline:
        baseline = {}
        if BASELINES.is_file():
            baseline = json.loads(BASELINES.read_text(encoding="utf-8"))
        baseline["tier1"] = tier1_summary["metrics"]
        baseline["tier1Provenance"] = tier1_summary["provenance"]
        baseline["tier2"] = tier2_summary["metrics"]
        baseline["tier2Provenance"] = tier2_summary["provenance"]
        BASELINES.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline to {BASELINES.relative_to(EVALS_ROOT.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
