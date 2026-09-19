---
title: "Archived source — 03-multi-signal-retrieval-ranking"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/03-multi-signal-retrieval-ranking.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 3 — Preserve and Extend Multi-Signal Retrieval Ranking

## Objective

Migrate Memory Seed retrieval to the hosted PostgreSQL/pgvector architecture **without losing the existing ranking behaviour**.

The current retrieval system is not a simple semantic search engine.

It already combines:

- semantic relevance
- chronology
- graph-edge boosting
- graph-edge damping
- preferred keywords supplied by the active agent

Those signals are part of the product and should remain intact.

---

## Core Ranking Model

Conceptually:

\[
R = f(V, C, K, G_b, G_d)
\]

Where:

- `V` = vector/semantic relevance
- `C` = chronological relevance
- `K` = preferred-keyword signal
- `G_b` = graph-edge boost
- `G_d` = graph-edge damping

The exact implementation can remain more sophisticated than a simple weighted sum.

The important point is that pgvector should replace only the vector-storage and candidate-search component, not the complete ranking algorithm.

---

## Hosted Retrieval Architecture

```text
Agent task
    |
    +--> semantic query
    +--> 1-5 preferred keywords
    |
    v
Memory Search API
    |
    +--> pgvector candidate retrieval
    +--> chronology signal
    +--> keyword signal
    +--> graph boosts
    +--> graph damping
    |
    v
Existing multi-signal ranking logic
    |
    v
Final ranked memories
```

---

## PostgreSQL Data Requirements

The hosted schema needs to expose the signals required by the ranking layer.

At minimum:

```text
memory / decision record
├── embedding
├── timestamp
├── topics
├── graph edges
├── edge type
├── edge confidence
├── supersession state
├── provenance
└── other ranking metadata
```

This allows the retrieval algorithm to behave the same way regardless of whether storage is file-based or PostgreSQL-backed.

---

## Candidate Retrieval vs Final Ranking

Recommended flow:

```text
1. pgvector retrieves a broad candidate set
2. semantic score is retained
3. chronology adjustment is applied
4. preferred-keyword boost is applied
5. graph-neighbourhood boosts are applied
6. graph-edge damping is applied
7. final rank is produced
```

A top-50 to top-100 vector candidate set may be a reasonable starting range, but this should be benchmarked rather than hard-coded permanently.

---

## Preferred Keywords

The working agent should remain responsible for supplying preferred keywords.

The user-facing agent already understands the task, so another model call should not be introduced merely to generate keywords.

Example request:

```yaml
query:
  semantic: >
    How should derived relationships between source-code
    changes and Memory Seed entries be represented?

  preferred_keywords:
    - commit SHA
    - derived edge
    - source code
    - sidecar
```

The observed improvement of a relevant result from rank 44 to rank 1 demonstrates that this signal can be highly valuable.

However, keyword boosts should remain bounded so a poor keyword choice cannot completely overwhelm other relevance signals.

---

## Chronology

Chronology should remain a first-class ranking signal.

Potential uses include:

- increasing relevance of recent decisions for current-state questions
- preserving older records for historical questions
- preferring current descendants over superseded predecessors
- supporting recency-aware exploration without deleting history

Chronology should not simply mean "newer is always better."

It should be context-sensitive.

---

## Graph Boosting

Graph structure should improve ranking where relationships are meaningful.

Possible boosts:

```text
current decision           -> strong boost
supporting decision        -> moderate boost
implementation record      -> moderate boost
same topic                 -> modest boost
nearby relevant neighbour  -> modest boost
```

---

## Graph Damping

Damping is as important as boosting.

Examples:

```text
superseded record          -> damp for current-state queries
contradicted record        -> context-dependent damping
weak/uncertain edge        -> minimal impact
historical predecessor     -> neutral or damped depending on query
```

The retrieval engine should not assume that "connected" always means "more relevant."

---

## Curator Interaction

The curator and retrieval engine should remain separate.

```text
Curator
   |
   +--> better edges
   +--> better edge types
   +--> better topics
           |
           v
Retrieval ranking
           |
           v
Better results
```

The curator improves knowledge structure.

The retrieval engine decides how that structure affects search.

---

## Retrieval Benchmark

Create a benchmark containing realistic agent tasks and known-useful memories.

Example:

```yaml
task:
  "Why did we stop storing derived graph relationships directly in decision entries?"

expected_memories:
  - memory_481
  - memory_502
  - adr_019
```

Evaluate variants such as:

- semantic only
- semantic + chronology
- semantic + chronology + keywords
- semantic + graph
- full current ranking algorithm
- later curator-enhanced graph ranking

Recommended metrics:

- Recall@5
- Recall@10
- Mean Reciprocal Rank
- NDCG
- first-relevant-result rank

---

## Success Condition

The hosted migration succeeds only if the current retrieval quality is preserved or improved.

The target is not:

> pgvector search

It is:

> the existing Memory Seed multi-signal retrieval system, backed by PostgreSQL and pgvector.
