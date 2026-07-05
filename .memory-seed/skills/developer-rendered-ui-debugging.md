---
memory-system-version: 2.16
tags:
  - memory-seed
  - skill
  - developer
  - rendered-ui-debugging
---

# Developer Rendered UI Debugging Skill

Use this skill when debugging local browser UI behavior, especially click, hover, scroll, layout, theme, stale asset, SVG, canvas, graph, timeline, or pane regressions.

## Inputs

- Local URL or file path for the rendered app.
- Expected user action and visible result.
- Relevant source files, tests, and known browser/tooling constraints.

## Procedure

1. Reproduce the issue in a real browser or browser automation before fixing it.
2. Check page health: URL, title, blank states, and console errors or warnings.
3. Verify loaded assets: inspect script/link URLs and confirm the browser is running the edited JS/CSS content; hard-reload or cache-bust when needed.
4. For click, hover, drag, and scroll bugs, inspect the rendered target with `elementFromPoint`, bounding boxes, computed `pointer-events`, overflow, z-index, and scroll containers.
5. Fix the smallest root cause. Prefer stable delegated handlers and explicit `data-*` attributes for dynamic SVG/canvas-adjacent interactions.
6. Re-run targeted unit/static tests and rendered browser checks. Include narrow viewport coverage when panes, timeline, graph, or responsive controls are affected.
7. Record residual ambiguity, such as overlapping nodes where the topmost element determines selection.

## Output

- Root cause.
- Files changed.
- Commands and browser checks run.
- Remaining risk or skipped verification.
