---
title: "Memory Trace Renderer Benchmark Evidence"
date: "2026-07-16"
project: "memory-seed"
status: "active-evidence"
spec_binding: "B0a renderer selection gate"
parent: "memory-trace-renderer-neutral-graph-projection.md"
---

# Memory Trace Renderer Benchmark Evidence

Status: **in progress**. This record is evidence for B0a, not a renderer decision.

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
| Cytoscape.js 3.34.0 | Passes the initial harness smoke test. | Rendered all seven fixture nodes, preserved selected-node state through layout/filter changes, rendered the connected three-node view, and collapsed to one column at the mobile viewport. Initial local timing: 37ms. |
| vis-network 10.1.0 | Failed the current visual smoke test. | Accepted all seven fixture nodes and produced valid positions, but painted zero non-transparent canvas pixels in the local Chrome harness. Initial local timing is not comparable until this adapter renders visibly. |

## Initial Bundle Accounting

- The harness bundle contains both candidates and is therefore evidence tooling, not a production bundle
  budget. It is minified before packaging and must later be split into lazy per-candidate measurements.
- Current combined output: 1,109,930 bytes JavaScript and 2,529 bytes CSS. A candidate cannot claim
  acceptable packaged cost from this combined output.

## Decision Boundary

- Do not select Cytoscape.js yet: the benchmark still needs all layout cases, offline wheel validation,
  keyboard interaction evidence, bundle accounting, and a documented vis-network disposition.
- Do not promote or alter the vanilla SVG fallback.
- The vis-network result is an adapter/runtime failure observation, not a general claim about the library.
