# Learn extraction eval (deferred)

The full `/greybeard:learn` extraction eval is **deferred until after the MVP**.

`learn` mines merged PR history (review comments, PR descriptions, merged diffs) and
verifies each candidate against the code that actually shipped. A faithful eval
therefore needs:

- **Snapshotted provider data** — PR lists, comment threads, descriptions, and merged
  diffs captured offline so the eval needs no network access.
- **Semantic matching** — extraction is fuzzy, so scoring extracted decisions against
  a gold set requires meaning-level comparison, not exact string match.

Both are heavier than the MVP tiers, so this stays empty for now. The MVP still covers
`learn`'s most important gate transitively: its adoption/candidate logic is the shared
`references/decision-candidate.md` bar that **Tier 1** exercises directly.

When implemented, this folder will contain snapshotted PR fixtures plus a gold decision
set, and a `tier3` extraction eval that scores precision/recall against it.
