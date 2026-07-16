---
title: "Memory Trace Trail, Search and Graph UX Specification"
date: "2026-07-11"
project: "memory-seed"
status: "proposed-specification"
spec_binding: candidate
parent: "../2_Todo/memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Trail, Search and Graph UX Specification

Status: Active proposed specification, promoted from inbox on 2026-07-11. B0a shell clarification
implemented in the vanilla UI on 2026-07-16; renderer and dock-layout work remain separately gated.
Priority: P1 UX contract for Trail/search/graph parity before frontend replacement.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, reconciled with current Trail UI decisions and completed product/trail plan.
Scope: Trail-first hierarchy, search-to-Trail contract, range/scale behaviour, inspection workspace, graph page, cross-tab selection, and accessibility.
Non-goals: No graph-edge semantic redefinition, no full global graph before density validation, no mobile-first authoring.
Dependencies: `../2_Todo/memory-trace-product-and-system-architecture-blueprint.md`, `../2_Todo/memory-trace-frontend-architecture-and-design-system-proposal.md`, `graph-edge-contract.md`, and current Memory Trace parity fixtures.
Acceptance criteria: Trail/search/graph behaviours meet the specification without losing current vanilla Trail density, typed relationships, selection context, or keyboard/a11y support.

## 1. Purpose

This specification defines the signature Memory Trace interaction model. It is implementation-neutral except where the product requirement depends on renderer behaviour.

## 2. Product hierarchy

The primary hierarchy is:

1. Trail;
2. search and filtering;
3. inspection workspace;
4. graph exploration;
5. AI and export actions.

The Trail is not a secondary tab. It is the primary chronological context through which project memory is understood.

### 2.1 Current B0a shell contract

The vanilla shell has three independent regions: **Navigation and filters** on the left, the **Trail or
Graph workspace** in the centre, and the **Inspector** on the right. The navigation control toggles
only the left region; it never hides or changes the centre workspace. The Inspector control is
independent: selection continues to update shared state while it is hidden, and reopening it presents
that selection without changing the Trail position or Graph viewport. `Ctrl/Cmd+B` toggles navigation;
`Ctrl/Cmd+I` toggles the Inspector. This is the B0a clarification only, not the later dockable-Inspector
implementation.

Manual refresh also re-enumerates local worktrees without using a browser-cached response. It retains the active worktree while it exists, otherwise falls back to the root checkout, labelled **current project**; non-root checkouts are labelled **worktree**.

## 3. Trail model

The Trail is a vertical gitgraph-style chronology combining:

- session entries;
- branch lanes;
- relationship lanes;
- supersession/evolution status;
- commits;
- pull requests and review events;
- annotations;
- generated-artifact references.

### 3.1 Non-negotiable current behaviours

Preserve:

- vertical chronological scrolling;
- branch/merge lanes;
- typed relationships such as related/evolves/supersedes;
- entry rows aligned to the graph;
- branch badges;
- selection highlighting;
- a persistent inspection surface;
- dense information presentation;
- incremental loading of older entries.

### 3.2 Event classes

Trail events must display their provenance class:

- authored memory;
- source-control event;
- pull-request/review event;
- automation/CI event;
- human annotation;
- release event;
- generated artefact.

External and generated events must not visually appear as authored memory.

## 4. Search-to-Trail contract

1. A user enters a query.
2. The backend returns ranked entry matches and chronological neighbourhoods.
3. The Trail initially moves to the strongest neighbourhood.
4. All matching entries are highlighted.
5. Additional match regions are marked on a scrollbar/minimap.
6. Next/previous controls cycle through matches.
7. A compact ranked-results drawer allows direct selection.
8. The inspection workspace changes while the Trail retains position and context.

Search must not terminate in a detached results page by default.

### 4.1 Search result semantics

Use deterministic relations first when constructing neighbourhoods:

1. supersedes/evolves lineage;
2. branch;
3. shared PR/commit;
4. controlled topic;
5. shared file;
6. chronological proximity;
7. semantic similarity as ranking/suggestion only.

