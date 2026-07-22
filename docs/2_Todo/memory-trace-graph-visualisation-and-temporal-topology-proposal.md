---
title: "Memory Trace Graph Visualisation and Temporal Topology Proposal"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
recommended_target: "docs/2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md"
related:
  - "docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md"
  - "docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md"
  - "docs/3_Spec/memory-trace-trail-search-and-graph-ux.md"
  - "docs/3_Spec/graph-edge-contract.md"
---

# Memory Trace Graph Visualisation and Temporal Topology Proposal

Status: **PROMOTED to `2_Todo`** 2026-07-15 (active; folded into B0a/B0b of `0_NEXT_STEPS.md`).
Priority: P1 - contract, fixtures, and renderer evidence before React; selected-renderer implementation after the shell.
Source: Downloaded proposal set supplied by JNL on 2026-07-15.
Next action: Define the renderer-neutral graph projection/fixture contract, then benchmark vis-network against Cytoscape.js before selecting a renderer or changing default graph behaviour.

## 1. Executive decision

Memory Trace should replace its dependency-free prototype graph renderer with a mature, renderer-backed graph experience that is visually structured, semantically faithful, and lightly historical.

The recommended design is:

- **Topology first:** node fill colour communicates detected graph community or subsystem.
- **Typed semantics remain explicit:** edge colour, direction, width, dash pattern, and provenance communicate relationship meaning.
- **Time is a weak positional force:** older items drift left or down; newer items drift right or up, according to user-selected orientation.
- **The graph remains secondary to the Trail:** it explores structural neighbourhoods and provides transitions back to chronological evidence.
- **Renderer and data provider remain separate decisions:** Graphify may inspire the visual design without becoming the graph renderer or canonical graph source.
- **Benchmark vis-network and Cytoscape.js before final selection:** vis-network offers the fastest route to Graphify-like quality; Cytoscape.js offers stronger graph analysis, compound structures, and layout flexibility.

The default graph configuration should be:

```text
Colour: Topological community
Layout: Force-directed with mild temporal drift
Temporal orientation: Auto
Node size: Connectivity
Scope: Local or bounded neighbourhood
Inspector: Docked according to workspace preference
```

## 1.1 Constitutional fit

Five-question contribution:

- **Retrieval:** exposes bounded structural, topic, file, and lifecycle neighbourhoods with a direct route back to Trail evidence.
- **Validation:** requires common fixtures plus renderer, accessibility, offline-package, and scale benchmarks before selection or fallback retirement.
- **Trust:** keeps edge type, direction, timestamps, scope, provenance, and derived-versus-authored status inspectable.
- **Application:** turns retrieved relationships into navigable investigation paths while preserving shared selection.
- **Capture is not claimed:** layout and rendering never author entries or canonical edges.

Invariant guards: the graph consumes Memory Seed's canonical semantic service; layout, community, colour, and viewport data stay rebuildable; bounded display scope never becomes a retrieval filter; external/generated nodes remain visually distinct; and the current SVG renderer remains available until explicit parity sign-off.

## 2. Context and problem

The current Memory Trace graph is a useful prototype, but it is implemented as a custom SVG graph engine inside the vanilla frontend. It includes deterministic seeded positions, a hand-built force simulation, collision separation, pan and zoom, label suppression, and semantic edge styling.

This approach has established the product contract but now creates limitations:

- the graph remains visually flatter than mature network visualisation tools;
- straight edges create avoidable crossings;
- custom physics require ongoing maintenance;
- clustering is implicit rather than visually encoded;
- node hierarchy is weak because the size range is narrow;
- graph interactions are rebuilt alongside the full DOM;
- scale, animation, focus transitions, and progressive expansion require bespoke code;
- the renderer risks becoming an internal general-purpose graph engine, which is explicitly outside the product roadmap.

Graphify appears visually stronger because it combines a mature renderer with deliberate information hierarchy:

- vis-network rendering;
- ForceAtlas2-based physics;
- community-based colour;
- degree-based node size;
- smooth curved edges;
- confidence-based edge styling;
- aggressive label suppression;
- animated node focus;
- community filtering;
- aggregation into a community meta-graph when density is high.

Memory Trace should adopt these design principles while preserving its stronger typed relationship, provenance, decision, Git, and temporal semantics.

## 3. Product role of the graph

The graph is not a replacement for the Trail.

| Surface | Primary question |
|---|---|
| Trail | How and why did the project evolve? |
| Graph | What is structurally connected to this item? |
| Search | Where should investigation begin? |
| Inspector | What is the underlying evidence? |

