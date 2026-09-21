---
title: "Decision storyline retrieval"
date: "2026-09-21"
status: deferred
deferred_reason: "A narrative history mode is outside the capture-first hosted MVP and remains a later experience candidate."
revisit_when: "The P0/P1 governed memory and retrieval loop is proven and the bounded local lineage/Trace experience supplies evaluated traversal and evidence fixtures."
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Decision Storyline Retrieval

## Current disposition

**DEFERRED P2 CANDIDATE.** The [hosted programme](../2_Todo/hosted-memory-mvp-programme.md) reserves a focused experience for after service value; the [local Trace plan](../2_Todo/memory-trace-ux-reference-model-implementation-plan.md) already covers bounded lineage exploration. A future story mode should traverse authored lineage deterministically, add only a derived and inspectable narrative-importance overlay, link claims to exact evidence, and keep peripheral live history accessible through explicit controls. It must not silently prune the authoritative graph or change default task retrieval ranking. The classifier choice follows the [tournament](../2_Todo/decision-layer-model-tournament-plan.md).

## Purpose

Add a retrieval mode designed to answer a different question from ordinary semantic retrieval.

Normal retrieval asks:

> What information is most relevant to this current query?

Storyline retrieval asks:

> How did this idea, architecture or decision evolve into its current state?

This is useful for:

- project management;
- architecture reviews;
- onboarding;
- postmortems;
- ADR discovery;
- governance;
- understanding why the current design exists.

## Core Concept

Memory Seed already stores relationships such as:

- supersedes;
- superseded_by;
- evolved_from;
- related decisions;
- ADR links;
- chronology.

This graph can be used to reconstruct the evolution of an idea.

Example:

```text
Initial idea
    ↓
Early experiment
    ↓
Design decision
    ↓
Revision
    ↓
ADR
    ↓
Later amendment
    ↓
Current implementation
```

The output is a narrative path through the decision graph rather than a ranked bag of semantically similar nodes.

## Critical Path vs Peripheral Branches

The full graph may contain branches that are historically related but not central to the story.

Example:

```text
D1
├── D2
│   └── D4
│       └── D7
│
└── D3
    └── D5
```

Suppose the architecture eventually evolves through:

```text
D1 → D2 → D4 → D7
```

D3 and D5 may still contain relevant information but should not necessarily appear in the primary narrative.

The system therefore needs two layers:

1. deterministic graph expansion;
2. decision-based relevance scoring.

## Proposed Pipeline

```text
user asks for history/evolution
          │
          ▼
identify target/current decision
          │
          ▼
deterministic graph traversal
          │
          ▼
candidate lineage subgraph
          │
          ▼
cheap decision classifier
          │
          ├── core
          ├── supporting
          └── peripheral
          │
          ▼
ordered narrative
```

## Deterministic Expansion First

The classifier should not decide which nodes are initially retrieved.

Memory Seed should first reconstruct the graph neighborhood deterministically using:

- supersession edges;
- evolution edges;
- ADR links;
- explicit parent/child relationships;
- chronology.

This prevents an imperfect classifier from deleting history.

The decision model should only rank or annotate the candidate graph.


## Decision Engine Role

Storyline retrieval should not assume Laya, Jev or any other model. The graph traversal is authoritative for candidate discovery; the model only decides narrative importance.

This is a relatively stable classification task because the output schema can remain global across projects:

```text
core
supporting
peripheral
```

That makes it a good candidate for the full tournament, including Model2Vec + Logistic Regression and XGBoost. A generalized decision model is only justified if it materially improves accuracy/calibration or avoids hand-engineered task-specific models.

The same principle applies to origin discovery: first enumerate plausible ancestors deterministically, then classify which node is the meaningful seed of the current design.

## Relevance Overlay

Each candidate node can receive:

```yaml
story_role:
  class: core
  probability: 0.94

supporting_context:
  probability: 0.72
```

The classification can be performed by:

- Model2Vec + classifier;
- XGBoost;
- SetFit;
- Laya;
- Jev;
- another pluggable decision model.

The model tournament should determine which performs best.

## Never Hard-Delete Story Nodes

Classifier output should be an overlay.

Example:

```text
core path → shown by default
supporting → collapsed
peripheral → hidden but expandable
```

This is safer than permanently pruning branches.

## Origin Discovery

Storyline retrieval should attempt to find the earliest meaningful seed of the concept.

That seed may be:

- an initial conversation;
- a decision record;
- a problem statement;
- an experiment;
- a proposal;
- an ADR predecessor.

The origin is not necessarily the oldest semantically related record.

It is the earliest node that materially begins the chain that led to the current state.

This can itself become a classification task.

## ADR Integration

An ADR should appear as a major narrative milestone rather than as a separate document repository.

Example:

```text
D014 — initial hosted curator idea
D026 — Postgres + pgvector selected
D031 — local/central deployment considered
ADR-007 — curator architecture formalized
D055 — Laya added as local decision layer
```

This creates a readable architectural history.

## Constitution Integration

If a decision leads to a constitutional rule or amendment, storyline retrieval should surface it as a governance milestone.

Example:

```text
decision
   ↓
repeated pattern
   ↓
architectural principle
   ↓
constitutional amendment
```

The reverse traversal should also work:

> Why does this constitutional rule exist?

The system should be able to trace the rule back to the decisions that motivated it.

## Query Types

Potential interface:

```text
/story <decision>
```

or natural language:

```text
How did we arrive at the current retrieval architecture?
```

```text
Show me the evolution of the curator design.
```

```text
Where did the Postgres decision originate?
```

```text
What decisions eventually led to ADR-007?
```

## Story Output

Suggested format:

```markdown
# Evolution of the Curator Architecture

## 1. Initial Problem
D014 — ...

Reason:
...

## 2. First Proposed Architecture
D026 — ...

Changed:
...

## 3. Major Revision
D031 — ...

Why:
...

## 4. Formalization
ADR-007 — ...

## 5. Current State
D055 — ...
```

Optional expandable section:

```text
Related branches
- D019
- D023
- D040
```

## Scoring

Critical-path classification can use features such as:

- explicit supersession edges;
- number of downstream descendants;
- relationship to final/current node;
- ADR membership;
- semantic similarity;
- chronology;
- shared files/modules;
- topic continuity;
- classifier probability.

This suggests a hybrid score rather than pure semantic relevance.

## Recommendation

Implement storyline retrieval as a separate retrieval mode rather than changing existing task retrieval.

Memory Seed would then support at least two different retrieval questions:

```text
task retrieval:
"What do I need right now?"

story retrieval:
"How did we get here?"
```

These should share the graph and embeddings but use different ranking logic.
