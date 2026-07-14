---
memory-system-version: 2.15
tags:
  - memory-seed
  - architecture
  - graph
  - contract
---

# Decision-Graph Edge Contract

**As of:** 2026-07-10 - control-plane `2.16` (+ unreleased `evolves`/`continuity`/D5-D7 additions)

This is the single reference for how Memory Seed's decision-graph edges and derived metrics are
defined, computed, and read across every surface (CLI, MCP, Memory Trace, `links check`). It exists
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
| `evolves` | stored | this entry's `evolves` (decisions it extends while they stay valid) |
| `evolved_by` | computed | entries that evolve this one (freshness, never retirement) |
| `importance_score` | computed | see below |

Computed inverse fields exist **only** in this derived read layer - they are never written into any
entry file (append-only). `links check` flags a stored `superseded_by:`/`evolved_by:` key as
`authored-inverse-field`.

Inbound-style fields are computed only from refs that resolve to a known `entry_id`; stored fields are
reported as-is (`links check` flags dangling stored refs).

## Edge kinds - never merged

Four independent edge kinds live in entry YAML - and, since 2026-07-12, `related_entries`/
`supersedes`/`evolves` edges may ALSO be authored after the fact in append-only **link sidecars**
(`sessions/links/YYYY-MM/YYYY-MM-DD.md`; see `lifecycle-edge-linking-sidecars.md`). Effective edges
are union(entry YAML, sidecar), merged at read time by
`retrieval.augment_chunks_with_link_sidecars()` before the shared graph builder runs; `links check`
validates sidecar refs through the same dangling and forward-only guards. MCP graph tools
(`memory_link_show`, `memory_get_chunk`, `memory_search`) use the same effective edge set, so
outbound fields and computed inverses match the Trail/reader contract. Edge kinds are parsed
separately and never folded into one another:

- **`related_entries`** - relatedness. Forward-only (reference only entries that already existed).
  Bidirectional at read time via `inbound`.
- **`supersedes`** - a typed *status* edge: "this decision replaces that one." Forward-only, so the
  supersession graph is acyclic by construction. Its inverse is `superseded_by`. A supersession is
  **not** a relatedness signal and must never be counted as one. A feature removal with no
  successor still supersedes the removed feature's decision entries.
- **`evolves`** - a typed *freshness* edge: "this decision extends/refines that one, which remains
  valid but is incomplete alone." Forward-only and acyclic with the same guards as `supersedes`,
  checked independently per kind (an `evolves` + `supersedes` pair between the same two entries is
  legal). Its inverse is `evolved_by`. Being evolved **never dampens** `importance_score` and never
  feeds `exclude_superseded` - that is the semantic line between evolution and supersession.
- **`commits`** - full 40-character SHAs implementing the entry's decision. The commit *side* of the
  link is the `Memory-Entry: <entry_id>` commit-message trailer; the `commits:` field is optional
  same-turn backfill. Read both via `memory-seed link commits`.
- **`branch`** - an optional single scalar: the git branch the entry's work happened on, captured at
  record time. A *stored label*, not a relational edge - it never links two entries the way the
  edge kinds above do; entries sharing a `branch:` value form a time-ordered *axis* the Trail view
  chains, the same way `topic`/`agent`/`day` chains are derived. Forward-only, never backfilled, and
  never validated against live git refs (a deleted feature branch is expected history). There is no
  `worktree:` field - a worktree is an ephemeral local path with no evolution semantics.
- **`continuity`** - stored artifact-lineage items (label family with `branch:`, not a relational
  entry edge): `kind: rename|migration|removal` with `from:`/`to:` recording what an artifact
  (path, command, or concept term) became. `to` is required for rename/migration and forbidden for
  removal. Values are historical labels, never validated against the live tree. `link suggest`
  derives a transitive old->new alias table from these mappings for file-overlap ranking; Trace
  may derive a continuity display chain. Membership is never duplicated as topic vocabulary.

**Indexed topics (implemented 2026-07-10, topics P1):** `topics:` is authored entry metadata - an
optional list of 1-3 slugs (`^[a-z0-9][a-z0-9_-]{0,63}$`) resolved against the deploy-once
project-local vocabulary `.memory-seed/topics.yaml` (canonical slugs + aliases; aliases resolve at
read time). Topics are neighbourhood *membership*, not an edge kind: they never link two entries
directly, and they are validated by the separate `memory-seed topics check`
(unknown-slug/malformed/duplicate/collision errors; count and deprecated-use warnings) -
deliberately outside `links check`'s edge-validation authority. `MemoryChunk.topics` carries the
stored slugs; retrieval dicts expose them; `memory_search` accepts an opt-in pre-ranking `topics`
filter (alias-expanded, fail-open on unknown names, no effect when unused). Memory Trace **prefers
indexed topics** as of topics P4: its single `_topics()` chokepoint returns the authored `topics:`
slugs when an entry has any and falls back to the hashtag/heading-derived axes only for entries
predating the field - never mixing the two. That effective set feeds the topics facet, the reader's
topic chips, the graph's `topic` chronological chains, and the topic filter, and the filter is
alias-expanded through `topics.yaml` (via `expand_topic_filter`, fail-open) so a canonical slug
matches alias-stored entries and vice versa. The MCP-topic-management half of Phase 4 is tracked
separately (`docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md`).

