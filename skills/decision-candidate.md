# Greybeard Decision Candidate Rules

These rules decide whether a comment, PR description point, author statement, or document note is
eligible to become a Greybeard decision. Skills that identify or accept decisions must read this
file before applying skill-specific mechanics.

`decision-candidate.md` governs **what counts**. `decision-format.md` governs **how accepted
decisions are written**.

---

## The Bar

A decision candidate must answer all four questions:

1. **What should future engineers do, avoid, or prefer?**
2. **Why does that rule exist?**
3. **When would a future engineer apply it?**
4. **What evidence backs it?**

If any answer is missing, do not store it as a decision.

---

## A Decision Candidate Is

Keep investigating when the item is:

- **Durable** - expected to matter after the original PR, task, meeting, or incident is gone.
- **Generalizable** - applies to a future, different change, not only the exact line being edited.
- **Actionable** - it can shape a concrete code/config/test/docs/design/rollout/operational choice.
- **Rationalized** - includes a non-trivial reason a future engineer should not have to rediscover.
- **Evidenced** - backed by merged code, a PR/commit/file/doc link, or named human attestation.

Strong positive signals:

- A reviewer objected, the author changed code, and the merged diff confirms the change.
- A PR description states a rule and the merged code implements it.
- The same guidance appears across multiple PRs or reviews.
- The item explains operational, compatibility, security, privacy, rollout, ownership, reliability,
  data, API, or testing rationale.
- The rule would prevent a future engineer from rediscovering the same non-obvious constraint,
  tradeoff, or risk.

---

## Not A Decision

Drop the item immediately when it is:

- A one-off bug fix, typo, migration chore, or local cleanup.
- A pure style nit with no project-specific rationale.
- A question with no settled answer.
- Status noise: "LGTM", "fixed", "done", "bump coverage", stale-bot output, approval-only comments.
- A request that was overruled, ignored, or contradicted by the merged code.
- A comment whose only meaning is "change this exact line here".
- A generic quality phrase: "make this cleaner", "improve maintainability", "add tests" with no
  specific future check.
- A restatement of a tool-enforced rule unless the rationale or exception policy is the useful part.
- A fact about the world with no named attestor.
- A candidate whose future engineer would not know how to apply or verify it.

---

## Elimination Rules

Apply these before writing or emitting a candidate:

1. **No why, no decision.** If the rationale is missing or generic, drop it.
2. **No future application check, no decision.** If a future engineer cannot apply or verify it
   concretely, drop it.
3. **No evidence, no decision.** Evidence can be code-checkable or human-attested, but it must exist.
4. **Merged code beats comments.** For code-backed candidates, comments, approvals, and thread status
   are clues only. If merged code does not adopt the rule, do not emit it as a decision.
5. **Unclear adoption means no canon.** If code adoption is ambiguous, mark it PARTIAL or drop it;
   do not store it as an accepted code-checkable decision.
6. **World facts need an owner.** If code cannot prove the claim, require a named `attestor`.
7. **Prefer silence to poison.** A missed real decision costs rediscovery. A wrong decision makes
   future use untrustworthy.

---

## Evidence Routes

### Code-Checkable Decision

Use this route when code, config, tests, docs, or build/deploy artifacts can prove whether the rule
is applied. For mined PRs, this requires adoption proof from the merged code. For a forward-looking
`/greybeard:remember` entry where no implementation exists yet, use this route because the future
check is code/config/test/docs evidence, but mark it medium confidence and state that it has no code
evidence yet.

Required evidence:

- PR, commit, file, or document pointer.
- Original quote or description point.
- For mined PRs, the merged diff and final/current contents needed to verify adoption.
- For forward-looking manual entries, the named author/source and the explicit statement that this
  is a go-forward rule with no code evidence yet.

### Human-Attested Fact

Use this route when the claim is useful but no diff can prove it, such as ownership, external
constraints, consumers, support boundaries, or operational gotchas.

Required evidence:

- Named `attestor`.
- Short explanation of why the fact matters to future work.

`/greybeard:learn` reports human-attested facts as not emitted. `/greybeard:remember` may store
them at low confidence when the attestor is present.

---

## Learn-Specific Rules

When mining PR history:

- Review comments must have either led to a merged code change or drawn a substantive human reply.
- PR descriptions can be candidates even with no comments, but only when they state a rule plus
  rationale and the merged code corroborates it.
- Do not drop bot comments by author alone. A bot comment that led to a merged code change or a
  substantive human reply is valid evidence.
- Process each PR independently first; clustering, stable IDs, and supersession happen later.

Adoption verdicts:

- **ADOPTED** - merged code moved in the candidate's direction. Keep for reduce.
- **NOT-ADOPTED** - merged code did not change as requested, did the opposite, or retained the
  complained-about behavior. Do not emit.
- **PARTIAL** - partly adopted, unclear, or adopted as an explicit deviation from the literal ask.
  Flag for human; do not emit as canon.
- **NOT-CODE** - the item is a world fact or non-code claim. Route as human-attested; `/learn` does
  not emit it.

---

## Remember-Specific Rules

When capturing a decision by hand:

- The author can be the source of truth; a merged-code adoption check is not required.
- The candidate still needs a rule, why, future application check, and evidence.
- Forward-looking rules are allowed, but if current code visibly contradicts the rule, surface that
  contradiction before writing.
- Human-attested facts still require `attestor`.

---

## Final Test

Before accepting a candidate, ask:

> Would this change how a future engineer designs, implements, reviews, operates, or de-risks a change?

If not, drop it.
