---
title: "Proposal: Deterministic Context Assembly"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../1_Inbox/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Deterministic Context Assembly

**Status:** Explore further before promotion to ADR  
**Date:** 2026-07-18  
**Related documents:** [Evidence Model](evidence-model-and-packets-exploration.md), [Benchmarking](benchmarking-decision-quality-exploration.md)

## Summary

Memory Seed should assemble model context using deterministic structural rules before applying stochastic semantic ranking or summarization.

The objective is not to eliminate all model variability. It is to ensure that the system consistently selects the same relevant decision and evidence surface for the same task and repository state.

## Problem

Naive retrieval often combines:

- semantic similarity;
- recency;
- large document chunks;
- model-generated summaries;
- vendor-specific token budgets.

This can produce different context on repeated runs, omit decisive evidence, retrieve superseded decisions, and waste context on loosely related text.

Token savings alone are not a sufficient objective. A very small context that omits a critical qualification is worse than a slightly larger complete packet.

## Proposal

Use a staged context assembly pipeline:

1. Resolve the task and target entities.
2. Traverse explicit ontology relationships.
3. Resolve active decision state.
4. collect direct evidence, contradictions, and qualifications.
5. include required dependencies and definitions.
6. apply deterministic ordering and deduplication.
7. use semantic retrieval only to fill defined gaps.
8. compress only after preserving provenance and required facts.
9. emit a packet manifest.

## Deterministic does not mean entirely non-stochastic

The desired boundary is:

- **Deterministic selection core:** IDs, types, relationships, status resolution, topic membership, dates, permissions, exact filters.
- **Controlled stochastic layer:** semantic expansion, reranking, summarization, answer generation.
- **Recorded provenance:** policy version, candidates, scores, omissions, and source versions.

The deterministic core reduces the number of decisions delegated to the model.

## Context assembly policy

A policy should be versioned and testable.

```yaml
policy:
  id: decision-explanation-v1
  task_types:
    - explain-decision
    - explain-supersession

  required:
    - target-decision
    - resolved-status
    - direct-predecessor-or-successor
    - linked-supporting-evidence
    - linked-contradictory-evidence
    - linked-qualifying-evidence

  optional:
    - related-session-observations
    - affected-artifacts
    - topic-neighbourhood

  limits:
    max_evidence_items: 8
    max_background_items: 3

  ordering:
    - active-decision
    - evolution-chain
    - decisive-evidence
    - contradictory-evidence
    - qualifications
    - affected-artifacts
    - background
```

## Proposed assembly stages

### 1. Task normalization

Convert the user request into a task type and explicit targets.

Example:

```yaml
task:
  type: explain-supersession
  targets:
    - dec-0042-02
```

### 2. Exact entity resolution

Resolve stable IDs, deterministic anchors, exact topics, and file references.

### 3. Active-state resolution

Determine whether the target is active, superseded, updated, or unresolved.

### 4. Structural expansion

Traverse only relationships permitted by the task policy.

For a supersession explanation:

```text
target decision
→ successor decision
→ rationale
→ direct evidence
→ relevant contradiction and qualification
→ affected artifacts
```

### 5. Semantic gap filling

Semantic retrieval is permitted only for declared gaps, such as missing rationale or unlinked historical observations.

Every semantic addition should be labelled as inferred or candidate context until validated.

### 6. Deduplication and compression

Deduplicate by stable identity and source span before summarization. Prefer extracted facts and structured fields to model-written summaries.

### 7. Sufficiency check

Before answering, verify that the packet contains the minimum elements required by the task.

### 8. Manifest emission

```yaml
manifest:
  task_id: bench-explain-supersession-01
  policy_id: decision-explanation-v1
  repository_revision: abc123
  included:
    decisions: 2
    evidence: 4
    artifacts: 1
  omitted:
    - id: ev-0019
      reason: lower-priority duplicate
  semantic_expansion_used: false
  estimated_context_units: 1480
```

## Vendor-independent context units

Token counts may still be logged, but the primary evaluation should use additional model-independent measures:

- Unicode characters;
- words;
- structured fields;
- source chunks;
- evidence items;
- unique propositions;
- retrieved documents;
- proportion of included content used;
- proportion of relevant evidence retrieved.

This allows comparison across vendors and tokenizers.

## Context sufficiency

A packet is sufficient when it contains all information necessary for a competent system to perform the benchmark task correctly, subject to the defined task scope.

Sufficiency should be tested empirically, not assumed from schema completeness.

## Relevance and necessity labels

Each packet component may be labelled:

| Label | Meaning |
|---|---|
| `required` | Removing it makes the answer incorrect or materially incomplete |
| `supporting` | Improves confidence or explanation |
| `background` | Helpful but not necessary |
| `candidate` | Semantically retrieved and not yet structurally confirmed |

These labels support packet pruning and benchmark analysis.

## Determinism metrics

### Selection repeatability

For repeated runs with the same repository state:

```text
repeatability = identical selected item IDs / total repeated comparisons
```

### Ordering repeatability

Measure whether selected items appear in the same order.

### Active-decision accuracy

Measure whether the assembler selects the currently valid decision.

### Evidence recall

```text
evidence recall = relevant evidence items retrieved / relevant evidence items in benchmark gold set
```

### Irrelevant context ratio

```text
irrelevant ratio = irrelevant included context units / total included context units
```

## Expected benefits

- Lower irrelevant context volume.
- More repeatable agent behaviour.
- Fewer stale-decision errors.
- Better grounding.
- Easier debugging.
- Vendor-independent optimization.
- Clear division between deterministic tooling and probabilistic reasoning.

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| Typed traversal first | High precision | Depends on metadata quality |
| Semantic gap filling second | Better recall | Adds variability |
| Packet manifests | Auditability | Storage and implementation overhead |
| Task-specific policies | Better relevance | More policies to maintain |
| Sufficiency checks | Fewer omissions | Requires benchmark definitions |

## Risks and mitigations

### Risk: Deterministic retrieval is consistently wrong

**Mitigation:** measure evidence recall and allow controlled semantic gap filling.

### Risk: Policies proliferate

**Mitigation:** begin with a small number of high-value task families.

### Risk: Metadata defects propagate

**Mitigation:** validate IDs, relationships, status, and evidence links in CI.

### Risk: Compression removes material nuance

**Mitigation:** compress only after required facts are selected and preserve provenance.

### Risk: Optimizing for repeatability suppresses useful discovery

**Mitigation:** separate operational answer mode from exploratory discovery mode.

## Initial task policies

Start with three:

1. `explain-decision`
2. `explain-supersession`
3. `identify-active-constraint`

These directly test whether ontology and evidence improve practical reasoning.

## Questions for exploration

1. Which context elements must never be summarized?
2. How should semantic candidates become validated structural links?
3. What is the correct fallback when evidence is incomplete?
4. Should packet policies live in code, YAML, or skills?
5. How should permissions filter evidence without creating misleading gaps?
6. How should task normalization be tested?
7. What stability level is sufficient when semantic retrieval is used?

## Recommended prototype

Implement a local assembler for ten benchmark questions. Compare:

- whole-file retrieval;
- semantic top-k retrieval;
- deterministic structural retrieval;
- hybrid structural plus semantic retrieval.

Record quality, evidence recall, irrelevant context, repeatability, latency, and context size.

## Promotion criteria

1. Structural or hybrid assembly improves grounded answer quality over the baseline.
2. Repeated runs select materially equivalent decision and evidence sets.
3. Active decisions are resolved correctly.
4. Relevant contradictory evidence is not systematically omitted.
5. Context reduction does not reduce benchmark quality.
