"""Tier 0: decision-bank format linter.

Catches structural drift in a ``docs/greybeard/`` decision bank WITHOUT calling
an LLM. The rules below are the machine-checkable subset of
``skills/greybeard/references/decision-format.md``; that file stays the canonical
prose schema and this linter must track it.

The linter returns a result dict::

    {"passed": bool, "errors": [Error, ...]}

where each ``Error`` is ``{"code", "file", "decisionId", "detail"}``. Errors are
intended to be a stable set so a fixture can assert exactly which errors a broken
bank produces (see ``bank-broken/expected-errors.json``).
"""

from __future__ import annotations

import re
from pathlib import Path

MAX_CATEGORY_FILES = 5

EVIDENCE_TYPES = {"code-checkable", "human-attested"}
CONFIDENCES = {"high", "medium", "low"}

# Field matchers (case-sensitive on the field labels, tolerant of surrounding
# whitespace). Decision bodies use ``**Future benefit:**`` / ``**Application
# check:**`` and a ``- field: value`` list for the structured metadata.
RE_HEADING = re.compile(r"^###\s+(?P<id>\S+)\.\s+(?P<statement>.+?)\s*$")
RE_FUTURE_BENEFIT = re.compile(r"^\s*\*\*Future benefit:\*\*\s*(?P<v>.*\S)?\s*$")
RE_APPLICATION_CHECK = re.compile(r"^\s*\*\*Application check:\*\*\s*(?P<v>.*\S)?\s*$")
RE_EVIDENCE_TYPE = re.compile(r"^\s*-\s*evidence-type:\s*(?P<v>.+?)\s*$")
RE_CONFIDENCE = re.compile(r"^\s*-\s*confidence:\s*(?P<v>.+?)\s*$")
RE_EVIDENCE = re.compile(r"^\s*-\s*evidence:\s*$")
RE_ATTESTOR = re.compile(r"^\s*-\s*attestor:\s*(?P<v>.+?)\s*$")
RE_SUPERSEDED_BY = re.compile(r"^\s*-\s*superseded-by:\s*(?P<v>.+?)\s*$")
RE_SUPERSEDED_BY_SHAPE = re.compile(r"^\S+\s+\(.+\)\s*$")
RE_LIST_ITEM = re.compile(r"^\s+-\s+\S")

# Canonical index line: ``- <ID> (<file>) - <one-line statement> [conf]``
RE_INDEX_LINE = re.compile(
    r"^-\s+(?P<id>\S+)\s+\((?P<file>[^)]+)\)\s+-\s+(?P<statement>.+?)\s+\[(?P<conf>[^\]]+)\]\s*$"
)


def _err(code, file=None, decision_id=None, detail=None):
    return {"code": code, "file": file, "decisionId": decision_id, "detail": detail}


