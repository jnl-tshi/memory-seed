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
| Cytoscape.js 3.34.0 | Passes the current state and visual smoke test. | Rendered the seven-node fixture in topology, temporal-topology, and evolution-hierarchy modes; preserved selection through layout/filter changes; rendered the connected three-node view; and collapsed to one column at the mobile viewport. The native controls and visible-node buttons support keyboard layout, filtering, and selection. Local timings were 10-12ms in the repeat sweep; the original visual smoke timing was 37ms. |
| vis-network 10.1.0 | Failed the current visual smoke test. | Accepted all seven fixture nodes and produced valid positions in all three modes, but painted zero non-transparent canvas pixels in the local Chrome harness. Replacing `DataSet` input with documented raw node and edge arrays did not change that result. Initial timing is not comparable until this adapter renders visibly. |

The all-layout keyboard/state sweep completed without browser errors. It verifies the shared node selection,
the connected filter, three layout controls, and the mobile single-column layout. Pointer panning and zooming
remain renderer-owned behaviour to be assessed separately; they are not represented as a keyboard feature.

## Initial Bundle Accounting

- The harness bundle contains both candidates and is therefore evidence tooling, not a production bundle
  budget. It is minified before packaging and must later be split into lazy per-candidate measurements.
- Current combined output: 1,109,930 bytes JavaScript and 2,529 bytes CSS. A candidate cannot claim
  acceptable packaged cost from this combined output.

## Offline Packaging Status

- The static service and package manifest tests verify that `benchmark.html`, `renderer-benchmark.js`, and
  `renderer-benchmark.css` are included and served without external resources.
- Actual offline wheel inspection is **blocked in this local environment**, not passed: isolated builds cannot
  obtain `setuptools>=68` without network access, and the installed local setuptools has no `bdist_wheel`
  command. Re-run this check in the release build environment with its wheel backend already provisioned.

## Decision Boundary

- Do not select Cytoscape.js yet: the benchmark still needs offline wheel inspection, per-candidate lazy
  bundle accounting, pointer pan/zoom evidence, and a documented vis-network disposition.
- Do not promote or alter the vanilla SVG fallback.
- The vis-network result is an adapter/runtime failure observation, not a general claim about the library.
