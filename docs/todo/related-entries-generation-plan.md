---
memory-system-version: 2.12
tags:
  - memory-seed
  - plan
  - 3.0
  - related-entries
  - graph
---

# Related-Entries Generation - Scope

> **Status: DECIDED + P1 IMPLEMENTED (2026-06-15).** The four open decisions are resolved (see
> "Open Decisions" below) and the P1 core has shipped to the worktree: `memory-seed link suggest`
> and `memory-seed link show` plus the bidirectional read-time graph (`build_related_entry_graph`).
> Companion to [`3.0-plan.md`](3.0-plan.md) (see "Related Entry Linking" and B3/B5). Pillar B
> is tracked separately and out of scope here.

## What Exists Today (2.12.0)

The `related_entries` edge is **read, exposed, validated, and authorable** - but nothing *assists*
creating it:

- **Read** - `semantic_cache.py` parses entry-level `related_entries` from each entry's fenced YAML
  block into `MemoryChunk.related_entries`.
- **Exposed** - `memory_search` / `memory_get_chunk` return `related_entries` (A-P4).
- **Validated** - `check_session_links()` flags any `related_entries` ref that does not resolve to a
  known `entry_id` (`dangling-related-entry`); `memory-seed links check` is the CI gate.
- **Authorable** - the optional `related_entries` field is documented in the `agent-rules.md`
  session-log schema (2.12.0), so an agent *can* hand-write edges at entry-creation time.

**The gap:** there is no mechanism to *generate* or *assist* edges. They are 100% hand-authored, so
in practice the explicit graph stays sparse.

## Reframe: The Graph Is Not Empty

This is an assist for **curation**, not filling a blank canvas. The 3.0 plan's **B3** already defines
*derived* edges - same day, same tag, same project, same contributor, same file - computed at read
time. Explicit `related_entries` are the **high-confidence curated overlay** a future UI should rank
*above* those derived edges. So "generation" means: make it cheap to add the high-value explicit
links a human/agent would otherwise skip. It does not need to manufacture a graph from nothing.

## The Core Tension: Append-Only History

An edge lives in the source entry's YAML. Creating an edge **from** entry A **to** entry B means
writing into A's YAML block. That is fine when A is the entry being written right now, but editing an
*existing* entry collides with two locked rules:

- **Append-Only Chronology** - session files are append-only; entries are never reordered or rewritten.
- **Change Permission Model** - "editing prior session logs except for explicit repair, archival
  cleanup, or user-requested correction" is locked.

B5 of the 3.0 plan already takes a side on the analogous curation problem: *"later curation should use
separate annotation/patch records rather than silently rewriting session history."*

## Design Model

### Primary mechanism (recommended): forward-in-entry + bidirectional read-time traversal

- An entry may declare `related_entries` only to entries that **already existed when it was written**
  (forward edges). This is authored at entry-creation time and never edits history.
- The graph is traversed **bidirectionally at read time**: a forward edge A -> B is surfaced as a
  relationship on *both* A and B. A future UI can build derived edges at read time, so this
  adds no new storage and no history edits.
- Net effect: the old <-> new relationship is captured for free, append-only is fully preserved, and
  Markdown stays the single source of truth.

### The residual case (and its append-only-native answer)

The only thing forward-only does not cover: *two **pre-existing** entries turn out to be related, and
you don't want to write a new entry saying so.* Options, cheapest first:

1. **Write a new linking entry** that references both - fully append-only, zero new machinery.
   Recommended default.
2. **Sidecar edge record** (e.g. `.memory-seed/links.yaml` or per-edge annotation records) read
   *alongside* entry YAML by `links check` and MCP. Preserves immutability of entries but adds a second
   edge source and reader. Deferred; only if real usage shows #1 is insufficient. Consistent with B5.
3. **Sanctioned in-entry edit** of the historical entry, treated as an explicit "user-requested
   correction" with backup. Single source of truth, but normalizes editing history. Not recommended.

### Generation modes

