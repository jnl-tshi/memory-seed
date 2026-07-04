---
memory-system-version: 2.15
tags:
  - memory-seed
  - architecture
  - graph
  - contract
---

# Decision-Graph Edge Contract

**As of:** 2026-07-04 · control-plane `2.15`

This is the single reference for how Memory Seed's decision-graph edges and derived metrics are
defined, computed, and read across every surface (CLI, MCP, Memory Lense, `links check`). It exists
so those surfaces stay consistent instead of each re-deriving graph semantics. If you add a new
consumer or a new edge kind, update this doc and make the consumer read the canonical graph rather
than fork parsing.

## Canonical reader

`build_related_entry_graph(cwd, *, chunks=None)` in `memory_seed/semantic_cache.py` is the **one**
graph reader. It returns `dict[str, RelatedEntryNode]` keyed by `entry_id`. Every consumer that needs
edges or derived metrics must go through it (pass an already-extracted `chunks=` corpus to avoid
re-parsing). Do not re-implement edge parsing or inverse computation elsewhere.

`RelatedEntryNode` fields:

| Field | Kind | Meaning |
|---|---|---|
| `outbound` | stored | this entry's `related_entries` (forward edges it declared) |
| `inbound` | computed | entries whose `related_entries` point here (backlinks) |
| `supersedes` | stored | this entry's `supersedes` (decisions it retires) |
| `superseded_by` | computed | entries that supersede this one |
| `importance_score` | computed | see below |

Inbound-style fields are computed only from refs that resolve to a known `entry_id`; stored fields are
reported as-is (`links check` flags dangling stored refs).

## Edge kinds — never merged

Three independent edge kinds live in entry YAML. They are parsed separately and never folded into one
another:

- **`related_entries`** — relatedness. Forward-only (reference only entries that already existed).
  Bidirectional at read time via `inbound`.
- **`supersedes`** — a typed *status* edge: "this decision replaces that one." Forward-only, so the
  supersession graph is acyclic by construction. Its inverse is `superseded_by`. A supersession is
  **not** a relatedness signal and must never be counted as one.
- **`commits`** — full 40-character SHAs implementing the entry's decision. The commit *side* of the
  link is the `Memory-Entry: <entry_id>` commit-message trailer; the `commits:` field is optional
  same-turn backfill. Read both via `memory-seed link commits`.

## Derived metrics — two distinct numbers, distinct names

Two node-degree metrics exist. They measure different things and must keep distinct names:

- **`inbound_relation_count`** = `len(inbound)` — inbound `related_entries` backlinks only. The
  directional "how many entries cite this one" importance precursor. Surfaced by `link show` and
  `memory_get_chunk`.
- **`connectivity`** (Memory Lense graph nodes only) = distinct neighbors via a `related_entries`
  edge in *either* direction (inbound ∪ outbound). An undirected node-sizing weight for the graph
  view. Computed by `_connectivity_degrees()` in `lense.py`. Never conflate with
  `inbound_relation_count`.

**`importance_score`** builds on `inbound_relation_count`:

```
importance_score = inbound_relation_count
if superseded_by:  importance_score *= SUPERSEDED_IMPORTANCE_DAMPING   # 0.25
```

**`commit_reference_count`** — how many distinct commits link to this entry (its `commits:` field ∪
commits carrying a `Memory-Entry:` trailer, deduped by SHA). Computed **by the caller** via
`commit_reference_ids()`, not in the graph, so the git query never touches the hot read path. It is
exposed as its own read-only number and is **deliberately not folded into `importance_score`** —
composing it into the score is a later, evidence-gated ranking experiment, keeping `importance_score`
one consistent number across every surface (per "One name, one meaning" below).

Rules (the harmony contract):

1. Base is inbound `related_entries` count only — supersession edges never inflate it.
2. Being superseded applies a fixed dampener (`SUPERSEDED_IMPORTANCE_DAMPING = 0.25`) **after** the
   count, as a hard override, so a well-cited-but-retired decision ranks below a live one.
3. Outbound `supersedes` count (cleanup credit) never adds to the score — a large cleanup entry must
   not game its own rank.
4. Never hide, only deprioritize: a superseded entry stays fully retrievable.

## Validation authority

`links check` (`check_session_links()` in `core.py`) is the single validator, run over both session
layouts. Issue kinds it owns:

- `duplicate-entry-id`, `duplicate-hash-id`
- `dangling-related-entry`, `dangling-related-memory`, `dangling-supersedes`
- `self-supersedes`, `supersedes-postdates`, `supersedes-cycle` (the forward-only/acyclic guards)
- `malformed-commit-hash` (always), `unknown-commit` (only when a `.git` repo is present)
- per-user-file frontmatter checks (user/date/schema/hash)

A new edge kind's validation belongs here, reusing the entry-YAML scan, not a parallel validator.

## Read surfaces

| Surface | Exposes |
|---|---|
| `memory-seed link show <id>` | outbound, inbound, `supersedes`, `superseded_by`, `inbound_relation_count`, `importance_score`, `commit_reference_count` |
| `memory-seed link commits <id>` | `commits:` field + `Memory-Entry:` trailer scan |
| `memory-seed link suggest` | ranked older candidates to link (read-only) |
| MCP `memory_get_chunk` | `superseded_by`, `inbound_relation_count`, `importance_score`, `commit_reference_count` (+ stored fields) |
| MCP `memory_search` | results carry stored `supersedes`; opt-in `exclude_superseded` filter |
| Memory Lense graph | `connectivity` (its own metric) and `importance_score` per node; a "Size:" toggle sizes nodes by either |

## Standing rules for new work

- **Read the canonical graph.** New consumers call `build_related_entry_graph()`; they do not parse
  edges themselves.
- **Keep git out of the hot path.** `build_related_entry_graph()` must stay pure (no subprocess). Any
  commit/git-derived signal is computed by the caller and passed in, so `memory_search` and other
  frequent readers never shell out to git.
- **Expose before you rank.** New derived signals are surfaced read-only first; default
  `memory_search` ranking stays stable until a signal proves useful against fixtures on a branch.
- **One name, one meaning.** If two surfaces need different numbers, give them different names (the
  `connectivity` vs `inbound_relation_count` split is the precedent).

## Provenance

Consolidates the graph/ranking work shipped in 2.15.0: typed supersession edges, git↔entry commit
linking, `inbound_relation_count`/`importance_score`, the `connectivity` rename, and the
`exclude_superseded` filter. Plans in `docs/todo/completed/supersession-edges-plan.md`,
`git-commit-entry-linking-plan.md`, `interaction-frequency-ranking-plan.md`, and
`exclude-superseded-filter-plan.md`.
