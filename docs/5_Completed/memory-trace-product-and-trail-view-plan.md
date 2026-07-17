---
title: "Proposal: Memory Trace (product) with Trail as a Branch/Supersession Evolution View"
date: "2026-07-05"
project: "memory-seed"
related_to: "docs/5_Completed/memory-trail-renaming-plan.md; docs/2_Todo/memory-trace-distribution-plan.md"
author_context: "Prepared for Jean Nathan Tshibuyi"
format: "Markdown research proposal"
---

# Proposal: Memory Trace (product) with Trail as a Branch/Supersession Evolution View

> **Status:** COMPLETED 2026-07-06 - promoted from inbox on 2026-07-05 as the canonical naming/product plan for
> the companion UI workstream. Supersedes the Trail-only naming plan now archived at
> [`completed/memory-trail-renaming-plan.md`](memory-trail-renaming-plan.md).
> Future Memory Trace product/system evolution is now governed by
> [`../memory-trace-product-and-system-architecture-blueprint.md`](../2_Todo/memory-trace-product-and-system-architecture-blueprint.md)
> and [`../../3_Spec/memory-trace-trail-search-and-graph-ux.md`](../3_Spec/memory-trace-trail-search-and-graph-ux.md).
> **Priority:** Resolved. Naming, branch capture, package extraction, and the Trail view are present
> in the unpushed Memory Trace worktree.
> **Source:** Conversation 2026-07-05 (JNL): use **Memory Trace** as the overall package/product name,
> with **Memory Trail** as a core feature inside Trace for branch and supersession evolution.
> Prior source notes: [`../../4_Reference/memory-trail-competitor-analysis.md`](../4_Reference/memory-trail-competitor-analysis.md)
> and [`completed/memory-trail-renaming-plan.md`](memory-trail-renaming-plan.md).
> **Scope:** Product/package naming, package extraction gate, the Trail feature concept, and the
> minimal data-model/API/UI work needed to show feature evolution from branch labels plus
> supersession links.
> **Non-goals:** No immediate package extraction. No rewrite of historical session entries. No
> branch-existence validation. No write/curation UI. No fork of parser/ranker/retrieval logic.
> **Dependencies:** [`../memory-trace-distribution-plan.md`](../2_Todo/memory-trace-distribution-plan.md),
> [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md),
> [`../session-decision-diagrams-plan.md`](../2_Todo/session-decision-diagrams-plan.md), and
> [`../../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md).
> **Acceptance criteria:** see "Acceptance Criteria" below.

> **Provenance note:** this file was originally drafted as inbox research on 2026-07-05, then promoted
> to an active todo plan after the user confirmed Memory Trace as the product direction and Trail as
> the feature/view name.

## Part 1 - Naming: Trace as the product, Trail as a feature within it

[`completed/memory-trail-renaming-plan.md`](memory-trail-renaming-plan.md)'s Phase-0 check found
`memory-seed-trail` free on PyPI but "Memory Trail" already the name of a real (if small) same-niche
product ([analyzed here](../4_Reference/memory-trail-competitor-analysis.md)). This proposal offers a resolution:

- **Product/package name: Memory Trace.** Names the whole thing - durable, cross-agent, human-
  auditable project memory.

  **Phase-0 availability check ran 2026-07-05 - CLEAR.** PyPI (HTTP status of
  `https://pypi.org/pypi/<name>/json`; 404 = unregistered):

  | Name | Status |
  |---|---|
  | `memory-trace` | **available** (404) |
  | `memory-seed-trace` | **available** (404) |
  | `memoryseed-trace` | **available** (404) |

  Unlike the Trail check, even the bare `memory-trace` name is unregistered. A light positioning scan
  found **no product named "Memory Trace"** in the agent-memory space. One connotation note, not a
  collision: "trace" is an active *generic* term in adjacent products - Memori Labs builds memory
  from "agent traces" (execution telemetry) and agentmemory emits observability "trace spans" - so
  the word carries an execution-telemetry connotation in parts of the space. That reads as adjacent
  vocabulary, arguably even reinforcing (our Trace = decision provenance; their trace = execution
  logging), rather than a brand conflict with any named product.

  **Decided 2026-07-06 (JNL): the package distribution and the console command are both `memory-trace`**
  (the bare, brand-forward name), not `memory-seed-trace`. Trace is a distinct product line sitting on
  top of the `memory-seed` engine, so a distinct top-level name is deliberate - it matches the whole
  point of moving off "Trail" onto its own brand. Accepted tradeoff: the companion command no longer
  shares the `memory-seed-` prefix, so it won't surface under `memory-seed`+Tab discovery; that is the
  intended cost of a standalone brand, and core-package docs will cross-link to it. Reserve
  `memory-seed-trace` as a defensive alias only if a redirect is later wanted; `memory-trace` is the
  canonical name.
- **"Trail" survives as an internal feature name**, not the product's brand. It stops being the thing
  people search for or compare against a competitor's identically-named product, and becomes the name
  of the specific view described in Part 2 - where the metaphor (following a trail of branches and
  decisions) is a better fit than it is for the whole product anyway.

This directly defuses the risk the competitor analysis raised: **positioning/brand collision was the
real risk, functional collision was near zero.** Renaming the product away from "Trail" removes the
positioning collision almost entirely, while keeping the word exactly where its metaphor earns its
keep.

## Part 2 - Trail: a branch + supersession evolution view

### What it would show

A view of how one feature or decision **evolved over time**, combining two data sources that
currently exist independently and are never rendered together:

- **Supersession chain** (`supersedes` / computed `superseded_by`) - already modeled, already
  computed by `build_related_entry_graph()`, already exposed read-only via `link show` and
  `memory_get_chunk`. This is the "decision B replaced decision A" axis.
- **Git branch lineage** - which branch a decision was made on. **This does not exist in the data
  model at all today** (see "Current State" below) - this is the actual new work.

The result is a view answering "show me how this feature got to where it is": which branch a
decision started on, whether it was superseded, and whether the superseding decision happened on the
same branch or a different one (e.g., a decision made on a feature branch, later superseded by a
follow-up made after merge to `main`).

### Positioning

This is explicitly framed as **an evolution of the existing Trace timeline and graph views**,
not a new product surface. Memory Trace renders a timeline and a graph
(`related`/`topic`/`agent`/`day` edges); Trail adds `branch` as a data axis and `supersedes` as a
renderable edge type, then gives the combination its own view/mode rather than just another checkbox
in the existing edge-type list - the interesting content is the *interplay* between "same branch,
time order" and "cross-branch, supersession," which reads better as a dedicated lineage view than as
one more generic chain.

## Current State (verified directly against the code, 2026-07-05)

- **Supersession was modeled but not rendered as a Lense graph edge when scoped.** `build_related_entry_graph()`
  computes `supersedes`/`superseded_by`; `link show` and `memory_get_chunk` expose it read-only. But
  Lense's `_graph_edges()` (`memory-trace/memory_trace/lense.py`) only built `related`/`topic`/`agent`/`day` edge
  types - `supersedes` is not one of the renderable `edge_types` today. Rendering it is additive: the
  data already exists, it just isn't wired into the graph view yet.
- **There is no branch or worktree field anywhere in the schema.** Confirmed directly:
  `MemoryChunk`'s field list (`memory_seed/semantic_cache.py`) and the entry YAML block parsed by
  `check_session_links()` (`memory_seed/core.py`) both have `entry_id`, `user_initials`, `agent_type`,
  `agent_name`, `project_path`, `subproject_path`, `related_entries`, `supersedes`, `commits` - no
  `branch`. The only git linkage that exists is **commit-SHA-based**: the `Memory-Entry: <entry_id>`
  commit-message trailer (commit -> entry, always available) and the optional `commits:` field
  (entry -> commit, same-turn-only backfill). Neither carries branch information.
- **Branch data is captured transiently, once, and thrown away.** `agent_collaboration.md`'s Task
  Packet already has `base_branch` and `working_branch` fields, and the Final Handoff Gate already
  says the orchestrator's session entry should record "worker branches/worktrees" - but today that's
  unstructured prose in a handoff entry's body, not a queryable field, and it doesn't exist at all for
  single-agent work outside the fanout recipe.

## Proposed Design: capture branch at record time

**Implemented 2026-07-06:** `branch:` is now parsed and surfaced read-only, and the Memory Trace UI
uses it in the Trail view.

Per the user's stated preference, branch is **captured when the entry is written**, not derived
after the fact from git history. This is also the technically sound choice: "which branch was this
commit on" is unstable in git (branches move, get deleted after merge, commits get rebased), while a
value written at record time is a durable historical fact the same way a full commit SHA is.
Deriving it later via `git branch --contains <sha>` was considered and rejected as the primary
mechanism - a feature branch deleted after a clean merge would silently vanish from the view even
though the decision and commit both still exist.

- **New optional field on the session entry YAML: `branch:`.** A single scalar (the branch the
  entry's work happened on), parallel in spirit to `commits:` - optional, forward-only (never
  backfilled onto existing entries, never rewritten), and gracefully absent when not applicable
  (detached HEAD, no git repository, or an agent that chooses not to populate it).
- **Populated two ways, matching how work already happens:**
  - **Single-agent work:** the agent reads the current branch (e.g. `git rev-parse --abbrev-ref HEAD`)
    when writing the entry and includes it directly - a one-line addition to the existing entry-
    writing procedure in `session_logging.md`.
  - **Orchestrated multi-agent work:** the orchestrator backfills `branch:` from the Task Packet's
    `working_branch` when writing the Final Handoff Gate's session entry - formalizing what
    `agent_collaboration.md` already asks for in prose into an actual structured field.
- **Validation stance: existence is never checked.** Unlike `commits:` (where `links check` verifies
  the SHA exists in the repository when `.git` is present), a branch that no longer exists is
  **expected, not an error** - feature branches routinely get deleted after merge. `links check` would
  at most validate that a present `branch:` value is a plausible non-empty string, never that it
  currently resolves to a live ref.
- **Surfaced read-only** through the same paths as every other graph-edge-contract field: `link show`,
  `memory_get_chunk`, and the public retrieval service (`memory_seed/retrieval.py`) for the eventual
  Memory Trace package to consume - no new write surface, no new CLI mutation command.

## The Trail view itself

- **New Trace graph edge type: `supersedes`.** Additive to `_graph_edges()` - render the
  already-computed supersession graph as its own edge type, distinguished visually from `related`
  (e.g., a directed, differently-styled edge, since supersession is a typed status edge per
  `docs/3_Spec/graph-edge-contract.md` and must never be visually conflated with plain relatedness).
- **New data axis: `branch`.** Once captured, entries sharing a `branch:` value chain in time order
  (same pattern as the existing `topic`/`agent`/`day` chains in `_graph_edges()`), giving an
  intra-branch lineage thread.
- **A dedicated Trail view/mode** overlays both: intra-branch chains (this decision's lineage within
  one branch) plus cross-branch `supersedes` edges (where a later decision, possibly on a different
  branch, replaced an earlier one) - the actual "branching of features and their evolution" the user
  described, rather than a generic graph with two more edge-type checkboxes buried among four others.
- This is a **Memory Trace product surface**, per the already-decided split in
  [`memory-trace-distribution-plan.md`](../2_Todo/memory-trace-distribution-plan.md) -
  it belongs on the companion package's roadmap (post Phase-1 retrieval-service work, which already
  ships the shared service this view would consume), not as new in-package Lense feature work (Lense
  is maintenance-only per that plan's Phase 1).

## Non-Goals

- **No retroactive branch backfill.** Historical entries written before this field existed have no
  branch data and never will - this mirrors the repo's standing convention for every prior schema
  addition (entry-ID widening, `supersedes`, `commits:`): forward-only, never rewriting old records.
- **No branch-existence validation** in `links check` - a deleted branch is expected history, not an
  integrity problem.
- **No new write/mutation CLI command.** `branch:` is populated by the agent/orchestrator writing the
  entry, the same way every other entry field already is - not a new `memory-seed` subcommand.
- **Not a governance or permissions feature.** This is a visualization of history, not access control
  over branches.
- **Does not replace or duplicate `related`/`topic`/`agent`/`day` edges** - Trail adds two new
  ingredients (branch lineage, rendered supersession) to the same graph engine, it doesn't fork a
  parallel one.
- **No `worktree:` field alongside `branch:`.** Considered and rejected: a worktree is a path on
  someone's local disk - often ephemeral, gitignored, and machine-specific - with no evolution
  semantics of its own; it doesn't explain how a feature branched or got superseded, only where on
  disk the work happened, and is typically 1:1 with the branch during a task anyway. It would add
  schema surface without adding anything to the Trail view. The one place worktree identity has real
  value - short-term multi-agent debugging ("which parallel worker process produced this entry") - is
  already covered by the existing Final Handoff Gate's free-text handoff record in
  `agent_collaboration.md`; that's an operational-audit concern, not a durable-history one, so it
  stays out of the structured entry schema.

## Acceptance Criteria

- ~~Phase-0 availability is re-run for **Memory Trace** and likely package/command names
  (`memory-seed-trace`, `memory-trace`, `memoryseed-trace`) before public extraction.~~
  **Done 2026-07-05 - all three available on PyPI, no named-product collision found** (see the
  Phase-0 findings table in Part 1).
- Forward-looking product docs use **Memory Trace** for the companion package/product and **Trail**
  only for the feature-evolution view inside Trace. The distribution package and console command are
  both **`memory-trace`** (decided 2026-07-06), not the shared-prefix `memory-seed-trace`.
- The old Trail-only naming proposal remains completed/superseded, with its competitor evidence kept
  as provenance rather than active direction.
- ~~Session-entry guidance documents an optional `branch:` scalar captured at record time, omitted
  when unavailable, and never backfilled onto historical entries.~~
- ~~Retrieval/MCP/public service surfaces `branch` read-only once captured; no new write command is
  introduced.~~
- ~~Trace graph work renders `supersedes` as a distinct typed edge and can group entries by branch
  labels without treating branch existence as an integrity requirement.~~
- ~~The Trail view uses commits/trailers, `supersedes`, `related_entries`, file paths, and recorded
  branch labels as evidence; branch names are historical labels, not durable git truth.~~
- ~~The package split continues to depend on the shared retrieval service; Trace never forks parsing,
  ranking, graph, or diagram-sidecar reading logic.~~
  **Done 2026-07-06 in the unpushed Memory Trace extraction and Arc 2 Trail work.**

## Where This Would Fit (If Promoted)

- Schema: `branch:` added alongside `commits:`/`supersedes:` in the entry YAML - documented in
  `session_logging.md`'s schema section and `docs/3_Spec/graph-edge-contract.md` (a new stored field,
  parallel to how `commits:` is documented there).
