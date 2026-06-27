# /greybeard:learn

Bootstrap or extend a repository's decision memory by mining merged pull-request history and
writing decision files under `docs/greybeard/`.

This workflow is precision-biased. When a candidate is ambiguous, contradictory, or weakly
evidenced, drop it or report it as not emitted. A wrong decision is worse than a missing one because
it makes future `/greybeard:review` runs untrustworthy.

---

## Read first

Before scanning, read:

- `../references/decision-candidate.md` - canonical rules for what counts, what to drop, evidence
  routing, adoption verdicts, and confidence.
- `../references/decision-format.md` - canonical markdown format for accepted decisions.
- `../subagents/learn.md` - system instructions and JSON contract for every PR-scanning sub-agent.

This file owns orchestration only. Do not duplicate candidate rules here.

---

## Where decisions are stored

Write decisions to `docs/greybeard/`, intended for the main branch through normal PR review:

```text
docs/greybeard/
  index.md
  <topic>.md
```

`index.md` is always present. Topic files are emergent from the accepted decisions and capped at 5,
because `/greybeard:review` uses one sub-agent per decision file. Prefer the fewest broad coherent
topic files; if a sixth topic appears, fold it into the nearest existing topic.

---

## Inputs

Ask the user how much history to scan before doing expensive work. Offer:

- Last 100 merged PRs.
- All merged PRs from the last year.
- All merged PRs from project history.
- A custom count or date range.

Also determine:

- `provider` - GitHub (`gh`) or Azure DevOps (`az repos` / `az devops invoke`), auto-detected from
  remotes when possible.
- `mode` - `bootstrap` for an empty `docs/greybeard/`, or `extend` to dedupe against existing
  decisions.
- `maxSubAgents` - at most 5 for the whole run. Use fewer when simpler.

---

## Execution model

Use a map-reduce workflow:

```text
ORCHESTRATOR
  enumerate eligible merged PR refs
  confirm scan size with the user
  split selected PRs into <=5 batches
      |
      | fan out one learn sub-agent per batch
      v
SUB-AGENTS
  process assigned PRs one at a time
  apply decision-candidate.md
  return JSON defined by subagents/learn.md
      |
      v
ORCHESTRATOR
  merge results
  sort by PR merge date
  filter, cluster, dedupe, supersede
  write docs/greybeard/
  ask user to review
```

Rules:

- PR scanning always happens through sub-agents, even for small scans. Use one sub-agent for tiny
  scans.
- Spawn at most 5 sub-agents total.
- Put every selected merged PR in exactly one batch.
- Sub-agents may write scratch/output files, but only the orchestrator writes final
  `docs/greybeard/` files.
- Ordering lives in the reduce step. Do not rely on PR processing order inside batches.
- If a batch fails or returns malformed JSON, retry that batch or process it directly in the
  orchestrator.

---

## Stage 0 - Enumerate and batch

List completed/merged PRs only. Exclude active and abandoned PRs because they have no accepted merge
commit and may represent rejected proposals.

Capture at least:

- PR number or ID.
- Title.
- Merge commit SHA.
- Merge date.

For GitHub slices, use refs only:

```bash
gh pr list --state merged --limit <limit> --json number,title,mergeCommit,mergedAt
```

For Azure DevOps, list PRs with `status=completed` and capture `pullRequestId`, `lastMergeCommit`,
`title`, and `closedDate`.

If a provider exposes a reliable total count, report it. If not, report the size of the selected
slice instead of pretending it is a repository-wide total.

Never map a PR to a commit by grepping for the bare PR number. Prefer the provider's merge-commit
field. If you must derive a squash-merge commit locally, anchor on the literal merge-message prefix,
such as `Merged PR <N>:`.

Split the selected PRs into at most 5 work-balanced batches. If comment/thread counts are cheaply
available, balance by that count; otherwise split by PR count.

---

## Stage 1 - Fan out PR-scanning sub-agents

For each batch, start one sub-agent using `../subagents/learn.md`.

Give each sub-agent:

- The assigned PR refs.
- `../references/decision-candidate.md`.
- Enough provider/repo instructions to fetch review comments, PR descriptions, merge-commit bodies,
  merged diffs, and final/current file contents needed for adoption checks.

The sub-agent processes one PR at a time and returns only the JSON object defined in
`../subagents/learn.md`. It does not assign stable decision IDs and does not write
`docs/greybeard/`.

---

## Stage 2 - Reduce

Merge all sub-agent JSON results, then:

1. Sort candidates by PR merge date from the Stage 0 refs, oldest to newest.
2. Apply the verdict and evidence rules from `../references/decision-candidate.md`; emit only
   accepted `/greybeard:learn` decisions.
3. Cluster repeated guidance into one decision with multiple evidence cites.
4. In `extend` mode, dedupe against existing `docs/greybeard/` entries.
5. Assign stable IDs after clustering.
6. Group decisions into at most 5 topic files.
7. Handle supersession conservatively:
   - Supersede only when the new decision is the same subject with a new value or rule.
   - Keep superseded entries as tombstones with `superseded-by: <ID> (<date>)`.
   - Ask for human confirmation before finalizing supersession.

Use `../references/decision-format.md` when writing entries and `index.md`.

---

## Stage 3 - Write and stop

Write the generated category files and `index.md`, then stop for user review.

Do not create a PR automatically. After the user reviews the generated files and says there are no
concerns, suggest creating a normal review PR as the next step. Only create that PR if the user
explicitly approves.

---

## Output summary

Report:

- PRs scanned.
- Candidate count returned by sub-agents.
- Accepted decision count.
- Not-emitted counts from the sub-agent JSON.
- Generated `docs/greybeard/` path.
- Each generated markdown file and its decision count.

Example:

```text
Generated Greybeard decision docs in:
docs/greybeard/

Files created:
- index.md - 49 decisions indexed
- auth-api.md - 9 decisions
- infrastructure-config.md - 13 decisions
- observability.md - 10 decisions
- testing-synthetics.md - 14 decisions
- data-operations.md - 3 decisions

Not emitted:
- NOT-ADOPTED - 0
- PARTIAL - 1
- human-attested / NOT-CODE - 2
```
