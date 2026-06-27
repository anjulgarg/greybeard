"""Tier 1: candidate-bar eval.

Exercises the shared candidate bar (``references/decision-candidate.md``) on
single items: given one comment / PR-description point / attested fact, does the
skill correctly ``accept`` or ``drop`` it, and if accepted, route it as
``code-checkable`` vs ``human-attested``?

This tier needs a model to make the judgement. The prompt is assembled from the
REAL shipped ``decision-candidate.md`` (plus ``decision-format.md`` for routing
vocabulary) so a regression in the shipped rules shows up here. When no model
provider is configured the cases are reported as ``skipped`` (CI is not blocked
on an LLM judge).
"""

from __future__ import annotations

import json
from pathlib import Path

from load_skill_files import load_skill_files
from metrics import compute_classification_metrics
from model_provider import get_classifier

VERDICTS = {"accept", "drop"}
ROUTES = {"code-checkable", "human-attested", "none"}

SYSTEM_TEMPLATE = """\
You are evaluating whether a single item qualifies as a Greybeard decision, using
ONLY the rules below. Apply the bar strictly: precision over recall, prefer silence
to a wrong decision.

=== references/decision-candidate.md ===
{decision_candidate}

=== references/decision-format.md (routing vocabulary only) ===
{decision_format}

Respond with a single JSON object and nothing else:
{{"verdict": "accept" | "drop", "route": "code-checkable" | "human-attested" | "none"}}
Use "route": "none" whenever the verdict is "drop".
"""

USER_TEMPLATE = """\
ITEM:
{item}

CONTEXT:
{context}

Return the JSON verdict now.
"""


def load_cases(path):
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _parse_response(text):
    """Extract ``{"verdict", "route"}`` from a model response, tolerating prose."""
    if text is None:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    verdict = obj.get("verdict")
    route = obj.get("route")
    if verdict not in VERDICTS:
        return None
    if route not in ROUTES:
        route = "none" if verdict == "drop" else route
    return {"verdict": verdict, "route": route}


def evaluate(cases_path, classifier=None, skill_files=None):
    """Run Tier 1. ``classifier`` defaults to the configured model provider."""
    if classifier is None:
        classifier = get_classifier()
    if skill_files is None:
        skill_files = load_skill_files(["decision_candidate", "decision_format"])

    system = SYSTEM_TEMPLATE.format(
        decision_candidate=skill_files["decision_candidate"],
        decision_format=skill_files["decision_format"],
    )

    cases = load_cases(cases_path)
    results = []
    pairs = []  # (expected_verdict, predicted_verdict)
    for case in cases:
        expected = case["expect"]
        predicted = None
        if classifier is not None:
            raw = classifier(system, USER_TEMPLATE.format(item=case["item"], context=case.get("context", "")))
            predicted = _parse_response(raw)
        pred_verdict = predicted["verdict"] if predicted else None
        pred_route = predicted["route"] if predicted else None
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
                    else (pred_verdict == expected["verdict"] and pred_route == expected["route"])
                ),
            }
        )
        pairs.append((expected["verdict"], pred_verdict))

    metrics = compute_classification_metrics(pairs, positive_labels={"accept"})
    return {
        "tier": "tier1-candidate",
        "ran": classifier is not None,
        "metrics": metrics,
        "cases": results,
    }
