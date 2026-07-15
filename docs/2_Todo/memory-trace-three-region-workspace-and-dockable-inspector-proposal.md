---
title: "Memory Trace Three-Region Workspace and Dockable Inspector Proposal"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
recommended_target: "docs/2_Todo/memory-trace-three-region-workspace-and-dockable-inspector-proposal.md"
related:
  - "docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md"
  - "docs/2_Todo/memory-trace-frontend-architecture-and-design-system-proposal.md"
  - "docs/3_Spec/memory-trace-trail-search-and-graph-ux.md"
  - "docs/2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md"
---

# Memory Trace Three-Region Workspace and Dockable Inspector Proposal

Status: **PROMOTED to `2_Todo`** 2026-07-15 (active; folded into B0/B2 sequencing in `0_NEXT_STEPS.md`).
Priority: P1 - shell behaviour contract before React; dockable-inspector implementation after the React shell.
Source: Downloaded proposal set supplied by JNL on 2026-07-15.
Next action: Specify and, where non-duplicative, apply vanilla-safe shell clarification; carry full docking, persistence, and responsive layout implementation into the React shell.

## 1. Executive decision

Memory Trace should adopt a three-region desktop workspace:

```text
Left pane     → navigation, filters, saved views, project controls
Centre pane   → primary view: Trail, Graph, and later other workspace modes
Inspector     → selected entry, decision, evidence, files, commits, and history
```

The hamburger control must toggle only the left pane. It must not represent or hide the Trail, Graph, or other primary centre views.

The inspector should be independently dockable:

- **Right:** vertical side-by-side split;
- **Bottom:** horizontal stacked split;
- **Auto:** responsive recommendation based on viewport and active graph orientation;
- **Hidden:** centre view uses the available workspace while selection remains preserved.

This shell should treat Trail, Graph, Search, and Inspector as coordinated views over one shared selection state rather than separate pages.

## 1.1 Constitutional fit

Five-question contribution:

- **Retrieval:** shared selection keeps Search, Trail, Graph, and Inspector on one evidence path.
- **Validation:** responsive, keyboard, persistence, reading-mode, and installed-wheel workflows gate acceptance.
- **Trust:** the Inspector keeps source, provenance, timestamps, and exact relationships visible beside derived views.
- **Application:** the three-region hierarchy makes retrieved evidence usable for repeated investigation and review.
- **Capture is not claimed:** pane state and selection are experience-layer projections, not memory writes.

Invariant guards: layout changes never rewrite historical entries; selection and viewport state remain disposable; all required assets work offline; the vanilla UI remains the fallback until parity; and no centre view may replace Memory Seed's canonical retrieval or graph semantics.

## 2. Problem

The current interaction model visually suggests that nearly everything other than the entry viewer belongs to a hamburger menu. This weakens the product hierarchy:

- the Trail appears like hidden navigation rather than the primary product surface;
- the graph appears as an auxiliary menu screen rather than a centre workspace mode;
- the entry viewer dominates the perceived application structure;
- opening and closing navigation risks being confused with changing the main view;
- responsive behaviour is tied to pane visibility rather than explicit user layout preferences;
- long-form reading and wide graph exploration compete for the same fixed side-inspector arrangement.

Memory Trace is evolving into a project-intelligence workspace. Its shell should therefore resemble a desktop analysis application rather than a document viewer with a menu overlay.

## 3. Information architecture

### 3.1 Top bar

The top bar should contain:

- left-pane toggle;
- project or worktree selector;
- global search;
- centre-view switcher;
- optional inspector toggle;
- theme and application-level controls.

Suggested centre-view switcher:

```text
[ Trail ] [ Graph ] [ Artifacts ]
```

Potential later additions must pass a primary-workspace test. A view belongs in the centre switcher only when it changes the main way the project is explored.

### 3.2 Left pane

The left pane contains controls that navigate or constrain the workspace:

