---
name: learn
description: Bootstrap a project's decision memory by scanning the last X MERGED pull requests. Mines durable engineering decisions from review comments, PR descriptions, and the merged diffs themselves, verifies each against the merged code (adoption check), and emits generated decision markdown files into docs/greybeard/. Run once at setup, or re-run to extend.
---

# /greybeard:learn

Bootstrap (or extend) a repository's **decision memory** by mining its merged pull-request
history. Produces a generated set of decision files under `docs/greybeard/` on the main branch.

This is a **one-time / occasional bootstrap**, not a hot path. It is **precision-biased**:
when in doubt, drop the candidate. A wrong decision is worse than a missing one — a wrong
decision makes `/greybeard:review` flag conformant code, which destroys trust in the
whole system.

> **Why precision matters (real failure this design prevents):** In validation, a reviewer
> commented "100% trace sampling is too much," the thread was marked `fixed`, but the merged
> code *kept* 100% sampling (aligned with ACS RP). Trusting the comment/thread-status would
> have stored a decision the codebase **actively contradicts**. The adoption check (Stage 4)
> and description-mining (Stage 2) exist specifically to catch this.

---

## Where decisions are stored

A `docs/greybeard/` folder on the **main branch**, updated via normal PRs. Only `index.md` is
fixed; the category files are **emergent and capped at 5**:

```
docs/greybeard/
  index.md          # one-line summary + link per decision; the map (always present)
  <topic>.md        # emergent cluster, named for what it covers — e.g. api-compat, testing,
                    #   data-privacy, ownership. At most 5 such files.
```

Categories are derived from the decisions, **not** hardcoded. The 5-file cap keeps
`/greybeard:review` fan-out bounded (one sub-agent per category file, ≤5). Bias to the **fewest,
broadest** buckets that stay coherent: reuse the closest existing file before opening a new one,
and once 5 exist, fold a new cluster into its nearest neighbour rather than creating a 6th.
`evidence-type` is a per-decision entry field, independent of which file holds it. Use
`code-checkable` for rules whose application can be checked in code/config/tests/docs, and
`human-attested` for world facts that code cannot prove. Only `code-checkable` decisions with an
`ADOPTED` verdict are emitted into the final
decision files; human-attested facts are review notes, not canon.

---

## Inputs (ask the user if not provided)

1. **X** — number of most-recent merged PRs to scan. **Always ask the user** how many PRs the
   skill should run on before scanning — never silently assume a default. Present sensible choices:
   - **Last 100 PRs** (default if the user just wants a quick bootstrap)
   - **All PRs over the last 1 year** (a `window` of the past 12 months, any count)
   - **From the beginning of the project** (every merged PR in history)
   - **Custom** — a specific number of PRs or a specific date range the user provides
   Map the chosen option onto `X` and/or `window` (item 3): a count-based choice sets `X`; a
   time-based choice ("last 1 year", "from the beginning") sets `window` and leaves `X` effectively
   unbounded (use a high `--limit` and let the date range bound the scan).
2. **provider** — `github` (`gh` CLI) or `azure-devops` (`az repos`/`az devops invoke`). Auto-detect
   from the remote if possible.
3. **window** — optional date range to bound the scan.
4. **mode** — `bootstrap` (empty `docs/greybeard/`) or `extend` (dedupe against existing decisions).
5. **max sub-agents** — hard cap on the **total** number of sub-agents the scan spawns, for the
   whole run (default & max **5**). Use fewer or run inline when that is simpler.
6. **large-scan warning threshold** — comment-threads *per sub-agent* above which the run is
   flagged as large and slow (default **~250**). It does not add agents (the cap is 5); it prompts
   the user to lower **X** or narrow the **window** instead.

---

## Execution model (orchestrator + parallel sub-agents)

The pipeline is **map-reduce**. The per-PR work (Stages 1–4) is independent across PRs, so it is
parallelized; the global merge (Stages 5–6) is single-threaded.

```
ORCHESTRATOR (single-threaded, cheap)
  Stage 0  ONE bulk list call -> {number, mergeSha, mergedAt, title} for all eligible merged
           PRs; count, confirm scan size, split into <=5 work-balanced batches of PR refs
        |
        |  fan out <=5 sub-agents total (one per batch, all parallel)
        v
  SUB-AGENTS (<=5, parallel, independent)   <- a batch of PR refs
    Stage 1  walk THIS batch PR-by-PR: fetch threads + description, STREAM candidates to a
             file, release each PR's context before the next (batch size is unbounded)
    Stages 2–4  apply decision-candidate rules, route, adoption-check (local `git show`,
                 read current files)
    return: structured candidate decisions JSON (id-less), each tagged {mergeSha, mergedAt,
            evidenceType, verdict, confidence, evidence}. They NEVER write to docs/greybeard/.
        |
        |  collect all batch results
        v
  ORCHESTRATOR (single-threaded)
    Stage 5  sort candidates by mergedAt, cluster/dedupe/supersede, assign stable IDs
    Stage 6  emit docs/greybeard/ files, ask user to review, then suggest a PR
```

