# API Compatibility

Decisions about keeping published APIs and shared contracts stable.

### A1. Never remove a public API field without a deprecation window
Removing a field that external clients still read breaks them silently at runtime.
We keep removed fields serialized and documented as deprecated for at least one
release so consumers can migrate before the field disappears.

**Future benefit:** A future engineer trimming a response model will know the field
must survive a deprecation window, sparing downstream teams a surprise outage when
they upgrade.

**Application check:** When a field is deleted from a public response type, verify a
deprecation notice shipped at least one release earlier and the field is still
serialized until the window closes.

- evidence-type: code-checkable
- confidence: high
- evidence:
  - PR 4821 - "we cannot drop `legacyId` yet, two partners still read it"
  - src/api/UserResponse.cs - retains `[Obsolete] LegacyId` behind the deprecation flag

### A2. The billing event hub is owned by the Payments team
The `billing-events` hub has a single consumer group and a strict ordering
contract; changes to its schema must be coordinated with Payments before shipping
because no diff in this repo can prove the downstream impact.

**Future benefit:** A future engineer touching billing event schemas will know to
coordinate with Payments first instead of discovering the ownership boundary after
breaking the consumer.

**Application check:** Before changing any `billing-events` schema or partition key,
confirm sign-off from the Payments team named below.

- evidence-type: human-attested
- confidence: low
- evidence:
  - attested by platform-lead - "Payments owns billing-events, one consumer group, ordered"
- attestor: platform-lead

### A3. Version GraphQL types with explicit schema directives
Superseded: we moved off GraphQL to typed REST contracts, so this rule no longer
applies to current code.

**Future benefit:** Historical context only.

**Application check:** Not applicable; kept as a tombstone.

- evidence-type: code-checkable
- confidence: medium
- evidence:
  - PR 3110 - "tag every GraphQL type with @version"
- superseded-by: A5 (2024-11-02)
