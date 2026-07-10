---
memory-system-version: 2.15
tags:
  - memory-seed
  - plan
  - 3.0
  - memory-trace
  - packaging
---

# Memory Trace - Companion Distribution Plan (Pillar B)

> **Status:** ACTIVE - decided 2026-07-05. **Phase 1 implemented 2026-07-05, RELEASED in 2.16.0**
> (status corrected 2026-07-10; an earlier revision mislabeled it unreleased): the
> public retrieval service exists (`memory_seed/retrieval.py` - search/fetch orchestration, canonical
> result dicts, entry-level rollup, diagram-sidecar surfacing), MCP is a thin wrapper with a
> byte-identical contract (parity-tested), and Memory Trace consumes the service.
> **Phase 2 implemented 2026-07-06, merged to `main` and pushed** (status corrected 2026-07-10; the
> former feature branch no longer exists and nothing is unpushed):
> the review UI is extracted into the standalone **`memory-trace`** distribution (`memory-trace/` - its
> own `pyproject.toml`, `memory_trace` package, `memory-trace` console command, `static/` assets). It
> depends on `memory-seed` and imports only the public retrieval/parse/rank/graph surface; core sheds
> `fastapi`/`uvicorn` and `lense_static`; `memory-seed[lense]` + `memory-seed lense` are deprecation
> shims to `memory-trace`; cross-package parity with MCP is tested. `pip install memory-seed` imports
> no web framework and no UI code.
> **Release-ordering coupling:** the UI renders the `branch` field, so `memory-trace` declares
> `memory-seed>=2.17` - **memory-trace 0.1.0 cannot publish until the core 2.17 release (the Phase-0
> `branch:` field) ships first.** The held 2.17 core release is therefore a hard prerequisite for
> publishing the companion package, not an optional bundle.
> This is the canonical plan for Pillar B distribution.
> Supersedes the "open evaluation" framing in [`3.0-plan.md`](completed/3.0-plan.md) section "Pillar B" and closes the
> block in [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md).
> **Priority:** P2 (after the unreleased ranking/supersession/commit-linking batch releases; not a
> blocker for any shipped surface).
> **Source:** User decision 2026-07-05 (JNL) that the review UI should become a separate companion
> package and take over UI development, with clear separation from the core control-plane package.
> The earlier `memory-seed-explorer` placeholder is superseded by the canonical `memory-trace`
> package and command. Decision inputs: the Codex synergy evaluation's "Pillar B Distribution
> Decision" loop, the shipped `memory-seed[lense]` V1, and `3.0-plan.md`'s original companion-package
> intent.
> **Scope:** Two phases - (1) extract a stable public retrieval service inside `memory-seed` that both
> MCP and Memory Trace consume; (2) extract the UI into its own companion distribution that depends on
> `memory-seed`, named by the Memory Trace transition. Read-only throughout.
> **Non-goals:** No write/curation surface (stays post-3.0, B5). No desktop/VS Code shell in this plan
> (later shells wrap the same web app). No reopening shipped 2.13 legacy Lense retrieval/UI behavior. No
> forking of the parser/ranker into a second stack. No new default dependencies on core `memory-seed`.
> **Dependencies:** Graph-edge contract ([`../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md),
> done 2026-07-04) - Memory Trace builds on the same edge/metric contract. Phase 2 followed Phase 1
> proving the retrieval-service seam holds while it is still cheap to move (in-package).
> UI result granularity is governed by
> [`completed/memory-explorer-entry-level-ui-results-plan.md`](completed/memory-explorer-entry-level-ui-results-plan.md):
> entries are the selectable UI object; subsection matches are highlighted inside entries.
> Naming transition is governed by [`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md):
> Memory Trace is the intended product name for the companion UI line, with package/command naming
> checked before publication. Phase 1 shipped in 2.16.0 and Phase 2 is merged and pushed on `main`;
> remaining work (per the 2026-07-10 goal-run decision): (1) cut core **2.17** in this run;
> (2) `memory-trace 0.1.0` publication is deferred until the user creates the PyPI project and
> trusted-publisher config for `memory-trace` (none exists today - `.github/workflows/publish.yml`
> covers `memory-seed` only); a trace publish workflow file is prepared in advance so publication
> is one step once the PyPI side exists. Until then the README must not present
> `pip install memory-trace` as available (hotfix staged 2026-07-10).
> **Acceptance criteria:** see the per-phase gates below.

## Decision

Pillar B ships as a **separate companion distribution**, not as a permanent in-package optional
extra. The in-package `memory-seed[lense]` V1 (shipped 2.13.0) served its purpose
as a low-friction way to prototype and validate the UI against real session memory; from here, the
Memory Trace package takes over UI development so that the core `memory-seed` control plane stays a
lightweight, local-first, file-based package and the UI can iterate on its own cadence.

Why a separate distribution rather than continuing the in-package extra:

- **Release cadence.** Core is a control plane agents rely on for correctness; it should be stable.
  A UI iterates fast (visual QA, graph/contributor/stats features). Decoupling lets Memory Trace move
  without riding - or destabilizing - a core version bump.
- **Product-line clarity.** "Lightweight, local-first, no-server control plane" is core's identity; a
  web framework in its distribution metadata muddies that even as an optional extra. Future surfaces
  (VS Code, desktop) belong to the Memory Trace product, not to the control plane.

Note on the honest weight of the arguments: pure dependency isolation is *already* mostly handled by
the `[lense]` extra (`fastapi`/`uvicorn` never install for a plain `pip install memory-seed`). The
decision rests primarily on cadence and product-line separation, not on dependency isolation alone.

## The one rule that makes the split safe

**Memory Trace depends on `memory-seed`; core never imports Trace code, and Trace never
forks parsing/ranking.** The load-bearing principle from the UI research report holds: *same answers
as MCP - one canonical chunk model, one canonical ranking service.* The moment Trace lives in
its own distribution, whatever it imports from `memory_seed` becomes a **public API with semver
obligations.** That boundary is the entire cost of this decision; getting it right is Phase 1's job.

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
  (`.memory-seed/sessions/diagrams/YYYY-MM-DD.md`) alongside the Class-1 structural fields, per
  [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md), so Trace can render
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

## Phase 2 - Extract the `memory-trace` distribution

Once the seam is proven, move the review UI out.

- New distribution published as **`memory-trace`** (decided 2026-07-06; PyPI-available, no product
  collision - see [`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md)),
  with a matching **`memory-trace`** console command.
- It **depends on** `memory-seed` and imports the Phase-1 retrieval service; it never reimplements
  parsing or ranking.
- Move the web stack out of core: `fastapi`/`uvicorn` and the `lense_static/*` assets move to the
  Trace package. Core `pyproject.toml` sheds the `[lense]` extra's web deps and the `lense_static`
  package data.
- Keep `memory-seed[lense]` working as a **deprecated shim** for at least one release: the extra still
  installs/points users to Memory Trace with a deprecation notice, so existing
  `memory-seed[lense]` users don't hard-break.
- Memory Trace keeps the shipped read-only surface: search / reader / timeline / graph / contributors /
  stats, explainability fields, and the rebuildable outside-repo SQLite cache (never authoritative,
  safe for OneDrive-synced workspaces).
- The exportable static report / handover pack (Class-1 derived views + embedded Class-2 sidecars) is
  the paid-tier deliverable scoped in
  [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md) Phase 3 - a Trace
  product feature, gated on this split.

### Phase 2 acceptance criteria

- `pip install memory-seed` alone installs and imports **no** web framework and no Trace code.
- The package and command are both `memory-trace` per
  [`completed/memory-trace-product-and-trail-view-plan.md`](completed/memory-trace-product-and-trail-view-plan.md)
  (PyPI-available, no collision; decided 2026-07-06).
- The extracted UI command exposes the read-only companion UI and pulls `memory-seed` as a dependency.
- Trace API search/fetch matches MCP fixtures (retrieval parity preserved across the package
  boundary).
- `memory-seed[lense]` remains installable for one deprecation window and routes users to the new
  package rather than erroring.
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
- Companion-package intent: [`3.0-plan.md`](completed/3.0-plan.md) section "Pillar B".
- Decision inputs and evaluation loop: [`codex/proposal-synergy-evaluation.md`](codex/proposal-synergy-evaluation.md)
  section "Pillar B Distribution Decision".
- Retrieval-seam analysis: [`3.0-plan.md`](completed/3.0-plan.md) section "Review Correction: Retrieval Is Already
  Mostly Shared".
- Shared edge/metric contract: [`../3_Spec/graph-edge-contract.md`](../3_Spec/graph-edge-contract.md).
- Decision-diagram surfacing + paid report pack: [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
- Historical research (now completed): [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md).