Rules that keep parallelism *correct*, not just fast:
- **Sub-agents may write scratch/output files.** Only the orchestrator writes final
  `docs/greybeard/` files. Parallel final writes would race and make supersession undefined.
- **Ordering lives in the reduce, not the map.** Recency-wins supersession is applied in Stage 5
  by sorting the merged candidate pool on `mergedAt` — NOT by relying on PR processing order.
  This is why batching is safe.
- **Enumerate once (orchestrator); fetch per batch (sub-agent).** The orchestrator makes ONE
  cheap *list* call to get PR refs + merge SHAs — it never fetches threads. Each sub-agent then
  fetches its own batch's threads + descriptions **in parallel**, which parallelizes the slow I/O.
  This is the expensive stage, so parallelizing it is the main speedup.
- **At most 5 sub-agents, total.** The whole scan spawns ≤5; run them in parallel when parallelism
  helps. A large repo is absorbed by **bigger batches + per-PR streaming** (see **Sizing**), never
  by more agents.
- **Replayability.** Each sub-agent dumps its batch's raw fetch to a file, so a run is
  inspectable and individually re-runnable.
- **Bound it.** Per-batch retry — if a batch fails or returns malformed output, redo just that
  batch (or the orchestrator does it itself). The sub-agent *count* is fixed (≤5); only batch
  *contents* are derived (work-balanced) — see **Sizing** below.

---

## Sizing: how many sub-agents

Use **at most 5 sub-agents for the entire scan**. The orchestrator chooses the simplest useful
strategy: run inline for tiny scans, use fewer agents for small scans, and use up to 5 agents when
parallelism will materially help. Do not spawn idle agents just to reach the cap.

**Put every selected merged PR in exactly one batch.** Do not special-case PRs with zero comments:
their descriptions can still contain decisions. If comment/thread counts are already available
cheaply, balance batches by that count; otherwise split by PR count and move on.

**A batch can be large, so each sub-agent STREAMS — it never holds its whole batch in context.**
For large scans, the sub-agent processes its batch **one
PR at a time** — fetch → pre-filter → route → adoption-check → **append that PR's candidates to its
output file → drop the PR's diff/file contents from context** → next PR. Only the small running
candidate list stays resident. This is what lets a fixed cap absorb large repos (see Stage 1).

**Guardrail for very large scans.** Estimate per-agent load from the planned batches. If that
exceeds the **large-scan warning threshold** (default ~250 threads/agent), the orchestrator
**warns** that the run will be large and slow and suggests lowering **X** or narrowing the
**window**.

**Worked examples:**
- **8 PRs selected:** likely run inline.
- **46 PRs selected:** use a few work-balanced batches if parallel fetch will help.
- **1000 PRs selected:** use up to 5 batches; warn if the known thread load exceeds the guardrail
  and offer to narrow the scan.

---

## Pipeline (6 stages, map-reduce)

Before starting Stage 1, read `../decision-candidate.md`. That file is the canonical source for
what counts as a decision candidate, what must be dropped, evidence routing, and adoption verdicts.
Every sub-agent must receive and apply those rules. This skill owns orchestration; the shared file
owns candidate judgment.

### Stage 0 — Enumerate eligible PRs, confirm scan size, split into batches (ORCHESTRATOR)
First **count the merged PRs actually available**, then **always ask the user how many PRs to scan**
before fanning out — `X` is meaningless if only 60 merged PRs exist, or if 500 exist and the user may
only want a recent slice. Offer the standard choices (**last 100 PRs**, **all PRs over the last 1
year**, **from the beginning of the project**, or a **custom** count/date range — see **Inputs**),
then report: total merged PRs available, the slice to be scanned, and the resulting batch/sub-agent
count.

