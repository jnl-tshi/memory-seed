---
title: "Memory Trace Product and System Architecture Blueprint"
date: "2026-07-11"
project: "memory-seed"
status: "proposed-canonical-plan"
audience:
  - maintainers
  - codex
  - claude
  - product-owner
related:
  - "docs/3_Spec/functionality-audit.md"
  - "docs/3_Spec/graph-edge-contract.md"
  - "docs/2_Todo/memory-trace-ai-timeline-summarisation-plan.md"
---

# Memory Trace Product and System Architecture Blueprint

Status: Active canonical Memory Trace product/system blueprint, promoted from inbox on 2026-07-11.
Priority: P0 planning entry point before next-generation Memory Trace implementation.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, folded against existing Memory Trace plans on 2026-07-11.
Scope: Product hierarchy, architectural layers, authority boundaries, local/hosted product split, and document map for next-generation Memory Trace.
Non-goals: No direct implementation, no retirement of active implementation plans, no change to Memory Seed's canonical graph contract.
Dependencies: `docs/3_Spec/functionality-audit.md`, `docs/3_Spec/graph-edge-contract.md`, `memory-trace-next-generation-coverage-matrix.md`, and the existing active Memory Trace implementation plans.
Acceptance criteria: Future Memory Trace work routes through this blueprint, preserves Markdown/Git authority, uses Memory Seed canonical services, and maintains parity with current Trace before replacing the vanilla UI.

## 1. Executive decision

Memory Trace should evolve from a compact read-only companion UI into the **human-facing project-intelligence layer for Memory Seed**, while preserving the existing local-first, Markdown-first and vendor-neutral foundations.

The central product concept is the **Trail**:

> Memory Trace is organised around a chronological, evidence-linked Trail of how project decisions, branches, files, commits and pull requests evolved.

Search, graph exploration, document inspection, AI summaries, project updates and presentations should all lead back to the Trail and its evidence. The graph is a specialised topic/document exploration surface, not a replacement for chronology.

The recommended next-generation architecture is:

```text
Authoritative records
  Markdown session entries
  Git history
  Git-provider records
  append-only shared annotations
          |
          v
Canonical semantic services
  retrieval
  graph construction
  validation
  deterministic anchors
  evidence-pack construction
          |
          v
Projection layer
  rebuildable SQLite
  search indexes
  cached provider metadata
  latest annotation state
  saved layout and viewport state
          |
          v
Experience layer
  Trail
  search
  inspection workspace
  graph
  filters
          |
          v
Derived layer
  AI summaries
  project updates
  reports
  presentations
  exports
```

The architecture must preserve one governing rule:

> Memory Trace does not silently mutate authoritative history. It projects, annotates and derives artefacts while preserving append-only evidence.

## 2. Current system baseline

### 2.1 Memory Seed core

Memory Seed is currently a Python 3.11+ package that installs a project-local `.memory-seed/` control plane. Its durable source of truth is Markdown and YAML under the repository. The core provides:

- project initialisation and forward-only updates;
- agent routing and hook configuration;
- append-only session records;
- multi-user-compatible session layouts;
- deterministic validation;
- lexical, semantic and recency-based retrieval;
- MCP search and fetch surfaces;
- typed relationship and lifecycle semantics;
- Git and branch integration.

The current architecture correctly separates authoritative files from derived reads. Computed inverse relationships are not written back to historical entries.

### 2.2 Canonical graph semantics

The canonical related-entry graph is built by `build_related_entry_graph()`. Consumers must not independently parse or reinterpret relationship fields.

The graph contract distinguishes:

| Concept | Meaning |
|---|---|
| `related_entries` | Authored relatedness |
| `inbound` | Computed backlinks |
| `supersedes` | Authored replacement/status transition |
| `superseded_by` | Computed inverse of replacement |
| `evolves` | Authored refinement/freshness transition |
| `evolved_by` | Computed inverse of refinement |
| `branch` | Historical axis label, not an edge |
| `continuity` | Artifact rename, migration or removal lineage |
| `topics` | Controlled neighbourhood membership, not an edge |
| `commits` | Evidence connecting a decision to implementation |

These distinctions must remain visible through the UI. Memory Trace must not flatten all relationships into a generic graph link.

### 2.3 Memory Trace today

Memory Trace is a separate source/product boundary that currently ships through the root
`memory-seed[trace]` optional extra and exposes the `memory-trace` command. It uses:

- FastAPI;
- Uvicorn;
- vanilla JavaScript;
- HTML and CSS;
- static assets packaged inside the root `memory-seed` Python wheel when the `trace` extra is used;
- a rebuildable SQLite cache outside the repository.

