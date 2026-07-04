---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - 3.0
  - ranking
  - lense
---

# Interaction-Frequency Ranking - Scope

> **Status: P1a IMPLEMENTED 2026-07-03 (unreleased); P1b unblocked, not yet built; Option B remains
> the deferred end goal.** `related_degree` (inbound backlink count) is exposed read-only via
> `memory-seed link show` and `memory_get_chunk`; default `memory_search` ranking is untouched.
> Source: external review doc `Memory-Seed Logic Capture Improvement.md` (its
> "ephemeral memory nexus" / attention-weighted retrieval proposal), refined through review.
> Companion to [`supersession-edges-plan.md`](supersession-edges-plan.md) (defines the harmony
> contract this plan depends on; its P1 core shipped 2026-07-03, so P1b is unblocked) and
> [`related-entries-generation-plan.md`](related-entries-generation-plan.md)
> (reuses `build_related_entry_graph()`).

## Motivation

`rank_memory_chunks`/`rank_session_memory` (`memory_seed/semantic_cache.py`) combine lexical,
metadata, optional semantic, and recency signals. None of these capture "how often, or how
durably, has this entry actually mattered" — a foundational decision with no recent activity and no
close textual match to a new query can fade below noisy recent entries that happen to share
vocabulary, even when the foundational decision is the one that actually explains the current
system.

## Correcting An Earlier Framing

An initial review of this idea wrongly treated it as requiring a new external-database pattern,
which would conflict with the project's local-first, no-external-DBMS stance. That's incorrect:
Memory Lense already ships a rebuildable SQLite cache outside the repository
(`memory_seed/lense.py`, `default_cache_path()` at line 34, `LenseCache.rebuild()` at line 60) —
gitignore-equivalent by location, rebuildable, keyed by file mtime/size, never authoritative,
matching `3.0-plan.md`'s B4 cache spec exactly. Extending that infrastructure with an interaction
signal is not a new architectural pattern; it reuses one already shipped and proven.

## Design - P1 (Option C, ship first): zero-new-infrastructure derived signal

Split P1 into two slices so the plan does not claim supersession-aware scoring before the
`supersedes` schema exists.

### P1a - raw inbound relation count

- `inbound_relation_count(entry)` = `len(inbound)` from `build_related_entry_graph()`
  (`memory_seed/semantic_cache.py`) - how many other entries cite this one via `related_entries`.
- Exposed read-only via `memory-seed link show <entry_id>` and `memory_get_chunk` metadata. Do
  **not** blend it into `memory_search`'s default ranking math.
- **Naming collision found and resolved (2026-07-03/04):** Lense graph nodes shipped a
  `related_degree` field (Lense V1) counting **inbound + outbound** `related_entries` edges combined
  - a node-connectivity display metric for graph node sizing, a genuinely different number from this
  plan's inbound-only importance precursor. Resolution: the backend importance signal is named
  `inbound_relation_count` (descriptive of the inbound-only count), and Lense's display field was
  renamed to `connectivity` with its combined-degree computation unchanged. Neither is "the newer
  version of the other" - they measure different things and now have distinct names. This closes the
  P0 graph-contract prerequisite for exposing `importance_score` in Lense during P1b.

### P1b - supersession-aware importance score

- `importance_score(entry)` starts from `inbound_relation_count(entry)`.
- **Harmony contract (defined in `supersession-edges-plan.md`, binding here):** if the entry has
  any inbound `supersedes` edge, apply a fixed dampening multiplier to `importance_score` *after*
  computing it - never fold `supersedes` inbound edges into the same count as `related_entries`
  inbound edges. Outbound `supersedes` count (cleanup credit) does not add to `importance_score`.
  This is the concrete failure mode reviewed and resolved before this plan was written: a naive
  backlink count would otherwise reward a decision for being deprecated.
- P1b depends on `supersession-edges-plan.md` P1 (shipped 2026-07-03), which is now satisfied — P1b is unblocked.
- Once `git-commit-entry-linking-plan.md` ships, extend `importance_score` with a second free term:
  commit-reference count (how many commits carry a `Memory-Entry:` trailer for this entry, or list
  it in `commits:`).