The graph should support:

1. local graph around the current entry or decision;
2. topic neighbourhood;
3. file and document neighbourhood;
4. lifecycle graph for `evolves` and `supersedes`;
5. later structural-code enrichment;
6. community-level overview when detailed graphs become too dense.

A full global graph should remain deferred until real usage and performance evidence justify it.

## 4. Visual encoding contract

### 4.1 Primary visual channels

| Information | Primary visual channel |
|---|---|
| Topological community or subsystem | Node fill colour |
| Node type | Shape and optional icon |
| Importance or connectivity | Node size |
| Relationship type | Edge colour and label |
| Direction | Arrowhead |
| Authored, provider-derived, or generated provenance | Node border style and badge |
| Extracted versus inferred relationship | Edge width, opacity, and dash pattern |
| Selected state | Accent ring |
| Superseded state | Reduced saturation plus status marker |
| Approximate time | Mild positional pull |
| Exact date and provenance | Tooltip and inspector metadata |

### 4.2 Why topology owns colour

Agent-based colouring explains who authored an item, but does not explain why nodes form clusters. The graph’s first visual task is to reveal project structure.

Community colouring can expose clusters such as:

- retrieval;
- Memory Trace UI;
- CLI and MCP;
- graph infrastructure;
- documentation;
- release and packaging;
- tests;
- provider integrations.

Agent, user, node class, and provenance remain available as secondary modes, but should not be the default node fill.

### 4.3 Stable community colours

Community identifiers produced by Leiden, Louvain, or similar algorithms may change between rebuilds. Colour assignments must therefore be stabilised.

Recommended process:

1. compute current communities;
2. generate a community fingerprint from stable member identities and dominant topics or paths;
3. compare member overlap with the previous projection;
4. retain the previous colour when overlap exceeds a threshold;
5. allocate a new colour only for genuinely new communities;
6. persist the mapping in the rebuildable Memory Trace projection.

Suggested projection fields:

```text
community_id
community_fingerprint
community_label
community_colour_slot
community_member_count
community_dominant_topics
community_dominant_paths
community_previous_id
```

Colour mapping remains non-authoritative and may be rebuilt.

## 5. Optional temporal topology

### 5.1 Design objective

The graph should communicate approximate old-to-new direction without becoming a rigid timeline. The Trail remains the canonical chronological surface.

The force layout therefore combines:

```text
connection attraction
+ node repulsion
+ community cohesion
+ collision avoidance
+ weak temporal gravity
```

Topology must remain dominant.

### 5.2 Orientations

#### Horizontal

```text
Older  ←────────────────────────→  Newer
```

Older nodes receive a weak pull to the left. Newer nodes receive a weak pull to the right.

#### Vertical or portrait

```text
Newer
  ↑
  │
  ↓
Older
```

Older nodes receive a weak pull toward the bottom. Newer nodes receive a weak pull toward the top.

#### Automatic

```text
viewport width > height  → horizontal
viewport height ≥ width  → vertical
```

An explicit user preference overrides automatic behaviour.

### 5.3 Temporal force model

For each visible node:

```text
time_position =
  (node_time - oldest_visible_time)
  / (newest_visible_time - oldest_visible_time)
```

Target position:

```text
Horizontal:
  target_x = left_padding + time_position × usable_width

Vertical:
  target_y = bottom_padding - time_position × usable_height
```

The renderer applies a configurable attraction toward the target axis position.

Recommended user options:

```text
Temporal drift: Off | Mild | Strong
Orientation: Auto | Horizontal | Vertical
Temporal normalisation: Visible range | Project range
```

Default:

```text
Temporal drift: Mild
Orientation: Auto
Temporal normalisation: Visible range
```

Initial tuning should target a temporal force that is visibly meaningful but weaker than community and connection forces. A starting value near five per cent of the dominant attraction force is suitable for prototyping, but must be validated through fixtures rather than treated as a contract.

### 5.4 Date semantics by node type

| Node type | Temporal value |
|---|---|
| Memory entry | Authored timestamp |
| Decision anchor | Anchor entry timestamp |
| Commit | Commit timestamp |
| Pull request | Event timestamp relevant to the selected view |
| Annotation | Annotation event timestamp |
| File | Last relevant Git change within the selected revision or scope |
| Symbol | Last relevant Git change within the selected revision or scope |
| External provider observation | Indexed revision timestamp plus observed time |

Filesystem modification time must not be used for repository history because clone, checkout, and rebase operations make it unreliable.

