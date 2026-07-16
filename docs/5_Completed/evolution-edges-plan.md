---
memory-system-version: 2.18
implemented_by: 558cc63
shipped: 2026-07-15
tags:
  - memory-seed
  - plan
  - graph
  - related-entries
---

# Typed Evolution Edges (`evolves` / `evolved_by`) - Scope

> **Status:** **SHIPPED 2026-07-15.** P1 + lineage-seeding shipped in 2.18.0 (built 2026-07-10 on branch
> `claude-feature-evolution-edges`): D1-D7 with tests (evolves edge + inverse, authored-inverse-field
> guard, continuity field + malformed-continuity, F-overlap ranking with alias table and shared-file
> evidence, search freshness fields, harvest prompts in live + seed skills, graph-edge-contract updated).
> The final Trace lineage pass shipped 2026-07-15: Trail renders typed `evolves` chain brackets and
> derived rename/migration/removal continuity lanes without adding authored graph edges.
> **Disposition:** Completed and moved from `docs/2_Todo/` to `docs/5_Completed/` on 2026-07-15.
> **Priority:** Completed P1-adjacent graph-semantics work.
> **Source:** User observation 2026-07-10: the `session merge-branch` work evolved the fuse
> integration workflow, but the history shows no typed lifecycle signal - `supersedes` would have
> been wrong (fuse is not retired), so the relationship collapsed into untyped `related_entries`.
> Session entries `mse_dr5eprnhrctqeeg3` (the evolution that went untyped) and
> `mse_81v7vk4x5ys3k2n0` (the partially-evolved fuse entry) are the motivating example.
> **Scope:** One new authored edge kind (`evolves:`), its computed inverse (`evolved_by`),
> `links check` guards, `link show`/MCP exposure, a documented removal convention under
> `supersedes`, a Decision Harvest lifecycle prompt, the `F:` file-overlap ranking signal (D5),
> the structured `continuity:` artifact-lineage field (D6), and retrieval-time freshness
> surfacing in search results (D7).
> **Non-goals:** No new `removes:` edge kind (removal stays under `supersedes`; see D3). No
> default `memory_search` ranking changes (D7 surfaces status, never re-ranks). No editing of
> historical entries (the post-P1 seeding pass writes new entries only). No Memory Trace UI work
> in P1. No seeded core-topic vocabulary (an earlier draft of D6; replaced by the structured
> field). No git-rename reconciliation checker (considered 2026-07-10, rejected: advisory value
> judged below its noise risk on docs-heavy histories; continuity is authored at record time).
> **Dependencies:** `supersedes` P1 (shipped, unreleased) - this mirrors its implementation
> pattern. `docs/3_Spec/graph-edge-contract.md` must be updated in the same change. No dependency
> on the topics plan: D6's continuity events are a structured entry field, not topic vocabulary;
> Trace may later derive a continuity display chain from it.
> **Acceptance criteria:** see final section.

## Motivation

Decisions have three lifecycle relations to earlier decisions, and the schema currently types only
one of them:

| Relation | Old entry still valid? | Expressible today |
|---|---|---|
| **Evolves/extends** | Yes - but reading it alone is now incomplete | Untyped `related_entries` only |
| **Replaces** | No - a successor exists | `supersedes` |
| **Removes** | No - the feature is gone, no successor | `supersedes` (fits "deprecates"), but indistinguishable from replacement |

The missing signal is **freshness without retirement**. `superseded_by` is the only "newer
information exists" marker, and it is deliberately heavy: it applies the x0.25 importance dampener
and makes the entry droppable via `exclude_superseded`. Using it for evolution would tell retrieval
"do not rely on this" about decisions that are still load-bearing. So agents correctly avoid it for
evolution - and the evolution becomes invisible, which is exactly what happened with
`session merge-branch`.

There is also a granularity trap that pushes agents away from `supersedes` even for genuine partial
replacement: supersession is entry-level, but entries can carry several decisions (`D1`/`D2`).
Retiring a whole entry because one of its decisions was replaced would falsify the others. A
lighter-weight `evolves` edge is the honest marking for "part of that entry's decision surface
changed."

## Design

### D1 - New authored edge kind: `evolves`

```yaml
evolves:
  - mse_81v7vk4x5ys3k2n0
```

