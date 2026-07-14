---
title: "Memory Trace Next-Generation Implementation Roadmap"
date: "2026-07-11"
project: "memory-seed"
status: "proposed"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Next-Generation Implementation Roadmap

Status: Active staged roadmap, promoted from inbox on 2026-07-11.
Priority: P0 sequencing document for the next Memory Trace implementation goal.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, integrated through `memory-trace-next-generation-coverage-matrix.md`.
Scope: Phase gates from baseline/parity fixtures through versioned API, React shell, Trail/search/graph parity, annotations, Evidence Packs, provider integrations, hosted foundations, and team security.
Non-goals: No real-time collaborative editing, IDE/source editor, mobile-first authoring, full-repository storage by default, unconfirmed AI writes, or hosted work blocking local migration.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-frontend-architecture-and-design-system-proposal.md`, `memory-trace-evidence-annotations-and-projection-architecture.md`, and the two Memory Trace specs in `docs/3_Spec/`.
Acceptance criteria: Each phase ships with tests, docs, package/wheel validation, source-of-truth boundaries preserved, parity fixtures where relevant, and session/plan status updates.

## 1. Goal

Deliver a React-based, Trail-first Memory Trace without regressing the current vanilla application, then add evidence, annotations, AI-derived artefacts and hosted foundations in controlled phases.

## 2. Stage gates

A phase cannot be marked complete without:

- tests;
- documentation;
- package/wheel validation;
- source-of-truth boundaries preserved;
- relevant non-regression fixtures;
- session log and plan status update.

## 3. Phase 0 — baseline and parity fixtures

> **Status: DELIVERED 2026-07-11.** Evidence:
> [`../3_Spec/memory-trace-vanilla-parity-checklist.md`](../3_Spec/memory-trace-vanilla-parity-checklist.md)
> (the parity gate), the measurements/screenshot report at
> [`../4_Reference/memory-trace-phase0-baseline/README.md`](../4_Reference/memory-trace-phase0-baseline/README.md),
> the deterministic 500/1k/10k generator (`memory-trace/tests/fixtures/generate_synthetic.py`),
> and the Trail golden fixture (`memory-trace/tests/fixtures/trail-golden-48.json`).
> Interaction recordings were consciously waived - rationale in the report.

Deliver:

- screenshots and interaction recordings of current tabs;
- representative project fixtures;
- 500, 1,000 and 10,000-entry synthetic datasets;
- Trail lane/edge golden fixtures;
- current package-size and performance measurements;
- explicit parity checklist.

Exit:

- all current behaviours are documented;
- no migration work begins without measurable baseline.

## 4. Phase 1 — versioned API contract

> **Status: DELIVERED 2026-07-11.** Evidence: `memory_trace/models.py` (Pydantic models for
> every existing dict shape, plus the `ProvenanceClass` and `EdgeType` enums), the
> `/api/v1/{runtime,facets,search,chunks,graph,trail}` routes in `memory_trace/service.py`
> (legacy `/api/*` untouched), `memory-trace/tests/test_v1_api_contract.py` and
> `test_openapi_contract_fixture.py`, and the committed contract fixtures under
> `memory-trace/tests/contract/` (`openapi.v1.json`, `types.ts`, regeneration documented in
> that directory's `README.md`). `/api/timeline` has no v1 counterpart - Trail is its
> designated successor and nothing consumes it. The "React client consumes only versioned
> API" exit criterion is enabled but not yet self-certifiable - no React client exists until
> Phase 2; it becomes a checkable fact once that client is built against `types.ts`.

Deliver:

- versioned FastAPI routes;
- OpenAPI models;
- generated TypeScript client;
- contract fixtures;
- Trail event model;
- graph typed-edge model;
- provenance class field.

Exit:

- vanilla frontend can continue operating;
- React client consumes only versioned API.

## 5. Phase 2 — React shell and design system

Deliver:

- Vite/TypeScript workspace;
- Base UI/shadcn primitives;
- semantic tokens;
- Storybook;
- Playwright harness;
- local shell;
- packaged asset pipeline;
- bundle-size reporting.

Exit:

- built wheel serves React shell;
- no Node.js required at runtime;
- accessibility baseline established.

## 6. Phase 3 — search and inspection workspace

Deliver:

- search query/results;
- strongest-neighbourhood navigation;
- next/previous cycling;
- ranked results drawer;
- entry/section highlighting;
- evidence workspace;
- wide and reading-mode prototypes.

Exit:

- search-to-reader behaviour equals or exceeds current UI;
- reading layout decision recorded.

## 7. Phase 4 — Trail parity

Deliver:

- vertical chronological Trail;
- branch lanes;
- typed relationship lanes;
- row virtualisation/windowing;
- incremental history;
- stable selection;
- match markers;
- keyboard navigation.

Exit:

- no functional or performance regression;
- 10,000-entry target measured;
- vanilla Trail remains available behind fallback until sign-off.

## 8. Phase 5 — graph page

Deliver:

- React Flow adapter;
- local/topic/file/evolution modes;
- graph-specific filters;
- Obsidian-inspired interaction benchmark;
- bounded initial range;
- list/table alternative;
- transition from graph node to Trail.

Exit:

- graph code lazy-loads;
- graph remains separate from Trail renderer;
- default last-seven/last-five-active-day range works.

## 9. Phase 6 — deterministic anchors and annotations

Deliver:

- decision/section anchor parser;
- fingerprints;
- participant roles;
- JSONL event schema;
- annotation API;
- SQLite latest-state projection;
- private/shared note distinction;
- agent retrieval tools.

Exit:

- append-only history is preserved;
- authorisation and actionability rules are tested;
- comments live under `sessions/`.

## 10. Phase 7 — Evidence Packs and derived artefacts

Deliver:

- deterministic evidence-pack builders;
- range/branch/PR/topic selections;
- integration with existing AI summarisation plan;
- programmatic provenance appendix;
- report and presentation export adapters;
- explicit promotion workflow.

Exit:

- generated claims cite chunks;
- exports are deterministic after summary validation;
- no generated output mutates sessions.

## 11. Phase 8 — provider integration research and prototype

Deliver:

- GitHub App permission model;
- live/cached/snapshot/unavailable states;
- PR/commit/review normalisation;
- retention policy proposal;
- provider cache prototype.

Exit:

- security review completed;
- snapshot strategy decision recorded;
- PR discussion remains provider-owned.

## 12. Phase 9 — Pro and hosted foundations

Deliver:

- feature entitlement service;
- signed offline licences;
- authentication;
- organisations/workspaces;
- synchronisation prototype;
- billing integration;
- managed AI metering.

Exit:

- Community remains fully usable offline;
- premium checks are server-authoritative where required;
- data export and subscription-expiry behaviour verified.

## 13. Phase 10 — security hardening and team release

Deliver:

- ASVS-derived verification;
- tenant isolation tests;
- audit logs;
- security headers/CSP;
- secret/token management;
- rate limits;
- deletion/retention;
- independent review.

Exit:

- suitable for private repository team use;
- known enterprise gaps documented.

## 14. Dependencies

```text
Phase 0
  -> Phase 1
  -> Phase 2
  -> Phase 3
  -> Phase 4
  -> Phase 5

Phase 1 -> Phase 6 -> Phase 7
Phase 1 -> Phase 8 -> Phase 9 -> Phase 10
```

Graph work may proceed in parallel after the shell and API are stable. Hosted work must not block local migration.

## 15. Out of scope

- real-time collaborative editing;
- replacing GitHub code review;
- IDE/source editor;
- arbitrary graph editing;
- mobile-first authoring;
- storing full repositories by default;
- unconfirmed AI writes to memory;
- custom primitive library;
- custom general graph engine;
- terminal-agent execution before local evidence-pack AI is stable.

## 16. Release strategy

- build React in parallel;
- use feature flags;
- retain vanilla fallback during parity phase;
- publish alpha wheels;
- test from installed wheel, not source checkout only;
- remove vanilla frontend only after explicit product-owner sign-off.

## 17. Success measures

Technical:

- parity checklist complete;
- bundle budgets reported;
- Trail interaction responsive at target scale;
- accessibility workflows pass;
- wheel installation remains simple.

Product:

- users can find and explain a decision faster than by reading raw logs;
- graph leads to useful Trail neighbourhoods;
- evidence-linked exports are understandable;
- annotations feed actionable context to agents without noise.
