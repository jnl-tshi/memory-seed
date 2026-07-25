---
title: Append-only link retraction
status: draft
spec_binding: draft
parent: ../lifecycle-edge-linking-sidecars.md
---

# Append-Only Link Retraction

Status: **DRAFT — IMPLEMENTED 2026-07-25.** Extends the live contract
[lifecycle-edge-linking-sidecars.md](../lifecycle-edge-linking-sidecars.md).

## Why

Link sidecars are append-only: a published edge's block is never reopened (the fuse enforces this — it
refuses a merge that modifies an existing block). That left no sanctioned way to **downgrade or remove**
a published edge — e.g. a hand audit finding an `evolves` was really a `related`. Editing the block in
place bypasses the guard; deleting it loses history. `retracts:` gives the removal an append-only
spelling: a *new* block (which the fuse accepts) declares that a prior edge no longer holds, and the
reader subtracts it from the effective set.

## Shape

A link-sidecar block MAY carry a `retracts:` list. Each item names a previously-declared edge to remove,
in the grammar the edge was authored with, optionally suffixed with the original declaration date:

```
<kind> <ref> [(<YYYY-MM-DD>)]
```

`<kind>` is `replaces` / `evolves` / `related_entries` (or the `related` / `supersedes` aliases). `<ref>`
is the exact target ref — `mse_x`, `mse_x:d1`, or `d2 -> mse_x:d1`. The block's own `entry_id` is the
edge source. The optional date pins which declaration (the "use the date and the id" handle) for
provenance and the forward-only check.

A **downgrade** is a retract of the old kind plus a fresh edge of the new kind, authored together in the
correction block — append-only, no block reopened:

```yaml
## 2026-07-26 09:00 - Reclassify: X was a landing, not an evolve
entry_id: mse_source
retracts:
  - evolves mse_x:d3 (2026-07-25)
related_entries:
  - mse_x:d3
note: hand-audit rule 5
```

## Semantics

- **Reader** (`entry_link_sidecars`): unions every block's edges as before, then subtracts each retracted
  edge. Entry-level retracts match by `(kind, target_id)`; decision retracts match the exact
  `(kind, source_ordinal, target_id, target_ordinal)` tuple. A downgrade therefore lands as
  `evolves = ()` + `related_entries = (target,)`. An **arrow-prefixed bare ref** (`d2 -> X`) is one
  authored statement collected as TWO edges — an entry-level edge AND a source-only decision edge
  `(kind, dN, X, "")` — so retracting it removes both twins, or the decision edge would silently survive.
- **`links check`** validates: `malformed-retract` (unparseable item); `dangling-retract` (names an edge
  the corpus never declared for this entry — nothing to remove); `retract-before-declaration` (filed
  earlier than the edge it removes — forward-only, like every lifecycle statement).
- **Fuse**: the correction is a new block, so `session merge-branch` accepts it — no bypass needed.

## Deferred

Cross-file retraction (a retract filed under a different date than the declaration) is validated by
identity but the date-mismatch nicety is not surfaced. A `reclassifies:` sugar (retract-plus-readd in one
item) could reduce the two-line downgrade to one; not built — the explicit pair is clearer for now.
