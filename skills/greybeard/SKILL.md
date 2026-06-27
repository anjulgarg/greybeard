---
name: greybeard
description: Team decision-memory for codebases. Use for /greybeard:learn to bootstrap decisions from merged PR history, /greybeard:remember to capture one decision by hand, or /greybeard:review to check a supplied change against recorded decisions in docs/greybeard/.
---

# Greybeard

Route by command or user intent:

- `/greybeard:learn` or bootstrap/mining PR history -> read `workflows/learn.md`.
- `/greybeard:remember` or capture one decision by hand -> read `workflows/remember.md`.
- `/greybeard:review` or check a change against recorded decisions -> read `workflows/review.md`.

Shared resources:

- Before identifying or accepting decisions, read `references/decision-candidate.md`.
- Before writing or interpreting decision entries, read `references/decision-format.md`.
- For `/greybeard:learn` PR-scanning sub-agents, use `subagents/learn.md`.
- For `/greybeard:review` category-checking sub-agents, use `subagents/review.md`.

Keep this file as the router. The workflows own execution details; the references own shared rules
and formats.