- project or workspace navigation;
- worktree or branch selection where not kept in the top bar;
- saved views;
- date, user, agent, and topic filters;
- graph-specific filters when Graph is active;
- artifact filters when Artifacts is active;
- provider status and optional enrichment controls;
- project-level settings entry point.

The left pane supports:

```text
Expanded | Compact | Hidden
```

The hamburger toggles this pane only.

### 3.3 Centre pane

The centre pane is the main working surface.

Primary modes:

- Trail;
- Graph;
- Artifacts or Evidence Packs when promoted;
- future decision overview only if it proves to be a distinct primary mode.

The Trail remains the default centre view and primary product experience.

### 3.4 Inspector

The right-hand entry viewer should be reframed as an inspection workspace rather than a fixed sidebar.

Recommended tabs or sections:

- Summary;
- Entry;
- Decisions;
- Evidence;
- Relationships;
- Files;
- Commits;
- Pull requests;
- Annotations;
- Generated artifacts;
- History.

The inspector follows the shared selection and does not own the primary navigation state.

## 4. Layout configurations

### 4.1 Right-docked inspector

Best for wide monitors and vertically oriented content.

```text
┌──────────────┬─────────────────────────────┬──────────────────┐
│ Left pane    │ Centre view                 │ Inspector        │
│              │ Trail / Graph               │ Entry / evidence │
└──────────────┴─────────────────────────────┴──────────────────┘
```

### 4.2 Bottom-docked inspector

Best for:

- long-form reading;
- code and document evidence;
- horizontal temporal graph layouts;
- medium-width screens.

```text
┌──────────────┬──────────────────────────────────────────────┐
│ Left pane    │ Centre view                                  │
│              │ Trail / Graph                                │
│              ├──────────────────────────────────────────────┤
│              │ Inspector                                    │
└──────────────┴──────────────────────────────────────────────┘
```

### 4.3 Hidden inspector

The centre view expands while the selected identity remains in application state. Reopening the inspector restores the same selected item and active inspector tab.

### 4.4 Compact and narrow layouts

For narrow screens:

- left pane becomes an overlay or sheet;
- inspector defaults below the centre where practical;
- very narrow layouts use a temporary inspector sheet;
- closing a temporary pane restores focus and centre-view position.

Mobile-first authoring remains out of scope, but inspection and navigation must remain usable.

## 5. User preference model

Recommended persisted state:

```yaml
workspace:
  main_view: trail | graph | artifacts
  left_pane:
    state: expanded | compact | hidden
    width: number
  inspector:
    visible: true | false
    dock: auto | right | bottom
    right_width: number
    bottom_height: number
    active_tab: summary | entry | evidence | relationships | files | commits | history
  graph:
    orientation: auto | horizontal | vertical
    layout: topology | temporal | evolution | community
```

Preferences should be stored per user and, where useful, per project.

The application should distinguish:

- user preference;
- responsive recommendation;
- temporary session override.

An explicit user choice must not be continuously overwritten by automatic layout behaviour.

## 6. Responsive recommendation logic

Recommended defaults:

```text
Wide viewport       → Inspector right
Medium viewport     → Saved user preference
Narrow viewport     → Inspector bottom
Very narrow viewport→ Inspector temporary sheet
```

Graph-specific recommendation:

| Active graph orientation | Recommended inspector dock |
|---|---|
| Horizontal temporal | Bottom |
| Vertical temporal | Right |
| Pure topology | User preference |
| Evolution hierarchy | Right or bottom based on hierarchy direction |

This should be advisory under `dock: auto`; explicit `right` or `bottom` settings win.

## 7. Shared selection and navigation model

All centre views and the inspector must use one shared selection identity.

### 7.1 Trail to Graph

```text
Select decision in Trail
  → open Graph
  → same decision remains selected
  → graph focuses its neighbourhood
  → inspector remains on the same item
```

### 7.2 Graph to Trail

```text
Select graph node
  → inspector updates
  → switch to Trail
  → Trail scrolls to the corresponding entry or nearest evidence anchor
```

