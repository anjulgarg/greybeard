# Greybeard Decision Entry Format

This file is the canonical format for entries in `docs/greybeard/` category files.
Skills that write or interpret decisions must read this file instead of carrying a local copy of
the schema.

Each decision entry in a category file:

```markdown
### <ID>. <one-line imperative statement of the rule>
<1-3 sentence elaboration, including the WHY.>

**Future benefit:** <1-2 sentences explaining how this decision helps future engineers make better
decisions in this project, grounded in the actual service/config/test/operational reality.>

**Review check:** <1 sentence telling reviewers exactly what to check in future changes to apply
this decision, such as required evidence, code/config shape, tests, rollout boundary, operational
proof, or coordination to ask for.>

- evidence-type: code-verified | human-attested
- confidence: high | medium | low-needs-attestation
- evidence:
  - PR <N> (<date>) - "<verbatim reviewer quote or description excerpt>"
  - <commit/file/doc pointer, if any>
- attestor: <alias>  review-by: <date>      # human-attested only (required)
- superseded-by: <ID> (<date>)              # only if tombstoned
```

`index.md` carries one line per decision:

```markdown
- <ID> (<file>) - <one-line statement> [conf]
```

Rules:

- `Future benefit` is required. If it cannot be written clearly and specifically, do not canonize
  the candidate.
- `Review check` is required. If there is no concrete future check, the decision is too vague for
  `review`.
- `evidence-type` and `confidence` are entry fields, not file-level frontmatter.
- Human-attested entries require `attestor` and `review-by`.
- Do not store a separate applicability field. Relevance is judged semantically from the decision
  text, category, evidence, and changed content.
