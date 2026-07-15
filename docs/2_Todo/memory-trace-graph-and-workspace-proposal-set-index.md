---
title: "Memory Trace Graph and Workspace Proposal Set"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
recommended_target: "docs/2_Todo/memory-trace-graph-and-workspace-proposal-set-index.md"
---

# Memory Trace Graph and Workspace Proposal Set

Status: **PROMOTED to `2_Todo`** 2026-07-15 (active; folded into `0_NEXT_STEPS.md` as the B0 graph/workspace programme).
Priority: P1 - B0a decisions and evidence before React; B0b implementation after the React shell.
Source: Downloaded proposal set supplied by JNL on 2026-07-15.
Next action: Complete B0a (shell behaviour, renderer-neutral contract, fixtures, benchmark, topology model), then use its outputs in the React shell and complete B0b (selected renderer and dockable inspector) before any optional structural-provider pilot.

## 1. Purpose

This document coordinates three proposals produced from the Memory Trace graph and workspace review:

1. **Graph visualisation and temporal topology**
2. **Structural graph enrichment providers**
3. **Three-region workspace and dockable inspector**

The proposals are deliberately separate because they govern different architectural decisions:

```text
Graph semantics and visualisation
  ≠ structural code extraction
  ≠ application workspace layout
```

They must remain independently replaceable while sharing stable identities, selection state, and projection contracts.

## 1.1 Constitutional fit

Five-question contribution:

- **Retrieval:** graph neighbourhoods expose typed structural and lifecycle relationships and always lead back to Trail evidence.
- **Validation:** renderer, topology, accessibility, packaging, and scale decisions are fixture- and benchmark-gated.
- **Trust:** provenance, authority, confidence, freshness, and exact edge types remain inspectable.
- **Application:** shared selection and a stable workspace help people apply retrieved evidence without losing context.
- **Capture is not claimed:** graph rendering and provider extraction do not author canonical memory.

Invariant guards:

