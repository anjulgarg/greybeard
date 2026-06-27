"""Load the REAL shipped Greybeard skill files.

The eval harness must exercise the markdown that actually ships in
``skills/greybeard/``. If a tier built its prompts from a copy/pasted shadow
prompt, the eval could pass while the shipped skill silently regressed. So every
tier that needs prompt text loads it through this module.
"""

from __future__ import annotations

import os
from pathlib import Path

# evals/runner/load_skill_files.py -> repo root is two parents up from this dir.
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "greybeard"

# The shipped files the harness loads. Keys are stable handles the tiers use; the
# values are paths relative to ``skills/greybeard/``.
SKILL_FILES = {
    "decision_candidate": "references/decision-candidate.md",
    "decision_format": "references/decision-format.md",
    "subagent_learn": "subagents/learn.md",
    "subagent_review": "subagents/review.md",
    "workflow_review": "workflows/review.md",
    "workflow_learn": "workflows/learn.md",
    "workflow_remember": "workflows/remember.md",
    "skill": "SKILL.md",
}


def skill_path(handle: str) -> Path:
    """Return the absolute path for a known skill-file handle."""
    if handle not in SKILL_FILES:
        raise KeyError(f"unknown skill file handle: {handle!r}")
    return SKILL_ROOT / SKILL_FILES[handle]


def load_skill_files(handles=None) -> dict:
    """Load shipped skill files, returning ``{handle: text}``.

    Raises ``FileNotFoundError`` if a requested file is missing, so a renamed or
    deleted shipped file fails the harness loudly instead of silently shrinking
    the prompt context.
    """
    if handles is None:
        handles = list(SKILL_FILES.keys())
    out = {}
    for handle in handles:
        path = skill_path(handle)
        if not path.is_file():
            raise FileNotFoundError(
                f"shipped skill file missing for handle {handle!r}: "
                f"{os.path.relpath(path, REPO_ROOT)}"
            )
        out[handle] = path.read_text(encoding="utf-8")
    return out


if __name__ == "__main__":
    loaded = load_skill_files()
    for handle, text in loaded.items():
        print(f"{handle}: {SKILL_FILES[handle]} ({len(text)} chars)")