This stage is **cheap**: one bulk *list* call that returns PR refs (`number`, `mergeCommit`,
`mergedAt`, `title`) — it does **not** fetch comment threads (that is the sub-agent's job).

Only **completed/merged** PRs are eligible. Abandoned or active PRs are excluded:
- There is no merge commit to run the adoption check against.
- An abandoned PR often means the proposal was **rejected** — including it would poison the bank.

GitHub — get the true count, then the slice (refs only, no threads):
```
gh pr list --state merged --limit 1000 --json number | jq length      # total available
gh pr list --state merged --limit X \
  --json number,title,mergeCommit,mergedAt                             # the slice (refs only)
```
Azure DevOps: list PRs with `status=completed` (the API returns a total count); capture
`pullRequestId`, `lastMergeCommit`, `title`, `closedDate`.

Each PR's **merge commit SHA** comes for free from this list call (`mergeCommit` /
`lastMergeCommit`). If you ever must derive it from a number in a squash-merge repo, anchor on
the literal commit-message prefix (`git log --all --grep "Merged PR <N>:"`). **Do NOT grep for
the bare PR number** — that also matches later PRs whose description merely *references* this PR,
and silently returns the wrong commit. (This was a real bug.)

Then **split the selected PR refs into at most 5 work-balanced batches** (by comment count — see
**Sizing**) and fan out **one sub-agent per batch (≤5 total, all in parallel)**.

### Stage 1 — Fetch this batch's evidence sources (SUB-AGENT, per batch)
The sub-agent walks its batch **one PR at a time** (so an arbitrarily large batch still fits a
single context window): for each PR it fetches the two sources below, runs Stages 2–4 on that PR,
**appends the surviving candidates to its output file, then releases that PR's threads/diff/file
contents before the next PR** — only the small running candidate list stays resident. It also
dumps each PR's raw fetch to a batch file for replayability. The two sources per PR:
1. **Review comment threads** — all of them. **Do NOT drop bot comments.** A bot comment that
   led to a merged code change, or that drew a substantive human reply, is a valid signal.
   Keep authorship as metadata, not as a filter.
2. **PR description / merge-commit body** — frequently states the decision *and its rationale*
   even when no comment thread exists. The merged code is the corroborating evidence that the
   description's claim actually shipped.

The third source — **the merged diff** — is not fetched from the API: it is pulled **locally**
via `git show <mergeSha>` during the Stage-4 adoption check (local git has no rate limit).

### Stage 2 — Cheap pre-filter (drop the noise) — SUB-AGENT, per batch
Apply `../decision-candidate.md` strictly. Most review activity is not a decision; keep only items
that pass the shared durability, generalizability, why, evidence, and application-check rules.
Expect roughly **~15–20%** of comments to survive this stage.

### Stage 3 — Route each surviving candidate — SUB-AGENT, per batch
Use the evidence routes in `../decision-candidate.md`:
- **Code-checkable decision** — continue to Stage 4.
- **Human-attested fact** — report as not emitted / needs human follow-up. `/learn` does **not**
  emit these as decisions.

### Stage 4 — Adoption check (the core — code-checkable decisions only) — SUB-AGENT, per batch
Within its batch, the sub-agent runs this for each code-checkable candidate using the **full
context**, never just the comment:

> Inputs: the candidate statement + verbatim quote; the file(s) it concerns; the **merged diff of
> those files** (`git show <mergeSha> -- <path>`, run locally); and the **final/current contents**
> of those files. Match by **semantic content, not comment line numbers** — squash merges and later
> review iterations move the lines the comment originally pointed at.

Return exactly one adoption verdict per candidate using the verdict definitions in
`../decision-candidate.md`: `ADOPTED`, `NOT-ADOPTED`, `PARTIAL`, or `NOT-CODE`. Human-attested
facts skip the adoption check because a diff cannot confirm them.

**Sub-agent output contract:** return a JSON array of candidate decisions — each with
`{statement, why, futureBenefit, applicationCheck, evidenceType, verdict, confidence,
evidence:{pr, date, quote, mergeSha, before, after}}`. `futureBenefit` must clearly explain how
this decision helps future engineers make better decisions in this project; it must be articulate,
specific, and grounded in project reality (not generic "improves maintainability" filler).
`applicationCheck` must state how future engineers should apply or verify this decision — concrete
evidence, code/config shape, test coverage, design constraint, rollout boundary, operational proof,
or coordination to ask for. The `mergeSha`, `before`, and `after` fields are internal adoption-check
proof only; use them during
reduce/review, but do not emit before/after proof into the final decision markdown. **No stable IDs**
(the orchestrator assigns those after clustering) and **no writes** to `docs/greybeard/`. A batch
that fails or returns malformed JSON is retried, or the orchestrator processes it directly.

### Stage 5 — Reduce: sort, cluster, dedupe, supersede — ORCHESTRATOR
0. **Sort the merged candidate pool by `mergedAt` (oldest → newest).** Supersession is applied in
   this order — *here in the reduce*, not by PR processing order — which is what makes the
   parallel map safe.
