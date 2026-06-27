"""Thin Tier 2: review classification eval.

Given a decision bank, a category file, and a supplied change, does the review
sub-agent return the right classification — ``VIOLATION`` for a real
code-checkable break, ``ADVISORY`` for a touched human-attested fact, or
``SILENT`` (no finding) for conformant code and tombstoned rules?

The prompt is built from the REAL shipped ``subagents/review.md`` plus
``decision-format.md`` and the actual category file from the fixture bank, so the
eval tracks the shipped sub-agent instructions. With no model provider configured
the cases are reported as ``skipped`` (CI stays off the LLM judge).

False-alarm rate is the headline metric here: firing on case 002 (conformant) or
003 (tombstoned) is exactly the precision failure the product must avoid.
"""

from __future__ import annotations

import json
from pathlib import Path

from load_skill_files import load_skill_files
from metrics import compute_classification_metrics
from model_provider import get_classifier

FIXTURES_REVIEW = Path(__file__).resolve().parents[1] / "fixtures" / "review"

LABELS = {"VIOLATION", "ADVISORY", "SILENT"}

SYSTEM_TEMPLATE = """\
{subagent_review}

=== references/decision-format.md (canonical schema) ===
{decision_format}
"""

USER_TEMPLATE = """\
ASSIGNED CATEGORY FILE: {category}

--- category decisions ---
{category_contents}

--- supplied change ---
file: {file}
summary: {summary}

{contents}

Return the findings JSON object now, following subagents/review.md exactly.
"""


def load_case(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _category_text(bank, category):
    path = FIXTURES_REVIEW / bank / "docs" / "greybeard" / category
    return path.read_text(encoding="utf-8")


def _parse_findings(text):
    """Return the highest-severity label from a sub-agent findings response."""
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
    findings = obj.get("findings", []) or []
    types = {f.get("type") for f in findings}
    if "VIOLATION" in types:
        return "VIOLATION"
    if "ADVISORY" in types:
        return "ADVISORY"
    return "SILENT"


def evaluate(cases_dir, classifier=None, skill_files=None):
    if classifier is None:
        classifier = get_classifier()
    if skill_files is None:
        skill_files = load_skill_files(["subagent_review", "decision_format"])

    system = SYSTEM_TEMPLATE.format(
        subagent_review=skill_files["subagent_review"],
        decision_format=skill_files["decision_format"],
    )

    case_paths = sorted(Path(cases_dir).glob("*.json"))
    results = []
    pairs = []
    for case_path in case_paths:
        case = load_case(case_path)
        expected = case["expect"]["type"]
        change = case["change"]
        predicted = None
        if classifier is not None:
            user = USER_TEMPLATE.format(
                category=case["category"],
                category_contents=_category_text(case["bank"], case["category"]),
                file=change.get("file", ""),
                summary=change.get("summary", ""),
                contents=change.get("contents", ""),
            )
            predicted = _parse_findings(classifier(system, user))
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
        "ran": classifier is not None,
        "metrics": metrics,
        "cases": results,
    }
