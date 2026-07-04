---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - 3.0
  - related-entries
  - graph
---

# Typed Supersession Edges - Scope

> **Status: P1 IMPLEMENTED (unreleased).** Schema parsing, the read-time `superseded_by` inverse,
> `links check` validation (dangling/self/postdates/cycle), `link show` + `memory_get_chunk`
> exposure, and the `session_logging.md` schema doc shipped 2026-07-03; the harmony-contract
> dampening shipped 2026-07-04 with `interaction-frequency-ranking-plan.md` P1b
> (`SUPERSEDED_IMPORTANCE_DAMPING = 0.25`, with the required fixture). Still open: the deferred P2
> Lense UI surfacing. Source: external review doc
> `Memory-Seed Logic Capture Improvement.md` (the "Supersession Pointer" field in its proposed
> decision schema). Companion to
> [`related-entries-generation-plan.md`](related-entries-generation-plan.md) (extends the same
> forward-edge / bidirectional-read-time-traversal model) and
> [`interaction-frequency-ranking-plan.md`](interaction-frequency-ranking-plan.md) (defines the
> harmony contract below that the ranking plan depends on). The field name is `supersedes`; the
> alternative `deprecates` is rejected for P1 to avoid leaving the schema undecided.

## Motivation

There is currently no way to mark a decision entry as replaced or deprecated by a later one.
Combined with interaction-frequency ranking (see the companion plan), this is not just a missing
feature but a **correctness hazard**: if "importance" is derived from how many entries link to a
given entry, a stale, superseded decision that a newer entry explicitly points back at gains an
inbound edge *because it was deprecated* — the opposite of the intended signal. A naive
implementation would resurface dead decisions as if they were load-bearing.

## What Exists Today