1. **Filter final decisions to only ADOPTED code-checkable candidates.** Human-attested facts,
   PARTIAL candidates, NOT-CODE candidates, and NOT-ADOPTED candidates are not emitted as decisions.
   Count them in the run summary as "not emitted / needs human follow-up" where useful, but keep the
   canonical decision files clean.
2. **Cluster recurring decisions** into a single entry with multiple evidence cites. Recurrence
   (same guidance re-litigated across PRs/reviewers) is a strong **confidence booster** — record
   every occurrence. (Real example: a "safer defaults" config rule recurred across 3 PRs over 3
   months — exactly the repeated cost a decision memory removes.) When clustering, preserve or
   synthesize one clear `futureBenefit` and one actionable `applicationCheck` for the clustered decision
   from the strongest evidence.
3. **Group into ≤5 category files and assign stable IDs.** Derive emergent topic buckets from the
   clustered decisions (not a fixed list); choose the **fewest, broadest** files that stay coherent,
   hard-capped at **5** — if a 6th topic appears, fold it into its nearest neighbour. ID = a short
   prefix from the topic + a number (e.g. `testing` → `T1`,
   `api-compat` → `A1`), stable thereafter.
4. **Supersession (recency wins), handled carefully:**
   - Distinguish three cases: **supersede** (same subject, new value — e.g. default 10s → 20s),
     **coexist** (different subject — a rule for service A vs service B), and **false
     contradiction** (the semantic match was wrong). Only *supersede* replaces.
   - **Tombstone, never delete.** Mark the superseded entry `superseded-by: <id>` + date and
     keep it. History is needed for audit (and contradiction-detection is itself an imperfect
     semantic match — keep the trail).
   - **Human-confirms every supersession** during file review or in the eventual review PR; never
     apply silently.
   - In `extend` mode, dedupe new candidates against the existing `docs/greybeard/` folder; skip
     anything already captured.

### Stage 6 — Emit + user review gate
Write the category files + `index.md`, then **stop and ask the user to review the generated
decision files before taking any PR action**. Report where the files were written and report counts
for candidates not emitted because they were human-attested, PARTIAL, NOT-CODE, or NOT-ADOPTED.

Do **not** create a PR automatically. After the user reviews the files and says there are no
concerns, suggest creating a normal review PR as the final precision backstop. Only create that PR
if the user explicitly approves.

---

## Confidence ranking

Record a `confidence` per emitted decision, ranked by evidence strength:
1. **High** — contested in review **and** adopted in the merged code (two parties + code proof).
2. **Medium** — stated in the PR description **and** corroborated by the merged code (single
   party, but the code shipped).
Do not emit low-confidence decisions. Human-attested facts, PARTIAL candidates, and NOT-ADOPTED
comments are not low-confidence canon; they are excluded from the final decision files.

---

## Decision entry format

Read `../decision-format.md` before writing or updating entries. That file is the canonical
schema shared by `/greybeard:learn`, `/greybeard:remember`, and `/greybeard:review`.

---

## Critical gotchas (learned the hard way — do not repeat)

1. **PR thread `status=fixed` proves nothing.** It is author-settable and does not mean the
   reviewer's point was adopted. Verify against the **merged code**, always (Stage 4).
2. **Never map PR→commit by bare PR number.** Anchor on `"Merged PR <N>:"` / the provider's
   `mergeCommit` field. Bare-number grep matches later PRs that merely reference this one.
3. **Give sub-agents the current file contents, not just the diff.** Diff-only context caused
   both a false-positive and a miss in validation. The adoption check needs full file state.
4. **Match comments to code by meaning, not line number.** Squash merges and later iterations
   relocate the original lines.
5. **Precision over recall.** Dropping a real decision costs a re-derivation later. Storing a
   wrong one poisons every future `review` run. When unsure, drop or flag for human.

---

## Output summary to the user

After the run, report: PRs scanned, candidates after pre-filter, emitted ADOPTED code-checkable
decision count, not-emitted counts (NOT-ADOPTED, PARTIAL, human-attested / NOT-CODE), and the path
to the generated `docs/greybeard/` files. Also list each generated markdown file with its decision
count so the user knows what to review, e.g.:

```text
Generated Greybeard decision docs in:
<repo>\docs\greybeard\

Files created:
- index.md — 49 decisions indexed
- auth-api.md — 9 decisions
- infrastructure-config.md — 13 decisions
- observability.md — 10 decisions
- testing-synthetics.md — 14 decisions
- data-operations.md — 3 decisions

Not emitted:
- NOT-ADOPTED — 0
- PARTIAL — 1
- human-attested / NOT-CODE — 2
```

Ask the user to review those files. Only include a review PR link if the user already approved PR
creation in a later step.
