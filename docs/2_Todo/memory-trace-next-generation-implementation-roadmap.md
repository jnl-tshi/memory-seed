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
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-graph-and-workspace-proposal-set-index.md`, `memory-trace-frontend-architecture-and-design-system-proposal.md`, `memory-trace-evidence-annotations-and-projection-architecture.md`, the Memory Trace specs in `docs/3_Spec/`, and the constitutional gates named below.
Acceptance criteria: Each phase ships with tests, docs, package/wheel validation, source-of-truth boundaries preserved, parity fixtures where relevant, and session/plan status updates.

## 1. Goal

Settle the graph/workspace contract and renderer evidence first, then deliver a React-based, Trail-first Memory Trace without regressing the current vanilla application. Add evidence, annotations, AI-derived artefacts and hosted foundations only through the constitutional gates below.

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

## 4.1 B0a — pre-React graph/workspace contract and benchmark

Deliver:

- three-region shell behaviour and shared-selection contract;
- renderer-neutral graph projection models and common fixtures;
- vis-network versus Cytoscape.js benchmark on the same bounded fixture;
- topology-first visual encoding and optional temporal-position rules;
- vanilla-safe shell clarification and current SVG fallback coverage.

Exit:

- renderer choice is recorded from packaging, accessibility, topology, temporal, hierarchy, and scale evidence;
- graph semantics and renderer implementation remain separate;
- the post-shell B0b acceptance path is bound to Phases 3 and 5;
- no full renderer migration or dockable-inspector implementation is duplicated in vanilla.

## 5. Phase 2 — React shell and design system

Deliver:

- Vite/TypeScript workspace;
- Base UI/shadcn primitives;
- semantic tokens;
- Storybook;
- Playwright harness;
- local shell;
- three-region layout primitives and shared-selection state shaped by B0a;
- packaged asset pipeline;
- bundle-size reporting.

Exit:

- built wheel serves React shell;
- no Node.js required at runtime;
- B0a shell behaviour is represented without bypassing canonical API services;
- accessibility baseline established.

## 6. Phase 3 — search and inspection workspace

Deliver:

- search query/results;
- strongest-neighbourhood navigation;
- next/previous cycling;
- ranked results drawer;
- entry/section highlighting;
- evidence workspace;
- independently visible Inspector with right, bottom, auto, and hidden states;
- persisted layout preference with stable selection and scroll state;
- wide and reading-mode prototypes.

Exit:

- search-to-reader behaviour equals or exceeds current UI;
- Inspector docking, keyboard control, and responsive behaviour pass B0b workspace acceptance;
- reading layout decision recorded.

Implementation status (2026-07-16): exact `mse_` and legacy `ms-` entry-ID navigation, ranked search
results, resilient shared selection, persisted Inspector docking, keyboard canvas controls, and responsive
React workspace controls are implemented. Reader highlighting, evidence workspace, and Trail transition
remain open, so this phase is not accepted yet.

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

### Post-Trail platform proposal gate

The [`post-Trail platform review set`](../1_Inbox/memory-seed-post-trail-platform-review-proposal-set.md)
is intentionally sequenced after this exit. Its Evidence Envelope, derived review queue/document-lineage,
and capability-status/publishability candidates must not redefine the Trail, graph, provider, or projection
contracts while B0b remains incomplete. Each remains an Inbox item requiring separate approval and may be
promoted only with the established constitutional and source-of-truth gates intact.

## 8. Phase 5 — graph page

Deliver:

- B0a-selected renderer adapter over the renderer-neutral graph projection;
- local/topic/file/evolution modes;
- graph-specific filters;
- topology-first communities, stable colours, typed/curved edges, and optional mild temporal drift;
- bounded/community overview modes;
- bounded initial range;
- list/table alternative;
- transition from graph node to Trail.

Exit:

- graph code lazy-loads;
- graph remains separate from Trail renderer;
- B0b renderer, offline packaging, accessibility, shared-selection, and scale gates pass;
- current SVG fallback remains until explicit parity sign-off;
- default last-seven/last-five-active-day range works.

Implementation status (2026-07-16): the lazy Cytoscape adapter consumes the renderer-neutral projection;
the recent seven-day default range, overview/local/topic filters, edge filters, selected-context lifecycle
routes, deterministic renderer colour, label policy, curved typed edges, fit/zoom keyboard controls, and
list alternative are implemented. The current graph deliberately renders only the connected context plus
the selected node; the bounded list retains unlinked results. Evidence-backed community detection, file and
evolution modes, optional mild temporal layout, Trail transition, diagram rendering in the React reader,
and final accessibility/scale acceptance remain open.

## 9. Phase 6 — deterministic anchors and annotations

Gate: adopt [`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md) before any annotation is surfaced to an agent as actionable. Provenance, lifecycle, participant role, and actionability remain separate fields.

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

Gate: establish the read-only baseline from [`memory-quality-metrics-v0-proposal.md`](memory-quality-metrics-v0-proposal.md) before any quality label affects ranking or agent behaviour. Generated output remains non-authoritative unless explicitly promoted.

> **Partial delivery 2026-07-15:** the deterministic timeline Evidence Pack builder and committed
> snapshot fixture shipped as Phase 1 of
> [`memory-trace-ai-timeline-summarisation-plan.md`](memory-trace-ai-timeline-summarisation-plan.md).
> Provider/local-model summarisation, broader export adapters, and explicit promotion remain future work;
> generated output is still derived and non-authoritative.

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

Gate: the candidate
[`hosted Markdown settlement and projection contract`](../3_Spec/draft/memory-trace-hosted-markdown-settlement-contract.md)
must pass security review, acceptance fixtures, maintainer approval, and promotion into `3_Spec/` before
hosted project-memory writes are implemented.

Deliver:

- feature entitlement service;
- signed offline licences;
- authentication;
- organisations/workspaces;
- synchronisation prototype;
- append-only Markdown settlement and conflict-resolution protocol;
- projection wipe/rebuild and offline round-trip fixtures;
- billing integration;
- managed AI metering.

Exit:

- Community remains fully usable offline;
- premium checks are server-authoritative where required;
- project-owned hosted writes are durable only after settlement into append-only Markdown;
- deleting the hosted project-memory projection and rebuilding from the repository yields equivalent memory;
- no server database is the only copy of project memory, and complete export survives subscription expiry;
- authentication, billing, and entitlements are explicitly outside project-memory authority;
- provider-owned records remain external evidence with source and freshness, never silent Memory Seed truth;
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
  -> B0a
  -> Phase 2
  -> Phase 3
  -> Phase 4
  -> Phase 5 (B0b complete)

Phase 1 -> Provenance/authority gate -> Phase 6 -> Phase 7
Phase 1 -> Memory-quality v0 baseline -> quality-informed ranking or agent behaviour
Phase 1 -> Phase 8 -> Markdown-settlement candidate adoption -> Phase 9 -> Phase 10
```

B0a precedes React feature implementation; B0b is delivered through the post-shell inspection and graph phases. The optional structural-provider tail starts only after B0b acceptance. Hosted work must not block local migration.

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

- complete B0a before React feature implementation;
- build the React shell and B0b in staged parity increments;
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
