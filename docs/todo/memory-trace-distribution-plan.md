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

> **Status:** ACTIVE — decided 2026-07-05. **Phase 1 implemented 2026-07-05 (unreleased):** the
> public retrieval service exists (`memory_seed/retrieval.py` — search/fetch orchestration, canonical
> result dicts, entry-level rollup, diagram-sidecar surfacing), MCP is a thin wrapper with a
> byte-identical contract (parity-tested), and the in-package Lense consumes the service.
> **Phase 2 implemented 2026-07-06 (unreleased, on branch `claude/refactor/memory-trace-extraction`):**
> the review UI is extracted into the standalone **`memory-trace`** distribution (`memory-trace/` — its
> own `pyproject.toml`, `memory_trace` package, `memory-trace` console command, `static/` assets). It
> depends on `memory-seed` and imports only the public retrieval/parse/rank/graph surface; core sheds
> `fastapi`/`uvicorn` and `lense_static`; `memory-seed[lense]` + `memory-seed lense` are deprecation
> shims to `memory-trace`; cross-package parity with MCP is tested. `pip install memory-seed` imports
> no web framework and no UI code.
> This is the canonical plan for Pillar B distribution.
> Supersedes the "open evaluation" framing in [`3.0-plan.md`](3.0-plan.md) §"Pillar B" and closes the
> block in [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md).
> **Priority:** P2 (after the unreleased ranking/supersession/commit-linking batch releases; not a
> blocker for any shipped surface).
> **Source:** User decision 2026-07-05 (JNL) that the Explorer should become a separate companion
> package and take over UI development, with clear separation from the core control-plane package.
> `memory-seed-explorer` remains the working placeholder until the Memory Trace naming transition
> completes. Decision inputs: the Codex synergy evaluation's "Pillar B Distribution
> Decision" loop, the shipped `memory-seed[lense]` V1, and `3.0-plan.md`'s original companion-package
> intent.
> **Scope:** Two phases — (1) extract a stable public retrieval service inside `memory-seed` that both
> MCP and Lense consume; (2) extract the UI into its own companion distribution that depends on
> `memory-seed`, named by the Memory Trace transition. Read-only throughout.
> **Non-goals:** No write/curation surface (stays post-3.0, B5). No desktop/VS Code shell in this plan
> (later shells wrap the same web app). No reopening shipped 2.13 Lense retrieval/UI behavior. No
> forking of the parser/ranker into a second stack. No new default dependencies on core `memory-seed`.
> **Dependencies:** Graph-edge contract ([`../graph-edge-contract.md`](../graph-edge-contract.md),
> done 2026-07-04) — the Explorer builds on the same edge/metric contract. Phase 2 is gated on Phase 1
> proving the retrieval-service seam holds while it is still cheap to move (in-package).
> Explorer UI result granularity is governed by
> [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md):
> entries are the selectable UI object; subsection matches are highlighted inside entries.
> Naming transition is governed by [`memory-trace-product-and-trail-view-plan.md`](memory-trace-product-and-trail-view-plan.md):
> Memory Trace is the intended product name for the companion UI line, with package/command naming
> checked before publication. The next approved implementation goal is Phase 1 only: extract the
> public retrieval service, entry-level rollup contract, and decision-diagram surfacing; do not create
> the separate package in that pass.
> **Acceptance criteria:** see the per-phase gates below.

## Decision

Pillar B ships as a **separate companion distribution**, not as a permanent in-package optional
extra. The in-package `memory-seed[lense]` V1 (shipped 2.13.0) served its purpose
as a low-friction way to prototype and validate the UI against real session memory; from here, the
Memory Trace package takes over UI development so that the core `memory-seed` control plane stays a
lightweight, local-first, file-based package and the UI can iterate on its own cadence.

Why a separate distribution rather than continuing the in-package extra:

- **Release cadence.** Core is a control plane agents rely on for correctness; it should be stable.
  A UI iterates fast (visual QA, graph/contributor/stats features). Decoupling lets the Explorer move
  without riding — or destabilizing — a core version bump.
- **Product-line clarity.** "Lightweight, local-first, no-server control plane" is core's identity; a
  web framework in its distribution metadata muddies that even as an optional extra. Future surfaces
  (VS Code, desktop) belong to an Explorer product, not to the control plane.

Note on the honest weight of the arguments: pure dependency isolation is *already* mostly handled by
the `[lense]` extra (`fastapi`/`uvicorn` never install for a plain `pip install memory-seed`). The
decision rests primarily on cadence and product-line separation, not on dependency isolation alone.

## The one rule that makes the split safe

**The Explorer depends on `memory-seed`; core never imports Explorer code, and the Explorer never
forks parsing/ranking.** The load-bearing principle from the UI research report holds: *same answers
as MCP — one canonical chunk model, one canonical ranking service.* The moment the Explorer lives in
its own distribution, whatever it imports from `memory_seed` becomes a **public API with semver
obligations.** That boundary is the entire cost of this decision; getting it right is Phase 1's job.

## Phase 1 — Freeze a public retrieval service in-package (prerequisite, on the critical path)

Do this *before* extracting the distribution, while both consumers still live in one repo and the seam
is cheap to move.

`3.0-plan.md` §"Review Correction: Retrieval Is Already Mostly Shared" already did the analysis: the
genuinely shared substrate — the parser (`extract_memory_chunks`, `iter_session_documents`) and the
ranker (`rank_memory_chunks` / `rank_session_memory`) — already lives in `memory_seed/semantic_cache.py`.
The only still-MCP-coupled piece is the search-orchestration and result-dict contract in
`memory_seed/mcp_server.py`: `call_tool`, `format_search_results`, `_ranked_to_dict`, `_chunk_to_dict`,
and `_semantic_provider`.