- **Write-time suggestion (the high-value core).** When an entry is being authored, reuse the existing
  `rank_session_memory` / `rank_memory_chunks` to propose candidate prior entries (by semantic +
  lexical + recency similarity to the new entry's text). The author confirms which become
  `related_entries`. No new ranking code; no history edits.
- **Manual `link add` (current entry only).** Add a specific forward edge to the entry being authored
  after the fact within the same session, validated immediately.
- **Automatic at write-time** - already enabled by the schema doc; the suggestion mode makes it cheap.

## Command Surface (proposed)

Fits the existing `subparsers` shape in `cli.py` (`links`, `migrate`, `session` are the precedents):

```text
memory-seed link suggest [--for <entry_id|current>] [--top-k N]
    Print ranked candidate prior entries to link, using rank_session_memory.
    Read-only; never writes.

memory-seed link add <target_entry_id> [--from <entry_id>]
    Add a forward related_entries edge. Default --from is the newest entry in the
    active session target. Refuses if --from is not the current/newest entry
    (no historical rewrite) and fails immediately if <target> does not resolve.
```

`suggest` is read-only and uncontroversial; `add` is the only writer and is constrained to the current
entry, so it never touches history.

## Validation & Idempotency

- **Add-time validation:** `link add` resolves the target against the known-entry-id set up front and
  **fails immediately** on a dangling target - it does not defer to `links check`.
- **Idempotency:** adding an edge that already exists is a no-op (no duplicate list item).
- **`links check` stays the gate, unchanged:** it already detects dangling refs across both ID
  namespaces (`ms-` and `mse_`). Generation must only ever produce resolvable, deduplicated edges, so
  the gate keeps passing.

## Phasing

- **P1 - shippable, no history edits (recommended first increment):** `link suggest` (read-only,
  reuses the ranker) + `link add` restricted to the current/newest entry + bidirectional read-time
  traversal documented as the canonical graph-read model. `links check` unchanged. This directly fixes
  "nothing assists" with zero append-only tension.
- **P2 - backfill between pre-existing entries (deferred, needs a decision):** only if P1 proves
  insufficient. Pick option 1/2/3 from "The residual case" - default to "write a new linking entry,"
  escalate to a sidecar only with explicit sign-off (B5-aligned).

## Open Decisions (RESOLVED 2026-06-15)

1. **Directionality / traversal:** **Bidirectional read-time traversal of directed forward edges.**
   Edges are stored once (a newer entry's `related_entries`) and inverted at read time, so each entry
   also exposes computed backlinks. No reciprocal edges are stored; history is never edited.
2. **Backfill between two pre-existing entries:** **Out of 3.0 scope.** Bidirectional traversal makes
   it unnecessary - the append-only-native move ("write a new linking entry") covers the case. A
   sidecar (P2) remains available only behind explicit future sign-off (B5-aligned).
3. **Target selection UX:** **Raw `entry_id`.** `link suggest` handles discovery and prints a
   copy-pasteable `related_entries:` snippet, so id-based selection is sufficient.
4. **Writer scope:** **`link add` is held (not built).** P1 ships read-only `suggest` + `show`; the
   author includes `related_entries` at write time (schema doc, 2.12.0), and `suggest`'s paste-ready
   snippet removes most of the friction. `link add` (current/newest entry only) remains an optional,
   append-only-safe follow-on if hand-editing YAML proves painful in practice.

## P1 - As Shipped (worktree, unreleased)

- `memory-seed link suggest [--for <entry_id>] [--top-k N]` - read-only; ranks **older** candidate
  entries (forward-only) by similarity to the target (default: newest entry), excludes self and
  already-linked entries, and prints a paste-ready `related_entries:` snippet. Reuses
  `rank_memory_chunks` with recency disabled.
- `memory-seed link show <entry_id>` - read-only; prints stored outbound edges and computed inbound
  backlinks, making bidirectional traversal observable today before a future UI consumes it.
- `build_related_entry_graph(cwd)` in `semantic_cache.py` - the canonical bidirectional graph the
  MCP and future UI consumers should consume (don't fork parsing/ranking). Inbound is computed only from resolvable
  refs; outbound is reported as stored (`links check` flags dangling outbound).
- `links check` unchanged and still green. No package version bump - queued under `## Unreleased`.

## Definition of Done (P1)

- `link suggest` returns ranked prior-entry candidates with parity to MCP ranking; read-only.
- `link add` writes a deduplicated forward edge to the current entry, fails fast on a dangling target.
- `links check` still passes; bidirectional read-time traversal documented for future UI consumers.
- Green tests, `doctor` healthy, docs updated, concise session log entry.
