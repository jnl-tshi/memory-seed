---
title: "Proposal: Benchmark Decision Quality Under Constrained Context"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: Benchmark Decision Quality Under Constrained Context

**Status:** Explore further before promotion to ADR  
**Date:** 2026-07-18  
**Related documents:** [Context Assembly](deterministic-context-assembly-exploration.md), [Constitution](constitutional-principles-decision-efficiency-exploration.md)

## Summary

Memory Seed should be evaluated by how well it enables correct, grounded decisions under limited context.

Token count should be recorded where available, but the core benchmark must remain vendor-independent. The benchmark should measure whether the system supplies sufficient relevant information with low retrieval waste, stable selection, and low human or agent decision effort.

## Core hypothesis

> A structured memory system with explicit decisions, evidence, and deterministic context assembly will achieve equal or better task quality than baseline retrieval while requiring less irrelevant context and less decision effort.

## Why token cost is insufficient

Token cost varies with:

- tokenizer;
- model family;
- provider pricing;
- prompt formatting;
- context caching;
- input and output price differences;
- reasoning-token accounting;
- tool-call representation.

It remains commercially useful but is not a stable primary measure of architectural efficiency.

## North-star metric

### Decision quality under constrained context

A benchmarked system should answer correctly, cite the right evidence, respect active decisions, and state uncertainty while operating within a defined context budget.

This can be represented as a scorecard rather than a single opaque number.

## Proposed benchmark dimensions

| Dimension | Question |
|---|---|
| Correctness | Is the conclusion factually and logically correct? |
| Grounding | Are material claims supported by the supplied evidence? |
| Active-state accuracy | Did the system use the current decision rather than a superseded one? |
| Evidence recall | Did it retrieve the evidence needed for the task? |
| Contradiction handling | Did it surface important conflicting evidence? |
| Context efficiency | How much irrelevant or unused context was supplied? |
| Repeatability | Does the same task receive materially equivalent context? |
| Decision effort | How much additional searching or clarification was needed? |
| Abstention quality | Does the system identify insufficient evidence rather than inventing an answer? |
| Traceability | Can the answer be traced to stable project references? |

## Benchmark task families

### 1. Explain a decision

Example:

> Why did the project choose Mermaid as the default diagram language?

Expected output:

- current decision;
- rationale;
- supporting evidence;
- qualifications;
- stable references.

### 2. Explain supersession

Example:

> Why was decision `dec-0042-02` superseded, and what remains valid?

### 3. Identify the active constraint

Example:

> Which rule currently governs topic validation?

### 4. Assess a proposed change

Example:

> Would adding a new evidence entity conflict with the current minimal-metadata principle?

### 5. Trace impact

Example:

> Which plans, tasks, or artifacts should be reviewed after this decision changes?

### 6. Detect insufficient evidence

Example:

> Is the current evidence sufficient to promote this proposal to an ADR?

## Gold-set construction

Each benchmark case should include:

```yaml
case:
  id: bench-supersession-001
  task_type: explain-supersession
  question: Why was dec-0042-02 superseded?

  gold:
    active_decision: dec-0067-01
    required_evidence:
      - ev-0067-01
      - ev-0067-02
    required_qualifications:
      - Legacy D2 diagrams are not automatically invalid.
    prohibited_errors:
      - Treating dec-0042-02 as active.
      - Claiming all D2 use is banned.
    acceptable_abstention: false
```

Gold sets should be authored or reviewed by a human who understands the project history.

## Baselines

At minimum compare:

1. **No Memory Seed:** model receives only the task.
2. **Whole-document baseline:** model receives complete related files.
3. **Semantic top-k baseline:** vector or hybrid search retrieves chunks.
4. **Structured retrieval:** ontology and direct relationships only.
5. **Hybrid retrieval:** structured core plus semantic gap filling.
6. **Oracle packet:** human-selected minimum sufficient context.

The oracle packet establishes an approximate lower bound for useful context.

## Vendor-independent context measures

Record:

- number of source files;
- number of chunks;
- number of evidence items;
- number of decisions;
- words;
- characters;
- structured fields;
- unique propositions;
- context items used in the answer;
- irrelevant items;
- omitted required items.

Provider token counts and financial cost may be added as secondary measures.

## Proposed metrics

### Task quality score

Use a rubric scored by human review or a validated evaluator:

```text
quality = weighted(
  correctness,
  grounding,
  active-state accuracy,
  contradiction handling,
  traceability,
  abstention quality
)
```