Phase 1 extracts exactly those functions into a public, MCP-independent retrieval service (e.g.
`memory_seed/retrieval.py` or a `memory_seed.retrieval` sub-API) that:

- exposes search + chunk-fetch + the derived-graph/timeline/contributor/stats reads the Explorer needs,
  returning the canonical chunk/result dicts (aligned with `docs/graph-edge-contract.md`);
- supports an Explorer-facing entry-level result rollup so section-level matches can improve scoring
  and highlighting without becoming separate selectable UI records;
- surfaces, per entry, any authored decision-diagram sidecar
  (`.memory-seed/sessions/diagrams/YYYY-MM-DD.md`) alongside the Class-1 structural fields, per
  [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md), so the Explorer can render
  reasoning diagrams next to their entry without forking a reader;
- is consumed by `mcp_server.py` (thin wrapper, unchanged external behavior) **and** by the in-package
  Lense today, proving both consumers ride the same contract;
- is documented as the public retrieval API — the surface `memory-trace` will import in Phase 2.

During Phase 1 the in-package Lense goes **maintenance-only**: bug/parity fixes to keep it working, but
no new UI feature development in-package. New UI development targets the Explorer package once Phase 2
lands. Phase 1 is a fast prerequisite on the path to the split, **not** a reason to keep growing the
in-package extra.

### Phase 1 acceptance criteria

- MCP tool behavior (`memory_search`, `memory_get_chunk`) is byte-for-byte unchanged against existing
  fixtures — the extraction is a refactor, not a behavior change.
- The retrieval service has no import dependency on `mcp_server.py`; `mcp_server.py` imports it.
- The in-package Lense consumes the service (no private reach-through into `mcp_server` internals).
- The public retrieval API is named in a doc as the frozen surface Phase 2 depends on.
- Parity tests assert MCP results and service results are identical for the same query.
- Explorer-facing tests prove section matches collapse into one visible entry-level result while
  retaining matched-section highlight metadata.

## Phase 2 — Extract the `memory-seed-explorer` distribution

Once the seam is proven, move the Explorer out.

- New distribution published as **`memory-trace`** (decided 2026-07-06; PyPI-available, no product
  collision — see [`memory-trace-product-and-trail-view-plan.md`](memory-trace-product-and-trail-view-plan.md)),
  with a matching **`memory-trace`** console command.
- It **depends on** `memory-seed` and imports the Phase-1 retrieval service; it never reimplements
  parsing or ranking.
- Move the web stack out of core: `fastapi`/`uvicorn` and the `lense_static/*` assets move to the
  Explorer package. Core `pyproject.toml` sheds the `[lense]` extra's web deps and the `lense_static`
  package data.
- Keep `memory-seed[lense]` working as a **deprecated shim** for at least one release: the extra still
  installs/points users to Memory Trace with a deprecation notice, so existing
  `memory-seed[lense]` users don't hard-break.
- The Explorer keeps the shipped read-only surface: search / reader / timeline / graph / contributors /
  stats, explainability fields, and the rebuildable outside-repo SQLite cache (never authoritative,
  safe for OneDrive-synced workspaces).
- The exportable static report / handover pack (Class-1 derived views + embedded Class-2 sidecars) is
  the paid-tier deliverable scoped in
  [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md) Phase 3 — an Explorer
  product feature, gated on this split.

### Phase 2 acceptance criteria

- `pip install memory-seed` alone installs and imports **no** web framework and no Explorer code.
- The package and command are both `memory-trace` per
  [`memory-trace-product-and-trail-view-plan.md`](memory-trace-product-and-trail-view-plan.md)
  (PyPI-available, no collision; decided 2026-07-06).
- The extracted UI command exposes the read-only companion UI and pulls `memory-seed` as a dependency.
- Explorer API search/fetch matches MCP fixtures (retrieval parity preserved across the package
  boundary).
- `memory-seed[lense]` remains installable for one deprecation window and routes users to the new
  package rather than erroring.
- Explorer stays read-only: no writes to session files; every deep link uses `chunk_id`.

## Explicit non-goals / deferrals

- **Write/curation surface** stays post-3.0 (3.0-plan B5). Later curation uses separate
  annotation/patch records, never silent rewrites of session history.
- **Desktop / VS Code shells** are later wrappers around the same web app (Tauri preferred for a
  desktop shell), not part of this plan.
- **Persistent cache changes** beyond the shipped rebuildable SQLite cache wait on demonstrated need
  (3.0-plan B4).

## Provenance

- User decision 2026-07-05 (JNL).
- Companion-package intent: [`3.0-plan.md`](3.0-plan.md) §"Pillar B".
- Decision inputs and evaluation loop: [`codex/proposal-synergy-evaluation.md`](codex/proposal-synergy-evaluation.md)
  §"Pillar B Distribution Decision".
- Retrieval-seam analysis: [`3.0-plan.md`](3.0-plan.md) §"Review Correction: Retrieval Is Already
  Mostly Shared".
- Shared edge/metric contract: [`../graph-edge-contract.md`](../graph-edge-contract.md).
- Decision-diagram surfacing + paid report pack: [`session-decision-diagrams-plan.md`](session-decision-diagrams-plan.md).
- Historical research (now completed): [`user-interface-deep-research-report.md`](completed/user-interface-deep-research-report.md).