## Derived metrics - two distinct numbers, distinct names

Two node-degree metrics exist. They measure different things and must keep distinct names:

- **`inbound_relation_count`** = `len(inbound)` - inbound `related_entries` backlinks only. The
  directional "how many entries cite this one" importance precursor. Surfaced by `link show` and
  `memory_get_chunk`.
- **`connectivity`** (Memory Trace graph nodes only) = distinct neighbors via a `related_entries`
  edge in *either* direction (inbound ∪ outbound). An undirected node-sizing weight for the graph
  view. Computed by `_connectivity_degrees()` in `service.py`. Never conflate with
  `inbound_relation_count`.

**`importance_score`** builds on `inbound_relation_count`:

```
importance_score = inbound_relation_count
if superseded_by:  importance_score *= SUPERSEDED_IMPORTANCE_DAMPING   # 0.25
```

**`commit_reference_count`** - how many distinct commits link to this entry (its `commits:` field ∪
commits carrying a `Memory-Entry:` trailer, deduped by SHA). Computed **by the caller** via
`commit_reference_ids()`, not in the graph, so the git query never touches the hot read path. It is
exposed as its own read-only number and is **deliberately not folded into `importance_score`** -
composing it into the score is a later, evidence-gated ranking experiment, keeping `importance_score`
one consistent number across every surface (per "One name, one meaning" below).

Rules (the harmony contract):

1. Base is inbound `related_entries` count only - supersession edges never inflate it.
2. Being superseded applies a fixed dampener (`SUPERSEDED_IMPORTANCE_DAMPING = 0.25`) **after** the
   count, as a hard override, so a well-cited-but-retired decision ranks below a live one.
3. Outbound `supersedes` count (cleanup credit) never adds to the score - a large cleanup entry must
   not game its own rank.
4. Never hide, only deprioritize: a superseded entry stays fully retrievable.
5. `evolved_by` never dampens and never excludes - evolution is freshness, not retirement. Only
   `superseded_by` triggers the dampener or the opt-in filter.

### Supersession rank-dampener (`memory_search` order) - on by default

Separate from the read-only `importance_score` dampener above, `memory_search` folds a supersession
rank-dampener into the **default** order (`freshness-aware-memory-ranking-proposal.md`).
`rank_memory_chunks` multiplies `SUPERSEDED_RANK_DAMPING` (0.25, mirroring the `importance_score`
harmony constant) into `final_score` for any entry with a non-empty `superseded_by`, so a live
replacement out-ranks the decision it retires. It:

- is **on by default** (`supersession_damping=True` in `search_memory` and the MCP `memory_search`
  tool); pass `supersession_damping=False` to restore byte-for-byte prior ordering (`importance_score`
  is still not a term in `final_score`). Graduated to default-on after validation on the real corpus:
  both YAML- and sidecar-authored supersession lineages surfaced the live replacement above the
  decisions it retired, and queries with no superseded hit in-window are provably unaffected.
- sources `superseded_by` from the **sidecar-augmented** graph the search path already builds, so a
  supersession authored later in a link sidecar dampens too.
- **down-ranks only, never hides**: the superseded entry stays fully retrievable, just lower (still
  present in the full ranked list, only below the default window). Hard exclusion remains the separate
  opt-in `exclude_superseded` filter. A surfaced supersession is a decision to verify against the code
  (files are authority), not a claim the code already changed.
- leaves `evolved_by` untouched (evolution is freshness, not retirement); the evolves lineage is
  *surfaced* instead - `memory_search` results carry `evolved_head`, the head-of-lineage the
  `evolved_by` chain resolves to, so the current fuller form is reachable without burying the
  still-valid original.

## Validation authority

`links check` (`check_session_links()` in `core.py`) is the single validator, run over both session
layouts. Issue kinds it owns:

- `duplicate-entry-id`, `duplicate-hash-id`
- `dangling-related-entry`, `dangling-related-memory`, `dangling-supersedes`, `dangling-evolves`
- `self-supersedes`, `supersedes-postdates`, `supersedes-cycle` and `self-evolves`,
  `evolves-postdates`, `evolves-cycle` (the forward-only/acyclic guards, run independently per
  edge kind)
- `authored-inverse-field` (a stored `superseded_by:`/`evolved_by:` key - append-only enforcement)
- `malformed-continuity` (unknown kind, missing `from`, `to` on removal, missing `to` on
  rename/migration)
- `malformed-commit-hash` (always), `unknown-commit` (only when a `.git` repo is present)
- per-user-file frontmatter checks (user/date/schema/hash)

A new edge kind's validation belongs here, reusing the entry-YAML scan, not a parallel validator.

## Read surfaces

| Surface | Exposes |
|---|---|
| `memory-seed link show <id>` | outbound, inbound, `supersedes`, `superseded_by`, `evolves`, `evolved_by`, `continuity`, `inbound_relation_count`, `importance_score`, `commit_reference_count` |
| `memory-seed link commits <id>` | `commits:` field + `Memory-Entry:` trailer scan |
| `memory-seed link suggest` | ranked older candidates to link (read-only), re-ranked by the rarity-weighted `F:` file-overlap boost (alias-resolved through recorded `continuity` renames, transitively) with shared-file evidence shown; boost-only, never a gate |
| MCP `memory_get_chunk` | `superseded_by`, `evolved_by`, `inbound_relation_count`, `importance_score`, `commit_reference_count` (+ stored fields incl. `evolves`, `continuity`) |
| MCP `memory_search` | results carry stored `supersedes`/`evolves`/`continuity` **and computed `superseded_by`/`evolved_by`/`evolved_head`** (freshness at the moment of consumption - additive fields; default order untouched); opt-in `exclude_superseded` hard filter and the `supersession_damping` rank-dampener (**on by default**; down-ranks superseded entries so a live replacement out-ranks the decision it retires, `supersession_damping=False` opts out - see the harmony contract above) |
| Memory Trace graph | `connectivity` (its own metric) and `importance_score` per node; a "Size:" toggle sizes nodes by either; `has_diagram` per node (Class-2 decision-diagram sidecar presence) drives a badge on Trail rows / Graph nodes whose popover lazy-loads the diagram - legacy `/api` surface only, the v1 `GraphNode` model strips it until polished |
| Memory Trace `/api/graph` + `/api/chunks` **and** `/api/v1/{graph,trail,chunks}` | additionally `merges` / `branches` (commit-accurate Trail merge events from `Memory-Entry` trailers) and `merged_by` per chunk. Shipped legacy-only under "vanilla only, polish first"; promoted onto the versioned surface in 2.18 (the `MergeEvent` / `BranchInfo` / `ForkPoint` response models, `merged_by: CommitInfo`) once the vanilla implementation had survived a release cycle - additive, so the promotion breaks no existing v1 client |

## Standing rules for new work

- **Read the canonical graph.** New consumers call `build_related_entry_graph()`; they do not parse
  edges themselves.
- **Keep git out of the hot path.** `build_related_entry_graph()` must stay pure (no subprocess). Any
  commit/git-derived signal is computed by the caller and passed in, so `memory_search` and other
  frequent readers never shell out to git.
- **Expose before you rank.** New derived signals are surfaced read-only first; default
  `memory_search` ranking stays stable until a signal proves useful against fixtures on a branch. This
  line has **fully graduated for supersession**: `superseded_by` was exposed read-only first, then
  promoted to the default `memory_search` ranking signal (`supersession_damping` on by default) once
  fixtures **and** a real-corpus check proved it surfaces the live replacement above the decisions it
  retires without disturbing queries that lack a superseded hit. `supersession_damping=False` is the
  opt-out; `evolved_by` remains exposed-only (never a dampener) by design.
- **One name, one meaning.** If two surfaces need different numbers, give them different names (the
  `connectivity` vs `inbound_relation_count` split is the precedent).

## Provenance

Consolidates the graph/ranking work shipped in 2.15.0: typed supersession edges, git↔entry commit
linking, `inbound_relation_count`/`importance_score`, the `connectivity` rename, and the
`exclude_superseded` filter. Plans in `docs/2_Todo/completed/supersession-edges-plan.md`,
`git-commit-entry-linking-plan.md`, `interaction-frequency-ranking-plan.md`, and
`exclude-superseded-filter-plan.md`. The `supersession_damping` rank-dampener (exposed in 2.18, then
turned **on by default** after real-corpus validation) and `evolved_head` successor-surfacing come from
`docs/5_Completed/freshness-aware-memory-ranking-proposal.md`.