### 7.3 Search

Search remains a function over the active centre view:

- Trail: scroll to ranked neighbourhood and highlight matches;
- Graph: focus or isolate matching nodes;
- Inspector: highlight matching sections;
- Artifacts: match claims and citations.

Search must not become a detached centre view by default.

### 7.4 Layout changes

Selection, scroll anchor, and inspector content must survive:

- left-pane toggle;
- inspector dock change;
- inspector hide and restore;
- centre-view switch;
- viewport resize;
- theme change;
- graph layout change.

## 8. Centre-view responsibilities

### 8.1 Trail

The Trail centre view owns:

- chronology;
- branch and merge lanes;
- lifecycle routes;
- search highlights;
- incremental range loading;
- primary decision context.

Trail controls belong in its own view bar, not the left pane, when they directly affect chronology and navigation.

### 8.2 Graph

The Graph centre view owns:

- topology and temporal layout controls;
- graph scope;
- node and edge layers;
- community filters;
- graph fit and reset;
- local expansion;
- graph-to-Trail transition.

The left pane may expose expanded graph filter forms, but the graph’s primary mode and layout controls should remain close to the graph.

### 8.3 Artifacts

Artifacts or Evidence Packs may become a centre mode when they are substantive project outputs rather than inspector attachments. Until then, they remain inspector content.

## 9. Inspector behaviour

### 9.1 Context-preserving inspection

The inspector changes content without forcing the centre view to lose position.

Selecting a different node or Trail entry updates inspector content while the graph viewport or Trail scroll anchor remains stable.

### 9.2 Reading mode

Bottom-docked inspection should support a reading mode with sufficient width for:

- Markdown entries;
- code excerpts;
- diffs;
- evidence tables;
- decision diagrams;
- generated reports.

### 9.3 Independent scrolling

The left pane, centre view, and inspector must preserve independent scroll positions. Full-shell rerenders must not reset pane state.

### 9.4 Inspector resizing

- right dock: horizontal drag handle adjusts width;
- bottom dock: vertical drag handle adjusts height;
- sizes persist independently;
- minimum and maximum sizes protect usability;
- double-click or reset action returns to sensible defaults.

## 10. React shell architecture

The next-generation React shell should model layout explicitly rather than derive it from scattered CSS classes.

Suggested component structure:

```text
AppShell
├── TopBar
├── WorkspaceGrid
│   ├── LeftPane
│   ├── MainWorkspace
│   │   ├── MainViewSwitcher
│   │   └── ActiveMainView
│   └── InspectorDock
└── OverlayLayer
    ├── NarrowLeftSheet
    └── NarrowInspectorSheet
```

Suggested state domains:

```text
workspacePreferences
workspaceResponsiveState
activeMainView
sharedSelection
searchState
filterState
graphViewState
trailViewState
inspectorState
```

The shared selection should use stable entry, decision, commit, file, or symbol identities rather than DOM references.

## 11. CSS and layout strategy

Use CSS Grid for the primary workspace and a split-pane implementation for resize handles.

Right dock conceptual grid:

```text
grid-template-columns:
  [left] var(--left-width)
  [main] minmax(0, 1fr)
  [inspector] var(--inspector-width)
```

Bottom dock conceptual structure:

```text
outer columns:
  left | work-area

work-area rows:
  main
  inspector
```

The layout must avoid remounting active views during dock changes where possible. Preserving component instances reduces lost graph positions, scroll anchors, and input state.

## 12. Migration from the vanilla frontend

Phases A and the behaviour/fixture portion of B are **B0a pre-React** work. Full independent docking, persistence, responsive layout, and component ownership are **B0b post-shell** work; they should not be built twice in vanilla and React.

### Phase A — B0a clarify controls

- make the hamburger control only the left pane;
- keep Trail and Graph in the top or centre view switcher;
- relabel the right pane as Inspector where user-facing labels exist;
- preserve current behaviour otherwise.