def _split_entries(text):
    """Split a category file into decision entries keyed by their heading.

    Returns a list of ``(heading_match_or_None, raw_heading_line, [body_lines])``.
    Content before the first ``###`` heading is ignored (file title/intro).
    """
    entries = []
    current = None
    for line in text.splitlines():
        if line.startswith("### "):
            if current is not None:
                entries.append(current)
            current = {"heading": line, "match": RE_HEADING.match(line), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current is not None:
        entries.append(current)
    return entries


def _parse_fields(body_lines):
    """Pull the structured fields out of a decision body."""
    fields = {
        "why": "",
        "future_benefit": None,
        "application_check": None,
        "evidence_type": None,
        "confidence": None,
        "has_evidence_label": False,
        "evidence_items": 0,
        "attestor": None,
        "superseded_by": None,
    }
    why_lines = []
    seen_field = False
    in_evidence = False
    for line in body_lines:
        if RE_FUTURE_BENEFIT.match(line):
            fields["future_benefit"] = RE_FUTURE_BENEFIT.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif RE_APPLICATION_CHECK.match(line):
            fields["application_check"] = RE_APPLICATION_CHECK.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif RE_EVIDENCE_TYPE.match(line):
            fields["evidence_type"] = RE_EVIDENCE_TYPE.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif RE_CONFIDENCE.match(line):
            fields["confidence"] = RE_CONFIDENCE.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif RE_EVIDENCE.match(line):
            fields["has_evidence_label"] = True
            seen_field = True
            in_evidence = True
        elif RE_ATTESTOR.match(line):
            fields["attestor"] = RE_ATTESTOR.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif RE_SUPERSEDED_BY.match(line):
            fields["superseded_by"] = RE_SUPERSEDED_BY.match(line).group("v")
            seen_field = True
            in_evidence = False
        elif in_evidence and RE_LIST_ITEM.match(line):
            fields["evidence_items"] += 1
        elif not seen_field and line.strip():
            why_lines.append(line.strip())
    fields["why"] = " ".join(why_lines).strip()
    return fields


def _lint_entry(file_name, entry, errors):
    """Validate one decision entry; append errors. Returns (decision_id, is_live)."""
    match = entry["match"]
    if match is None:
        errors.append(
            _err("MISSING_HEADING_ID", file=file_name, detail=entry["heading"].strip())
        )
        decision_id = None
    else:
        decision_id = match.group("id")

    fields = _parse_fields(entry["body"])
    is_live = fields["superseded_by"] is None

    if not is_live:
        # Tombstoned entries are history. Only validate the supersession marker
        # shape; do not re-check the live-entry requirements.
        if not RE_SUPERSEDED_BY_SHAPE.match(fields["superseded_by"].strip()):
            errors.append(
                _err(
                    "INVALID_SUPERSEDED_BY",
                    file=file_name,
                    decision_id=decision_id,
                    detail=fields["superseded_by"],
                )
            )
        return decision_id, False

    # ---- live-entry requirements ----
    if not fields["why"]:
        errors.append(_err("MISSING_WHY", file=file_name, decision_id=decision_id))

    if not fields["future_benefit"]:
        errors.append(
            _err("MISSING_FUTURE_BENEFIT", file=file_name, decision_id=decision_id)
        )
    if not fields["application_check"]:
        errors.append(
            _err("MISSING_APPLICATION_CHECK", file=file_name, decision_id=decision_id)
        )

    if fields["evidence_type"] is None:
        errors.append(
            _err("MISSING_EVIDENCE_TYPE", file=file_name, decision_id=decision_id)
        )
    elif fields["evidence_type"] not in EVIDENCE_TYPES:
        errors.append(
            _err(
                "INVALID_EVIDENCE_TYPE",
                file=file_name,
                decision_id=decision_id,
                detail=fields["evidence_type"],
            )
        )

    if fields["confidence"] is None:
        errors.append(
            _err("MISSING_CONFIDENCE", file=file_name, decision_id=decision_id)
        )
    elif fields["confidence"] not in CONFIDENCES:
        errors.append(
            _err(
                "INVALID_CONFIDENCE",
                file=file_name,
                decision_id=decision_id,
                detail=fields["confidence"],
            )
        )

    if not fields["has_evidence_label"] or fields["evidence_items"] < 1:
        errors.append(_err("MISSING_EVIDENCE", file=file_name, decision_id=decision_id))

    if fields["evidence_type"] == "human-attested" and not fields["attestor"]:
        errors.append(_err("MISSING_ATTESTOR", file=file_name, decision_id=decision_id))

    return decision_id, True


def _parse_index(text):
    """Parse index.md decision lines. Returns (entries, bad_line_numbers).

    ``entries`` maps decision id -> dict(file, statement, conf).
    """
    entries = {}
    bad_lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        m = RE_INDEX_LINE.match(stripped)
        if m is None:
            bad_lines.append((i, stripped))
        else:
            entries[m.group("id")] = {
                "file": m.group("file"),
                "statement": m.group("statement"),
                "conf": m.group("conf"),
            }
    return entries, bad_lines


def lint_bank(bank_dir):
    """Lint a decision bank rooted at ``<bank_dir>/docs/greybeard``.

    ``bank_dir`` may point either at the bank root (containing ``docs/``) or
    directly at the ``docs/greybeard`` folder.
    """
    bank_dir = Path(bank_dir)
    greybeard_dir = bank_dir / "docs" / "greybeard"
    if not greybeard_dir.is_dir():
        # Allow passing the greybeard dir directly.
        if bank_dir.name == "greybeard" and bank_dir.is_dir():
            greybeard_dir = bank_dir
        else:
            return {
                "passed": False,
                "errors": [_err("INDEX_MISSING", detail=str(greybeard_dir))],
            }

    errors = []
    index_path = greybeard_dir / "index.md"
    if not index_path.is_file():
        errors.append(_err("INDEX_MISSING", file="index.md"))
        return {"passed": False, "errors": errors}

    category_files = sorted(
        p for p in greybeard_dir.glob("*.md") if p.name != "index.md"
    )
    if not category_files:
        errors.append(_err("NO_CATEGORY_FILES"))
    if len(category_files) > MAX_CATEGORY_FILES:
        errors.append(
            _err(
                "TOO_MANY_CATEGORIES",
                detail=f"{len(category_files)} > {MAX_CATEGORY_FILES}",
            )
        )

    live_decisions = {}  # id -> file name
    for cat_path in category_files:
        text = cat_path.read_text(encoding="utf-8")
        for entry in _split_entries(text):
            decision_id, is_live = _lint_entry(cat_path.name, entry, errors)
            if is_live and decision_id is not None:
                live_decisions[decision_id] = cat_path.name

    # ---- index.md cross-checks ----
    index_entries, bad_lines = _parse_index(index_path.read_text(encoding="utf-8"))
    for _line_no, raw in bad_lines:
        errors.append(_err("INDEX_BAD_FORMAT", file="index.md", detail=raw))

    for decision_id, file_name in live_decisions.items():
        if decision_id not in index_entries:
            errors.append(
                _err("INDEX_MISSING_DECISION", file="index.md", decision_id=decision_id)
            )
        elif index_entries[decision_id]["file"] != file_name:
            errors.append(
                _err(
                    "INDEX_WRONG_FILE",
                    file="index.md",
                    decision_id=decision_id,
                    detail=f"index says {index_entries[decision_id]['file']}, found in {file_name}",
                )
            )

    for decision_id in index_entries:
        if decision_id not in live_decisions:
            errors.append(
                _err("INDEX_UNKNOWN_DECISION", file="index.md", decision_id=decision_id)
            )

    return {"passed": len(errors) == 0, "errors": errors}


def error_key(err):
    """Stable comparison key for an error (code + file + decisionId)."""
    return (err.get("code"), err.get("file"), err.get("decisionId"))


def run(bank_dir):
    return lint_bank(bank_dir)