- Optional sibling list of `entry_id` values, same shape as `supersedes`.
- Meaning: "this entry extends, refines, or partially replaces that decision; the old decision
  remains valid but is incomplete without this one."
- Forward-only: only entries that already existed may be referenced. Same guards as `supersedes`:
  `links check` rejects dangling refs, self-references, targets that postdate the referencing
  entry, and cycles (`dangling-evolves`, `self-evolves`, `evolves-postdates`, `evolves-cycle`).
- Never merged with `related_entries` or `supersedes` (fourth edge kind under the contract's
  "never merged" rule). An entry may declare both `evolves` and `related_entries` refs; they answer
  different questions.

### D2 - Inferred inverse: `evolved_by` (never stored, anywhere)

- `evolved_by` is **inferred at read time only**, by `build_related_entry_graph()`, exactly like
  `superseded_by`. It is never written into any entry file - not by agents, not by tooling, not by
  backfill. The old entry's bytes never change when a newer entry declares `evolves:` against it;
  append-only is preserved because the inverse exists only in the derived read layer
  (`Markdown entries -> parsed chunks -> canonical graph reader -> CLI/MCP/Trace`), which is
  disposable and rebuildable.
- **Enforced, not just documented:** `links check` gains an `authored-inverse-field` issue that
  flags a hand-written `evolved_by:` (or `superseded_by:`) key found in stored entry YAML, so a
  well-meaning agent or script cannot quietly break the append-only contract. Today a hand-written
  `superseded_by:` is merely ignored by the parser; this makes it a named integrity error.
- **No importance dampener.** Being evolved leaves `importance_score` untouched - the target is
  still live. This is the semantic line between `evolved_by` and `superseded_by`, and the reason
  the two must never share a field.
- Surfaced through the existing read surfaces (`memory-seed link show`, MCP `memory_get_chunk`,
  and later, non-P1, the Trace Trail view as a freshness hint) - same parity `superseded_by` has
  today. All of these consume the inferred graph; none of them persist it back.

### D3 - Removal stays under `supersedes` (no new `removes:` edge)

A feature-removal entry `supersedes` the removed feature's decision entries. Rationale:

- Removal and replacement have identical retrieval semantics: "do not rely on this decision."
  The dampener and `exclude_superseded` behavior should apply to both.
- The distinction between them is discoverable, not lost: `superseded_by` points at the
  removing/replacing entry, whose `D:`/`R:` states which it is.
- Keeping the contract at four edge kinds instead of five respects the anti-proliferation lean in
  `docs/4_Reference/graph-architecture-lessons.md`.

The removal convention gets one sentence in `session_logging.md`'s `supersedes` paragraph: a
removal with no successor still supersedes the removed decisions.

### D4 - Decision Harvest lifecycle prompt

Add one step to the Decision Harvest in `session_logging.md`/`end_of_turn.md` (live + seed): after
harvesting the turn's decisions, ask **"does any harvested decision replace, remove, or evolve an
earlier entry's decision?"** - replace/remove -> `supersedes`; evolve -> `evolves`; neither ->
`related_entries` only. This closes the behavioral gap that has left `supersedes` unused since it
shipped (zero occurrences in the corpus as of 2026-07-10) and gives the new edge a trigger from
day one.

### D5 - `F:` file-overlap as a high-signal lifecycle-candidate ranker

Decisions that are semantically similar **and** touch the same files are disproportionately likely
to be evolutions or supersessions rather than mere relatedness. `F:` overlap is therefore treated
as a first-class precision signal when ranking candidate targets for `evolves`/`supersedes` - in
`suggest_related_entries()` (CLI `link suggest`, MCP `memory_link_suggest`), which is what the
Decision Harvest prompt leans on to answer "does this evolve or replace an earlier entry?".

Constraints that make the signal trustworthy instead of noisy:

1. **Boost, never gate.** `F` is optional in DRAFT; entries without it must not be penalized or
   excluded - the signal only re-ranks candidates that semantic/lexical similarity already
   surfaced.
2. **Rarity-weighted.** Hub files (`CHANGELOG.md`, `README.md`, `.memory-seed/index.md`, the
   session logs themselves, broad test files, `core.py`) appear in a large share of entries and
   carry near-zero discriminative signal. Overlap weight is scaled by inverse corpus frequency of
   the file, stopword-style: sharing a rarely-touched file is strong evidence; sharing a
   touched-by-everything file is none.
