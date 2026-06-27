# Testing

Decisions about how changes are tested before merge.

### T1. Gate merges on the contract test suite, not only unit tests
Unit tests pass while cross-service contracts drift, so a green unit run is not
enough signal to merge. The contract suite catches consumer-breaking changes that
mocked unit tests hide.

**Future benefit:** A future engineer wiring CI for a new service will know to wire
the contract suite into the merge gate, not just unit tests, avoiding a class of
integration breakages that only surface in production.

**Application check:** Confirm the merge gate runs the contract suite (not only unit
tests) for any service that publishes or consumes a shared contract.

- evidence-type: code-checkable
- confidence: high
- evidence:
  - PR 5102 - "added contract job to required checks after the v2 outage"
  - .ci/pipeline.yml - `contract-tests` listed under required status checks

### T2. Seed deterministic clocks in time-sensitive tests
Tests that read the wall clock flake across timezones and around midnight. We inject
a fixed clock so time-dependent assertions are reproducible.

**Future benefit:** A future engineer debugging a flaky time-based test will know the
convention is an injected fixed clock, not `DateTime.Now`, and can fix the flake at
its root instead of adding retries.

**Application check:** Time-sensitive tests must inject a fixed clock abstraction
rather than reading the system clock directly.

- evidence-type: code-checkable
- confidence: medium
- evidence:
  - PR 4490 - "use the injected IClock, the midnight rollover broke this twice"
  - tests/Scheduling/RolloverTests.cs - constructs `FakeClock(fixedInstant)`