Semantic similarity may suggest links but must not silently create visible authoritative relationships.

## 5. Trail range and scale

Initial load:

- last seven calendar days; or
- last five days containing activity.

The exact default can be user-configurable. Users can expand by date, active day, branch, PR, topic or arbitrary start/end entry.

At scale:

- virtualise rows;
- maintain stable scroll anchors;
- preserve lane continuity across window boundaries;
- load older/newer ranges incrementally;
- provide bounded summary markers rather than rendering every offscreen edge.

Target: 10,000 entries per project.

## 6. Inspection workspace

The inspection workspace is more than a “details sidebar.” It is the document and evidence workspace.

Potential tabs/sections:

- Summary;
- Entry;
- Decisions;
- Evidence;
- Relationships;
- Files;
- Commits;
- Pull requests;
- Annotations;
- Generated artefacts;
- History.

### 6.1 Layout variants

#### Wide split

Trail left/centre, inspection workspace right.

#### Reading mode

Trail selection remains visible while the selected document is presented in a wider vertical reading surface. This may appear below the Trail or as a dedicated reading layout.

This variant must be prototyped because it may improve long-form reading compared with a narrow sidebar.

#### Narrow screen

Inspection opens as a sheet/drawer. Closing it must restore focus and Trail position.

## 7. Decision navigation

Selecting a decision:

- highlights its deterministic anchor;
- shows predecessor/successor relationships;
- shows typed related entries;
- exposes annotations;
- provides previous/next decision navigation;
- provides source path and provenance.

The user must be able to cycle through connected entries without losing chronological context.

## 8. Graph page

The graph is a specialised exploration surface for topic, document and relationship neighbourhoods.

### 8.1 Initial modes

1. Local graph around current entry.
2. Topic neighbourhood.
3. File/document graph.
4. Evolution-only graph.

A full global graph is deferred until density and performance are validated.

### 8.2 Graph-specific filters

Graph-only controls belong on the graph page:

- relationship types;
- node classes;
- topic selection;
- date/activity range;
- minimum connectivity;
- active/superseded state;
- local/global scope;
- layout mode;
- label density.

Do not pollute the Trail tab with controls that only affect force-directed graph behaviour.

### 8.3 Interaction benchmark

Meet or exceed the useful interaction qualities of Obsidian graph view:

- smooth pan/zoom;
- local/global modes;
- hover and neighbour emphasis;
- search and focus;
- progressive disclosure;
- clustering;
- density control;
- minimap/viewport awareness.

Memory Trace should exceed Obsidian in:

- typed relationship semantics;
- provenance;
- chronological context;
- branch/PR evidence;
- decision status;
- direct transition back to the Trail.

## 9. Cross-tab behaviour

Search behaviour adapts to the selected tab:

| Tab | Search action |
|---|---|
| Trail | Scroll to ranked neighbourhood and mark matches |
| Graph | Focus/isolate matching nodes |
| Inspector | Highlight matching section/decision |
| Artifacts | Match source claims and citations |

Selection should remain coherent across tabs through a shared entry/decision identity.

## 10. Accessibility

- Every graph view has a list/table equivalent.
- Trail entries are navigable by keyboard.
- Relationship labels are not colour-only.
- Focus position is preserved through tab and inspector transitions.
- Reduced-motion preference disables non-essential movement.
- Search match announcements are screen-reader accessible.
- Dense mode remains legible at browser zoom.

## 11. Acceptance criteria

- Search reliably navigates to the strongest Trail neighbourhood.
- Next/previous match cycling preserves context.
- Current vanilla Trail behaviours are retained.
- Reading-mode inspector prototype is tested.
- Graph filters are isolated to the graph surface.
- Graph search can transition to the corresponding Trail entry.
- Default graph range is bounded but expandable.
- Provenance classes remain visually distinct.
- Keyboard-only primary workflow is complete.
