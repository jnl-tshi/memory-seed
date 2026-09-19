---
title: "Archived source — 06-mvp-80-20-plan"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/06-mvp-80-20-plan.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 6 — 80/20 MVP Plan for Hosted Memory Seed

## Objective

Identify the smallest amount of implementation work that proves the hosted Memory Seed thesis and delivers most of the user value.

---

## The Core MVP Loop

```text
Conversation
    |
    v
PostgreSQL
    |
    v
Automatic decision extraction
    |
    v
Topic + relationship curation
    |
    v
Existing multi-signal retrieval
    |
    v
Useful memory returned to the agent
```

The MVP should make decision management feel like infrastructure rather than a manual task.

---

## Build These First

### 1. Canonical PostgreSQL + pgvector Backend

Store:

- conversation events
- decisions
- decision versions
- topics
- graph edges
- embeddings
- curator runs

### 2. Dumb Append-Only Hooks

Hooks should only send timestamped events to the server.

Do not put decision logic in hooks.

### 3. One Background Curator Worker

The worker should:

- detect durable decision content
- extract decision candidates
- assign topics
- find likely related records
- create typed relationship judgments

### 4. Preserve Existing Retrieval

The hosted implementation must retain:

- semantic relevance
- chronology
- preferred-keyword boosting
- graph-edge boosting
- graph-edge damping

pgvector should provide candidate retrieval, not replace the ranking engine.

### 5. One Semantic Decision Provider

Use OpenRouter first through a provider abstraction.

Do not build model-specific logic into the curator.

### 6. Governance Escalation Only

The curator may detect potential ADR or Constitution impact.

Actual governance modifications should be handled by a reasoning model and/or authorised user.

---

## Do Not Build Yet

Postpone:

- local/cloud bidirectional sync
- multi-master replication
- automatic constitutional amendments
- sophisticated ADR rewriting
- Jev integration
- custom graph database
- multiple curator models
- elaborate microservice topology
- graph-wide continuous reprocessing
- fine-tuning
- enterprise permissions beyond what the MVP requires

---

## Recommended Processing Boundary

Avoid processing every message independently.

Use:

```text
normal work
   |
events accumulate
   |
session boundary / inactivity / commit
   |
curator receives bounded context
   |
0-N durable decisions extracted
```

This is simpler and likely to produce cleaner decisions.

---

## Minimal Curator Questions

Start with only:

```yaml
is_durable_decision: true/false

topics:
  - ...

related_to:
  - candidate_id

relationship:
  one_of:
    - supports
    - evolves
    - supersedes
    - contradicts
    - implements
    - duplicate
    - related
```

Add richer ontology only after the benchmark indicates a need.

---

## Minimal Provider Interface

```python
class DecisionProvider:
    def evaluate(self, evidence, questions):
        ...
```

Initial implementation:

```text
OpenRouterProvider
```

Future implementations:

```text
JevProvider
LocalProvider
```

---

## MVP Deployment

Use the same codebase for local and hosted versions.

```text
Docker
├── memory-seed-api
├── curator-worker
└── postgres + pgvector
```

Configuration selects the target deployment.

---

## Definition of Done

The first hosted milestone is:

> **Conversation -> PostgreSQL -> automatic decision -> topic -> related decision -> existing multi-signal retrieval -> useful memory returned to the agent.**

If that loop works reliably, most of the hosted Memory Seed value proposition has been proven.