3. **Conservative extraction.** Only backtick-quoted, path-like tokens on `F:` lines are parsed;
   prose fragments ("same as D1", "live + seed") are ignored - missed paths are acceptable, false
   ones are not. `session_logging.md` gains a one-line authoring nudge: list `F:` paths
   backtick-quoted and repo-relative so they are machine-extractable.
4. **Suggest-only, with shown evidence.** The suggestion output annotates *why* a candidate ranked
   ("shares: `memory_seed/core.py`, `.memory-seed/skills/agent_collaboration.md`"), making the
   evolves/supersedes/related judgment concrete for the agent - but the edge is always authored,
   never machine-written, per the expose-before-you-rank standing rule.
5. **Known blind spot, patched by D6.** Major refactors and renames break file continuity exactly
   at the largest evolution moments (e.g. the Lense -> Memory Trace extraction). Semantic
   similarity remains the primary recall channel; file overlap sharpens precision and must never
   become a filter. D6's `continuity:` alias table closes the gap where the rename itself was
   recorded; unrecorded renames remain a blind spot by design (record them going forward rather
   than guessing historically).

### D6 - Structured artifact-lineage field: `continuity:`

(Replaces this draft's earlier core-topics design after user review: a topic records *that* a
rename happened but not *what became what* - and the mapping is where the traceability value
lives. Structured data also drops the topics-plan dependency entirely.)