- **Exposure before ranking changes.** Surface `inbound_relation_count` / `importance_score` read-only first.
  Do **not** blend either signal into `memory_search`'s default ranking math until real usage shows
  the derived signal is actually useful - this matches the existing "Ranking Experiments" policy
  (`docs/todo/NEXT_STEPS.md`: keep ranking behavior stable on `main`; validate ranking changes on a
  separate branch against fixtures before merging) and `3.0-plan.md` B4's "add only after real usage
  demonstrates need" principle, applied here to a scoring change instead of a cache.

## Design - P2 (Option B, the stated end goal, deferred): real interaction/access-frequency telemetry

### Write path: append-only JSONL

Every access event appends one line to `interactions.jsonl`, stored in the same cache directory as
`default_cache_path()` (outside the repo, cloud-sync-safe by construction, no gitignore needed
since it isn't under the workspace root). Concrete instrumentation points, both already centralized
single dispatch functions:

- `mcp_server.py`'s `memory_search` dispatch (`memory_seed/mcp_server.py:82`) and
  `memory_get_chunk` dispatch (`memory_seed/mcp_server.py:115`) — one hook per tool, not per call
  site.
- Lense's detail/card-expand API handler in `lense.py`.

Each line: `{"entry_id_or_chunk_id": ..., "ts": ..., "source": "mcp_search" | "mcp_get_chunk" |
"lense_view"}`. Appends use `O_APPEND` so multiple concurrent processes (Claude Code, Codex, other
MCP clients, the Lense web server) can write without corrupting the file.

### Read path: fold into a table, not the disposable content cache

**Architectural wrinkle found during research:** `LenseCache.rebuild()` (`lense.py:60-109`) does a
full wipe-and-atomic-replace of its SQLite file whenever session Markdown content changes
(`_metadata_matches()` at `lense.py:139-148` triggers this on any mtime/size drift). Interaction
counts must **not** live in the same tables `rebuild()` replaces, or every session-log edit would
silently zero out accumulated interaction history.

Design: a **separate** SQLite file (e.g. `<digest>.interactions.sqlite3`, same cache directory),
independent of the content cache's rebuild cycle. On cache access, fold any JSONL lines appended
since the last fold into this table — mirroring the existing `ensure_current()` staleness-check
pattern (`lense.py:111-113`) rather than inventing a new one. WAL mode tolerates concurrent readers
during a writer's fold.

### Scoring

Same override contract as P1: supersession dampens regardless of hit count; superseded entries are
deprioritized, never hidden or excluded from lookup.

### Privacy

This is behavioral telemetry about *what was queried*, not project content. It stays in the local
cache directory (already outside the repo) and must never be promoted into `index.md` or session
logs. Flag under `memory_hygiene.md` when this gets built in detail.

## Phasing

- **P1a (Option C):** ship now. No schema change, no new dependency, no ranking-default change -
  pure raw related-degree derivation exposed via `link show` / metadata.
- **P1b (supersession-aware score):** ship after `supersession-edges-plan.md` P1, because the harmony
  contract needs real `supersedes` edges to dampen against.
- **P2 (Option B):** the stated end goal. Deferred until (a) `supersession-edges-plan.md` ships
  (the harmony contract needs real `supersedes` edges to dampen against), and (b) real usage shows
  P1's derived signal is insufficient on its own.

## Open Decisions

1. Whether `importance_score` ever gets blended into default `memory_search` ranking, or stays a
   separate, explicitly-requested signal indefinitely.
2. JSONL retention/compaction policy for P2 (unbounded growth needs a periodic fold-and-truncate
   step).
3. Exact dampening multiplier for the supersession harmony contract - needs a concrete number once
   P1b ships and there's a real score to dampen against.

## Definition of Done (P1)

- [x] P1a computes `inbound_relation_count` from `build_related_entry_graph()` inbound counts.
- [x] P1a exposes `inbound_relation_count` via `memory-seed link show <entry_id>` and
  `memory_get_chunk`, not blended into default ranking. (Shipped 2026-07-03; Lense's separate
  `connectivity` display field renamed 2026-07-04.)
- [ ] P1b computes `importance_score` with the supersession dampener applied per the harmony contract.
- [ ] P1b fixture proves a superseded-but-heavily-cited entry scores below a non-superseded,
  moderately-cited one.
- Concise session log entry.
