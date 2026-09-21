---
title: "Decision-centric governance architecture — source rationale"
date: "2026-09-21"
status: archived-reference
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Decision-Centric Governance Architecture

## Current disposition

**ARCHIVED SOURCE RATIONALE.** The [hosted programme](../../2_Todo/hosted-memory-mvp-programme.md) and [edition authority contract](../../3_Spec/edition-authority-contract.md) already own authenticated identity, exact pending mutations, delegation, and approval. Classifier output is a proposal, never permission or authority. The source pipeline and candidate labels below remain explanatory rather than a new governance contract.

## Purpose

Define how Memory Seed can use explicit decision records to provide governance even as AI agents become more autonomous and their internal reasoning becomes less visible.

## Problem

Agent systems increasingly perform complex reasoning internally.

The internal process may be:

- inaccessible;
- compressed;
- proprietary;
- ephemeral;
- non-reproducible across model versions.

Attempting to treat internal reasoning traces as the primary governance record is therefore fragile.

## Proposed Governance Boundary

Govern the transition from model behavior into persistent project state.

```text
Agent / Model
      ↓
proposed decision
      ↓
decision validation
      ↓
governance checks
      ↓
accepted project mutation
```

Memory Seed should capture the decision before the mutation becomes authoritative.

## Governance Objects

### Constitution

Long-lived rules and principles.

Examples:

- deterministic retrieval must remain reproducible;
- humans retain final authority over constitutional changes;
- derived edges are not silently deleted.

### ADRs

High-impact architectural decisions.

### Ordinary Decisions

Operational design choices that may later evolve into ADRs.

### Evidence

Supporting material:

- conversation;
- code;
- benchmarks;
- tests;
- documents;
- metrics.

## Decision Promotion

A normal decision may evolve into an ADR.

Example:

```text
D12
  ↓
D19
  ↓
D27
  ↓
repeated architectural significance
  ↓
ADR-005
```

A decision classifier can estimate whether a new decision:

```text
remains operational
updates an ADR
requires a new ADR
suggests a constitutional implication
```

Low-confidence cases should escalate.


## Dynamic Project State as Governance Input

Some governance decisions depend on project-specific state that cannot be encoded as a universal fixed classifier label set. Topic assignment is the clearest example: each project can have different Areas, Activities and hierarchy relationships.

The governance layer should therefore pass the current source of truth into the decision engine:

```text
current project ontology
+ active ADRs
+ Constitution
+ candidate relationships
+ retrieved evidence
→ bounded decision
```

The model does not own this state. Memory Seed does. The decision engine receives a snapshot and returns a proposal.

This keeps the ontology, ADRs and Constitution as the durable source of truth while allowing Jev, Laya or future engines to be swapped underneath.

## Governance Check Pipeline

```text
new decision
    │
    ▼
retrieve relevant constitution + ADRs + prior decisions
    │
    ▼
cheap decision layer
    │
    ├── clearly aligned
    │       ↓
    │     accept
    │
    ├── ambiguous
    │       ↓
    │   LLM curator
    │
    └── material conflict
            ↓
        human review
```

The exact classifier can remain pluggable.

## No Hidden Reasoning Dependency

Memory Seed should never require private chain-of-thought as evidence.

Instead, require explicit artifacts such as:

```yaml
decision:
reason:
alternatives:
evidence:
affected_files:
relationships:
confidence:
```

This creates a portable governance record.

## Human Authority

Classifier or LLM predictions should be proposals.

High-impact state changes should retain human authority, particularly:

- Constitution changes;
- major ADR creation;
- destructive graph changes;
- conflicting supersession paths;
- irreversible migration decisions.

## Model Independence

The governance layer should not know whether a prediction came from:

- Laya;
- Jev;
- XGBoost;
- SetFit;
- an LLM;
- a future system.

It should consume a normalized output.

Example:

```json
{
  "task": "adr_significance",
  "prediction": "new_adr",
  "confidence": 0.93,
  "engine": "laya-ms-v2",
  "evidence_ids": ["D41", "D52", "ADR-004"]
}
```

## Auditability

Every accepted model-generated relationship should be reconstructable.

Store:

```text
who/what proposed it
model version
input evidence
confidence
acceptance status
timestamp
supersession history
```

Do not overwrite historical model outputs.

## Recommendation

Treat decision capture as the governance seam between increasingly opaque AI reasoning systems and durable project state.

This architecture should remain stable even if model internals, harnesses and providers change dramatically.
