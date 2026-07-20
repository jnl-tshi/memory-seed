---
title: "Memory Trace Frontend Architecture and Design-System Proposal"
date: "2026-07-11"
project: "memory-seed"
status: "proposed"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Frontend Architecture and Design-System Proposal

Status: Active proposal, promoted from inbox on 2026-07-11.
Priority: P2 after Phase 0 parity fixtures and Phase 1 versioned API contract in `memory-trace-next-generation-implementation-roadmap.md`.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`; reconciled with `completed/memory-trace-ui-audit.md` and `../4_Reference/21st-dev-components.md`.
Scope: React/TypeScript/Vite frontend architecture, design-system boundaries, Trail/graph renderer split, packaging, budgets, and UI testing.
Non-goals: No immediate replacement of the current vanilla UI, no Node.js runtime requirement for users, no custom primitive library, no Trail implementation in React Flow.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-next-generation-implementation-roadmap.md`, `../3_Spec/memory-trace-trail-search-and-graph-ux.md`, and the current Memory Trace parity baseline.
Acceptance criteria: Built wheel serves the React shell, generated API client is used, component/test/a11y gates pass, bundle budgets are reported, and vanilla fallback remains until sign-off.

## 1. Decision

Adopt **React + TypeScript + Vite** for the next-generation Memory Trace frontend, using **Base UI-backed shadcn/ui components**, semantic design tokens and Memory Trace-specific domain components.

Retain:

- FastAPI and Uvicorn;
- Python-wheel distribution;
- local/offline operation;
- the current CLI;
- the canonical Memory Seed retrieval and graph services;
- no Node.js requirement for end users.

Do not replace the current vanilla frontend until the React implementation reaches functional and performance parity.

## 2. Why migration is justified

The current vanilla application has the benefit of a small dependency surface and simple packaging. It becomes increasingly brittle as the product adds:

- shared state across Trail, graph, search and inspection;
- dynamic layout modes;
- typed annotations;
- provider events;
- large virtualised histories;
- accessible dialogs, menus and comboboxes;
- generated artefacts;
- hosted authentication and workspace features.

React reduces interaction-level brittleness through declarative rendering and component/state boundaries. TypeScript adds compile-time checking for API model changes, edge types, annotation records and component contracts.

The cost is a heavier development toolchain and a larger dependency graph. That cost is acceptable if the release output remains static assets packaged inside the wheel and the dependency surface is governed.

## 3. Alternatives evaluated

| Criterion | Vanilla JS | Svelte + TS | React + TS |
|---|---:|---:|---:|
| Preserve current implementation | Strong | Weak | Weak |
| Modern primitive ecosystem | Medium | Strong | Very strong |
| Agent familiarity | Medium | Medium | Very strong |
| Graph ecosystem | Medium | Strong | Very strong |
| Component/testing ecosystem | Medium | Strong | Very strong |
| Runtime weight | Strong | Very strong | Medium |
| Contributor familiarity | Medium | Medium | Strong |
| Long-term hosted-product path | Medium | Strong | Very strong |
| Migration effort | Low | High | High |

### 3.1 Vanilla JavaScript

Use only if the product remains a small local viewer. It is no longer the recommended long-term architecture because application state and domain surface are expanding.

### 3.2 Svelte

Svelte is credible and potentially lighter. It was not selected because React has a larger component, testing and graph ecosystem and is more predictable for Codex/Claude-generated implementation work.

### 3.3 React

React is selected because it provides the best combined fit for:

- modern accessible primitives;
- established graph tooling;
- component isolation;
- TypeScript contracts;
- AI-agent familiarity;
- local and hosted shared components;
- broad testing support.

## 4. Recommended stack

```text
React
TypeScript
Vite
Base UI
shadcn/ui
Tailwind CSS
TanStack Query
TanStack Virtual
React Flow (graph tab only)
Storybook
Playwright
Vitest / Testing Library
```

### 4.1 Primitive and component layer

Base UI provides unstyled behavioural primitives and is tree-shakable. shadcn/ui distributes editable component code rather than acting as a closed component package.

Rules:

- feature code does not import Base UI directly;
- primitive wrappers live under `src/components/ui/`;
- Memory Trace domain components live under `src/components/trace/`;
- generated shadcn code is reviewed and owned;
- custom dialogs, menus, popovers, comboboxes and tooltips are prohibited unless a documented primitive gap exists.

### 4.2 Styling

Use Tailwind as an implementation mechanism for semantic design tokens, not as the design system itself.

Example token families:

```css
--surface-canvas
--surface-panel
--surface-raised
--text-primary
--text-muted
--edge-related
--edge-supersedes
--edge-evolves
--edge-branch
--status-active
--status-superseded
--status-unresolved
--focus-ring
--density-row
```

Support:

- light/dark themes;
- compact/comfortable density;
- reduced motion;
- high contrast;
- one semantic role per colour;
- consistent focus states.