### 5.5 Interpretation rules

Temporal placement is approximate. The inspector should expose the exact timestamp and source.

A graph legend should state:

```text
Temporal drift: Mild, horizontal
Visible range: 1 May–15 July 2026
Code revision: main@<sha>
```

The system must not imply that a current code graph represents the code structure that existed at an old decision date unless a historical revision was explicitly indexed.

## 6. Layout modes

Memory Trace should provide multiple graph layouts because one layout cannot serve all graph questions.

### 6.1 Topology

Pure force-directed layout based on graph connections and community cohesion.

Use for:

- general local graph;
- topic neighbourhood;
- file and document exploration;
- structural-code graph.

### 6.2 Temporal topology

Force-directed topology plus weak time gravity.

Use for:

- understanding how a subsystem evolved;
- identifying recently active communities;
- seeing long-lived concerns stretched across time;
- identifying migrations from old to new communities.

### 6.3 Evolution hierarchy

Directed hierarchical layout for `evolves` and `supersedes` relationships.

Use for:

- decision replacement chains;
- lineage analysis;
- explicit predecessor and successor navigation.

### 6.4 Community overview

Aggregated meta-graph where communities become nodes and cross-community relationships become weighted edges.

Use when:

- visible graph density exceeds a configured threshold;
- users request a project-level overview;
- the detailed graph would become a hairball.

Selecting a community should expand into its local detailed graph.

### 6.5 Motion and force exploration

Motion is an exploration affordance, not evidence. A moving position must never imply a changed
relationship, timestamp, rank, or authoritative graph fact; all simulation state remains local and
rebuildable.

The default is **Settled**:

- run the selected topology or temporal layout to its bounded convergence budget;
- cache the resulting positions by dataset, scope, layout mode, temporal settings, and renderer version;
- restore an exact cache match without rerunning the simulation; and
- keep the graph still while a person reads, selects, searches, or changes Inspector dock position.

Provide two optional exploration behaviours:

- **Animate layout** — visibly interpolate force iterations from the current layout to the new settled
  layout when the user explicitly requests it. It is useful for understanding how a community or temporal
  force affects a bounded graph, but ends by returning to the same cached settled state as the default.
- **Reheat on drag** — after a deliberate node drag, briefly re-run local forces so neighbouring nodes can
  respond, then cool and persist the resulting positions in the local renderer cache. It never writes
  positions to Markdown or changes the graph projection.

Continuous physics is permitted only for a bounded exploratory graph (initially at most 150 visible
nodes). Above that threshold, the UI must use a short end-state transition or Settled mode and explain
why live motion is unavailable. This follows the measured layout profile: force layout remains useful at
the default scale but cannot be allowed to monopolise the main thread on larger graphs.

## 7. Renderer evaluation

### 7.1 vis-network

Strengths:

- closest visual match to Graphify;
- built-in ForceAtlas2-based physics;
- mature pan, zoom, hover, focus, and selection;
- smooth edges and arrowheads;
- rapid implementation;
- suitable for a read-only exploratory graph.

Weaknesses:

- custom temporal constraints may require extending layout behaviour or carefully manipulating positions;
- fewer graph-analysis features than Cytoscape.js;
- accessibility and list-equivalent behaviour must be implemented outside the canvas;
- large graphs remain canvas-bound rather than WebGL-bound.

### 7.2 Cytoscape.js

Strengths:

- strong typed-graph model;
- directed edge support;
- selectors and filtering;
- graph algorithms;
- compound nodes and community containers;
- multiple layout extensions;
- better foundation for switching between topology, temporal, and hierarchy modes.

Weaknesses:

- more configuration work to reproduce Graphify’s immediate visual quality;
- layout extensions and styling need deliberate curation;
- custom node presentation is less React-native than React Flow.

### 7.3 Sigma.js and Graphology

Retain as a future global-graph option if projects require thousands or tens of thousands of simultaneously rendered nodes. It should not be the first renderer unless scale tests show canvas-based approaches are insufficient.

### 7.4 React Flow

React Flow remains suitable for authored diagrams, workflow builders, and manually arranged node interfaces. It should not be assumed to be the default exploratory graph renderer.

### 7.5 Decision process

Build one bounded prototype in vis-network and one in Cytoscape.js using the same fixture and design tokens.

Benchmark:

- first stable render;
- pan and zoom responsiveness;
- hover and selection latency;
- local expansion;
- community filtering;
- temporal drift implementation;
- hierarchical lifecycle layout;
- 500, 1,000, and 5,000-node behaviour;
- lazy-loaded bundle cost;
- accessibility support burden;
- packaged wheel behaviour without internet access.

