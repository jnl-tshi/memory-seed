---
memory-system-version: 2.15
tags:
  - memory-seed
  - plan
  - 3.0
  - memory-trace
  - packaging
---

# Memory Trace - Optional Trace Extra Release Strategy (Pillar B)

> **Status:** COMPLETE 2026-07-20 - the plan's last open obligation, dropping the deprecated
> `memory-seed[lense]` alias and `memory-seed lense` shim after one release window, was resolved the
> same day as `0_NEXT_STEPS.md` Track A.4 (removed, targeted at the 2.20 release). No obligations
> remain; moved from `2_Todo/` to `5_Completed/`.
>
> History below, retained as revised 2026-07-11 and implemented on `main` 2026-07-12. The architecture
> split remains: Memory Trace is the human-facing UI layer and Memory Seed remains the canonical
> memory/retrieval layer. The installation and publication strategy changed: ship Trace through the
> main `memory-seed` distribution as the optional `trace` extra, not as a separate PyPI project.
>
> **Reason for revision:** PyPI rejected the pending `memory-trace` project name as too similar to
> the existing `memorytrace` project. Since the commercial strategy does not use the installation
> layer as the monetisation boundary, the simpler release path is to keep one PyPI project
> (`memory-seed`) and expose the UI through `memory-seed[trace]` plus the `memory-trace` command.
>
> **Phase 1 implemented 2026-07-05, RELEASED in 2.16.0**
> (status corrected 2026-07-10; an earlier revision mislabeled it unreleased): the
> public retrieval service exists (`memory_seed/retrieval.py` - search/fetch orchestration, canonical
> result dicts, entry-level rollup, diagram-sidecar surfacing), MCP is a thin wrapper with a
> byte-identical contract (parity-tested), and Memory Trace consumes the service.
> **Phase 2 source extraction implemented 2026-07-06, merged to `main` and pushed:** the review UI
> lives under `memory-trace/` (`memory_trace` package, `memory-trace` console command, `static/`
> assets) and imports only the public retrieval/parse/rank/graph surface. That source boundary is
> still useful, but the release target is now the root `memory-seed` wheel rather than a separately
> published `memory-trace` wheel.
> **Optional-extra fold-in implemented 2026-07-12:** `pyproject.toml` includes the `memory_trace`
> package and static assets, exposes `memory-trace = "memory_trace.cli:main"`, keeps `lense` as a
> deprecated alias to `trace`, and removed the obsolete standalone Trace PyPI workflow/project
> metadata.
> This is the canonical plan for Pillar B distribution.
> Supersedes the "open evaluation" framing in [`3.0-plan.md`](../5_Completed/3.0-plan.md) section "Pillar B" and closes the
> block in [`user-interface-deep-research-report.md`](../5_Completed/user-interface-deep-research-report.md).
> **Priority:** P2 (after the unreleased ranking/supersession/commit-linking batch releases; not a
> blocker for any shipped surface).
> **Source:** User decision 2026-07-05 (JNL) that the review UI should have a clear product/source
> boundary and take over UI development, revised 2026-07-11 after PyPI blocked the `memory-trace`
> project name and the monetisation strategy confirmed that the installation layer is not the
> commercial boundary. The earlier `memory-seed-explorer` placeholder remains superseded by the
> canonical Memory Trace product and `memory-trace` command. Decision inputs: the Codex synergy
> evaluation's "Pillar B Distribution Decision" loop, the shipped `memory-seed[lense]` V1,
> `3.0-plan.md`'s original companion-package intent, and the monetisation report's free local Trail
> strategy.
> **Scope:** Two phases - (1) extract a stable public retrieval service inside `memory-seed` that both
> MCP and Memory Trace consume; (2) keep the UI in its own source/product boundary while publishing it
> through the root `memory-seed[trace]` extra. Read-only throughout.
> **Non-goals:** No write/curation surface (stays post-3.0, B5). No desktop/VS Code shell in this plan
> (later shells wrap the same web app). No reopening shipped 2.13 legacy Lense retrieval/UI behavior. No
> forking of the parser/ranker into a second stack. No new default web dependencies on plain
> `memory-seed`.
> **Dependencies:** Graph-edge contract ([`../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md),
> done 2026-07-04) - Memory Trace builds on the same edge/metric contract. Phase 2 followed Phase 1
> proving the retrieval-service seam holds while it is still cheap to move (in-package).
> UI result granularity is governed by
> [`completed/memory-explorer-entry-level-ui-results-plan.md`](../5_Completed/memory-explorer-entry-level-ui-results-plan.md):
> entries are the selectable UI object; subsection matches are highlighted inside entries.
> Naming transition is governed by [`completed/memory-trace-product-and-trail-view-plan.md`](../5_Completed/memory-trace-product-and-trail-view-plan.md):
> Memory Trace is the intended product name for the companion UI line and `memory-trace` remains the
> command. Phase 1 shipped in 2.16.0, Phase 2 source extraction is merged, and the 2026-07-12 fold-in
> changed the install path to `pip install "memory-seed[trace]"`. Do not ask users to create a
> separate Trace PyPI project, and do not document `pip install memory-trace` as available.
> **Acceptance criteria:** see the per-phase gates below.

> **Next-generation planning link:** future Memory Trace product and system evolution is governed by
> [`memory-trace-product-and-system-architecture-blueprint.md`](../2_Todo/memory-trace-product-and-system-architecture-blueprint.md).
> This distribution plan remains active only for the package/release ordering, publication, and
> dependency-boundary acceptance criteria that are still unique to the companion distribution.

## Decision

Pillar B ships as a **separate product/source boundary** but not as a separate PyPI project for the
next release. The in-package `memory-seed[lense]` V1 (shipped 2.13.0) served its purpose as a
low-friction way to prototype and validate the UI against real session memory; the extracted
`memory-trace/` source tree still owns UI development. The install path is now:

```bash
pip install "memory-seed[trace]"
memory-trace
```

The plain install remains lightweight:

```bash
pip install memory-seed
```

That plain path must not install `fastapi`/`uvicorn` or require any UI runtime dependencies.

`memory-seed[lense]` remains a deprecated compatibility alias for one release window, and
`memory-seed lense` remains a shim that points users at the `memory-trace` command.

Why an optional extra rather than a separately published distribution:

- **No PyPI name fight.** `memory-trace` is blocked as too similar to `memorytrace`; publishing as
  `memory-seed-trace` would add install/name friction without helping the commercial model.
- **Monetisation is not at install time.** The commercial plan keeps the local single-project Trail
  free and charges later for advanced analysis, cross-project features, hosted collaboration,
  managed AI, exports, and enterprise controls.
- **One release front door.** Users already install Memory Seed first; Trace is easiest to explain as
  the optional human UI for the same package.
- **Dependency hygiene still holds.** Optional extras keep web dependencies out of `pip install
  memory-seed`.

The cost of this revision is release cadence: Trace UI updates will usually ride Memory Seed
releases. That is acceptable until usage volume proves that Trace needs an independent public release
cadence.

## Current release strategy

The packaging fold-in is implemented on `main`:

1. Keep `memory-trace/` as the source/product boundary for now.
2. Include the `memory_trace` package and static assets in the root `memory-seed` wheel.
3. Add a root optional extra `trace = ["fastapi>=0.110", "uvicorn>=0.27"]`.
4. Keep `lense` as a deprecated alias to the same dependencies for one release window.
5. Add the root console command `memory-trace = "memory_trace.cli:main"`.
6. Ensure `memory-trace` and `memory-seed lense` print install hints rather than crashing when UI
   dependencies are absent.
7. Remove the standalone Trace project metadata and standalone PyPI workflow.
8. Keep docs and release notes aligned to `memory-seed[trace]`; never present `pip install
   memory-trace` as the active install path.

## The one rule that makes the split safe

**Memory Trace consumes `memory_seed.retrieval` and never forks parsing/ranking.** The load-bearing
principle from the UI research report holds: *same answers as MCP - one canonical chunk model, one
canonical ranking service.* Even when Trace ships inside the root wheel, the source boundary still
matters: Trace may depend on Memory Seed public APIs, but Memory Seed core must not depend on Trace
UI implementation details for CLI/MCP operation.

## Phase 1 - Freeze a public retrieval service in-package (prerequisite, on the critical path)

Do this *before* extracting the distribution, while both consumers still live in one repo and the seam
is cheap to move.

`3.0-plan.md` section "Review Correction: Retrieval Is Already Mostly Shared" already did the analysis: the
genuinely shared substrate - the parser (`extract_memory_chunks`, `iter_session_documents`) and the
ranker (`rank_memory_chunks` / `rank_session_memory`) - already lives in `memory_seed/semantic_cache.py`.
The only still-MCP-coupled piece is the search-orchestration and result-dict contract in
`memory_seed/mcp_server.py`: `call_tool`, `format_search_results`, `_ranked_to_dict`, `_chunk_to_dict`,
and `_semantic_provider`.

Phase 1 extracts exactly those functions into a public, MCP-independent retrieval service (e.g.
`memory_seed/retrieval.py` or a `memory_seed.retrieval` sub-API) that:

- exposes search + chunk-fetch + the derived-graph/timeline/contributor/stats reads Memory Trace needs,
  returning the canonical chunk/result dicts (aligned with `docs/3_Spec/graph-edge-contract.md`);
- supports a Trace-facing entry-level result rollup so section-level matches can improve scoring
  and highlighting without becoming separate selectable UI records;
- surfaces, per entry, any authored decision-diagram sidecar
  (`.memory-seed/sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`, with legacy flat sidecars still readable)
  alongside the Class-1 structural fields, per
  [`session-decision-diagrams-plan.md`](../2_Todo/session-decision-diagrams-plan.md), so Trace can render
  reasoning diagrams next to their entry without forking a reader;
- is consumed by `mcp_server.py` (thin wrapper, unchanged external behavior) **and** by Memory Trace,
  proving both consumers ride the same contract;
- is documented as the public retrieval API - the surface `memory-trace` will import in Phase 2.

During Phase 1 the in-package Lense route goes **maintenance-only**: bug/parity fixes to keep it working, but
no new UI feature development in-package. New UI development targets the Memory Trace package once Phase 2
lands. Phase 1 is a fast prerequisite on the path to the split, **not** a reason to keep growing the
in-package extra.

### Phase 1 acceptance criteria

- MCP tool behavior (`memory_search`, `memory_get_chunk`) is byte-for-byte unchanged against existing
  fixtures - the extraction is a refactor, not a behavior change.
- The retrieval service has no import dependency on `mcp_server.py`; `mcp_server.py` imports it.
- Memory Trace consumes the service (no private reach-through into `mcp_server` internals).
- The public retrieval API is named in a doc as the frozen surface Phase 2 depends on.
- Parity tests assert MCP results and service results are identical for the same query.
- Trace-facing tests prove section matches collapse into one visible entry-level result while
  retaining matched-section highlight metadata.

## Phase 2 - Extract the Trace source boundary, then fold into the root distribution

Once the seam is proven, move the review UI out of core source files but publish it through the root
package extra.

- Product and command are still **Memory Trace** and **`memory-trace`**.
- Installation is **`pip install "memory-seed[trace]"`**, not `pip install memory-trace`.
- Trace imports the Phase-1 retrieval service; it never reimplements parsing or ranking.
- Move the web stack out of mandatory core dependencies: `fastapi`/`uvicorn` belong only to the
  `trace` extra. Plain `memory-seed` remains web-framework-free.
- Keep `memory-seed[lense]` working as a **deprecated alias** for at least one release.
- Memory Trace keeps the shipped read-only surface: search / reader / timeline / graph / contributors /
  stats, explainability fields, and the rebuildable outside-repo SQLite cache (never authoritative,
  safe for OneDrive-synced workspaces).
- The exportable static report / handover pack (Class-1 derived views + embedded Class-2 sidecars) is
  the paid-tier deliverable scoped in
  [`session-decision-diagrams-plan.md`](../2_Todo/session-decision-diagrams-plan.md) Phase 3 - a Trace
  product feature, gated on this split.

### Phase 2 acceptance criteria

- `pip install memory-seed` alone installs no web framework and no required UI dependencies.
- `pip install "memory-seed[trace]"` installs Trace's UI dependencies and exposes the
  `memory-trace` command.
- The product and command are `Memory Trace` / `memory-trace`; the PyPI project remains
  `memory-seed`.
- Trace API search/fetch matches MCP fixtures (retrieval parity preserved across the package
  source boundary).
- `memory-seed[lense]` remains installable for one deprecation window and routes users to the Trace
  extra/command rather than erroring.
- Trace stays read-only: no writes to session files; every deep link uses `chunk_id`.

## Explicit non-goals / deferrals

- **Write/curation surface** stays post-3.0 (3.0-plan B5). Later curation uses separate
  annotation/patch records, never silent rewrites of session history.
- **Desktop / VS Code shells** are later wrappers around the same web app (Tauri preferred for a
  desktop shell), not part of this plan.
- **Persistent cache changes** beyond the shipped rebuildable SQLite cache wait on demonstrated need
  (3.0-plan B4).

## Provenance

- User decision 2026-07-05 (JNL).
- Companion-package intent: [`3.0-plan.md`](../5_Completed/3.0-plan.md) section "Pillar B".
- Decision inputs and evaluation loop: [`../7_Replaced/codex-proposal-synergy-evaluation.md`](../7_Replaced/codex-proposal-synergy-evaluation.md)
  section "Pillar B Distribution Decision".
- Retrieval-seam analysis: [`3.0-plan.md`](../5_Completed/3.0-plan.md) section "Review Correction: Retrieval Is Already
  Mostly Shared".
- Shared edge/metric contract: [`../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md).
- Decision-diagram surfacing + paid report pack: [`session-decision-diagrams-plan.md`](../2_Todo/session-decision-diagrams-plan.md).
- Historical research (now completed): [`user-interface-deep-research-report.md`](../5_Completed/user-interface-deep-research-report.md).
