---
name: remember
description: Manually record ONE engineering decision into the project's decision memory (docs/greybeard/). Interviews the author to extract the rule + rationale + scope + evidence, classifies its evidence type, checks it against the existing bank for duplication/supersession, writes the entry, and opens a review PR. Use right after a design call, or whenever you want to capture a decision by hand instead of mining PR history.
---

# /greybeard:remember

Capture **one** decision the author already knows, by hand. Complements `/greybeard:learn`
(which mines many decisions from merged history) and feeds the same `docs/greybeard/` store that
`/greybeard:review` later checks new PRs against.

The author is the authority here — there is **no adoption check** (a recorded decision may be
forward-looking, about code that does not exist yet). But the skill still enforces quality: every
entry must be **generalizable, carry a "why", be scoped, be deduped against the bank, and pass a
review PR.** A sloppy manual entry poisons `review` exactly like a bad mined one — so this
skill is an interview, not a text box.

---

## Where decisions are stored

The same `docs/greybeard/` folder on the **main branch**, updated via normal PRs. Only `index.md`
is fixed; category files are **emergent and capped at 5**, named for what they cover:

```
docs/greybeard/
  index.md          # one-line summary + link per decision; the map (always present)
  <topic>.md        # emergent cluster — e.g. api-compat, testing, data-privacy. At most 5.
```

If `docs/greybeard/` does not exist yet, create it with an empty `index.md`; suggest running
`/greybeard:learn` first to bootstrap from history.

---

## Inputs (ask only for what's missing)

1. **statement** — the decision, however the author phrases it. Conversational is fine; the skill
   refines it.
2. **evidence** *(optional)* — a PR/commit/file/doc link, or `tribal: <who told you>`. If absent,
   the skill asks.
3. **category** — pick the **existing** category file whose topic is closest; propose a *new* file
   only if none fits **and** fewer than 5 exist. If 5 already exist and none fits, fold it into the
   nearest one (broaden that file's scope) rather than opening a 6th. Confirm the chosen/new
   category with the author.

---

## Flow

### 1. Interview to fill the gaps (do not store a vague one-liner)
Extract four things; ask only for what the author has not already given:

- **Rule** — a one-line imperative: "Always X", "Never Y", "Prefer X over Y".
- **Why** — the durable rationale a future engineer needs and cannot trivially re-derive. **If the
  author cannot articulate a why, push back** — a rule without a why is a style preference, not a
  decision, and it does not get stored.
- **Scope** — internal matching metadata for where it applies (which services / layers / file
  globs). Use it to choose the category and avoid false matches, but do not emit it into the final
  markdown entry.
- **Evidence** — what backs it (drives the evidence type, below).

### 2. Route the evidence type
- **Code-verified decision** — a convention / logic / config rule. Evidence = a PR/commit/file
  that demonstrates it, or an explicit "go-forward, no code yet."
- **Human-attested fact** — ownership, a gotcha, or a non-obvious fact no diff can confirm — e.g.
  "this event hub is owned by the platform team, 1 consumer group". **Requires a named attestor +
  a review-by/expiry date**, stored at lower confidence. A world fact with no human owner rots and
  there is no diff to re-verify it — so human-attested facts without an attestor are rejected.

### 3. Coherence check against the existing bank (read `index.md`, then the category file)
Before writing, compare the new decision to what is already recorded:

- **Duplicate** — the same rule already exists → offer to **add this evidence to the existing
  entry** instead of creating a second one.
- **Contradiction** — it directly breaks an existing decision → this is a **supersession**.
  Recency wins (the author is asserting the new reality), but:
  - **Confirm with the author** before overturning anything.
  - **Tombstone, never delete** — mark the old entry `superseded-by: <new-id>` + date and keep it.
  - Distinguish a true **supersede** (same scope, new value) from **coexistence** (different scope —
    e.g. a rule for service A vs service B). Coexistence keeps both.
- **New / coexisting** — assign the next stable ID in the category.

> Note: do **not** run learn's adoption check — the author, not a merged diff, is the source
> of truth. But if the **current code visibly contradicts** a code-verified go-forward rule, surface that
> as an FYI so the author records the decision knowingly (and can file the follow-up to fix code).

### 4. Draft the entry + write it
Render in the standard entry format (below). Append to the right category file, add the `index.md`
line, and set confidence:
- **high** — author + concrete code/PR evidence.
- **medium** — author assertion; evidence thin or forward-looking.
- **low-needs-attestation** — human-attested facts, or any entry whose why/evidence the author
  could not fully pin down.

### 5. Open a review PR
Same human gate as learn — nothing becomes canon until a teammate approves. In the PR body,
surface the **evidence type**, the **confidence**, and **any supersession this triggers** (so the
reviewer sees exactly what is being overturned and why).

---

## Decision entry format

```markdown
### <ID>. <one-line imperative statement of the rule>
<1–3 sentence elaboration, including the WHY.>

- evidence-type: code-verified | human-attested
- confidence: high | medium | low-needs-attestation
- evidence:
  - PR <N> (<date>) — "<verbatim quote or author's stated rationale>"
  - <commit/file/doc pointer, if any>
- attestor: <alias>  review-by: <date>      # human-attested only (required)
- superseded-by: <ID> (<date>)              # only if tombstoned
```

`index.md` carries one line per decision: `- <ID> (<file>) — <one-line statement> [conf]`.

---

## Gotchas

1. **A rule without a why is a preference — do not store it.** The "why" is what makes the bank
   worth more than a linter config.
2. **Scope it tightly.** An over-broad rule makes `review` flag conformant code — the precision
   failure that destroys trust in the whole system.
3. **Never silently overwrite a contradicting decision.** Tombstone + human-confirm; keep the trail.
4. **Human-attested facts without attestor + expiry are forbidden.** There is no diff to re-verify a
   world fact, so it needs a human owner and a refresh date.
5. **One decision per run.** If the author rattles off several, capture them one at a time so each
   gets a real interview — batch capture is what `/greybeard:learn` is for.
