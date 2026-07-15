---
memory-system-version: 2.18
tags:
  - memory-seed
  - plan
  - architecture
  - projection
  - performance
priority: P0
next_action: START Phase 1 — extend the existing SQLite cache into the read-model (git-watermark warm start + atomic build/swap) per the projection contract
---

# Derived-projection implementation plan

**Status:** ACTIVE — the **foundation** item; development resumed Constitution-aligned 2026-07-14
([`0_NEXT_STEPS.md`](0_NEXT_STEPS.md)). Start Phase 1 by extending the existing SQLite cache.
**Priority:** P1 (it is what makes Memory Trace fast on large histories).
**Source:** the maintainer's design conversation on performance vs. the Markdown source of truth (2026-07-14).
**Implements:** [`../3_Spec/draft/derived-read-model-projection-contract.md`](../3_Spec/draft/derived-read-model-projection-contract.md)
(the normative contract — this plan builds it; the spec owns the guarantees, this doc owns the sequencing).

## Scope

Make the derived DB projection fast and correct on large histories, per the contract's guarantees G1–G7,
for the **local, single-writer** case. Build on the rebuildable SQLite cache Memory Trace already has —
this is a formalize-and-extend, not a greenfield.

## Non-goals

- The **hosted / collaborative multi-writer** path (out of scope in the spec; gated on the Constitution §10
  commercial-tier decision).
- The DB ever becoming a source of truth, a write buffer that outlives Markdown, or a per-keystroke commit
  loop. Markdown-first writes only.

## Phases

### Phase 1 — Formalize the projection over the existing cache
Make Markdown→projection the explicit, tested contract on the current SQLite cache.

**Warm start + atomic swap + schema versioning SHIPPED 2026-07-15** (`TraceCache`):
- Explicit ingest with a **schema version** (`PROJECTION_SCHEMA_VERSION`) — a bump forces a full rebuild;
  the `rebuild` reproduces byte-identical read results (G2, tested via an independent-rebuild equivalence).
- **Cheap warm start (G5) — DONE.** Stores the build watermark (last-built HEAD) + a signature of the
  git-dirty session files. `ensure_current` proves freshness in **O(changes)**: HEAD unmoved AND the dirty
  signature unchanged → no rebuild, no whole-corpus scan. Measured on the real repo: full rebuild ~6.2 s →
  warm `ensure_current` ~78 ms with no rebuild. Every git ambiguity (moved/gone watermark, `git status`
  error) **fails toward rebuild**; no git → the existing mtime scan (G7 honest degradation).
- **Atomic build & swap (G4) — DONE.** Temp DB + `os.replace` (Windows-retry) means a crashed build never
  serves a half-built DB (old DB stays, or cold-rebuilds); the schema-version gate is the validity check.
- *Acceptance met:* rebuild-from-Markdown is byte-identical; a clean warm start does not rebuild or scan
  the corpus; a killed mid-build leaves no half-served DB.

**Remaining (fast-follow):** **incremental ingest** — on a change, re-project only the delta files' chunks
(O(1 files)) and recompute the whole-history git meta (`entry_commits`/`main_commit_entries`/
`trailer_merges`) only when HEAD moved, instead of the current full rebuild-on-change. Gate it behind an
**incremental == full-rebuild equivalence test** (that equivalence *is* G2); ship only if it holds. The
detection is already O(changes); this makes the *ingest* O(changes) too.

### Phase 2 — Git-rooted historical integrity (G6/G7)
Detect out-of-band edits to historical Markdown without trusting the disposable projection.
- Extend `links check` / `esr`: flag any entry whose file changed in a commit *after* its introducing
  `Memory-Entry:` commit (beyond a pure append), or that is dirty in the working tree, as an append-only
  violation, naming the offending commit/file. Deletion is the same class.
- **Honest no-git degradation:** when there is no git repo, report that the projection self-heals but the
  past cannot be *proven* unaltered — no false guarantee.
- *Acceptance:* an accidental edit to a historical entry is flagged with its commit and is `git revert`-able;
  no-git mode states the limitation explicitly.

### Phase 3 — Performance projection for Trace
Move the heavy read compute onto the projection so the front end stays fast.
- Serve graph layout / Trace aggregation / lineage walks / search from the projection, not raw MD.
- **Cold-start on large histories:** background + progressive build (newest-first / lazy per-view) with a
  progress indicator (reuse the worktree-switch subway loader); atomic-swap when complete.
- Candidate engines, evaluated on real corpora, each a derived accelerator (spec G1–G2): **DuckDB** for
  analytical graph/trace queries, **SQLite FTS5** for full-text, a **vector index** (sqlite-vec/pgvector/
  hnswlib) for semantic search.
- *Acceptance:* Trace on a large corpus is interactive within a bounded time via progressive load; heavy
  queries measurably faster than the raw-MD path, with fixture benchmarks.

### Phase 4 — Optional accelerators (candidate, gated)
Package heavier engines (e.g. DuckDB/vector) as *optional* extras that degrade to the core, per the
Constitution's optional-layer model. **Hosted/collaborative stays out of scope** until the tier decision.

## Dependencies

- Constitution ratified; development resumed (this plan is blocked until then).
- The `3_Spec/draft/` contract graduates to live `3_Spec/` when Phase 1 ships and it is adopted as binding.