- Memory Trace remains useful offline and without a structural provider (Invariant #1).
- Authored history is never mutated by layouts, renderers, or provider observations (Invariant #2).
- Every external or generated claim retains source, revision, and provenance (Invariant #3).
- Memory Seed owns canonical decision semantics; UI and providers do not redefine them (Invariants #4 and #5).
- Communities, positions, colours, viewport state, and provider indexes remain disposable projections (Invariant #6).
- Bounded graph views are presentation scopes only; they never remove live history from canonical retrieval (Invariant #7).

Promotion gates: evidence before renderer choice; one canonical graph projection rather than renderer-specific semantics; current SVG fallback retained until parity, accessibility, offline packaging, and performance sign-off.

## 2. Proposal map

### 2.1 Graph visualisation and temporal topology

File:

```text
memory-trace-graph-visualisation-and-temporal-topology-proposal.md
```

Defines:

- topology-first node colour;
- stable community colour mapping;
- optional temporal force;
- horizontal and vertical temporal orientation;
- topology, temporal, evolution, and community layouts;
- vis-network versus Cytoscape.js benchmark;
- graph interaction, accessibility, scale, and acceptance criteria.

Primary decision:

> Colour explains topology. Position explains topology plus approximate time. Edges explain exact typed relationships.

### 2.2 Structural graph enrichment provider

File:

```text
memory-trace-structural-graph-enrichment-provider-proposal.md
```

Defines:

- provider-neutral enrichment architecture;
- code-review-graph as the first production candidate;
- Graphify as a prototype and UX benchmark;
- SCIP as a later precision provider;
- authority, provenance, revision, confidence, and freshness contracts;
- namespaced identities;
- decision-to-commit-to-file-to-symbol joining;
- impact analysis and Evidence Pack integration.

Primary decision:

> External providers enrich the graph but never own Memory Seed’s canonical decision semantics.

### 2.3 Three-region workspace and dockable inspector

File:

```text
memory-trace-three-region-workspace-and-dockable-inspector-proposal.md
```

Defines:

- hamburger control limited to the left pane;
- Trail and Graph as centre workspace modes;
- independently visible inspector;
- right and bottom docking;
- responsive Auto mode;
- shared selection and search state;
- graph-orientation and inspector-dock synergy;
- React shell and migration strategy.

Primary decision:

> The centre pane is the product workspace. The left pane navigates and filters. The inspector examines selected evidence.

## 3. Combined target architecture

```text
Authoritative layer
  Memory Seed entries and decisions
  Git history
  append-only annotations
          |
          v
Canonical semantic services
  retrieval
  typed lifecycle graph
  topics
  continuity
  commit references
          |
          +-----------------------------+
          |                             |
          v                             v
Structural enrichment providers     Git/provider evidence
  code-review-graph                 commits, PRs, reviews
  SCIP later
  Graphify benchmark
          |                             |
          +---------------+-------------+
                          v
Memory Trace projection
  namespaced graph nodes
  typed and provenance-aware edges
  communities
  temporal values
  provider freshness
  saved layout state
                          |
                          v
Three-region experience
  Left pane: navigation and filters
  Centre: Trail / Graph / Artifacts
  Inspector: evidence and details
```

## 4. Dependency order

Recommended implementation order:

### B0a - pre-React decisions, contracts, and evidence

### Step 1 — shell clarification

- hamburger toggles only the left pane;
- Trail and Graph remain visible centre modes;
- specify independent inspector visibility and shared selection behaviour;
- make only vanilla-safe clarification changes that do not duplicate the future shell.

### Step 2 — renderer-neutral graph contract

- formalise graph projection models;
- separate renderer from graph semantics;
- preserve current SVG renderer as fallback;
- add fixtures.

### Step 3 — renderer benchmark

- vis-network prototype;
- Cytoscape.js prototype;
- topology and temporal layouts;
- select renderer.

### Step 4 — topology-first graph

- specify community detection and stable colour mapping;
- define node hierarchy, curved/typed edge styling, and local/community modes;
- prove the model against fixtures and the current SVG fallback;
- do not perform the full renderer migration yet.

### B0b - post-React-shell implementation

### Step 5 — selected renderer and topology implementation

- integrate the selected renderer through the renderer-neutral projection;
- implement topology-first and optional mild-temporal layouts;
- preserve graph-to-Trail selection and the SVG fallback until sign-off.

### Step 6 — dockable inspector

- right and bottom docking;
- layout preferences;
- graph-orientation recommendations;
- reading-mode validation.

### Optional structural-provider tail - only after native B0b acceptance

### Step 7 — provider contract

- namespaced identities;
- revision and freshness;
- confidence and authority classes;
- provider status UI.

### Step 8 — code-review-graph pilot

- file and symbol extraction;
- decision-to-code join;
- impact lens;
- stale index handling.

### Step 9 — comparative provider validation

- Graphify adapter or export comparison;
- SCIP precision experiment;
- final provider support decision.

## 5. Cross-cutting rules

### 5.1 Trail-first hierarchy

The Trail remains the default and primary explanation of project evolution. The graph must always provide a path back to Trail evidence.

### 5.2 One authority per concept

- Memory Seed owns decision and lifecycle meaning.
- Git owns revision history.
- Providers own derived structural observations.
- Memory Trace owns the read projection and presentation.

### 5.3 Renderer independence

The graph renderer consumes a Memory Trace projection. It must not read Graphify, code-review-graph, or other provider internals directly.

### 5.4 Provider optionality

Memory Trace must remain fully usable without structural code enrichment.

### 5.5 Offline-first delivery

Frontend renderers and required assets must be bundled into the installed package. Public CDN access must not be required.

### 5.6 Shared selection

Trail, Graph, Search, and Inspector operate on one shared identity model.

### 5.7 Progressive disclosure

Bound graph scope by default. Use local expansion, labels on demand, and community aggregation rather than rendering all nodes and labels at once.

### 5.8 Derived data remains rebuildable

Communities, colours, temporal positions, provider indexes, graph layouts, and viewport state remain non-authoritative projections.

## 6. Key product synergies

### 6.1 Topology plus time

Community colour reveals subsystem structure while temporal drift reveals approximate project evolution.

### 6.2 Graph plus Trail

The graph finds structural neighbourhoods. The Trail explains their chronology and rationale.

### 6.3 Enrichment plus evidence

Structural providers extend decisions into implementation evidence without weakening authored history.

### 6.4 Workspace plus graph orientation

- horizontal temporal graph → bottom inspector;
- vertical temporal graph → right inspector;
- pure topology → saved user preference.

### 6.5 Impact plus Evidence Packs

A selected decision can generate a bounded evidence chain:

```text
Decision → Commit → File → Symbol → Dependants → Tests
```

### 6.6 Drift detection plus continuity

Continuity mappings and structural indexes can identify removed, renamed, or replaced implementation artifacts that no longer match active decisions.

## 7. Decisions that should remain open until prototyping

- vis-network versus Cytoscape.js;
- exact temporal force strength;
- default community-detection algorithm;
- automatic inspector-dock switching versus recommendation only;
- code-review-graph process adapter versus Python library adapter;
- first supported code languages;
- threshold for community aggregation;
- whether code communities should influence authored topic suggestions.

These should be resolved through fixtures and user tasks rather than preference alone.

## 8. Unified success measures

### Technical

- graph remains responsive at target scale;
- renderer is lazy-loaded and works offline;
- community colours remain stable across minor rebuilds;
- temporal drift preserves topology;
- pane and selection state survive layout changes;
- provider absence and failure degrade gracefully;
- revision and confidence remain visible.

### Product

- users can identify a project subsystem visually;
- users can understand whether activity is old, recent, or sustained;
- users can move from a decision to implementation evidence;
- users can return from structural exploration to chronological rationale;
- users can choose reading or graph space without losing context;
- graph usage produces useful actions rather than visual novelty.

## 9. Recommended document integration

Place the four documents into `docs/2_Todo/` initially.

After validation:

- promote stable graph interaction rules into `docs/3_Spec/memory-trace-trail-search-and-graph-ux.md`;
- promote provider models into a dedicated versioned API or provider contract specification;
- promote workspace behaviour into the frontend architecture and UX specifications;
- retain evaluation evidence and renderer benchmarks under `docs/4_Reference/`.

## 10. Final synthesis

The proposals establish a coherent direction:

```text
Trail tells the story.
Graph reveals structure.
Topology owns colour.
Time gently biases position.
Providers add implementation evidence.
The centre pane owns primary work.
The inspector adapts around that work.
```

Together, these changes move Memory Trace from a capable prototype toward a distinctive project-intelligence environment without surrendering the local-first, Markdown-first, typed, and evidence-preserving architecture of Memory Seed.
