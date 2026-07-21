# Lifecycle-edge linking sidecars + end-of-session sweep

Status: IMPLEMENTED and reconciled 2026-07-16. This document is the live contract for the sidecar
format, read/validation semantics, and the inert `link audit --apply` scaffold workflow.
As-built deviations from the original draft: ref extraction uses the wider
`_TRAILER_ENTRY_ID_RE` (real corpus ids include non-Crockford letters; a strict regex silently
dropped edges), and `link audit` generates candidates from topic/file overlap (no all-pairs
semantic scan) with `--for <entry_id>` and `--date YYYY-MM-DD` scoping (the sweep audits only the
session's own entries against the full corpus). Since 2026-07-15, `--apply` may create inert,
idempotent `classify_pending` stubs; it never writes a live edge.
Related: [graph-edge-contract.md](graph-edge-contract.md)
Draft extension: [decision-level-link-sidecar-refs.md](draft/decision-level-link-sidecar-refs.md) — refs
that terminate on a specific decision rather than a whole entry. Not implemented; every ref described
below is entry-to-entry.

## Problem

`supersedes` ("replaces") and `evolves` are typed lifecycle edges an entry
declares in its own YAML. They render as the persistent replaces/evolves lines
in the Trail. But they are opt-in and the author must remember to stamp them at
write time — and in practice almost nobody does:

- Across all 312 entries, `supersedes:`/`evolves:` appear in **one file**
  (`2026-07-10.md`: 1 supersedes, 3 evolves). May and June: zero.
- Genuine supersessions are routinely logged as generic `related_entries`
  instead (e.g. 2026-07-12's palette chain — each palette replaced the prior
  one — and merge-accuracy replacing the positional heuristic; all logged as
  `related_entries`). `related_entries` only renders as faint on-select
  brackets, so the lifecycle distinction silently collapses.

Root cause: the edge depends on write-time recall, nothing surfaces the
omission, and at write time you often don't yet know an entry will supersede or
be evolved by later work. This is a coverage/authoring gap, not a render bug.

## Principles

1. **Append-only.** Never reopen a written entry to add edges. Inverse edges
   (`superseded_by`, `evolved_by`) are already computed at read time for
   exactly this reason. Entries commit per-entry and merge to main almost
   immediately, so a retroactive YAML edit rewrites a committed record.
2. **Mirror the diagram-sidecar precedent.** Late-authored, entry-keyed content
   already has a home: `entry_diagram_sidecars` /
   `iter_diagram_sidecar_documents`, stored under `sessions/diagrams/…`,
   optional, additive, validated by `links check`. Reuse that shape exactly.
3. **Write-time YAML stays canonical** for what the author knew; the sidecar is
   the enrichment layer for what's discovered later. Effective edges =
   union(YAML, sidecar).

## Layer 1 — Link sidecars + end-of-session sweep

### Format
`.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md` (legacy flat
`links/YYYY-MM-DD.md` also read), one dated file per day, mirroring
`sessions/diagrams/…`. Each block is keyed to a **source** entry:

```
## 2026-07-12 13:20 - Trail: brighter 4-pack lane palette

​```yaml
entry_id: mse_6dzkmp53e35rkzts
supersedes:
  - mse_jt2rs0r4k609vx7n
​```
```

`supersedes` / `evolves` / `related_entries` lists allowed; every ref is a
backward edge from the source entry to an older target.

An unresolved scaffold block is also valid sidecar structure:

```
entry_id: mse_xxxx
classify_pending: true
# candidates (evidence):
#   - mse_yyyy  # files: path/to/file.py | topics: graph
```

`classify_pending: true` and the commented evidence are intentionally ignored by graph readers, so a
stub creates zero edges. `links check` reports `sidecar-unclassified-stub` as a warning and ESR counts
open stubs; neither result blocks a merge or commit.

#### Recording "examined, no edge warranted" (`edge_status`, 2026-07-20)

A stub can be resolved two ways, and until now only one was expressible. Adding edges says "I looked
and found relationships". Saying **"I looked and there are none"** had no spelling — the only ways to
clear the warning were to invent an edge or delete the block, and deleting it destroys the evidence
that anyone looked. Every examined-but-empty entry therefore stayed indistinguishable from an
un-examined one, which is why an open-stub count says less than it appears to.

```
entry_id: mse_xxxx
edge_status: not_applicable
note: candidates shared topics only; no lifecycle relationship
```

`edge_status` takes the same three values as `MetricStatus` in `memory_seed/quality.py`, deliberately —
the distinction it draws is identical, and that module's own comment states it: *"`unavailable` — the
input does not exist yet — rather than `not_applicable`, which would claim we looked and found an empty
population."*

| Value | Means | Warning |
|---|---|---|
| *(edges listed, no `edge_status`)* | examined; relationships found | none |
| `not_applicable` | **examined; no relationship warranted** | none |
| `unavailable` | not yet examined — the explicit spelling of `classify_pending: true` | `sidecar-unclassified-stub` |

Rules:
- `edge_status` is **optional and additive**. `classify_pending: true` keeps its meaning, so no existing
  **link sidecar** needs migrating.
- When both are present, `edge_status` governs — it is the later, more specific statement.
- `not_applicable` creates zero edges, exactly like a stub. It records a judgement, not a relationship,
  so graph readers ignore it for the same reason they ignore `classify_pending`.
- `note:` is free text and optional, but it is the whole value of the state: record *why* nothing was
  warranted, so the next reader need not redo the judgement.

**Scope — this is a link-sidecar field.** `.memory-seed/sessions/` holds more than one sidecar kind:
diagram sidecars under `sessions/diagrams/…` and link sidecars under `sessions/links/…`, with the ADR
lifecycle sidecar in [draft](draft/adr-lifecycle-sidecar-contract.md) as a prospective third. "Sidecar"
unqualified is therefore ambiguous across this document — `edge_status` belongs to **link sidecars
only**, and its name says which question it answers (are there lifecycle *edges*?).

The pattern generalises even though the field does not. Any entry-keyed sidecar can be asked "was this
examined, and did it warrant anything?", and each kind should answer in its own file with its own field
name rather than a shared status vocabulary — a common manifest across kinds is exactly the one-owner
collision this design avoids.

This is a per-entry judgement recorded in the link sidecar, which already owns that entry's lifecycle
edges. It deliberately does **not** introduce a separate manifest owning evaluation state — that would
put the same fact in two places and collide with the one-owner rule (Invariant #6). "No edge warranted"
is an answer to the question the link sidecar already answers, not a new fact needing a new home.

### Reader (layered exactly like the diagram sidecars)
- `iter_link_sidecar_documents(sessions_dir)` in **`core.py`** — the file
  discoverer, one-for-one with `iter_diagram_sidecar_documents`.
- `entry_link_sidecars(cwd) -> {entry_id: {supersedes, evolves, related_entries}}`
  in **`retrieval.py`** — the entry-keyed parser, mirroring
  `entry_diagram_sidecars` (block regex → `entry_id` → list fields).

Placement is forced, not stylistic: `retrieval` already imports
`semantic_cache`, so `semantic_cache` can never import a reader in `retrieval`.
That is *why* the graph merge can't live in `build_related_entry_graph`. The
merge now lives in `retrieval.augment_chunks_with_link_sidecars()`, a core-safe
helper shared by MCP, CLI/retrieval, and Memory Trace callers before they invoke
the canonical graph builder.

### Merge (shared retrieval helper, applied to the INPUT chunk list)
`build_related_entry_graph` builds the inverse edges
(`superseded_by`/`evolved_by`) from its **input** chunks and is otherwise pure
over them. So the merge augments the *input*, and everything downstream
(`_graph_edges`, connectivity, the reader's inverses) follows with **no change
to `build_related_entry_graph` or `_graph_edges`**.

- Shared helper `augment_chunks_with_link_sidecars(chunks, cwd)`:
  `entry_link_sidecars(cwd)` → `dataclasses.replace` each chunk unioning
  `supersedes`/`evolves`/`related_entries` (dedup by target id, drop
  self-refs). MCP `memory_search`, `memory_get_chunk`, and `memory_link_show`
  call it before graph construction or payload formatting, so their outbound
  lifecycle fields and computed inverse fields reflect union(YAML, sidecar)
  edges. Memory Trace keeps the same rule by applying the helper with the
  per-worktree cwd before building graph/reader payloads.
- Read at **request time**, not baked into the cache: the lense cache
  invalidates on session-*file* mtime and does not track the new `links/`
  files, so caching sidecar edges would go stale on sidecar edits. Reading a
  few sidecar files per `graph()`/`chunk()` call is cheap and always fresh.
- **Integrity**: `links check` (`core.py`) adds sidecar refs to
  `supersedes_edges` / `evolves_edges`, attributing each to the **source
  entry's** heading timestamp (already in `entry_timestamps`, resolved from the
  entry — NOT the sidecar's authoring time), so the forward-only guard is
  unchanged in logic — a sidecar edge whose target postdates its source still
  fails. Dangling sidecar refs reuse the `dangling-supersedes` /
  `dangling-evolves` issue kinds.

### MCP parity
The earlier Trail-first scope boundary is closed. The **MCP graph tools now
reflect sidecar edges**: `memory_search`, `memory_get_chunk`, and
`memory_link_show` all pass extracted chunks through
`augment_chunks_with_link_sidecars()` before graph construction or payload
formatting. `links check` continues to validate sidecar edges through the same
dangling and forward-only guards, so read surfaces and validation agree on the
effective edge set.

### Sidecar-structural validation (mirrors diagram sidecars)
New `links check` issue kinds: `orphan-link-sidecar` (block whose `entry_id`
matches no entry), `link-sidecar-date-mismatch`, `malformed-link-sidecar`.
Sidecars always optional.

### Historical pre-apply sweep (superseded 2026-07-15)
After the session's entries are written, for each entry **authored this
session**: run `link suggest` (similarity + shared-`F:` evidence), classify each
strong candidate by the litmus — *retires it* → `supersedes`, *refines while it
stays valid* → `evolves`, otherwise `related_entries` — and write the result to
the day's link sidecar. **User approval before writing** (same gate as
persona/session-log evolution). Author-time YAML remains the first line; the
sweep is the safety net.

### End-of-session sweep (current)

After the session's entries are written, run `memory-seed link audit --date <today> --apply`. The
command may mechanically create chronologically ordered, idempotent `classify_pending` stubs with
commented file/topic evidence. This mechanical scaffold needs no relationship decision and never
writes a live edge.

A human then classifies each candidate: retire -> `supersedes`, refine while still valid -> `evolves`,
otherwise `related_entries` or no edge. **User approval is required before replacing a stub with a live
edge.** Author-time YAML remains the first line; the sidecar sweep is the append-only safety net for
later discoveries.

## Layer 2 — Detection (`memory-seed link audit`)

A new `link` subcommand, **not** folded into `links check` (the integrity gate
stays fast, deterministic, and dependency-light). `link audit` flags entries
whose structural neighbours (shared `F:` files or shared topics; file overlap
qualifies a pair even without a shared topic) are captured by **no** edge — YAML or sidecar —
printing the candidate, the shared-`F:` evidence, and the suggested edge type.
It is both the standalone "did we miss links?" check and the discovery step the
end-of-session sweep consumes. An already-declared edge (either source)
suppresses the flag.

With `--date <date> --apply`, the command writes only the inert scaffold above; without `--apply` it
is read-only. An already-declared edge or existing stub suppresses the candidate, making repeat
application idempotent.

## Scope

Primary target is the **typed lifecycle edges** (`supersedes`/`evolves`) — the
failing gap. The sidecar format and sweep also accept `related_entries` so the
sweep can record cross-branch relations it surfaces, but related is not the
focus and its write-time authoring is unchanged.

## Edge direction & timestamp pins
- Sidecar edges are keyed on the **newer** entry (the source), consistent with
  write-time direction: "B supersedes/evolves A" is a block under B's
  `entry_id` listing A.
- The forward-only guard resolves the source's timestamp from the **entry's**
  heading (not the sidecar), so "B supersedes A" is legal iff A predates B.
- The sidecar block heading is cosmetic; `entry_id` is authoritative. No
  heading-vs-entry consistency check beyond entry existence.

## Implementation order (as built - walking skeleton first)
Because `TRAIL_EDGE_TYPES` already requests `supersedes`/`evolves`
(`app.js:171`), the entire payoff hinges on the read path emitting those edges.
Prove that before building anything else:

0. **Skeleton gate** — hand-author one real sidecar (the 2026-07-12 palette
   chain) in a scratch copy, wire only the reader + lense merge, and confirm
   the Trail draws the `supersedes` line end-to-end. If it renders, the rest is
   mechanical; if not, everything downstream was premature.
1. **Read path** — `iter_link_sidecar_documents` (core) + `entry_link_sidecars`
   (retrieval) + `_augment_with_link_sidecars` in `graph()`/`chunk()` + tests.
2. **Integrity** — `links check` sidecar folding + `orphan-link-sidecar` /
   `link-sidecar-date-mismatch` / `malformed-link-sidecar` + tests.
3. **Detection** — `memory-seed link audit` + tests.
4. **Process** — `end_of_turn` sweep step + memory.

Each numbered phase is its own commit.

### Current extension (2026-07-15)

The detection phase now includes a dated `--apply` scaffold, `sidecar-unclassified-stub` warning, and
ESR open-stub count. The process phase separates safe scaffold creation from approval-gated live-edge
classification.

## Non-goals

- **No backfill** of historical entries (deferred; separate decision).
- **No mutation** of any written entry's YAML.
- No change to the `/api/v1/*` or graph-edge contract shapes (more edges, same
  schema).

## Test plan

- `core`: `iter_link_sidecar_documents` parsing (month + legacy layouts,
  malformed name, date/folder mismatch); `entry_link_sidecars` keying + list
  parsing.
- `links check`: sidecar edge folded into the forward-only guard (valid
  backward passes; forward-pointing sidecar edge fails, incl. self/cycle);
  dangling sidecar ref flagged; `orphan-link-sidecar` /
  `link-sidecar-date-mismatch` / `malformed-link-sidecar`.
- `semantic_cache` + graph: `node.supersedes`/`evolves` includes sidecar edges;
  a real-corpus `graph()` emits the extra `supersedes`/`evolves` edges;
  YAML-only behavior unchanged when no sidecar present.
- `link audit`: flags a high-overlap uncaptured candidate; silent once the edge
  is declared in YAML or sidecar.
- `link audit --apply`: creates one chronological inert stub with commented evidence, never a live
  edge; re-applying is idempotent; readers treat a stub as zero edges; `links check` warns and ESR
  counts it until a human classifies or deletes the stub.
- Regression: `test_trail_golden`, v1 contract, OpenAPI fixture unchanged.

## Verification

Full suite, then live: author a link sidecar for the 2026-07-12 palette chain in
a scratch copy, confirm the Trail draws the `supersedes` lines between the
palette entries and `links check` stays green, then discard (backfill is a
non-goal — this only proves the read path end-to-end).
