---
title: "Memory Trace Phase 0 Baseline Report"
date: "2026-07-11"
project: "memory-seed"
status: "reference-baseline"
parent: "../../2_Todo/memory-trace-next-generation-implementation-roadmap.md"
---

# Memory Trace Phase 0 Baseline Report

Measured 2026-07-11 on the vanilla application (branch `claude-feature-phase0-baseline`),
Windows 11, CPython 3.11, Chrome headless captures. Companion documents: the parity gate is
[`../../3_Spec/memory-trace-vanilla-parity-checklist.md`](../../3_Spec/memory-trace-vanilla-parity-checklist.md);
phase sequencing is the next-generation implementation roadmap.

## Fixtures

- **Synthetic corpora**: `memory-trace/tests/fixtures/generate_synthetic.py` - deterministic
  (same count+seed -> byte-identical tree), exercises branches (up to 3 parallel, bounded
  lifetimes), lifecycle edges, topics, and searchable prose. Generate on demand:
  `python tests/fixtures/generate_synthetic.py <count> <out-dir> [seed]` (default seed 20260711).
- **Trail golden fixture**: `memory-trace/tests/fixtures/trail-golden-48.json` - trailModel()
  output over the 48-entry corpus: 54 items (48 nodes + 6 day separators), 5 lanes, main pinned
  to lane 0, three branches daisy-chained onto lane 1, 44 lifecycle edges.
  **Regeneration** (browserless since 2026-07-13):
  `PYTHONPATH=".;memory-trace" python memory-trace/tests/fixtures/regen_trail_golden.py`
  regenerates the corpus, replays the app's exact `/api/graph` request, evaluates the REAL
  `app.js` in a node vm (`regen_trail_golden.mjs`, DOM stubs only), and rewrites the fixture -
  deterministic, byte-identical across runs; requires node. The original manual procedure
  (serve the corpus, evaluate `window.memoryTraceDebug.trailModel(graph)` in the browser)
  remains valid but is no longer needed. The fixture has been regenerated against the current
  model (time-ordered lane allocation; trailer-aware `linkRows` carrying an `estimated` flag),
  superseding the lane/edge snapshot described elsewhere in this report.
  `tests/test_trail_golden.py` validates internal consistency offline.

## Server-side measurements (synthetic corpora; median of 5 unless noted)

| Entries | Cache rebuild | Search (q, limit 50) | Graph (full) | Chunk read | Facets | Cache DB |
|--:|--:|--:|--:|--:|--:|--:|
| 500 | 1.11 s | 101 ms | 42 ms | 130 ms | 100 ms | 1.8 MB |
| 1,000 | 1.94 s | 204 ms | 80 ms | 252 ms | 187 ms | 3.6 MB |
| 10,000 | 16.95 s | 2,090 ms | 959 ms | 2,752 ms | 2,180 ms | 35.5 MB |

Latency grows roughly linearly with corpus size - the service layer re-reads and re-ranks
chunks per request. At 10k entries every interactive request sits above 2 s, which is the
strongest quantitative argument for the Phase 1+ versioned API to add server-side windowing
and for the retrieval path to stop scanning the full corpus per call.

## Known caps (baseline facts, preserve or consciously change)

- **Graph node cap 1000** (server-side): a 10,000-entry corpus renders only its newest 1,000
  entries in the Trail, and the Trail meta reads "of 1000 entries" - silently. Phase 4's
  incremental-history requirement replaces this cap; until then it is the effective client
  ceiling.
- **UI search limit 50**: the match counter shows `50+` when capped.

## Client-side measurements (1,000-entry corpus, full graph in client)

| Metric | Value |
|---|--:|
| DOMContentLoaded (initial navigation) | 149 ms |
| `/api/graph` fetch, 10k corpus (capped 1000 nodes) | ~1.2 s |
| `trailModel()` full 1,000-node layout (median of 5) | 0.7 ms |
| Full re-render, 120 Trail rows ("Load older" click) | 11.8 ms |
| Full re-render, 1,000 Trail rows (theme-toggle click, median of 4) | 56 ms |

The lane model is effectively free; DOM rebuild is the cost driver (~56 ms per render at
1,000 rows with `app.innerHTML` replacement). React virtualisation (Phase 4) should beat this
comfortably, but must also preserve the scroll/focus-restoration behaviours the checklist pins.

## Package size

| Artifact | Size |
|---|--:|
| `memory_trace-0.1.0-py3-none-any.whl` | 119 KB |
| `static/app.js` | 79.1 KB |
| `static/fonts/inter-var.woff2` | 47.1 KB |
| `static/fonts/space-grotesk-var.woff2` | 21.8 KB |
| `static/styles.css` | 19.3 KB |

These are the numbers React bundle budgets get compared against (roadmap Phase 2
"bundle-size reporting"): today's entire frontend is ~170 KB uncompressed including fonts.

## Screenshots (this directory, real 325-entry corpus)

| File | State |
|---|---|
| `01-trail-resting-dark.png` | Trail default view, dark, no selection |
| `02-trail-selected.png` | Selection active: saturated routes, reader open, branch chips |
| `03-trail-selection-muted.png` | Second click: pastel routes, pinned row + reader ring |
| `04-trail-search-dropdown.png` | Query "trail lane": ranked dropdown + match markers |
| `05-trail-search-markers.png` | Same query, dropdown closed: dots + dimmed misses |
| `06-graph-search-dim.png` | Graph under the query: matches labelled, misses dimmed |
| `07-graph-resting.png` | Graph resting after clear |
| `08-trail-light.png` | Trail in light theme |

Interaction *recordings* were deliberately not produced: no recording tooling is part of the
stack, and the screenshot sequence plus the checklist's behaviour prose covers the same
evidence. If Phase 4 sign-off wants motion evidence, capture it then with the same headless
harness (puppeteer-core against installed Chrome - see the session log of 2026-07-11).

## Phase 0 exit assessment

- [x] Current behaviours documented - parity checklist (3_Spec)
- [x] Representative project fixture - this repo's own 325-entry corpus (screenshots)
- [x] 500 / 1,000 / 10,000-entry synthetic datasets - deterministic generator + tests
- [x] Trail lane/edge golden fixtures - captured + consistency-tested
- [x] Package-size and performance measurements - tables above
- [x] Screenshots of current tabs - 8 states; recordings consciously waived (above)

Phase 0 exit criteria are met: no migration work begins without a measurable baseline, and the
baseline now exists.
