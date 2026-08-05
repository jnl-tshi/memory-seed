---
title: "Memory Seed Competitor Landscape"
status: active
last_reviewed: "2026-08-05"
next_review_due: "2026-11-01"
confidence: medium
---

# Memory Seed competitor landscape

## Purpose and current conclusion

This dossier tracks companies whose core products overlap Memory Seed's durable project memory,
context retrieval, human inspectability, or shared human-agent state.

The closest strategic competitors are **Unblocked, Pieces, Agiflow, and Acontext**. The other six
compete most directly with the memory and retrieval layer. Memory Seed should not claim differentiation
merely because agents have memory; its strongest position is **decision-centric, source-controlled
institutional memory with evidence, provenance, supersession, and human verification**.

## Competitor map

| Competitor | Category framing | Strategic overlap | Primary distinction from Memory Seed |
|---|---|---|---|
| Unblocked | Engineering context engine | Software history, decisions, cited context, MCP/API/CLI | Reconstructs context from enterprise systems; Memory Seed authors a Git-native canonical record |
| Pieces | Memory layer for modern work | Workflow timeline, decision recovery, portable context, MCP | Passive personal/workflow capture rather than governed project decisions |
| Agiflow | AI-native project board | Shared human-agent project state, artifacts, tasks, decisions | Project-management board rather than underlying decision infrastructure |
| Acontext | Open-source memory for agents | Human-readable Markdown, portability, self-hosting | Procedural agent learning rather than institutional project reasoning |
| Cognee | Open-source memory platform for agents | Graph memory, local/cloud deployment, cross-session recall | General semantic graph rather than an opinionated decision/provenance graph |
| Vectorize Hindsight | Agent memory system | Temporal recall, project continuity, reflection, self-hosting | Optimizes future agent behaviour more than independent human governance |
| Zep | Enterprise agent memory | Temporal context graphs, evolving facts, production retrieval | Application/conversation infrastructure rather than Git-native project records |
| Supermemory | Context infrastructure for AI | Persistent structured memory, graphs, connectors, MCP/API | Universal retrieval service rather than decision-centric institutional memory |
| Mem0 | Memory layer for AI applications | Persistent selective memory, agent independence, efficient retrieval | Personalization and conversation memory rather than shared project authority |
| Plastic Labs Honcho | Relational memory infrastructure | Longitudinal entities, relationships, projects, MCP | Identity/social cognition rather than traceable project-decision evolution |

## Competitor claims and evidence

The descriptions above summarize vendor positioning and should not be treated as independently verified
capability claims.