- Capture: one line in `session_logging.md`'s entry-writing procedure (solo case) and one line in
  `agent_collaboration.md`'s Final Handoff Gate (orchestrated case, backfilling from `working_branch`).
- Rendering: `memory-trace/memory_trace/lense.py`'s `_graph_edges()` gains a `supersedes` edge type and a `branch`
  chain grouping; the dedicated Trail view is Trace-package product work per the
  distribution plan.
- Retrieval: `memory_seed/retrieval.py` surfaces `branch` alongside the existing chunk fields once
  captured, so the shared service (not a forked reader) is what the eventual Trail view consumes.

## Open Questions For Promotion

- ~~**Re-run the Phase-0 availability check against "Memory Trace"**~~ - resolved 2026-07-05: all
  three PyPI names available, no named-product collision (Part 1 findings).
  ~~Which of `memory-seed-trace` vs. `memory-trace` to register~~ - resolved 2026-07-06: **`memory-trace`**
  is the canonical package and command name; `memory-seed-trace` reserved only as an optional
  defensive alias.
- **Detached-HEAD / no-branch fallback**: omit the field entirely (current recommendation) versus a
  sentinel value like `null` - likely omit, consistent with how `agent_name` is already `null` when no
  persona is active versus other optional fields simply being absent.
- **Should `branch:` ever be a list** (e.g., a squash-merge commit technically touches history from
  more than one branch)? Recommend keeping it a single scalar - "the branch I was on when I wrote
  this entry" is a well-defined single fact, unlike "every branch this ever touched."