The selected renderer must be bundled locally. CDN loading is incompatible with the offline-first product requirement.

## 8. Graph controls

Recommended toolbar:

```text
Colour:
  Communities
  Node type
  Provenance
  Agent

Layout:
  Topology
  Temporal topology
  Evolution hierarchy
  Community overview

Motion:
  Settled (default)
  Animate layout

Drag response:
  Fixed
  Reheat on drag

Temporal drift:
  Off
  Mild
  Strong

Orientation:
  Auto
  Horizontal
  Vertical

Node size:
  Connectivity
  Importance
  Fixed

Scope:
  Local
  Topic
  File
  Evolution
  Current range
```

Graph-only controls belong in the graph workspace and must not pollute the Trail.

## 9. Interaction model

Required interactions:

- smooth pan and zoom;
- search and animated focus;
- explicit force-layout animation for bounded exploration, with stop/reset controls;
- optional reheat-on-drag response that cools to a stable cached layout;
- hover neighbour emphasis;
- selection that updates the shared inspector;
- progressive label disclosure;
- community show and hide;
- node-class and edge-type filters;
- local expansion by depth;
- graph-to-Trail transition;
- Trail-to-graph transition with selection preserved;
- minimap or viewport awareness when beneficial;
- reset and fit controls;
- list or table equivalent for accessibility.

Selection must remain stable when:

- the layout mode changes;
- the inspector changes dock position;
- the centre view switches between Trail and Graph;
- the left pane opens or closes;
- the viewport resizes.

## 10. API and projection requirements

The graph response should eventually expose:

```text
node_type
community_id
community_label
community_fingerprint
temporal_value
temporal_source
provenance_class
authority_class
connectivity
importance_score
revision
provider
stale
```

Layout coordinates and community-colour assignments belong in the rebuildable projection, not authoritative Markdown.

Suggested cached state:

```text
renderer
layout_mode
temporal_strength
temporal_orientation
visible_scope
node_positions
viewport
community_colour_map
selected_node
hidden_communities
motion_mode
drag_response
```

## 11. Accessibility

- Every graph mode must have a list or table equivalent.
- Relationship meaning must not depend on colour alone.
- Node type must not depend on shape alone.
- Search results must be keyboard navigable.
- Selected-node changes must be announced to assistive technology.
- Reduced-motion mode disables animated focus and non-essential physics transitions.
- `prefers-reduced-motion` selects Settled mode and disables reheat-on-drag by default; an animation
  preference must remain visible and reversible rather than being silently inferred from motion alone.
- High-contrast themes must preserve community differentiation.
- Temporal direction must be stated textually in the graph legend.

## 12. Performance and scale

Initial targets:

- local graph: up to 500 visible nodes;
- bounded project graph: up to 1,000 visible nodes;
- community overview: derived when the detailed graph exceeds the useful density threshold;
- future global graph: only after evidence supports the requirement.

The renderer must lazy-load. Layout work should avoid blocking the main thread where practical. Positions should be cached by dataset, scope, renderer version, and layout settings.

## 13. Implementation phases

Phases A-B are **B0a pre-React** work. They settle contracts and evidence without committing the product to a renderer. Phases C-F are **B0b post-shell** implementation work and must consume the B0a projection and fixtures.

### Phase A — B0a renderer-neutral contract

- formalise node, edge, provenance, community, and temporal fields;
- separate graph projection from renderer implementation;
- create common fixtures;
- retain current SVG renderer as fallback.

### Phase B — B0a renderer benchmark

- implement vis-network prototype;
- implement Cytoscape.js prototype;
- benchmark topology, temporal topology, and hierarchy modes;
- record selection decision.

### Phase C — B0b topology-first visual encoding

- add community detection;
- stabilise community colour assignments;
- move agent identity to secondary styling;
- enlarge node-size range;
- add curved and confidence-styled edges.

### Phase D — B0b temporal topology

- add temporal values and provenance;
- implement horizontal, vertical, and automatic orientation;
- add Off, Mild, and Strong controls;
- validate that communities remain recognisable.

### Phase D1 — B0b bounded force motion

- retain Settled as the default and route every layout result through the existing position cache;
- add Animate layout as an explicit, cancellable presentation mode for bounded node sets;
- add Fixed/Reheat-on-drag response, with a cooling cap and no graph-data refetch or renderer remount;
- apply the 150-visible-node live-motion threshold and an end-state/Settled fallback above it;
- respect reduced-motion preferences and preserve the list/table equivalent throughout motion;
- measure interaction frame rate, convergence time, and main-thread cost separately from data loading.