- Pieces calls itself “the memory layer for everything you do” and describes on-device chronological
  capture across work applications. Checked 2026-08-01. [Pieces](https://pieces.app/)
- Cognee calls itself an open-source memory platform for agents and describes graph, vector, and
  relational recall. Checked 2026-08-01. [Cognee](https://www.cognee.ai/)
- Zep positions itself as agent memory at enterprise scale. Checked 2026-08-01.
  [Zep](https://www.getzep.com/)
- Mem0 reported more than 80,000 cloud sign-ups, 13M Python-package downloads, and growth from 35M
  Q1 2025 API calls to 186M in Q3. These are reported usage measures, not revenue. Checked 2026-08-01.
  [TechCrunch](https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/)

## Market lenses used by competitors

| Lens | Companies most aligned | Implication for Memory Seed |
|---|---|---|
| Memory infrastructure for every production agent | Mem0, Zep, Cognee, Hindsight, Supermemory, Honcho, Acontext | Fast-growing category, but exposed to hyperscaler bundling and commoditization |
| Developer and engineering memory | Unblocked, Pieces, Agiflow | Best initial wedge and distribution path |
| Enterprise knowledge/context infrastructure | Unblocked, Pieces, Cognee, Zep | Larger budgets, longer sales cycles, stronger governance requirements |

## Independent benchmarking: the category is now measured (2026-08-04)

**Verging Labs** ([verginglabs.com](https://verginglabs.com/)) published an **Agentic Memory Index
v0.1 (August 2026)**: 272 scored probes over 56 simulated sessions, independent ("no provider pays
for placement, ordering, or scores"), judge agreement 94.1% (kappa 0.85) on its sibling index. An
independent benchmark existing at all is a category-formation signal that qualifies this dossier's
"unoccupied" reading: the *memory-recall* layer is now a measured, contested market.

| Rank | Tool | Score | In this dossier? |
|---|---|---|---|
| 1 | Karpathy Wiki | 98.5 | **No — new name** |
| 2 | Mitosis Cortex | 96.9 | **No — new name** |
| 3 | gbrain | 92.9 | **No — new name** |
| 4 | Hyperspell | 92.4 | **No — new name** |
| 5 | Mem0 | 92.3 | Yes |
| 6 | Anthropic Memory | 84.0 | (platform built-in) |
| 7 | Supermemory | 77.1 | Yes |
| 8 | Zep | 75.1 | Yes |
| — | Claude Code built-in memory | 67.7 | (platform built-in) |

**Profiles of the four unknowns (checked 2026-08-05):**

- **Karpathy Wiki (98.5) — a pattern, not a product.** Andrej Karpathy's April 2026 `llm-wiki`
  gist (5,000+ stars in days): agent-curated interlinked Markdown, `raw/` immutable sources,
  `wiki/` generated pages, a schema file, ingest/query/lint operations — "agent memory should
  compound, not re-retrieve." Per the index author it was also **the only system that hallucinated
  on a never-stored question**, and its $568.93/1k answers is ~2x the cheapest tool.
  [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- **Mitosis Cortex (96.9) — real, but brand new.** A Reddit commenter claimed the product was
  hallucinated; it is not — [Mitosis Labs](https://mitosislabs.ai/) exists (ex-Meta founder,
  "agent colonies" infrastructure; Cortex is a private memory layer building a knowledge graph over
  Google Workspace/WhatsApp/GitHub). Recently launched, essentially no independent footprint yet;
  its #1-hosted rank rests on one v0.1 benchmark.
- **gbrain (92.9) — Garry Tan's (YC CEO) open-source memory system**, April 2026, MIT: Markdown +
  Postgres/pgvector, vector + keyword + **typed knowledge graph**, imports Markdown, **CLI + MCP
  surfaces**, PGLite local / Postgres shared. The closest new neighbour to Memory Seed's shape,
  carrying the most influential distribution in startups.
  [overview](https://vectorize.io/articles/what-is-gbrain)
- **Hyperspell (92.4) — YC F25, ~$1M seed**: connector-based passive memory (Slack, Gmail, Notion,
  Drive), continuous indexing. Belongs to the Unblocked/Pieces reconstruct-from-systems lens, not
  the authored-record lens. [site](https://hyperspell.com/)

**The category event behind the index:** Karpathy's gist and Tan's gbrain both landed in
**April 2026** — the two most influential figures in the space independently bet on
agent-curated Markdown, and four months later an independent benchmark shows that bet beating
every hosted memory API. **Memory Seed's substrate philosophy is now market-validated by the
category's biggest names.** The contested ground is what Memory Seed adds on top: the index
author's own data shows the wiki pattern's failures are exactly governance-shaped — the sole
never-stored hallucination (no validated write path), staleness and update weakness across
products (Zep passed 8/24 update questions; Supermemory 11/72 long-horizon), and collaboration.
One top thread comment states the differentiation thesis verbatim: the wiki "wins because it's
inspectable… The durable memory layer isn't recall, it's provenance, an append-only record."

Readings, marked as interpretation:

- **The four unknown top scorers need profiling.** Anything at 92+ on probes that include "updated
  facts" is operating near Memory Seed's supersession territory. Open action below.
- **The tracked API-memory vendors underperform the unknowns** (Mem0 5th, Supermemory and Zep below
  Anthropic's built-ins). Consistent with the commoditization watch point: raw recall is not where
  the differentiation is landing even on a recall benchmark.
- **Probe taxonomy convergence.** Their six categories (direct recall, updated facts, thread
  growth, synthesis, long-term retention, false memory check) map almost one-to-one onto the
  measures this programme built independently (capture, supersession/stale-head navigation,
  retrieval, faithfulness/fabrication - E5/E6/E8). Two teams converging on the same instrument is
  evidence the instrument is right - and Memory Seed's validated strengths (flawless stale-head
  navigation in E8, zero fabricated rationale in 121 judged decisions) sit exactly on the probes
  that separate tools.
- **The index measures recall, not capture.** No probe tests whether an agent *records* unprompted
  - the E5 question. Memory Seed's capture-side evidence has no external benchmark yet.

**Path to external validation:** submissions go via the form at
[verginglabs.com/radar](https://verginglabs.com/radar); **v0.2 is planned for early September
2026**, which puts a real deadline on the sequence agreed 2026-08-04: profile the unknowns (done
2026-08-05, above), dry-run their probe taxonomy privately against Memory Seed (design:
`docs/2_Todo/memory-index-dry-run-plan.md`), only then submit. Never enter a benchmark blind.
Benchmark mechanics that matter for the dry-run: each tool's agent is **given the tool's own docs
and left to follow them** across simulated multi-week sessions — so a Memory Seed run would
measure the shipped instruction surface end-to-end, and (per a sharp thread critique) part of any
score is really the curation strategy the docs induce, not the storage format.

## Strategic watch points

- Hyperscalers and model providers may bundle “good enough” memory into agent platforms.
- Passive-capture products may accumulate context faster than deliberate authoring systems.
- General memory APIs can commoditize storage and retrieval pricing.
- Memory Seed's moat must therefore accumulate in trusted project structure, provenance, decision
  relationships, workflow adoption, and human-agent governance—not raw recall alone.

## Unresolved validation questions

- Which products win direct head-to-head evaluations for real multi-agent engineering work?
- Which competitors support exportable authoritative records rather than opaque derived memory?
- How much revenue comes from memory itself versus adjacent orchestration, search, or services?
- Which vendors have meaningful team retention and production deployment rather than developer trials?
- Are Unblocked and Pieces expanding toward decision governance quickly enough to close the wedge?

## Related dossiers

- [Competitor pricing](competitor-pricing.md)
- [Market size](market-size.md)
- [Developer project-memory wedge](../wedges/developer-project-memory.md)
- [GitLens competitor report](memory-seed-gitlens-competitor-report.md)
- [Memory Trail competitor analysis](memory-trail-competitor-analysis.md)

## Change log

- **2026-08-05:** Profiled the four unknown top scorers (Karpathy pattern, Mitosis Cortex real-but-new, gbrain, Hyperspell); added the April-2026 category event, the provenance-shaped gap in the winners, the /radar submission path and the v0.2 early-September deadline.
- **2026-08-04:** Added the Verging Labs Agentic Memory Index section: four new competitor names, the category-formation signal, probe-taxonomy convergence with E5/E6/E8, and the profile -> dry-run -> submit sequence.
- **2026-08-01:** Created the canonical ten-company landscape and separated vendor framing from Memory
  Seed's strategic interpretation.

