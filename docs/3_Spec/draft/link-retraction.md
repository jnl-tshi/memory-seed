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
  earlier than the edge it removes — forward-only, like every lifecycle statement). "Declared" spans
  BOTH surfaces an edge can be authored on — the entry's own YAML and the link sidecars. Reading only
  the sidecar half (the shape shipped 2026-07-25) reported a false `dangling-retract` for every
  entry-YAML edge — a refusal the reader had already stopped agreeing with on 2026-08-09, when
  retracts gained their reach into entry YAML.
- **Fuse**: the correction is a new block, so `session merge-branch` accepts it — no bypass needed.

## The command

Hand-formatting the correction block was the only way to author one until 2026-08-10, while
retract-and-retype is the *mandated* fix for three `links check` errors — `untyped-evolves`,
`unknown-evolution-type` and `multiple-refines-successors`. `link retract` (CLI) and
`memory_link_retract` (MCP) write it:

```
memory-seed link retract <kind> <ref> --from <entry_id>
    [--retype <kind-or-evolution-type>] [--note ...] [--date-pin YYYY-MM-DD] [--dry-run]
```

`--from` is the edge's SOURCE entry; its session date selects the sidecar file
(`sessions/links/YYYY-MM/YYYY-MM-DD.md`), and the block heading carries the **authoring** wall clock, so
a later correction joins the same entry rather than colliding with an earlier block — block identity is
`(entry_id, heading timestamp)`. `<ref>` is spelled exactly as the edge was authored, arrow prefix and
`(type)` suffix included. `--retype` names either an edge kind (`replaces` / `evolves` /
`related_entries`) or an evolution type (`refines` / `builds-on`, which imply the `evolves:` key and ride
as a trailing token); omitting it leaves a pure retraction.

**Comma fan-out.** A retract names exactly ONE edge, so `mse_x:d1,d3` becomes one retract line per
ordinal — while the re-authored line keeps the comma form, which the ordinary ref grammar allows:

```yaml
## 2026-08-10 12:00 - edge retracted and retyped

entry_id: mse_source
retracts:
  - evolves mse_x:d1
  - evolves mse_x:d3
evolves:
  - mse_x:d1,d3 (refines)
```

**Guards, all before any byte is written**, reported together so each is independently fixable: unknown
kind or unparseable ref; unknown source entry; an edge the corpus never declared (the checker's
`dangling-retract`, using the same vocabulary); a retraction that would pre-date its declaration; a
`--date-pin` that is not the declaration date; a `refines` retype whose one successor slot **another**
entry already holds (the holder is named — when the current holder is the very edge being retracted,
that call IS the retype and is allowed); and a heading stamp already taken by a block for that entry.
After a successful write the CLI re-runs `links check` and exits non-zero if the write introduced an
error, the same contract `link add` carries. `--dry-run` / `dry_run` runs every guard and returns the
rendered block without writing.

`memory_link_retract` is the first MCP link-WRITE tool. It takes the same parameters, returns the
`memory_session_append` shape (`ok` / `written` / `path` / `issues` / `rendered`, plus `retracted`,
`reauthored` and `reauthored_key`), and carries **no** `merge_trigger` gate: an append-only correction
lands nothing and publishes nothing, so the authorization the integrate path needs has no counterpart
here. It refuses a `cwd` with no runtime rather than minting a phantom `.memory-seed/` tree.

## Deferred

Cross-file retraction (a retract filed under a different date than the declaration) is validated by
identity but the date-mismatch nicety is not surfaced. A `reclassifies:` sugar (retract-plus-readd in one
item) could reduce the two-line downgrade to one; not built — the explicit pair is clearer for now.
