# Live Specifications

This folder holds **live, normative** Memory Seed specs that current code and future work should obey.
Candidate specs that are **not yet binding** live in [`draft/`](draft/); retired contracts (kept) go in
`deprecated/`. A file's `spec_binding:` (`live`/`draft`/`candidate`/`deprecated`) states which it is.

- `functionality-audit.md` is the live system inventory: what exists, what surfaces expose it, and
  what remains queued or deferred.
- `graph-edge-contract.md` is the live decision-graph contract: edge kinds, derived metrics,
  validation authority, and read surfaces.
- `memory-trace-trail-search-and-graph-ux.md` — **candidate** (`spec_binding: candidate`, not yet
  binding): the proposed UX contract for next-generation Memory Trace Trail/search/graph behaviour.
  Belongs in `draft/`; physically moves there in lifecycle Phase 2 (deferred to batch its ~10 inbound links).
- `memory-trace-derived-artifact-provenance-contract.md` — **candidate** (`spec_binding: candidate`):
  the proposed provenance contract for AI summaries, project updates, reports, presentations, and exports.
  Belongs in `draft/`; moves there in Phase 2.
- `memory-trace-vanilla-parity-checklist.md` is the active React-migration parity gate: every
  user-observable vanilla behaviour, checked off only from the React app (Phase 0 deliverable).
- `lifecycle-edge-linking-sidecars.md` is the live contract for after-the-fact lifecycle-edge
  link sidecars (format, read/validation semantics, MCP scope boundary) plus its design record -
  implemented 2026-07-12; it stays here because the sidecar format is a normative contract, not a
  finished plan.

These files are not completed proposals. Completed proposal and source-plan documents belong in
`docs/2_Todo/completed/`; source-only research belongs in `docs/4_Reference/`.