- **Multi-user layout interaction**: does per-user session-file discovery need any change to carry
  `branch:`? Likely not - it's an entry-level field like `supersedes`, orthogonal to which file layout
  stores the entry.

## Sources / Cross-References

- Conversation 2026-07-05 (JNL): the Trace/Trail naming refinement and the record-time capture
  preference.
- [`memory-trail-competitor-analysis.md`](../4_Reference/memory-trail-competitor-analysis.md) - the positioning-
  collision finding this proposal's naming half resolves.
- [`memory-trail-renaming-plan.md`](memory-trail-renaming-plan.md) - the open naming decision
  this proposal offers a resolution path for, without deciding it here.
- [`memory-trace-distribution-plan.md`](../2_Todo/memory-trace-distribution-plan.md) -
  the product/package split Trail would live inside.
- [`../../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md) - the existing edge-kind contract a new
  `branch` field and rendered `supersedes` edge type would extend.
- Verified directly against code: `memory_seed/semantic_cache.py` (`MemoryChunk` fields),
  `memory_seed/core.py` (`check_session_links()` entry schema), `memory-trace/memory_trace/lense.py`
  (`_graph_edges()`), `.memory-seed/skills/agent_collaboration.md` (Task Packet `working_branch`,
  Final Handoff Gate).
