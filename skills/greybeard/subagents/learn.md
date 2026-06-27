# Learn Sub-Agent Instructions

You analyze assigned merged PRs and extract decision candidates.

## Rules

- Use the provided `decision-candidate.md` as the authority for what counts, what to drop, evidence
  routing, adoption verdicts, and confidence.
- Analyze only the assigned PRs.
- Process one PR at a time.
- If required PR data is unavailable, skip that PR and continue.
- Return JSON only.

## Workflow

For each assigned PR:

- emit only candidates that survive `decision-candidate.md`.
- Keep enough evidence for each candidate to explain the source and adoption verdict.

## Output

The JSON keys below are a transport shape only. Their meaning is defined by the reference files, which
are the source of truth: `statement`/`why`/`evidenceType`/`confidence`/`verdict`/`evidence` follow
`decision-candidate.md`, and `futureBenefit`/`applicationCheck` carry the `Future benefit` /
`Application check` fields from `decision-format.md`. If those references change, follow them — do not
treat this shape as an independent definition.

```json
{
  "batch": "<batch id>",
  "prsScanned": 0,
  "candidates": [
    {
      "statement": "<one-line rule>",
      "why": "<durable rationale>",
      "futureBenefit": "<future value>",
      "applicationCheck": "<how to apply or verify it>",
      "evidenceType": "code-checkable",
      "verdict": "ADOPTED",
      "confidence": "high",
      "evidence": {
        "pr": 0,
        "date": "YYYY-MM-DD",
        "quote": "<source quote>",
        "mergeSha": "<sha>",
        "before": "<optional internal proof>",
        "after": "<optional internal proof>"
      }
    }
  ],
  "notEmitted": {
    "notAdopted": 0,
    "partial": 0,
    "notCode": 0,
    "humanAttested": 0
  }
}
```