### Phase B — B0a specify independent inspector behaviour

- define inspector toggle, selection-preservation, and state-precedence contracts;
- add shared fixtures and vanilla-safe behaviour only where it will not duplicate the React shell;
- defer full persisted layout implementation to B0b.

### Phase C — B0b bottom docking prototype

- add bottom dock;
- test reading mode;
- test horizontal temporal graph layout;
- measure scroll and selection preservation.

### Phase D — B0b responsive Auto mode

- introduce `Auto | Right | Bottom` preference;
- apply viewport and graph-orientation recommendations;
- ensure explicit user choices override recommendations.

### Phase E — B0b React shell parity

- reproduce the layout in the React shell;
- keep vanilla fallback until parity and accessibility sign-off;
- validate packaged wheel behaviour.

## 13. Keyboard and accessibility contract

Suggested shortcuts, subject to conflict testing:

```text
Ctrl/Cmd+B       Toggle left pane
Ctrl/Cmd+Shift+B Cycle left pane state
Ctrl/Cmd+I       Toggle inspector
Ctrl/Cmd+Shift+I Change inspector dock
Alt+1            Trail
Alt+2            Graph
Alt+3            Artifacts, if promoted
```

Requirements:

- pane toggles expose `aria-expanded` and associated controls;
- focus returns to the invoking control when temporary sheets close;
- split handles are keyboard adjustable;
- centre-view tabs follow accessible tab semantics;
- inspector tab selection is keyboard navigable;
- pane changes do not trap focus;
- narrow-layout overlays announce themselves as dialogs or sheets.

## 14. Interaction with graph topology and time

The workspace proposal and graph proposal reinforce each other.

### Horizontal temporal graph

Use a bottom inspector to preserve horizontal graph width:

```text
Older ←────────────────────────────→ Newer
──────────────────────────────────────────
Inspector below
```

### Vertical temporal graph

Use a right inspector to preserve graph height:

```text
Newer
  ↑     | Inspector
  ↓     |
Older   |
```

In Auto mode, changing graph orientation may recommend a dock change. The application should show a non-disruptive option rather than silently moving the inspector while the user is working, unless the preference explicitly permits automatic changes.

## 15. Acceptance criteria

- Hamburger toggles only the left pane.
- Trail and Graph remain centre workspace modes at all times.
- Inspector visibility is independent of left-pane visibility.
- Inspector supports right and bottom docking.
- User preference is persisted.
- Auto mode responds sensibly to viewport shape.
- Shared selection survives centre-view and dock changes.
- Trail scroll position survives inspector changes.
- Graph viewport and selected node survive inspector changes.
- Bottom dock provides a materially better long-form reading surface.
- Narrow layouts remain usable through temporary sheets.
- Keyboard-only users can toggle, resize, and navigate all regions.

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Too many layout options increase complexity | Sensible defaults and a single Auto mode |
| Dock changes remount views and lose state | Stable component ownership and shared state stores |
| Main view becomes too narrow | Minimum centre width and automatic bottom recommendation |
| Inspector below consumes too much height | Persisted size, collapse control, reading-mode presets |
| Left pane accumulates view-specific controls | Keep primary mode controls in each centre view bar |
| Automatic layout feels unpredictable | Explicit preference precedence and optional recommendation prompt |
| Mobile behaviour becomes a separate product | Limit scope to responsive inspection and navigation |

## 17. Final recommendation

Adopt the three-region workspace as the canonical Memory Trace shell:

```text
Left pane   → navigate and filter
Centre pane → Trail, Graph, and primary work
Inspector   → inspect selected evidence
```

The hamburger controls only the left pane. The inspector independently docks right or below. Shared selection and search unify all regions.

This structure correctly reflects Memory Trace’s product hierarchy and creates the space required for a high-quality graph, a readable Trail, and substantial evidence inspection without forcing one view to masquerade as application navigation.
