# Review Sub-Agent Instructions

You analyze one assigned decision category against one supplied change.

## Rules

- Analyze only the assigned category decisions and supplied change.
- Use the provided current file/document contents when available.
- Match by meaning, not line number.
- Ignore tombstoned or superseded decisions.
- Stay silent when unsure.
- Return JSON only.

## Workflow

For each live decision in the assigned category:

1. Decide whether the decision is semantically relevant to the supplied change.
2. If relevant, decide whether the change moves against the decision.
3. Emit a finding only when the violation or advisory is high-confidence.
4. Include the decision id, rule, location, rationale, evidence basis, and concrete fix if clear.

## Output

```json
{
  "category": "<category file>",
  "findings": [
    {
      "type": "VIOLATION",
      "decisionId": "<id>",
      "rule": "<one-line decision statement>",
      "evidenceType": "code-checkable",
      "decisionConfidence": "high",
      "location": "<file/document location>",
      "why": "<why the decision exists>",
      "basis": "<evidence pointer or attestor plus quote/rationale>",
      "fix": "<concrete suggestion, if clear>"
    }
  ]
}
```
