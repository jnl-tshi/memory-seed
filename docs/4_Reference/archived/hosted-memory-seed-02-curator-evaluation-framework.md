---
title: "Archived source — 02-curator-evaluation-framework"
source_path: "docs/1_Inbox/memory-seed-hosted-proposals/02-curator-evaluation-framework.md"
captured_on: "2026-09-18"
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
archive_note: "Copied from the primary checkout without deleting or modifying the untracked original; superseded assumptions are preserved as source evidence."
---

# Proposal 2 — Curator Evaluation and Continuous Improvement Framework

## Objective

Create a dedicated evaluation framework for measuring whether the Memory Seed curator is actually improving the knowledge graph and decision layer.

The goal is to prevent silent degradation caused by inaccurate edges, topic assignments, or governance-impact classifications.

---

## Core Principle

Every curator output should be measurable against labelled examples.

Build a domain-specific benchmark from real Memory Seed decisions rather than relying only on generic model benchmarks.

Example:

```yaml
source: decision_017
target: decision_041

ground_truth:
  related: true
  relationship: supersedes
  same_topic: true
  adr_relevance: material
```

---

## Evaluation Dimensions

### 1. Edge Creation

Measure:

- precision
- recall
- F1
- false-positive rate
- false-negative rate

Graph precision is especially important because false edges can contaminate later retrieval.

### 2. Edge Type

Use a confusion matrix across relationship classes:

```text
supports
evolves
supersedes
contradicts
implements
depends_on
alternative_to
duplicate
related
none
```

### 3. Topic Assignment

Measure:

- correct existing-topic assignment
- unnecessary new-topic creation
- missed topic association
- excessive multi-topic assignment

### 4. ADR Relevance

Measure separately:

- ADR relevance recall
- false escalation rate
- missed material ADR impacts

### 5. Constitutional Relevance

Treat as a high-risk classification.

Prefer high recall for possible conflicts, followed by reasoning-model or human review.

---

## Preserve Raw Confidence

Do not collapse model outputs immediately to booleans.

Store:

```text
relationship = supersedes
confidence   = 0.927
```

instead of only:

```text
supersedes = true
```

This allows later calibration.

Example:

```text
confidence >= 0.95 -> precision 98.7%
confidence >= 0.85 -> precision 94.2%
confidence >= 0.70 -> precision 82.1%
```

Thresholds can then be set according to the risk of the action.

---

## Model Comparison

The same benchmark should support direct comparison between:

- OpenRouter Model A
- OpenRouter Model B
- different prompts
- different schemas
- different candidate-set sizes
- Jev
- future local/open-weight models

The curator should therefore be evaluated as a system, not just as a model.

---

## Shadow Evaluation

When introducing a new model, run it in shadow mode before production replacement.

```text
Production curator
      |
      +--> current provider -> database writes
      |
      +--> candidate provider -> evaluation log only
```

Example:

```text
OpenRouter/Qwen -> production
Jev             -> shadow
```

This allows comparison across real workloads without risking the production graph.

---

## Human Corrections as Labels

Corrections should become permanent benchmark data.

Example:

```yaml
original_prediction:
  relationship: supersedes
  confidence: 0.91

corrected_relationship:
  relationship: implements

context_version: ...
```

These corrections should not be discarded as isolated mistakes.

Over time they form the highest-value domain-specific dataset available to Memory Seed.

---

## Versioning

Every evaluation result should record:

- model/provider
- model version
- prompt version
- schema version
- evidence-packet version
- retrieval/candidate-generation version
- threshold policy

This makes regressions diagnosable.

---

## Success Condition

The framework succeeds when Memory Seed can answer:

> Is this new curator configuration objectively better than the current one for our actual decision-management workload?

without relying on subjective inspection.
