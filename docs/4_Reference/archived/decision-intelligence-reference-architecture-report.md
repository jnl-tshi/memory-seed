---
title: "Decision intelligence combined architecture — source reference"
date: "2026-09-21"
status: archived-reference
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Combined Reference Architecture for Memory Seed Decision Intelligence

## Current disposition

**ARCHIVED SOURCE ARCHITECTURE.** The [hosted programme](../../2_Todo/hosted-memory-mvp-programme.md) controls rollout order, SQL authority, capture scope, privacy, and provider-neutral curation. The [tournament](../../2_Todo/decision-layer-model-tournament-plan.md), [Laya worker](../../8_Deferred/laya-local-decision-worker-proposal.md), and [storyline retrieval](../../8_Deferred/decision-storyline-retrieval-proposal.md) hold the separately staged additions. The diagram's Postgres/pgvector selection, broad source ingestion, and benchmark-first sequence are illustrative, not approved implementation commitments.

## Purpose

Combine the model tournament, local decision worker, storyline retrieval and decision-governance ideas into one implementation architecture.

## High-Level Architecture

```text
                    ┌─────────────────────┐
                    │ Conversations / Code│
                    │ Docs / Tests / Git  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Memory Seed DB    │
                    │ Postgres + pgvector │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ Hybrid Retrieval │      │ Graph Traversal  │
        │ semantic/time/etc│      │ lineage/evolution│
        └────────┬─────────┘      └────────┬─────────┘
                 │                         │
                 └────────────┬────────────┘
                              ▼
                   ┌──────────────────────┐
                   │   Decision Router    │
                   └──────────┬───────────┘
                              │
         ┌────────────────────┼─────────────────────┐
         │                    │                     │
         ▼                    ▼                     ▼
┌─────────────────┐  ┌─────────────────┐   ┌─────────────────┐
│ Small Classifier│  │ Laya / Jev      │   │ LLM Escalation  │
│ LR / XGB/SetFit │  │ decision model  │   │ curator          │
└────────┬────────┘  └────────┬────────┘   └────────┬────────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              ▼
                   ┌──────────────────────┐
                   │ Governance Validator │
                   └──────────┬───────────┘
                              ▼
                   ┌──────────────────────┐
                   │ Decisions / Edges /  │
                   │ Topics / ADR Links   │
                   └──────────────────────┘
```

## Separation of Responsibilities

### Retrieval Layer

Answers:

> What evidence should be considered?

Includes:

- Model2Vec vector search;
- keyword ranking;
- chronology;
- graph boosting/damping;
- supersession handling;
- file/symbol metadata.

### Decision Layer

Answers:

> Given this evidence and the current project state, which category or action is most appropriate?

The router should distinguish two task families.

**Fixed-schema tasks** can use cheap trained classifiers:

- Logistic Regression;
- XGBoost;
- SetFit.

**Dynamic-schema tasks** receive their candidate label space at inference time and should use a candidate-conditioned engine:

- Jev;
- Laya if it demonstrates cross-project transfer;
- a future compatible decision model.

The router must not assume that one engine is best for both families.

### Generation Layer

Answers:

> How should this be explained to a person?

Used for:

- story summaries;
- proposal generation;
- ADR drafts;
- explanation of disagreements;
- curator escalation.

### Governance Layer

Answers:

> Is this proposed change allowed to become authoritative project state?


## Dynamic Ontology Path

Topic assignment should be represented as a candidate-conditioned decision rather than a globally fixed classifier whenever Memory Seed is operating as a reusable hosted service.

```text
new decision
   ↓
load current project ontology
   ↓
retrieve plausible Area/Activity candidates
   ↓
candidate-conditioned DecisionEngine
   ↓
Area + Activity candidate(s) + probabilities
   ↓
confidence / governance policy
```

The ontology can contain:

- names;
- descriptions;
- parent/child hierarchy;
- active/inactive status;
- optional examples.

The decision engine should not require those topic IDs to have existed during training.

## Generalization as a Deployment Gate

The benchmark harness must support leave-one-project-out evaluation. A specialized model is eligible for the hosted default only if it maintains acceptable performance on an unseen project with an unseen ontology.

This prevents a misleading result where a fine-tuned classifier performs extremely well on one corpus but fails when another user creates different Areas and Activities.

For a local single-project deployment, project-specific specialization can still be an optional optimization.

## Decision Queue

Background curator tasks should flow through a durable queue.

Example:

```text
conversation imported
       ↓
candidate decisions extracted
       ↓
queue:
- topic assignment
- link candidates
- ADR significance
- storyline role
       ↓
decision worker(s)
       ↓
validated updates
```

## Model Selection Policy

The router should choose the cheapest model known to meet the required reliability.

Example:

```text
fixed-schema relationship classification
→ cheapest validated classifier (LR/XGBoost/SetFit/etc.)

dynamic topic assignment
→ generalized candidate-conditioned engine (Jev/Laya/future model)

story-criticality
→ cheapest validated fixed-schema classifier or decision model

ambiguous governance case
→ LLM

constitutional conflict
→ human
```

This policy should be learned from tournament results, not hard-coded from assumptions.

## Story Retrieval Mode

Normal retrieval:

```text
query
 ↓
rank relevant current knowledge
```

Story retrieval:

```text
target/current node
 ↓
expand evolution graph
 ↓
classify core/supporting/peripheral
 ↓
chronological narrative
```

Both use the same underlying data but optimize for different objectives.

## Evidence Preservation

Never discard lower-confidence branches solely because a classifier marked them peripheral.

Store classification as metadata:

```yaml
story_role:
  predicted: peripheral
  confidence: 0.87
  engine: laya-ms-v1
```

This allows future models to re-evaluate the same graph.

## Historical Re-Evaluation

Because Memory Seed keeps decisions and evidence, future models can replay old classification tasks.

This creates a useful capability:

```text
old decision graph
      ↓
new model
      ↓
compare against existing curated labels
      ↓
measure improvement / regression
```

The project's own history therefore becomes an evolving benchmark.

## Versioned Model Registry

Maintain a simple registry:

```yaml
models:
  topic-v1:
    type: model2vec-logistic
    dataset: corpus-2026-09
  edge-v2:
    type: xgboost
    dataset: corpus-2026-10
  story-v1:
    type: laya
    dataset: corpus-2026-10
```

Every generated prediction references a model version.

## Recommended Implementation Sequence

### Phase 1 — Benchmark Harness

Build:

- dataset exporter;
- temporal split;
- common evaluation interface;
- metrics;
- latency measurement.

### Phase 2 — Cheap Baselines

Implement:

- Model2Vec + Logistic Regression;
- Model2Vec + XGBoost.

### Phase 3 — Specialist Models

Add:

- SetFit;
- Laya zero-shot;
- Laya fine-tuned;
- Jev.

### Phase 4 — Decision Queue

Implement a persistent worker abstraction and durable jobs.

### Phase 5 — Storyline Retrieval

Add deterministic lineage traversal plus relevance overlay.

### Phase 6 — Governance Routing

Add thresholds, escalation and model-version audit trails.

## Strategic Principle

Memory Seed should avoid betting its architecture on any specific model.

The durable elements should be:

```text
Decision objects
Relationships
Evidence
Evolution
Governance rules
Evaluation datasets
```

Models should remain replaceable components underneath those contracts.