## 5. Component architecture

```text
src/
  api/
    generated/
    adapters/
  components/
    ui/
    trace/
      entry/
      trail/
      graph/
      evidence/
      annotations/
      artifacts/
  features/
    search/
    trail/
    graph/
    inspector/
    settings/
  app/
    local-shell/
    hosted-shell/
```

### 5.1 Primitive components

Examples:

- Button;
- Dialog;
- Sheet;
- Menu;
- ContextMenu;
- Combobox;
- Tabs;
- Tooltip;
- ResizablePanel;
- ScrollArea;
- Command;
- Toast.

### 5.2 Domain components

Examples:

- `TraceEntryRow`;
- `TrailLane`;
- `TrailSearchMarker`;
- `EvidenceWorkspace`;
- `RelationshipLegend`;
- `DecisionAnchor`;
- `AnnotationThread`;
- `ProviderEventCard`;
- `EvidencePackViewer`;
- `GeneratedArtifactCard`;
- `TopicNeighbourhoodFilter`.

Domain components encode product semantics and prevent agents from rebuilding the product from generic primitives on every page.

## 6. State architecture

Separate three classes of state.

### Server-derived state

- entries;
- search results;
- Trail ranges;
- graph nodes/edges;
- evidence packs;
- annotations;
- provider events.

Use TanStack Query for request state, caching, cancellation and stale-data handling.

### Workspace state

- selected entry;
- active tab;
- open inspector section;
- graph viewport;
- search cursor;
- active filters.

Use feature-local React state or a small store only where cross-feature coordination requires it. Do not introduce a large global state framework by default.

### Durable preferences

- theme;
- density;
- panel sizes;
- last selected project;
- saved views.

Persist through the projection/API layer, not scattered browser storage.

## 7. Trail renderer versus graph renderer

The Trail is a constrained chronological visualisation. It should remain a custom renderer optimised for:

- vertical chronology;
- branch lanes;
- relationship routing;
- dense rows;
- incremental loading;
- search markers;
- stable scroll anchoring.

Evaluate SVG first. Canvas may be introduced for high-density lane rendering if profiling justifies it.

React Flow is recommended for the **graph tab**, where its viewport, custom nodes, edge rendering, minimap, layout integration and interaction model fit the problem. Do not force the Trail into React Flow merely to share a library.

## 8. Layout system

Layout should adapt to the selected tab.

### Trail tab

Evaluate two modes:

1. **Wide split mode:** Trail plus right-side inspection workspace.
2. **Reading mode:** Trail selection followed by a wider vertical document workspace below or in a dedicated reading pane.

The second mode is promising because entry text is document-shaped and can be difficult to read in a narrow sidebar. It must be validated by prototype and usability testing.

### Graph tab

Use a canvas-first layout with:

- graph-specific filter controls;
- local/global/topic/file/evolution modes;
- side or floating inspector;
- minimap and zoom controls;
- no Trail-specific filters unless shared semantics justify them.

### Narrow screens

Use a sheet/drawer for inspection. Mobile-first authoring is out of scope, but reading and navigation should remain viable.

## 9. Performance and package budgets

Initial governance targets:

| Measure | Starting budget |
|---|---:|
| Initial compressed JS | 300 KB |
| Initial compressed CSS | 75 KB |
| Total initial transfer | 500 KB |
| Graph code | Lazy-loaded chunk |
| Source maps | Excluded from published wheel |
| `node_modules` | Never shipped |

These are evaluation thresholds, not immutable requirements. CI should report:

- compressed asset sizes;
- chunk composition;
- wheel size;
- initial render time;
- Trail scroll performance;
- graph load time.

Use TanStack Virtual for long entry, search and topic lists. The Trail renderer may use its own windowing strategy if it needs lane continuity outside the visible range.

## 10. Build and packaging

```text
Developer/CI
  pnpm install --frozen-lockfile
  pnpm test
  pnpm build
        |
        v
memory_trace/static/dist/
        |
        v
Python wheel build
        |
        v
pip/uv install memory-trace
```

Requirements:

- use a committed lockfile;
- use a supported Node LTS in CI;
- production build is deterministic;
- package build fails if assets are stale/missing;
- built-wheel smoke test starts FastAPI and loads hashed assets;
- frontend source is not required at runtime;
- no remote CDN dependency.

## 11. Testing

### Component tests

- semantics and keyboard behaviour;
- domain variants;
- loading/empty/error states;
- annotation authority states;
- provenance labels.

### Storybook

Maintain stories for reusable UI and domain components. Storybook becomes the component inventory for humans and agents.