D5's stated blind spot - renames and relocations break file continuity at exactly the largest
evolution moments, and they break **semantic** recall too, because older entries use the older
vocabulary (this repo's Explorer -> Lense -> Memory Trace history is the live example) - is
patched by a structured optional entry-YAML field recording the artifact transition with
direction:

```yaml
continuity:
  - kind: rename
    from: memory_seed/lense.py
    to: memory_trace/lense.py
  - kind: rename
    from: Memory Lense
    to: Memory Trace
  - kind: migration
    from: .AGENTS/
    to: .memory-seed/
  - kind: removal
    from: memory-seed lense command
```

Rules:

1. **Shape.** `kind` is one of `rename | migration | removal`. `from` is required always. `to` is
   required for `rename`/`migration` and forbidden for `removal` (a removal with a successor is a
   rename or a supersession, not a removal). `links check` enforces this structurally
   (`malformed-continuity`).
2. **Values are historical labels, like `branch:`.** Free-form scalars - file paths, directory
   prefixes, command names, or product/concept terms - never validated against the live filesystem
   or git, because the old artifact is *expected* to be gone.
3. **Forward-only, append-only.** Authored at record time on the entry that performs the change;
   never backfilled; never edits the older entries that mention the old names. All bridging is
   derived read-time.
4. **Two lineage layers, never merged.** `supersedes`/`evolves` record **decision lineage**
   (entry -> entry); `continuity` records **artifact lineage** (name -> name). A feature removal
   typically writes both: `supersedes` retires the decision entries, `continuity` records the
   artifact. Neither substitutes for the other.
5. **Alias resolution in D5 ranking.** `suggest_related_entries()` builds a corpus-wide alias
   table from `continuity` mappings (union old->new, transitively: Explorer -> Lense -> Trace)
   and applies it when computing `F:` overlap, so a pre-rename entry and a post-rename entry
   genuinely overlap instead of requiring a two-hop bounce through the rename entry. The table is
   pure parsing (no subprocess), built only in the suggest path - default `memory_search` ranking
   stays untouched per expose-before-you-rank.
6. **Display chains are derived, not authored.** Trace may later render "continuity events" as a
   derived chronological axis (like `day`/`agent` chains) computed from the field; no seeded topic
   vocabulary exists. If the topics plan ships, `rename`-style topics remain unnecessary -
   membership is derivable from the field (one authored source of truth).
7. **Harvest-prompted.** The Decision Harvest lifecycle question (D4) extends by one clause:
   "...and did this turn rename, relocate, or remove any artifact? If so record a `continuity:`
   block with the old and new names." Same behavioral lesson as `supersedes`: an unprompted
   convention gets zero uses.
8. **Not a git-rename-detection substitute in either direction.** Git's heuristic detection is
   banned from the hot read path by the contract and cannot see concept renames that never pass
   through `git mv`; authored continuity blocks capture intent at record time.

Deferred (non-P1): feeding term-level `rename` mappings into search-query expansion (searching
"trace" also matching "lense"-era entries) - a retrieval behavior change that must wait for
fixture evidence per expose-before-you-rank.

### D7 - Retrieval-time freshness surfacing in search results

The lifecycle edges only pay off if readers see them **at the moment of consumption**. Verified
gap (2026-07-10): computed `superseded_by` is exposed by `memory_get_chunk` only; `memory_search`
results carry the stored `supersedes` field and the opt-in `exclude_superseded` filter, so an
agent consuming a search hit gets no warning it is reading a retired decision unless it makes a
per-result `get_chunk` round trip.

- `memory_search` result payloads gain the computed lifecycle fields - `superseded_by` and (new)
  `evolved_by` - alongside the stored fields already present.
- **Surfaces, never re-ranks:** default ranking and result order are untouched; the fields are
  additive read-only metadata (MCP tool contract change is additive-output only, matching prior
  precedent).
- **Hot-path rule respected:** the graph build is pure parsing (no subprocess) and must reuse the
  search's already-extracted corpus via `build_related_entry_graph(chunks=...)` so the search path
  never re-parses the session files.

### Decision rule of thumb (goes into `session_logging.md`)

- Old decision now wrong or dead -> `supersedes`.
- Old decision still right but incomplete without this entry -> `evolves`.
- Old decision merely context -> `related_entries`.

## Implementation sketch (mirrors supersession P1)

1. `semantic_cache.py`: parse `evolves:` in entry YAML into `MemoryChunk`; add
   `evolves`/`evolved_by` to `RelatedEntryNode`; compute inverse in
   `build_related_entry_graph()`.
2. `core.py` `check_session_links()`: the four guard kinds (reuse the supersedes guard
   implementation pattern; postdates/cycle checks operate per edge kind independently -
   an `evolves` + `supersedes` pair between the same two entries is legal, cycles are checked
   within each kind), the `authored-inverse-field` guard rejecting stored `evolved_by:` /
   `superseded_by:` keys in entry YAML (append-only enforcement), and the `malformed-continuity`
   guard (unknown kind, missing `from`, `to` missing on rename/migration or present on removal).
3. `cli.py` `link show`: print `evolves`/`evolved_by`.
4. `mcp_server.py`/`retrieval.py`: include both fields in `memory_get_chunk` output, and add
   computed `superseded_by`/`evolved_by` to `memory_search` result payloads (D7), reusing the
   search's extracted corpus via `build_related_entry_graph(chunks=...)` - additive, read-only; no
   tool-contract break, no re-parse on the search path.
5. `semantic_cache.py` `suggest_related_entries()`: conservative `F:` path extraction from entry
   bodies, corpus-frequency weighting, file-overlap ranking boost, shared-file evidence in the
   suggestion output (D5), and the `continuity`-derived alias table (transitive old->new mapping)
   applied during overlap computation (D6.5). Extraction, weighting, and the alias table live
   beside the existing ranking, not in a new parser, and only in the suggest path.
6. `semantic_cache.py` chunk parsing: parse `continuity:` items (kind/from/to) from entry YAML
   into `MemoryChunk`; expose stored blocks via `link show` and `memory_get_chunk` (additive,
   read-only).
7. Skills: `session_logging.md` schema paragraphs (`evolves`, `continuity`) + Decision Harvest
   prompt + rule of thumb + the backtick-quoted `F:` path authoring nudge + the D6 continuity
   clause (rename/relocate/remove -> `continuity:` block with old and new names);
   `end_of_turn.md` harvest step - live and seed copies byte-identical.
8. Spec: `docs/3_Spec/graph-edge-contract.md` (same change, not a follow-up) - the `evolves` edge
   kind, the no-dampener rule, the validation kinds, the D5 file-overlap ranking note,
   `continuity` as a stored artifact-lineage field (label-family with `branch:`, not a relational
   entry edge), and the `memory_search` read-surface row gaining computed lifecycle fields (D7).
9. Tests: fixture with an `evolves` chain - parse, inverse, all four guards, `link show` output,
   `memory_get_chunk` output, a regression asserting `importance_score` is NOT dampened by
   `evolved_by`; D5 ranking fixtures (two semantically comparable candidates where the one
   sharing a rare file ranks higher; a hub-file-only overlap producing no meaningful boost; an
   entry without `F:` suffering no penalty); D6 fixtures (continuity parse; all
   `malformed-continuity` shapes rejected; alias-bridged ranking - a pre-rename entry ranks for a
   post-rename target via the mapping, including one transitive chain).
10. Docs: README command/validation descriptions, functionality audit, `.memory-seed/index.md`,
    CHANGELOG.

## Acceptance criteria

- An entry can declare `evolves:`; `link show` and `memory_get_chunk` expose `evolves` and
  inferred `evolved_by`.
- `evolved_by` never appears in any stored file: declaring `evolves:` changes zero bytes of the
  target entry (append-only regression test), and `links check` flags a hand-written
  `evolved_by:`/`superseded_by:` key as `authored-inverse-field`.
- `links check` rejects dangling/self/postdating/cyclic `evolves` refs with distinct issue kinds.
- `importance_score` of an evolved-but-not-superseded entry is unchanged (regression test).
- Decision Harvest (live + seed) contains the lifecycle prompt and the continuity clause;
  `session_logging.md` documents the three-way rule of thumb, the removal convention, the
  backtick-quoted `F:` path nudge, and the `continuity:` field schema.
- `link suggest`/`memory_link_suggest` rank candidates with the rarity-weighted file-overlap boost
  and annotate shared-file evidence; no penalty for absent `F:`; hub-file overlap contributes no
  meaningful boost (fixture-proven).
- An entry can declare `continuity:` blocks; `links check` rejects every `malformed-continuity`
  shape (unknown kind, missing `from`, `to` on removal, missing `to` on rename/migration); stored
  blocks surface via `link show`/`memory_get_chunk`.
- The alias table bridges ranking across recorded renames: a pre-rename entry ranks for a
  post-rename target through the mapping, including one transitive chain, with default
  `memory_search` ranking untouched (fixture-proven).
- `memory_search` results carry computed `superseded_by`/`evolved_by` (fixture: a superseded and
  an evolved entry each surface their status directly in search results, with result order
  identical to the pre-change baseline).
- `graph-edge-contract.md` lists the new edge kind; no consumer parses edges outside
  `build_related_entry_graph()`.
- Full test suite green; `links check` clean on this repo's corpus.

## Post-P1: lineage seeding pass (user-reviewed)

The corpus carries zero lifecycle edges today, so every consumer of this plan - the alias table,
freshness surfacing, dampening, Trail rendering - launches inert. Immediately after P1 ships, run
one user-reviewed seeding session that writes **new** clarification entries (append-only,
forward-only; nothing historical is edited) typing known history:

- A clarification entry declaring `evolves: [mse_81v7vk4x5ys3k2n0]` for the `session merge-branch`
  wrapper around the fuse workflow - the motivating example.
- `continuity:` rename chain for the Explorer -> Lense -> Memory Trace product/concept renames.
- `continuity:` migration blocks for `.AGENTS/` -> `.memory-seed/` and the flat -> month-grouped
  session layout moves.
- `supersedes` edges where a decision was genuinely retired - candidates harvested with the new
  D5 ranking, each reviewed by the user before writing.

Each seeded entry is a normal dated session entry citing its evidence.

Boundary with [`related-entries-p2-mutation-plan.md`](../2_Todo/related-entries-p2-mutation-plan.md)
(reconciled 2026-07-10): this pass writes new entries only and owns all typed lifecycle history;
the P2 plan's explicit backfill mutates existing entries' YAML for untyped `related_entries` only.
Neither substitutes for the other.

## Shipped Trace Lineage Pass And Deferred Extensions

- **Trace lineage pass shipped 2026-07-15:** Trail renders `evolves` edges as typed chain brackets and
  derives continuity lanes for rename, migration, and removal events. The display remains read-only.
- Any ranking/retrieval *behavior* change keyed off `evolved_by` (per "expose before you rank") -
  remains outside this completed plan; D7 surfaces status and never re-ranks.
- Term-level query expansion from `rename` mappings (stated in D6).
