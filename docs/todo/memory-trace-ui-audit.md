---
memory-system-version: 2.16
tags:
  - memory-seed
  - memory-trace
  - ui
  - audit
---

# Memory Trace UI Audit (Arc 2b baseline)

> **Status:** ACTIVE — first evidence-based UI audit of the `memory-trace` package, run 2026-07-06 as
> the narrow deliverable of distribution-plan Arc 2b (the
> [designing-user-interfaces source learnings](../inbox/designing-user-interfaces-source-learnings.md)
> recommend a focused audit + token baseline, **not** a redesign). Scope: the shipped read-only
> surfaces — search, reader, timeline, graph, and the new Trail view.
> **Non-goals:** No visual redesign, no new component library, no responsive-breakpoint system.

This audit follows the source's audit dimensions (typography, color/state, spacing/grid, interactive
sizing, accessibility, empty/error/loading, consistency) and ends with the top improvements — not a
laundry list.

## What Arc 2b fixed

- **Color carries purpose (source #5).** The graph edge-type and status colors were scattered as
  inline hex in `edgeColor()`. They are now design tokens (`--edge-related/-topic/-agent/-day/`
  `-supersedes/-branch`, `--status-superseded`) with **one defined job each**; `edgeColor()` is the
  single JS reference and reads the tokens. Supersession (a status edge) can never silently reuse the
  relatedness color.
- **Token baseline (source #4, #6, #13).** Added a small reusable set: a spacing scale
  (`--space-xs…xl`), radii (`--radius-sm/md`), and typography roles (`--fs-title/body/meta/label`).
  This is the structural rule set future UI work refactors onto — not a one-off polish pass.
- **Microcopy consistency (source #12).** The UI self-identified as "Memory Lense" (topbar, boot,
  page title, manifest, server logs) after the product renamed to **Memory Trace**. Rebranded
  throughout. "Matched section" / "Best match" copy is used consistently in results/reader; raw chunk
  language stays out of normal flows.

## Inventory (evidence)

| Dimension | Finding |
|---|---|
| Typography | Roles now tokenized (`--fs-*`); usages still mostly literal `px`/`rem` — migrate incrementally, not urgent. |
| Color/state | Edge/status colors tokenized (done). Accent themes + light/dark already token-driven. |
| Spacing/grid | Scale defined (`--space-*`); existing rules still use literals — safe to converge over time. |
| Interactive sizing | Buttons/chips/tabs share `.tab`/`.chip` classes with stable states — consistent. Graph hit-targets use an oversized invisible `graph-hit` circle (good for small nodes). |
| Empty/error/loading | Present and specific: "No session entries match…", per-view "loading" states, boot error. |
| Trail view | New edge semantics render distinctly (supersedes = dashed + directed arrow + status color; branch = lineage color) with a plain-language legend. |
| Accessibility | Graph SVG has `role="img"`; legend has `aria-label`. Contrast of tokenized edge colors on both themes not yet formally measured. |

## Top improvements (ranked, for later)

1. **Contrast spot-check** the tokenized edge/status colors against both themes (WCAG AA for the
   graph/legend). Cheap, evidence-based, not yet done.
2. **Converge literals onto tokens** in `styles.css` opportunistically (spacing/type), so the baseline
   actually reduces drift rather than sitting unused.
3. **Icon labelling (source #7):** the theme toggle (`◐`) and a few icon-only controls rely on
   `title` tooltips; confirm they degrade acceptably for keyboard/screen-reader users.

These are follow-ups, not blockers; Arc 2b's baseline (tokens + color semantics + microcopy) is the
committed deliverable.
