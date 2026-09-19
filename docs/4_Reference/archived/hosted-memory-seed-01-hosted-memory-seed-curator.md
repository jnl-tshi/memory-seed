---
title: "Archived source — 01-hosted-memory-seed-curator"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/01-hosted-memory-seed-curator.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 1 — Hosted Memory Seed Curator

## Status

Draft proposal.

## Objective

Create a continuously running background curator for a hosted Memory Seed implementation.

The curator is not user-facing. It maintains the derived knowledge structure around captured conversations and decision records, including:

- decision extraction
- topic assignment
- graph-edge creation
- duplicate and near-duplicate detection
- decision evolution and supersession
- ADR relevance detection
- constitutional relevance detection
- escalation of consequential changes

The initial implementation should use a low-cost model through OpenRouter while preserving a provider abstraction that allows later migration to Jev, an open-weight model, or another specialised semantic decision system.

---

## Design Principles

1. **The curator owns the workflow; the model only makes bounded semantic judgments.**
2. **Candidate generation should be deterministic and cheap.**
3. **The curator should never compare every record with every other record.**
4. **Derived relationships must remain rebuildable.**
5. **Governance changes should be escalated, not silently applied.**
6. **The user should not need to manually maintain decision records during normal work.**

---

## Proposed Architecture

```text
Agent / CLI / IDE Hooks
        |
        v
Conversation Event API
        |
        v
PostgreSQL + pgvector
        |
        +--> raw conversation events
        +--> embeddings
        +--> curator jobs
                |
                v
        Candidate generation
                |
                v
        Evidence packet
                |
                v
        Semantic Decision Provider
          |             |
          v             v
      OpenRouter       Jev
        first          later
          \             /
           \           /
            v         v
             Typed judgments
                   |
        +----------+----------+
        |          |          |
        v          v          v
      Edges      Topics   Governance signals
```

---

## Hook Behaviour

Hooks should remain deliberately simple.

Their job is to append immutable conversation events, not to interpret them.

Example event:

```json
{
  "session_id": "S-812",
  "timestamp": "2026-09-16T08:20:00Z",
  "agent": "codex",
  "role": "assistant",
  "content": "...",
  "project": "memory-seed",
  "repository": "jnl-tshi/memory-seed",
  "branch": "main",
  "git_commit": "7f2a9d"
}
```

The curator should perform interpretation asynchronously.

---

## Curator Triggering

Do not run full decision extraction after every message.

Prefer a bounded processing window triggered by one or more of:

- session end
- 5–10 minutes of inactivity
- Git commit
- explicit checkpoint
- a batch-size threshold

This gives the curator enough surrounding context to distinguish exploration from durable decisions.

---

## Two-Pass Curator

### Pass 1 — Durable-Knowledge Detection

Cheap semantic check:

```text
Does this context contain:
- a durable decision?
- an alternative?
- a rationale?
- a constraint?
- an unresolved question?
```

Contexts without durable information stop here.

### Pass 2 — Knowledge Construction

For durable content:

```text
What decision was made?
What existing decision does it relate to?
Is it new, evolved, superseded, supporting, contradictory, or duplicate?
Which topics apply?
Could it affect an ADR?
Could it affect the Constitution?
```

---

## Typed Decisions

Avoid open-ended prompts when possible.

Example schema:

```yaml
is_durable_decision:
  type: boolean

relationship:
  type: enum
  values:
    - supports
    - evolves
    - supersedes
    - contradicts
    - implements
    - depends_on
    - alternative_to
    - duplicate
    - related
    - none

same_topic:
  type: boolean

adr_relevance:
  type: enum
  values:
    - none
    - related
    - material
    - potentially_changes_adr

constitution_relevance:
  type: enum
  values:
    - none
    - related
    - possible_conflict
    - possible_amendment
```

---

## Candidate Generation

Before asking any model to judge relationships:

1. embed the new or updated decision
2. use pgvector to retrieve likely related records
3. apply cheap metadata filters
4. send only a small candidate set to the semantic decision provider

Candidate signals can include:

- vector similarity
- existing topics
- shared files or symbols
- Git commit proximity
- timestamps
- existing graph neighbourhood
- ADR membership
- repository or workspace boundaries

---

## Provider Abstraction

The curator must not depend directly on OpenRouter.

Use an interface such as:

```python
class DecisionProvider:
    def evaluate(self, evidence, questions):
        ...
```

Possible implementations:

```text
OpenRouterDecisionProvider
JevDecisionProvider
LocalModelDecisionProvider
TestDecisionProvider
```

This makes Jev an optimisation, not an architectural dependency.

---

## Confidence and Escalation

Use asymmetric thresholds.

Low-risk operations can accept lower confidence than governance-changing operations.

Example policy:

```text
topic assignment              -> moderate confidence allowed
related edge                  -> moderate/high confidence
supersedes edge               -> high confidence
ADR-impact detection          -> high confidence
constitutional amendment      -> never autonomous
```

The exact thresholds should be determined empirically.

---

## ADR and Constitution Handling

The curator may detect a likely governance impact, but should not directly rewrite governance documents.

```text
New evidence
    |
    v
Curator detects potential ADR impact
    |
    v
Escalation packet
    |
    v
Reasoning agent
    |
    v
Proposed ADR update
    |
    v
User / authorised agent approval
```

The same pattern applies to constitutional changes.

---

## Provenance

Every curator decision should be reproducible.

Example:

```yaml
derived_edge:
  source: decision_183
  target: decision_094
  relation: supersedes
  confidence: 0.94

  evidence:
    - decision_183
    - decision_094
    - adr_012

  curator:
    provider: openrouter
    model: ...
    prompt_version: curator-v3
    schema_version: edge-v2

  created_at: ...
```

The evidence packet becomes the provenance record for the derived judgment.

---

## Initial Security Policy

For OpenRouter-backed deployments, enforce application-level routing policy rather than unrestricted provider selection.

Example:

```yaml
curator_security_policy:
  require_zero_data_retention: true
  allow_training: false
  allowed_regions:
    - EU
    - US
  allowed_providers:
    - ...
```

---

## Success Condition

The curator is successful when normal work can proceed without manual decision-management overhead while Memory Seed quietly:

```text
captures
-> extracts
-> structures
-> links
-> preserves provenance
-> escalates only when necessary
```