> **Conformance note, 2026-07-22.** Shipped in `memory-trace/client/src/`. Settled remains the default
> and every layout result still routes through the `settledPositions` cache in `GraphWorkspace.tsx`.
> Animate is cose `animate: true` — the same iterations from the same seeds, so it converges to the
> identical positions Settled produces and the cache stays valid either way. Reheat-on-drag runs a
> d3-force simulation over a two-hop neighbourhood (one-hop fallback for hubs, capped at 150) with a
> pinned boundary ring, cooling to rest or 1.5s, writing only into the renderer cache — no refetch, no
> remount, nothing into Markdown. The 150-node threshold gates Animate, with the end state applied
> above it and the reason stated in the Settings note. `prefers-reduced-motion` disables both controls
> visibly and forces Settled/Fixed. Measured live: a degree-5 drag moved its 5 neighbours and the 3
> second-hop nodes and **zero** of the 51 nodes outside the two-hop set; the arrangement then survived
> a full remount with 0px drift.
>
> One decision this section did not specify: **where edgeless entries go**. They were previously not
> rendered at all, which made the coverage readout look like a cap ("462 of 603"). They now take
> deterministic rings outside the connected core's bounding box — the closed form of repulsion plus
> weak centre gravity — and are deliberately excluded from the simulation, since a node with no edge
> has no spring to balance repulsion and would be flung through the core.

### Phase E — B0b density and aggregation

- add community overview;
- add drill-down and return transitions;
- test larger fixtures;
- add viewport and saved-state projection.

### Phase F — B0b promote and retire fallback

- complete parity and accessibility checks;
- validate packaged wheel without network access;
- retain fallback until explicit sign-off;
- retire the custom renderer only after acceptance criteria pass.

## 14. Acceptance criteria

- Default colour communicates stable topological community.
- Agent and provenance remain inspectable through secondary channels.
- Mild temporal drift is optional and enabled by default only after usability validation.
- Horizontal orientation pulls older nodes left and newer nodes right.
- Vertical orientation pulls older nodes down and newer nodes up.
- Topology remains recognisable under temporal drift.
- Settled remains the default, and an exact cached graph remount restores positions with no simulation.
- Animate layout is opt-in, cancellable, and finishes at the same settled positions as non-animated layout.
- Reheat-on-drag changes only local renderer positions; it performs no graph-data request and never authors
  a position or relationship into Markdown.
- Live force animation is unavailable above the bounded visible-node threshold, with a clear end-state
  fallback rather than a degraded or frozen page.
- Reduced-motion preferences disable non-essential force motion and keep every graph action available by
  keyboard and through the list/table equivalent.
- Exact timestamps remain available in the inspector.
- Directed lifecycle edges retain their canonical direction.
- Graph-to-Trail and Trail-to-graph transitions preserve selection.
- Renderer works fully offline from an installed wheel.
- Large graphs degrade into a useful community overview rather than a hairball.
- List or table equivalents support keyboard-only workflows.

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Community colours change after rebuild | Stable fingerprint and overlap-based colour reassignment |
| Temporal force damages cluster readability | Mild default, explicit Off control, fixture-based threshold |
| Continuous force simulation blocks reading or input | Settled default, bounded live-motion threshold, cancellable cooling budget, and end-state fallback |
| Motion implies false historical evidence | Explain motion as renderer-local exploration; preserve exact dates in Inspector and Trail |
| Users infer exact chronology from approximate position | Legend, inspector timestamps, Trail transition |
| Renderer becomes tightly coupled to API shapes | Renderer-neutral projection contract |
| Graph bundle becomes too large | Lazy loading and bundle budgets |
| Global graph becomes visually impressive but unusable | Bounded defaults and community aggregation |
| Older nodes appear less important | Do not use strong age-based fading |
| External code nodes use unreliable dates | Git-derived revision-aware timestamps only |

## 16. Final recommendation

Proceed with a renderer-neutral graph projection, benchmark vis-network against Cytoscape.js, and adopt topology-first colour plus optional mild temporal gravity as the defining visual model.

The resulting graph should answer three questions simultaneously:

```text
Colour   → Which subsystem or neighbourhood?
Position → How is it connected, and approximately when?
Edges    → What exact relationship exists?
```

This gives Memory Trace a graph that is visually stronger than the current prototype and more semantically useful than Graphify’s generic project map.
