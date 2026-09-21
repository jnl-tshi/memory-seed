---
title: "Laya as a local decision worker"
date: "2026-09-21"
status: deferred
deferred_reason: "A Laya-specific resident worker depends on the P1 tournament, privacy/cost evidence, and measured queue load."
revisit_when: "A task-specific Laya configuration beats simpler and generalized baselines on the relevant holdouts and a persistent worker is justified by measured latency or throughput."
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Laya as a Persistent Local Decision Worker — With Generalization Gate

## Current disposition

**DEFERRED MODEL-SPECIFIC IMPLEMENTATION.** The [hosted programme](../2_Todo/hosted-memory-mvp-programme.md) already requires an event-driven, provider-neutral curator and versioned jobs. Run the [tournament](../2_Todo/decision-layer-model-tournament-plan.md) before choosing Laya. A local resident process, if earned, remains optional and must not become a required dependency of the offline Markdown-authoritative OSS core. Keep inference stateless, jobs idempotent, predictions auditable, and mutations under the existing validator and approval rules. The serial/batch/multi-worker stages below are hypotheses to measure, not a committed topology.

## Purpose

Evaluate Laya as a local, persistent, stateless decision service for Memory Seed **without assuming it is the production default**. Laya must earn that role against Jev and conventional classifiers, and it must demonstrate cross-project generalization for dynamic ontology tasks.

The architecture should exploit an important property:

> The model can remain loaded while each inference request remains logically independent.

This provides low repeated latency without retaining conversational state between tasks.


## Generalization Gate

Laya has two materially different possible roles:

### Role A — Project-Specific Specialist

Fine-tune on one project's curated decisions and labels. This may produce excellent accuracy, but it creates a model tied to that project's ontology.

That can be useful for a single-user/local deployment, but it is not automatically suitable for a hosted Memory Seed service.

### Role B — Memory Seed General Decision Worker

Fine-tune on the abstract decision task rather than on fixed labels. For topic assignment, each training example should provide the current candidate ontology as part of the state:

```text
Decision
+ current Areas
+ current Activities
+ topic descriptions
+ hierarchy
→ selected candidate(s)
```

The model should then be evaluated on entirely unseen projects and unseen topic vocabularies.

Only if this transfer test succeeds should Laya be considered a general hosted decision worker for topic assignment.

## Jev Comparison

Jev remains an important baseline because its attraction is precisely the ability to consume the user's current state and candidate options at inference time without project-specific retraining.

For dynamic ontology tasks, the production decision should therefore be based on:

- accuracy;
- calibration;
- latency;
- cost;
- privacy/locality;
- **unseen-project generalization**.

For fixed-schema tasks, Laya should also compete against much simpler classifiers.

## Proposed Runtime Pattern

Do not start and stop the model for every decision.

Instead:

```text
Memory Seed
    │
    ▼
Decision Queue
    │
    ▼
Persistent Laya Worker
    │
    ├── Task 1
    ├── Task 2
    ├── Task 3
    └── Task N
```

The model remains resident in memory.

Each task supplies its own state and questions.

After inference, the task context can be discarded.

## Stateless Request Model

Conceptually:

```text
request A
state A + questions A
        ↓
      Laya
        ↓
response A

request B
state B + questions B
        ↓
      same loaded Laya
        ↓
response B
```

There should be no dependence between A and B unless Memory Seed explicitly places information from A into B.

This is desirable for governance because inference becomes:

- reproducible;
- isolated;
- easier to audit;
- easier to retry;
- less vulnerable to hidden conversational state.

## Queue-Based Execution

If inference is sufficiently fast, the simplest architecture may be a single queue.

```text
events
  ↓
job queue
  ↓
Laya worker
  ↓
decision results
  ↓
database
```

Potential jobs:

```text
assign_topics
classify_link
score_story_relevance
classify_adr_significance
check_candidate_supersession
score_retrieval_candidate
```

## Why Start Serial

A serial worker has several advantages:

- simplest operational model;
- predictable memory usage;
- no duplicated model instances;
- deterministic ordering when required;
- easier logging;
- easier retry handling.

If Laya processes jobs faster than Memory Seed creates them, parallelism is unnecessary.

## Scaling Path

If the queue becomes a bottleneck:

### Stage 1 — Batch Questions

Combine related questions about the same state.

Example:

```text
decision D102

questions:
- topic?
- ADR significance?
- core storyline?
- candidate relationship to D088?
```

This may be substantially cheaper than independent inference calls.

### Stage 2 — Micro-Batching

Combine multiple queued tasks into a small inference batch if the implementation supports it efficiently.

### Stage 3 — Multiple Workers

Only add additional model workers when required.

```text
               ┌─ Laya Worker 1
Queue/Router ──┼─ Laya Worker 2
               └─ Laya Worker 3
```

Each worker requires its own model memory unless shared-memory execution is explicitly supported.

This increases:

- RAM/VRAM requirements;
- process complexity;
- synchronization requirements.

Therefore parallel workers should be demand-driven rather than the default.

## Job Design

Every job should be:

### Idempotent

Running it twice should not corrupt state.

Example key:

```text
decision_id
classifier_version
task_type
candidate_set_hash
```

### Versioned

Record:

- model name;
- model version;
- prompt/question schema;
- feature/schema version;
- confidence threshold.

### Auditable

Store:

```yaml
job_id:
decision_id:
task_type:
input_hash:
model:
model_version:
output:
probabilities:
timestamp:
accepted_by:
```

Do not store hidden model reasoning as a governance dependency.

## Confidence Routing

The worker should not be forced to decide every task.

Example:

```text
Laya
  │
  ├── confidence >= threshold
  │       ↓
  │    accept
  │
  └── confidence < threshold
          ↓
       escalation
```

Escalation might route to:

```text
small LLM
     ↓
larger LLM
     ↓
human review
```

depending on importance.

## Production Principle

The Laya worker should be treated as infrastructure, not as an agent.

It should:

- receive bounded structured jobs;
- produce bounded structured outputs;
- retain no conversational history;
- mutate nothing directly;
- propose decisions rather than silently rewriting project state.

A separate curator/governance layer should decide how predictions become persistent graph changes.

## Recommendation

Prototype a single persistent worker with a durable queue before attempting parallel workers.

Measure:

- warm inference latency;
- jobs/second;
- queue depth under realistic load;
- model memory;
- calibration;
- percentage of jobs requiring escalation.

If one worker comfortably handles the workload, keep the architecture serial and simple.
