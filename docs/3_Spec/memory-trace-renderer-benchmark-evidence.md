---
title: "Memory Trace Renderer Benchmark Evidence"
date: "2026-07-16"
project: "memory-seed"
status: "active-evidence"
spec_binding: "B0a renderer selection gate"
parent: "memory-trace-renderer-neutral-graph-projection.md"
---

# Memory Trace Renderer Benchmark Evidence

Status: **ready for selection**. This record is evidence for B0a, not a renderer decision.

## Method

- Harness: `/benchmarks/renderer`, packaged into the Memory Trace wheel and served without external
  resources.
- Input: `memory-trace/tests/fixtures/graph-renderer/bounded-neighbourhood.v1.json` for both adapters.
- Cases: topology, mild temporal topology, and directed evolution hierarchy.
- Interaction checks: initial shared selection, layout switching, connected-neighbour filtering,
  pan/zoom support, and an accessible visible-node list.
- Environment: local Chrome on Windows, 1440px desktop and 390px mobile viewport.

## Current Results

| Candidate | Result | Evidence |
| --- | --- | --- |
| Cytoscape.js 3.34.0 | Passes the complete harness. | Rendered the seven-node fixture in topology, temporal-topology, and evolution-hierarchy modes; preserved shared selection through layout/filter changes; rendered the connected three-node view; accepted native pan/zoom; and collapsed to one column at the mobile viewport. The native controls and visible-node buttons support keyboard layout, filtering, and selection. Repeat timing: 8-12ms. |
| vis-network 10.1.0 | Passes the complete harness. | The initial blank canvas was a benchmark container-sizing fault, not a candidate failure. A bounded responsive surface now renders all seven nodes in all three modes, preserves selection/filter parity, accepts native pan/zoom, and collapses at the mobile viewport. Repeat timing: 185-192ms. |

The repeat sweep completed without browser errors. It verifies shared node selection, the connected filter,
three layout controls, pointer pan/zoom on direct canvas targets, and the mobile single-column layout.
The benchmark now constrains each surface to `clamp(420px, 58vh, 560px)`: the previous flexible grid row
allowed a candidate canvas to outgrow the viewport, which made visual and pointer evidence unreliable.

## Initial Bundle Accounting

- The harness bundle contains both candidates and is therefore evidence tooling, not a production bundle
  budget. Its current combined output is 1,110,121 bytes JavaScript and 2,779 bytes CSS.
- The lazy candidate measurements use the exact harness imports, minified for an ES2020 browser target:
  vis-network is 654,751 bytes (154,694 gzip); Cytoscape.js is 443,613 bytes (142,333 gzip). These are
  library-chunk measurements, not a claim about final B0b application cost.

## Offline Packaging Status

- The static service and package manifest tests verify that `benchmark.html`, `renderer-benchmark.js`, and
  `renderer-benchmark.css` are included and served without external resources.
- Local offline wheel inspection now passes after provisioning the local build backend. `pip wheel --no-deps
  --no-build-isolation` produced `memory_seed-2.18.0-py3-none-any.whl` (733,886 bytes) without a dependency
  download during the build, and the wheel contains all three benchmark assets.

## Selection Boundary

- The B0a evidence gate is complete. The user must choose the renderer after reviewing the current
  side-by-side output; the benchmark does not make that product decision automatically.
- Do not promote or alter the vanilla SVG fallback.
- The earlier vis-network failure was attributable to the benchmark surface sizing and is superseded by this
  successful bounded-surface result.
