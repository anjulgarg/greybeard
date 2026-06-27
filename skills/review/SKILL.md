---
name: review
description: Check a PR, diff, branch, local change set, document, or other supplied change against the project's recorded decisions (docs/greybeard/) and flag changes that violate them. Fans out one read-only sub-agent per decision category file; each matches the change — WITH current file/document contents where available, by meaning not line number — against its decisions and reports only high-confidence violations, citing the rule, the why, and the originating evidence. Precision-biased: a false alarm costs more than a miss.
---

# /greybeard:review

The payoff of the decision memory. Given a PR, diff, branch, local change set, document, or other
supplied change, surface changes that break a recorded decision — **with the rule, why it exists,
and the original evidence** — so the author fixes it before merge instead of a reviewer re-deriving
the rule from scratch (again).

Validated at **86% / 75% / 12%** on the calibration repo (strict recall / zero-overlap recall /
false-alarm rate). The **12% false-alarm number is the one to protect: precision over recall.** A
wrong flag on conformant code teaches people to ignore the tool, which destroys the whole system's
value. **When a sub-agent is unsure, it stays silent.**

---

## Inputs (auto-detect, confirm)

1. **target** — any supplied change, including:
   - a **PR number** → diff vs its base (`gh pr diff <N>` / ADO equivalent),
   - a **branch** → `git diff <base>...HEAD`,
   - **local changes** → staged/unstaged working tree,
   - a **diff/patch file**,
   - a **document or text artifact**.
   Default: PR if a number is given, else current branch vs its base, else the working tree.
2. **provider** — `github` / `azure-devops`, for fetching a PR and (optionally) posting comments.

---

## Execution model (map-reduce — fan out per CATEGORY FILE)

Unlike learn (which partitions *PRs*), here the natural unit is the **decision category file**.
They are few (**≤5**, enforced at write time by learn/remember) and independent, so fan-out is naturally bounded — at most 5 sub-agents, no streaming needed.

```
ORCHESTRATOR
  - resolve target -> changed files/documents + locations
  - load the CURRENT contents for changed files/documents where available   <- critical, see below
  - list docs/greybeard/ category files; load only LIVE decisions (skip tombstoned/superseded)
    from the BASE branch for PR/branch targets, or the provided/current bank for other targets
        |
        | fan out one sub-agent per category file (all parallel; count = #category files)
        v
  SUB-AGENT (read-only)   <- one category file + the change + current contents where available
    for each LIVE decision that appears semantically relevant to the change:
      does this change move AGAINST the rule?  match by MEANING, not line number
      emit { decision_id, evidenceType, location, why, confidence, fix? }  ONLY if high-confidence
        |
        | collect all sub-agent findings
        v
  ORCHESTRATOR
    dedupe, rank (code-verified violations by confidence first, advisories last),
    render report  and/or  post PR review comments
```

Why per-category-file fan-out:
- **Bounded** by category count (**≤5**, enforced when decisions are written) — no extra concurrency cap or streaming required. If one category
  file holds an unusually large number of decisions, that sub-agent walks them decision-by-decision.
- **Tight context** — each sub-agent sees one category's rules + the supplied change, nothing else.
- **Read-only** — only the orchestrator emits the single report; no write races.

---

## What each sub-agent MUST receive (the validated invariants)

1. **Current contents, not just the diff.** For code diffs, both validation errors were diff-only
   artifacts: a rule can be satisfied or broken by code *outside* the changed hunk. The sub-agent
   needs full file state to judge when that state is available.
2. **Match by meaning, not line number.** The diff's hunk lines and a decision's original lines will
   not align (squash merges, later iterations, unrelated edits).
3. **The decision's `why` + `evidence`**, so every flag explains itself and the author can judge
   whether it is real.

---

## Evidence-type handling

- **Code-verified decisions** — directly checkable. Flag a **violation** when the change moves
  *against* the rule.
- **Human-attested facts** — a diff cannot "violate" a fact. Instead emit an **advisory** when the
  change touches the fact's subject ("this edits the event hub owned by `<team>` — coordinate?").
  Advisory, never a blocking violation.
- **Confidence weighting** — `low-needs-attestation` decisions produce **advisories at most**, never
  hard violations (they are unverified by design).

---

## Skip (reduces false fire)

- **Tombstoned / superseded** decisions — never check; they are history.
- A decision that is clearly unrelated to the supplied change — do not force a match.

---

## Output

A report, and optionally PR review comments. Per finding:

```
[VIOLATION | ADVISORY]  <decision_id>  (<category>)  conf:<high|med>
  rule:   <one-line statement>
  why:    <the rationale — why this rule exists>
  where:  <file>:<hunk> or <document>:<section>
  basis:  <evidence pointer or attestor/review-by> — "<original evidence quote or rationale>"
  fix:    <concrete suggestion, if one is clear>
```

Summary line: `N violations, M advisories across K decisions; P targets reviewed.`

If there are **zero** findings, say so plainly — a clean pass is a valid, valuable result, not a
sign the tool did nothing.

---

## Gotchas (these bite hardest here)

1. **Precision over recall.** Silence beats a false flag. The false-alarm rate is the trust metric —
   guard it above recall.
2. **Current files, not just the diff.** (Validated failure mode #1.)
3. **Meaning, not line numbers.** (Validated failure mode #2.)
4. **Never check tombstoned decisions** — flagging a superseded rule is a guaranteed false alarm.
5. **For PR/branch targets, read the decision bank from BASE, not the PR head.** Otherwise a PR that
   edits `docs/greybeard/` to delete a rule could violate it and still pass. For other targets, use
   the provided or current decision bank.
6. **Cite the evidence on every finding.** An unexplained flag gets ignored; the originating PR/quote
   is what makes the author trust and act on it.

## Decision entry format

Read `../decision-entry-format.md` before interpreting entries. That file is the canonical schema
shared by `/greybeard:learn`, `/greybeard:remember`, and `/greybeard:review`.
