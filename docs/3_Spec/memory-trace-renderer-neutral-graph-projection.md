---
title: "Memory Trace Renderer-Neutral Graph Projection"
date: "2026-07-16"
project: "memory-seed"
status: "active-specification"
spec_binding: "B0a benchmark contract"
parent: "../2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md"
---

# Memory Trace Renderer-Neutral Graph Projection

Status: B0a contract and bounded benchmark fixture, implemented 2026-07-16. This document defines
the shared input for the vis-network and Cytoscape.js prototypes. It does not select a renderer or
change the public `/api/graph` response.

## Authority Boundary

- Authored Markdown and the canonical reader `build_related_entry_graph()` remain the authority for
  Memory Seed decision semantics.
- `memory_trace.graph_projection` validates the benchmark fixture and adapts an existing Trace graph
  response. It does not parse Markdown, write a cache, or add a second graph reader.
- Renderer positions, colour assignments, physics, viewport, and interaction cache are renderer-owned,
  derived state. They must not appear in the fixture or be written back to authored memory.
- Structural-provider edge types are not introduced here. The bounded fixture uses only current
  canonical Trace edge kinds: `related`, `supersedes`, `evolves`, `branch`, `topic`, `agent`, and `day`.

## Fixture Shape

The versioned fixture is at
`memory-trace/tests/fixtures/graph-renderer/bounded-neighbourhood.v1.json`. It contains a bounded
neighbourhood of canonical memory entries, stable community fingerprints, typed lifecycle and derived
edges, authored temporal evidence, a shared selected node, and three benchmark layout cases.

Each node carries these renderer-neutral semantic fields:

| Field | Meaning |
| --- | --- |
| `id`, `node_type`, `label` | Stable identity and human-readable role. |
| `provenance_class`, `authority_class` | Inspectable origin and authority; authority values remain open to BG1 rather than being frozen here. |
| `community.id`, `community.label`, `community.fingerprint` | Derived topology identity. The fingerprint is stable input; colour assignment is not. |
| `temporal.value`, `temporal.source`, `temporal.precision` | Evidence timestamp or authored date, without invented timezone precision. A source is required by node type; filesystem mtime is prohibited. |
| `connectivity`, `importance_score` | Existing, distinct graph-display metrics. |
| `revision`, `provider`, `stale` | Revision and freshness context without provider ownership of decision semantics. |

Every edge has an identity, source, target, canonical edge type, direction flag, and evidence references.
The fixture's selection must survive layout changes, pane visibility changes, and Trail/Graph workspace
switches. Its requirements also make offline packaging and a list equivalent benchmark gates.

## Benchmark Cases

Both renderer adapters must consume this exact fixture and run these cases:

1. `topology`: connection and community behaviour with temporal force off.
2. `temporal_topology`: the same graph with mild temporal drift.
3. `evolution_hierarchy`: directed lifecycle hierarchy with temporal force off.

The benchmark records render, pan/zoom, hover/selection, local expansion, filtering, layout behaviour,
bundle cost, offline wheel behaviour, and accessibility burden. It must not claim parity or retire SVG
until the explicit B0b acceptance gate passes.

The local evidence harness is served at `/benchmarks/renderer`. It packages both adapters into the
wheel and consumes this fixture without calling external resources. It is intentionally separate from
the shipped Graph tab: its role is to produce comparable evidence, not to select or migrate a renderer.

## Compatibility

The validator is intentionally outside the API models. `project_trace_graph()` adapts the current
`TraceService.graph()` response into the same renderer-facing node and edge shape, using an explicit
derived `unassigned` community until B0b adds evidence-backed community detection. Existing vanilla SVG
rendering and `/api/graph` remain the shipped fallback, and future renderer adapters receive a detached
fixture copy through `renderer_input()`. A future API expansion may consume this contract only additively
and with the normal OpenAPI/parity fixtures.