`MemoryChunk.related_entries` (`memory_seed/semantic_cache.py:55`) is a flat `tuple[str, ...]` of
entry IDs — a single, untyped edge kind. `build_related_entry_graph()`
(`memory_seed/semantic_cache.py:209-250`) computes `outbound` (as stored) and `inbound` (computed
at read time by scanning every entry's `related_entries` for refs pointing at this one) per entry,
returned as a `RelatedEntryNode`. There is no mechanism, typed or otherwise, for expressing "this
decision replaces that one."

## Design Model

### Schema: a sibling field, not a variant of `related_entries`

```yaml
entry_id: mse_...
...
related_entries: []
supersedes:
  - mse_older_decision_id
```

`supersedes` is parsed identically to `related_entries` today: forward-only (an entry may only
reference entries that already existed when it was written), optional, a flat list of entry IDs.
The computed inverse, `superseded_by`, is built at read time the same way `inbound` is computed for
`related_entries` (`semantic_cache.py:230-248` is the exact pattern to mirror).

**Why a separate field instead of a tagged variant inside `related_entries`:** this is purely
additive. `related_entries` parsing, `links check`, `memory_search`/`memory_get_chunk`, and
`link suggest`/`link show` are untouched — nothing already shipped can regress. `supersedes` is a
new, independent field read the same way.

### Free correctness property

Because `supersedes` edges are forward-only — an entry can only reference an entry that already
existed when it was written — the supersession graph is provably acyclic. No cycle-detection code
is needed; this is the same guarantee `related_entries` already gets from the append-only
constraint, extended for free.

## Validation

`supersedes` refs get the same dangling-ref check as `related_entries`, ideally through the same
`links check` gate rather than a parallel validator.

**Known dependency — resolved (2026-07-02, unreleased, shared with `git-commit-entry-linking-plan.md`):**
`check_session_links()`'s `related_entries` dangling-ref scan used to be scoped inside
`if doc.layout != "per-user-day": continue`, so it never ran against legacy-flat
`.memory-seed/sessions/YYYY-MM-DD.md` files (this repository's own layout). Fixed by moving the
entry-level scan out of that gate — `supersedes` validation can reuse the same, now-correct `links
check` path from day one instead of inheriting the blind spot.

**Forward-only is a convention, not yet an enforced invariant.** The "provably acyclic" claim above
holds only if every `supersedes` ref actually points at an entry that existed before the referencing
one — today `links check` only confirms a ref *resolves* to a known `entry_id` (`dangling-related-entry`
style), not that it's chronologically prior. A hand-edited or buggy-writer YAML block could in
principle create a cycle undetected. A cheap forward-only/cycle guard in `links check` for
`supersedes` (and ideally `related_entries`) is in P1 scope (signed off 2026-07-03): reject or flag
a ref whose target entry postdates the referencing entry.

## Harmony Contract With Interaction-Frequency Ranking

This is the core design constraint this doc exists to pin down, agreed during review:

1. **`importance_score`** = inbound `related_entries` count only. `supersedes`/`superseded_by`
   edges are never folded into this count.
2. **`superseded` status** = "does this entry have any inbound `supersedes` edge?" If true, apply a
   fixed dampening multiplier to `importance_score` **after** it is computed — a hard override, not
   a merged tally. A well-cited-but-superseded entry should rank low; a superseded entry should
   never look "hot" just because something replaced it.
3. **Outbound `supersedes` count** (how many decisions this entry retires) is surfaced as metadata
   only — it must not itself add to `importance_score`, or a large cleanup entry could game its own
   rank by superseding many old decisions at once.
4. **Never hide, only deprioritize.** A superseded entry stays fully retrievable — directly, or via
   its `superseded_by` pointer to current truth — consistent with the project's append-only,
   nothing-destroyed model. `3.0-plan.md`'s B5 already takes this position for curation generally
   ("later curation should use separate annotation/patch records rather than silently rewriting
   session history").
5. **This rule extends unchanged to Option B** (real interaction/access-frequency events, the
   stated end goal of the ranking plan): an access hit on a superseded entry gets the same
   dampening, never suppression.

This means `interaction-frequency-ranking-plan.md` may expose a raw related backlink degree before
`supersedes` ships, but it must not claim a supersession-aware `importance_score` until this P1 is
implemented.

## Exposure

Extend `memory-seed link show <entry_id>` and `memory_get_chunk` output to include `supersedes` /
`superseded_by` alongside the existing `related_entries` outbound/inbound fields.

## Phasing

- **P1:** schema + parsing + read-time inverse (`superseded_by`) + `links check` validation +
  `link show` exposure.
- **P2 (deferred, optional):** Lense UI surfacing — a deprecation banner or timeline chain showing
  the supersession lineage of a decision. Consistent with `3.0-plan.md` B5's stance that UI curation
  work stays out of the read-only Explorer MVP until there's real usage pressure for it.

## Open Decisions

1. ~~Field name: `supersedes` vs. `deprecates`~~ — resolved for P1: use `supersedes`. It is the
   term already used throughout the plan, matches "this entry replaces that older decision," and
   avoids a second naming pass across session schema, CLI, MCP, and UI docs.
2. Should `memory-seed link suggest` also propose supersession candidates, or stay
   `related_entries`-only for now? Leaning toward staying `related_entries`-only in P1 — suggesting
   *what to deprecate* is a much higher-stakes judgment call than suggesting *what's related*, and
   shouldn't be automated without more signal.
3. ~~The legacy-flat `links check` gap~~ — resolved 2026-07-02 (see Known Dependency above); no
   longer blocking either this plan or `git-commit-entry-linking-plan.md`.
4. ~~Exact dampening multiplier value for the harmony contract~~ — resolved 2026-07-04:
   `SUPERSEDED_IMPORTANCE_DAMPING = 0.25`, shipped with `interaction-frequency-ranking-plan.md` P1b.

## Definition of Done (P1)

- [x] `supersedes` documented in `session_logging.md` alongside `related_entries`.
- [x] Read-time `superseded_by` inverse computed and exposed via `link show` / `memory_get_chunk`.
- [x] `links check` validates `supersedes` refs with the same rigor as `related_entries` (post-fix,
  not inheriting the legacy-flat gap silently).
- [x] A forward-only/cycle guard in `links check` for `supersedes` (see Validation above) — shipped
  2026-07-03 (`supersedes-postdates` + `supersedes-cycle`), replacing the unenforced convention.
- [x] The harmony-contract dampening rule implemented wherever `importance_score` is computed
  (`interaction-frequency-ranking-plan.md` P1b, shipped 2026-07-04), with a fixture test proving a
  superseded-but-heavily-cited entry ranks below a non-superseded, moderately-cited one.
- Concise session log entry.