It already supports search, filters, timeline/Trail, graph and reader/detail views. The next architecture must preserve this functionality and treat the current implementation as the minimum parity baseline.

### 2.4 Strengths worth preserving

The existing design already has several strong properties:

- Markdown remains inspectable and Git-reviewable.
- Retrieval and graph semantics are shared between MCP and Trace.
- SQLite is explicitly non-authoritative and can be rebuilt.
- The optional-extra boundary keeps web dependencies out of plain Memory Seed installs while the
  source boundary keeps Trace UI development separate from Memory Seed core.
- Git branch history and typed edges provide richer semantics than a generic knowledge graph.
- Trace can operate locally without a hosted account.
- The Trail already renders a dense gitgraph-style chronology rather than a generic feed.

## 3. Product model

### 3.1 Primary user and buyer

The primary commercial design target is:

- **User:** developer or agent operator;
- **Buyer:** engineering lead, manager, agency owner or team administrator;
- **Secondary customer:** AI-forward agencies and consultancies;
- **Adoption channel:** solo developers using multiple coding agents.

There is no current adoption, retention or willingness-to-pay evidence. The correct market statement is therefore:

> Memory Seed has strong market-problem fit and a credible product-market-fit hypothesis, not demonstrated product-market fit.

### 3.2 Core product promise

Recommended positioning:

> Use any coding agent. Keep one inspectable project memory.

A more specific formulation:

> Memory Seed and Memory Trace provide Git-native institutional memory for software projects worked on by humans and AI agents.

### 3.3 Trail-first interaction model

The Trail is the primary experience:

```text
Search ---------------------> Trail match
Topic/file graph -----------> Trail neighbourhood
Entry selection ------------> Trail evidence workspace
Date/branch/PR selection ---> Trail range
AI summary -----------------> cited Trail evidence
Presentation/report --------> cited Trail evidence appendix
```

The graph serves a different task: exploring topic and document neighbourhoods through clusters and typed relationships. The quality target for graph interaction is the fluidity and progressive disclosure associated with Obsidian's graph view, adapted to Memory Seed's stronger provenance and typed-edge model.

## 4. Architectural layers

## 4.1 Authoritative layer

Authoritative sources are records whose meaning is not derived by the UI:

- `.memory-seed/sessions/` entries;
- session diagram sidecars;
- controlled topic vocabulary;
- Git commits and branch history;
- pull request and review records from their provider;
- append-only shared decision annotations;
- project participant and authority configuration.

Rules:

1. Historical entries remain append-only.
2. Computed inverse edges are never authored.
3. Pull request comments remain provider-owned; Trace links and displays them rather than replacing GitHub discussion.
4. Shared decision annotations are new authoritative project records but do not rewrite the decision being annotated.
5. Derived summaries and exports are not authoritative unless explicitly promoted.

## 4.2 Canonical semantic service layer

Memory Seed continues to own:

- session discovery and parsing;
- chunk extraction;
- retrieval ranking;
- graph construction;
- relationship validation;
- commit references;
- topic resolution;
- continuity aliases;
- entry and section addressing.

Memory Trace may add public service modules for:

- deterministic decision anchors;
- annotation validation;
- evidence-pack construction;
- Trail event assembly;
- provider-event normalisation.

New consumers must use these contracts rather than reimplementing semantics in React.

## 4.3 Projection layer

SQLite should be elevated from “cache implementation” to a documented **projection architecture** while remaining non-authoritative.

Potential projections include:

- parsed entries and sections;
- full-text search indexes;
- latest annotation versions;
- annotation history indexes;
- cached GitHub metadata;
- provider freshness state;
- evidence-pack cache;
- graph layout and viewport state;
- saved filters and workspace state;
- generated-artifact metadata.

Requirements:

- the projection can be deleted and rebuilt;
- authoritative records are sufficient to rebuild project-owned data;
- provider snapshots clearly record freshness and source;
- database schema migrations never rewrite authoritative Markdown;
- the database remains outside cloud-synchronised repository folders;
- corruption degrades to rebuild rather than data loss.

## 4.4 Experience layer

The experience layer is a React/TypeScript frontend served by the existing FastAPI package. It consists of:

- application shell;
- Trail;
- inspection workspace;
- search and filters;
- graph;
- evidence views;
- annotation controls;
- generated-artifact views.

The local and hosted products should share design tokens, domain components and most feature components, but use different shells where authentication, workspace switching and billing require it.

## 4.5 Derived layer

Derived artefacts include:

- AI timeline summaries;
- decision diffs;
- project updates;
- handover briefs;
- reports;
- presentations;
- tables and board exports.

Every material claim must cite evidence through a programmatic appendix. Derived output cannot silently become session memory.

## 5. API boundary

The next frontend should consume a versioned HTTP/JSON contract rather than directly depending on Python implementation details.