Do not collapse dimensions until individual failures remain visible.

### Context utilization

```text
context utilization =
context items materially used in answer
/
total context items supplied
```

### Relevant-context precision

```text
context precision =
relevant supplied items
/
total supplied items
```

### Evidence recall

```text
evidence recall =
required evidence items retrieved
/
required evidence items in gold set
```

### Constrained quality retention

```text
quality retention =
quality under constrained packet
/
quality under oracle or full-context condition
```

### Decision effort

Possible measures:

- number of follow-up retrieval actions;
- number of clarification questions;
- time to correct answer;
- number of inspected files;
- number of manual corrections;
- number of unresolved references.

### Efficiency frontier

Plot quality against context size. A better system moves the frontier toward higher quality with less context.

## Composite experimental metric

For experimentation only:

```text
Decision Information Efficiency =
Quality Score × Evidence Recall × Traceability
/
(1 + Irrelevant Context Units + Follow-up Actions)
```

This should not become a public north-star metric until its behaviour is tested. Composite metrics can hide important trade-offs.

## Experimental design

### Fixed corpus

Use a frozen repository revision and versioned benchmark cases.

### Repeated trials

Run multiple trials for stochastic systems. Keep the retrieved packet separately from the generated answer so retrieval variance can be isolated from model variance.

### Cross-model testing

Use at least:

- one local or low-cost model;
- one stronger hosted model;
- optionally one model with a different tokenizer or context strategy.

The aim is not to rank vendors. It is to test whether Memory Seed's value transfers across models.

### Ablation tests

Remove one feature at a time:

- decision IDs;
- evidence links;
- supersession resolution;
- contradiction retrieval;
- topic constraints;
- deterministic ordering.

This reveals which structures create measurable value.

## Success criteria

An initial implementation is promising if, across representative tasks:

1. Quality is equal to or better than semantic top-k retrieval.
2. Active-state errors fall materially.
3. Required evidence recall improves.
4. Irrelevant context decreases.
5. Retrieval repeatability improves.
6. Follow-up retrieval or clarification decreases.
7. Gains occur across more than one model.

## Failure conditions

The design should be reconsidered if:

- metadata burden exceeds retrieval benefit;
- structured retrieval misses too much evidence;
- packet compression causes material omissions;
- repeatability improves but quality declines;
- the benchmark can only show gains on contrived tasks;
- results depend on one model or evaluator;
- evidence links are too unreliable to trust.

## Reporting format

Each benchmark run should publish:

```yaml
run:
  case_id: bench-supersession-001
  retrieval_method: hybrid-v1
  model: local-model-a
  repository_revision: abc123
  packet_policy: decision-explanation-v1

  results:
    correctness: 1.0
    grounding: 0.9
    active_state_accuracy: 1.0
    evidence_recall: 1.0
    context_precision: 0.78
    repeatability: 1.0
    follow_up_actions: 0

  context:
    words: 940
    evidence_items: 4
    files: 3
    provider_tokens: null
```

## Risks and mitigations

### Risk: Benchmark leakage

**Mitigation:** separate benchmark authoring from implementation and retain hidden cases.

### Risk: Evaluator bias

**Mitigation:** use explicit rubrics, human review, and disagreement tracking.

### Risk: Optimizing for narrow tasks

**Mitigation:** use several task families and real project histories.

### Risk: Context precision rewards harmful omission

**Mitigation:** pair precision with evidence recall and quality retention.

### Risk: Cost data becomes stale

**Mitigation:** store vendor pricing separately from architectural metrics.

## Questions for exploration

1. Which task families represent Memory Seed's actual purpose?
2. What should count as a relevant context item?
3. How should human effort be measured consistently?
4. What quality threshold is acceptable for constrained packets?
5. How should benchmark cases evolve as the ontology changes?
6. Should benchmark failures automatically block schema promotion?
7. Which metrics should be visible in Memory Trace?

## Recommended first benchmark suite

Create 20 cases:

- 5 decision explanations;
- 5 supersession explanations;
- 4 active-constraint queries;
- 3 impact traces;
- 3 insufficient-evidence assessments.

Run all baselines on the same frozen repository revision and publish both aggregate results and failure examples.

## Promotion criteria

1. The suite includes real, non-trivial project cases.
2. Gold evidence and active decisions are independently reviewed.
3. Results separate retrieval quality from answer-generation quality.
4. The proposed architecture beats at least one meaningful baseline.
5. Metrics reveal failure modes rather than hiding them.
