# Lifecycle-edge linking sidecars + end-of-session sweep

Status: IMPLEMENTED 2026-07-12 (all phases merged to main; this document is now the live
contract for the sidecar format + read/validation semantics, plus the design record).
As-built deviations from the original draft: ref extraction uses the wider
`_TRAILER_ENTRY_ID_RE` (real corpus ids include non-Crockford letters; a strict regex silently
dropped edges), and `link audit` generates candidates from topic/file overlap (no all-pairs
semantic scan) with `--for <entry_id>` and `--date YYYY-MM-DD` scoping (the sweep audits only the
session's own entries against the full corpus).
Related: [graph-edge-contract.md](graph-edge-contract.md)

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

### Reader (layered exactly like the diagram sidecars)
- `iter_link_sidecar_documents(sessions_dir)` in **`core.py`** — the file
  discoverer, one-for-one with `iter_diagram_sidecar_documents`.
- `entry_link_sidecars(cwd) -> {entry_id: {supersedes, evolves, related_entries}}`
  in **`retrieval.py`** — the entry-keyed parser, mirroring
  `entry_diagram_sidecars` (block regex → `entry_id` → list fields).

Placement is forced, not stylistic: `retrieval` already imports
`semantic_cache` (confirmed, `retrieval.py:25`), so `semantic_cache` can never
import a reader in `retrieval`. That is *why* the graph merge can't live in
`build_related_entry_graph` and must live in `lense`.

### Merge (one shared lense helper, applied to the INPUT chunk list)
`build_related_entry_graph` builds the inverse edges
(`superseded_by`/`evolved_by`) from its **input** chunks and is otherwise pure
over them. So the merge augments the *input*, and everything downstream
(`_graph_edges`, connectivity, the reader's inverses) follows with **no change
to `build_related_entry_graph` or `_graph_edges`**.

- New lense helper `_augment_with_link_sidecars(chunks, cwd)`:
  `entry_link_sidecars(cwd)` → `dataclasses.replace` each chunk unioning
  `supersedes`/`evolves`/`related_entries` (dedup by target id, drop
  self-refs). Called at the **top of both `graph()` and `chunk()`** with
  `self.cache.cwd` — the correct per-worktree path (`graph()` currently calls
  `build_related_entry_graph(chunks=entries)` with cwd defaulting to `.`, which
  would read the wrong worktree; passing through the helper fixes that). Both
  entry points MUST use the same helper or the reader panel and the Trail
  disagree.
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

### Scope boundary (stated, not silent)
The **MCP graph tools do not reflect sidecar edges** — they call core
`build_related_entry_graph` over raw chunks and never pass through the lense
helper. `links check` *does* validate sidecar edges. This asymmetry is
acceptable for a Trail-focused first pass; MCP-graph parity is a deferred
follow-up (it would need the reader wired into a core-safe location).

### Sidecar-structural validation (mirrors diagram sidecars)
New `links check` issue kinds: `orphan-link-sidecar` (block whose `entry_id`
matches no entry), `link-sidecar-date-mismatch`, `malformed-link-sidecar`.
Sidecars always optional.

### End-of-session sweep (skill step, `end_of_turn`)
After the session's entries are written, for each entry **authored this
session**: run `link suggest` (similarity + shared-`F:` evidence), classify each
strong candidate by the litmus — *retires it* → `supersedes`, *refines while it
stays valid* → `evolves`, otherwise `related_entries` — and write the result to
the day's link sidecar. **User approval before writing** (same gate as
persona/session-log evolution). Author-time YAML remains the first line; the
sweep is the safety net.

## Layer 2 — Detection (`memory-seed link audit`)

A new `link` subcommand, **not** folded into `links check` (the integrity gate
stays fast, deterministic, and dependency-light). `link audit` flags entries
whose structural neighbours (shared `F:` files or shared topics; file overlap
qualifies a pair even without a shared topic) are captured by **no** edge — YAML or sidecar —
printing the candidate, the shared-`F:` evidence, and the suggested edge type.
It is both the standalone "did we miss links?" check and the discovery step the
end-of-session sweep consumes. An already-declared edge (either source)
suppresses the flag.

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
- Regression: `test_trail_golden`, v1 contract, OpenAPI fixture unchanged.

## Verification

Full suite, then live: author a link sidecar for the 2026-07-12 palette chain in
a scratch copy, confirm the Trail draws the `supersedes` lines between the
palette entries and `links check` stays green, then discard (backfill is a
non-goal — this only proves the read path end-to-end).
