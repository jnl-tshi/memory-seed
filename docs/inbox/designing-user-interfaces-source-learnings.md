---
memory-system-version: 2.15
tags:
  - memory-seed
  - inbox
  - source-learnings
  - ui-design
  - memory-lense
status: source-learnings
source: "_OceanofPDF.com_Designing_user_interfaces_-_Michal_Malewicz.pdf"
created: 2026-07-04
---

# Designing User Interfaces - Source Learnings

> **Status: SOURCE LEARNINGS, not an active proposal.** Extracted with `pdfplumber` from the local
> PDF on 2026-07-04. The PDF includes purchaser/license-identifying text; that information is
> intentionally omitted here. No full-text conversion is retained.

## Useful Principles

1. **Good UI is a system, not a single visual trait.** Layout, typography, color, interaction,
   component style, and copy work together. For Memory Seed, this argues against isolated polish
   passes on Memory Lense: design changes should be evaluated as a connected system.
2. **Use tested patterns first, then innovate deliberately.** Novel UI should be reserved for places
   where standard patterns fail. This matches Memory Seed's vendor-neutral, low-surprise philosophy.
3. **Perception rules matter.** Grouping, proximity, hierarchy, contrast, alignment, and repetition
   help users understand a screen before they read details. Memory Lense graph/timeline/search views
   should make relationships visually obvious before requiring text inspection.
4. **Grid and spacing decisions should be explicit early.** A grid is not just decoration; it is the
   structural rule that keeps hierarchy and scanning reliable. Future Lense/UI work should define
   spacing, gutters, pane widths, and responsive breakpoints as reusable tokens or constants.
5. **Color should carry purpose, not drift.** Audit all colors, gradients, borders, and state colors;
   keep only variants with a defined job. This is especially relevant for graph edge types, status
   labels, warnings, selected states, and search-match highlights.
6. **Typography should be reduced to a small reusable set.** Too many font sizes, weights, or label
   styles weaken hierarchy. UI surfaces should standardize heading, subheading, body, metadata,
   labels, links, and button text.
7. **Icons need labels when meaning is not universal.** Even apparently obvious icons can be
   misunderstood across audiences and contexts. Memory Lense should prefer icon+label or tooltip
   patterns for non-obvious actions.
8. **Interactive elements must look and behave consistently.** Buttons, inputs, toggles, tabs, and
   clickable cards should have stable sizing, affordance, hover/focus/disabled states, and clear
   action labels.
9. **Forms are conversion and reliability surfaces.** Any future settings/import/export workflow
   should test labels, placeholders, errors, validation, and completion flow rather than treating form
   layout as purely visual.
10. **Navigation failures cause severe drop-off.** Visible, hidden, and contextual navigation each
    have costs. Memory Lense should keep primary navigation obvious and reserve contextual controls
    for local actions.
11. **Animation should explain state changes.** Motion is useful when it clarifies navigation,
    hierarchy, feedback, or continuity; decorative motion should be treated skeptically.
12. **Microcopy is part of the interface.** Labels, empty states, warnings, errors, and helper text
    should be concise, precise, and consistent. Vague labels create product risk even when the visual
    UI is polished.
13. **Design systems reduce implementation drift.** Even a small library of components, tokens, and
    code-ready definitions improves consistency and developer handoff.
14. **UI audits should be periodic and evidence-based.** Audit screens, states, typography, colors,
    gradients, grid alignment, objects, interactive sizing, accessibility, and consistency. End each
    audit with the most important improvements, not trend-chasing.
15. **Designer/developer handoff is a QA loop, not a file drop.** Implementation should be checked
    against design intent, interaction details, accessibility, and performance. Designers and
    developers benefit from shared language around CSS/design rules.

## Candidate Memory Seed Applications

- **Memory Lense UI audit checklist:** Create a focused audit pass for search, graph, timeline,
  reader, filters, and details panes: typography inventory, color/state inventory, spacing/grid,
  interactive target sizes, accessibility contrast, empty/error/loading states, and responsive
  behavior.
- **Design-token baseline:** Define a small set of reusable UI tokens for Lense: spacing scale,
  typography roles, color roles, radius, border, elevation, and graph/status color semantics.
- **Microcopy pass:** Review Memory Lense labels and helper text for precision: search filters,
  graph controls, timeline labels, metadata names, error messages, and install-hint text.
- **Developer handoff pattern for generated UI work:** Extend UI tasks with evidence requirements:
  screenshot inspection, accessibility/contrast spot checks, responsive checks, and a short
  implementation drift report.
- **Component consistency rule:** Avoid one-off component styling in Lense unless the difference has
  a documented purpose. Audit buttons, fields, tabs, cards, panes, graph nodes, and status badges.

## Notes For Later Triage

- This source aligns with the existing `developer-rendered-ui-debugging` persona skill and the
  current Memory Lense roadmap, but it is not itself a proposal.
- If promoted, the likely active proposal should be narrow: either "Memory Lense UI audit checklist"
  or "Memory Lense design-token baseline", not a broad redesign.
- Partially promoted 2026-07-05 into
  [`../todo/memory-explorer-entry-level-ui-results-plan.md`](../todo/memory-explorer-entry-level-ui-results-plan.md),
  applying the hierarchy/navigation/component-consistency principles to Explorer result granularity.
- Any future proposal should avoid importing copyrighted book content; use these extracted principles
  as summarized rationale only.