Recommended structure:

```text
memory_seed canonical services
          |
          v
memory_trace API models and routes
          |
          v
OpenAPI schema
          |
          v
generated TypeScript client
          |
          v
local and hosted React applications
```

Versioned resources should include:

- entries and sections;
- Trail events and ranges;
- graph nodes and typed edges;
- search results and match neighbourhoods;
- annotations;
- evidence packs;
- provider events;
- generated artefacts.

The Python and TypeScript models should be contract-tested against the same fixtures.

## 6. Identity and authority

### 6.1 Participants

Decision annotations that are shared with the project require an author listed in `project.yaml` participants.

Recommended extension:

```yaml
participants:
  - user: jean
    initials: JNL
    role: owner
```

Initial roles:

- `owner`;
- `maintainer`;
- `reviewer`;
- `contributor`;
- `observer`.

Roles determine whether an annotation can become an actionable request for an agent.

### 6.2 Annotation classes

Recommended classes:

- `note`;
- `question`;
- `correction`;
- `decision-challenge`;
- `action-request`;
- `approval`.

Only annotations whose kind, author role and current state meet the authority policy should be surfaced to agents as actionable. Other annotations remain context.

## 7. Local and hosted product boundary

### 7.1 Community/local

The local product remains useful without an account:

- single-project Trail;
- complete local history;
- search-to-Trail navigation;
- entry/evidence inspection;
- basic graph;
- basic filters;
- local shared annotations;
- offline operation;
- MCP integration.

The default initial graph range should be the last seven calendar days or last five days with activity. This is a viewport default, not a paywall; users can expand the range.

### 7.2 Pro

Potential individual paid value:

- cross-project dashboards and search;
- saved views;
- advanced decision comparison;
- advanced graph modes;
- local/BYOK AI summarisation;
- project updates;
- presentation generation;
- premium templates and exports.

### 7.3 Team/Cloud

Potential team value:

- hosted workspaces;
- project synchronisation;
- authenticated collaboration;
- GitHub live integration;
- shared reports;
- cross-project search;
- managed AI allowances;
- role and permission management;
- audit history.

### 7.4 Enterprise

Potential enterprise value:

- SSO/SCIM;
- self-hosting;
- GitHub Enterprise/GitLab/Azure DevOps;
- private AI providers;
- retention and residency controls;
- advanced audit and policy enforcement.

## 8. Non-functional requirements

- Python wheel remains the end-user distribution for local mode.
- End users do not require Node.js.
- Frontend build runs in development and release CI only.
- All runtime assets are local; no required CDN.
- Free local operation remains offline-capable.
- WCAG 2.2 AA is the accessibility target.
- Keyboard navigation is complete for primary workflows.
- Graph information has a list/table alternative.
- Initial Trail target: 10,000 entries and 50,000–100,000 chunks.
- Initial graph only renders bounded neighbourhoods/ranges.
- Telemetry in local mode is off by default and content-free when enabled.
- Hosted security is designed for private repositories and team data from the start.

## 9. Decisions

1. Adopt a Trail-first product architecture.
2. Keep canonical graph and retrieval semantics in Memory Seed.
3. Introduce a documented projection architecture around rebuildable SQLite.
4. Use React + TypeScript for the next frontend.
5. Preserve FastAPI and Python-wheel distribution.
6. Use a versioned API and generated TypeScript client.
7. Keep Trail rendering independent from the exploratory graph renderer.
8. Treat Evidence Packs as a first-class contract.
9. Add append-only decision annotations with deterministic anchors.
10. Keep generated outputs derived and evidence-linked.
11. Preserve a useful free local Trail; monetise advanced local analysis, collaboration, managed AI and hosted operation.
12. Require non-regression against the current vanilla implementation before replacement.

## 10. Document map

This blueprint is supported by:

- `memory-trace-frontend-architecture-and-design-system-proposal.md`;
- `memory-trace-evidence-annotations-and-projection-architecture.md`;
- `memory-trace-commercialisation-and-monetisation-report.md`;
- `memory-trace-hosted-product-and-security-architecture.md`;
- `memory-trace-next-generation-implementation-roadmap.md`;
- `../3_Spec/memory-trace-trail-search-and-graph-ux.md`;
- `../3_Spec/memory-trace-derived-artifact-provenance-contract.md`;
- the existing `memory-trace-ai-timeline-summarisation-plan.md`.

## 11. Source basis

This blueprint was prepared from:

- `functionality-audit.md`;
- `graph-edge-contract.md`;
- `memory-trace-ai-timeline-summarisation-plan.md`;
- `memory-seed-market-fit-report.md`;
- current Trail screenshots and design decisions supplied during review.
