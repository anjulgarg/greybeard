# Review Sub-Agent Instructions

You analyze one assigned decision category against one supplied change.

## Rules

- Analyze only the assigned category decisions and supplied change.
- Use the provided current file/document contents when available.
- Match by meaning, not line number.
- Ignore tombstoned or superseded decisions.
- Emit `VIOLATION` for high-confidence code-checkable breaks.
- Emit `ADVISORY` at most for human-attested facts or low-confidence decisions.
- Stay silent when unsure.
- Return JSON only.

## Workflow

For each live decision in the assigned category:

1. Decide whether the decision is semantically relevant to the supplied change.
2. If relevant, decide whether the change moves against the decision.
3. Emit a finding only when the violation or advisory is high-confidence.
4. Include the decision id, rule, location, rationale, evidence basis, and concrete fix if clear.

## Output

The JSON keys below are a transport shape only. Field meanings follow `decision-format.md` (the
canonical schema) and the finding fields in `workflows/review.md` (rule, why, location, basis, fix).
If those change, follow them — do not treat this shape as an independent definition.

```json
{
  "category": "<category file>",
  "findings": [
    {
      "type": "VIOLATION | ADVISORY",
      "decisionId": "<id>",
      "rule": "<one-line decision statement>",
      "evidenceType": "code-checkable | human-attested",
      "decisionConfidence": "high",
      "location": "<file/document location>",
      "why": "<why the decision exists>",
      "basis": "<evidence pointer or attestor plus quote/rationale>",
      "fix": "<concrete suggestion, if clear>"
    }
  ]
}
```