**Harness landed 2026-07-20:** `storybook@10` + `@storybook/react-vite`, wired to `vitest` via
`@storybook/addon-vitest` (`npx vitest --project storybook run`) so stories run as real tests, not just
a visual sandbox. `@storybook/addon-a11y` is installed and set to `test: "error"` in
`.storybook/preview.tsx` — a genuine gate, not just a visibility panel — and it immediately caught a
real WCAG AA violation (see the Accessibility subsection below). One fully-storied component so far,
`SettingsMenu` (7 stories including keyboard-navigation and focus-restoration `play` functions).
**Not yet done:** the reusable primitive/token layer this section's migration step 3 calls for doesn't
exist yet — `App.tsx`/`EntryReader.tsx`/`GraphWorkspace.tsx`/`TrailWorkspace.tsx` are each one large
page-level component (167-844 lines), not a set of small composable pieces, so writing "component
inventory" stories for them the way this section intends isn't meaningful until that extraction happens.
Treat full story coverage as gated on that refactor, not as a checklist item to force now.

### End-to-end tests

Playwright must cover:

- ✅ search to strongest Trail match;
- ✅ next/previous match navigation;
- selection and inspector persistence;
- ✅ keyboard-only operation (covered for the search/find-bar flow above; not yet for the
  Trail/graph/inspector surfaces);
- graph search and neighbourhood focus;
- annotation creation/version resolution (the annotation feature itself doesn't exist yet - B3,
  gated on B2/B0b and BG1 - so this can't be tested until it's built);
- offline local startup;
- ✅ packaged-wheel loading (the harness runs against the built `../memory_trace/static/react`
  output, served by the real `memory-trace` CLI - not a mock, not Vite dev).

**Harness landed 2026-07-20:** `@playwright/test`, `playwright.config.ts` in `memory-trace/client/`.
`webServer` builds the client and launches `python -m memory_trace.cli` against this repo's own real
corpus (600+ session entries - no synthetic fixture, no mock server), so a passing run proves the
actual shipped path end to end. `e2e/search.spec.ts` covers 3 of the 8 required flows against real data:
search-to-match, next/previous navigation (including the wrap-around and the "no match focused yet"
initial state), and keyboard-only Enter-to-cycle. Run with `npm run test:e2e`.
**Remaining 5 flows are not yet covered:** selection/inspector persistence, graph search/focus, offline
local startup — all buildable now; annotation creation/version resolution cannot be tested until B3
ships the feature itself.

### Accessibility

Target WCAG 2.2 AA. Automated checks are necessary but not sufficient. Manually test keyboard order, focus restoration, screen-reader labels and graph alternatives.

**Automated gate landed 2026-07-20** via `@storybook/addon-a11y` (see Storybook subsection above). Its
first real run found a genuine violation: the light-theme `--muted` text token (`#8a7c66` on `#eee7d8`,
used in 26 places across `styles.css`) measured 3.3:1 contrast against the 4.5:1 AA minimum for text
under 18pt. Darkened to `#70624d` (computed to ~4.8:1 against both `--panel` and `--bg`); dark-theme
`--muted` was checked and already passes (~5.3:1). The manual obligations above (keyboard order, focus
restoration, screen-reader labels, graph alternatives) remain fully unaddressed beyond what
`SettingsMenu`'s own `play` functions incidentally proved for that one component - this is not yet a
project-wide manual accessibility pass.

## 12. AI-agent development constraints

Create a project-specific frontend skill containing:

- approved stack and import paths;
- component inventory;
- token names;
- layout rules;
- Trail/graph renderer boundaries;
- accessibility requirements;
- Storybook/test obligations;
- prohibited custom primitives;
- bundle-budget expectations.

Agents must check existing domain components before creating new ones.

## 13. Migration plan

1. Freeze current UI parity fixtures and screenshots.
2. Publish/version the HTTP API contract.
3. Create React shell, tokens and primitive layer.
4. Implement search and inspection workspace.
5. Implement Trail parity.
6. Implement graph page with dedicated renderer.
7. Add annotations and evidence views.
8. Add generated-artifact views.
9. Run performance, accessibility and wheel tests.
10. Replace vanilla entry point only after acceptance.

## 14. Non-regression gate

The React prototype must not regress:

- current Trail density;
- branch/relationship lane visibility;
- selection and linked-memory navigation;
- filters;
- scroll behaviour;
- older-entry loading;
- graph interaction;
- document inspection;
- startup and packaged operation;
- current supported data scale.

## 15. External references

- shadcn/ui introduction: https://ui.shadcn.com/docs
- Base UI quick start: https://base-ui.com/react/overview/quick-start
- React TypeScript guide: https://react.dev/learn/typescript
- Vite production build guide: https://vite.dev/guide/build.html
- React Flow: https://reactflow.dev/learn
- TanStack Virtual: https://tanstack.com/virtual/latest/docs/introduction
- TanStack Query: https://tanstack.com/query/latest/docs/framework/react/overview
- Storybook: https://storybook.js.org/docs
- Playwright: https://playwright.dev/docs/intro
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
