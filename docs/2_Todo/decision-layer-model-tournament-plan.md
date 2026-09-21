---
title: "Decision-layer model tournament"
date: "2026-09-21"
priority: P1
status: accepted-subplan
parent_plan: "docs/2_Todo/hosted-memory-mvp-programme.md"
next_action: "After the P0 thin slice, begin a dedicated design discovery with JNL; settle the evaluation design before dataset assembly or benchmarking."
blocked_by:
  - "P0.4 captured-decision and authenticated-retrieval thin slice"
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Decision-Layer Model Tournament

## Tranche entry gate

When this P1 tranche starts, run the [Next Steps design discovery](0_NEXT_STEPS.md#tranche-entry-gate--design-discovery-first)
with JNL first. Settle task definitions, label provenance, permissible datasets, holdout composition,
independent-project availability, thresholds, privacy constraints, cost ceiling, and decision authority
before preparing data or running candidates. This plan supplies candidates and safeguards for that
conversation; the reviewed tranche-specific design governs execution.

## Current disposition and execution brief

**ACTIVE P1 SUBPLAN** of the [hosted MVP programme](hosted-memory-mvp-programme.md), not a replacement for its capture-first P0 sequence. This file retains the supplied proposal details below as candidate designs; the following gates control execution.

- **Scope:** Evaluate each task separately. For stable global labels, start with Model2Vec plus Logistic Regression, Model2Vec plus XGBoost, and SetFit. Include deterministic baselines, Jev, Laya zero-shot, Laya fine-tuned, and a small language-model comparison only when the evaluation protocol and data permissions justify them. No candidate is the default in advance.
- **Dynamic topics:** Supply the current project's Area/Activity names, descriptions, hierarchy, and candidate set at inference time. Compare candidate-conditioned systems; a classifier trained on this project's topic IDs is a within-project baseline, not evidence of hosted transfer.
- **Dataset gate:** Inventory label provenance and ambiguity before calling the historical corpus a gold set. Keep decision-time features only; prevent future metadata and candidate-selection leakage. Freeze a reviewed test set and hard negatives. Unseen-project, unseen-ontology, and new-topic tests require independent projects; the local Memory Seed corpus alone cannot satisfy those gates.
- **Measurements:** Per-task precision/recall, macro F1, calibration, abstention coverage, high-risk false positives, latency, throughput, memory, and cost. Select numerical thresholds before autonomous use and compare the complete curator pipeline, including candidate retrieval and validation.
- **Authority:** Experimental labels such as `supports`, `contradicts`, or `unrelated` do not become authored lifecycle edges. Production edges remain `related`, `evolves`, and `replaces` unless the governed contract changes. A model may propose ADR relevance or conflict; it cannot authorize an ADR or Constitution mutation.
- **Acceptance:** Publish a reproducible per-task result table and an evidence-backed recommendation that names task-specific winners, abstention thresholds, cross-project limits, and whether any persistent specialist worker is warranted. Record a no-adoption result when no candidate clears the gate.
- **Non-goals:** No provider purchase, paid call, model training, private-data upload, or production model deployment is authorized by this planning document.

The source text below is retained as proposal evidence. Where its examples suggest a production winner or broader edge vocabulary, the execution brief and live programme govern.

## Purpose

Evaluate the best decision/classification architecture for Memory Seed using the existing curated corpus as the primary benchmark.

The goal is not to select a model based on generic benchmarks or current industry attention. The goal is to identify the cheapest, fastest, most accurate and best-calibrated approach for Memory Seed's actual decision-management tasks.

## Core Principle

Memory Seed already contains a valuable supervised dataset:

- historical decisions;
- curated topics;
- curated links;
- supersession/evolution relationships;
- ADR relationships;
- other graph metadata that has already been reviewed by an existing curator process.

This corpus can therefore act as a domain-specific gold set.

Rather than assuming that Jev, Laya, XGBoost, SetFit or another classifier is best, Memory Seed should run a controlled tournament against this existing curated history.

## Candidate Systems

### 1. Model2Vec + Logistic Regression

Pipeline:

```text
decision text/context
        ↓
Model2Vec embedding
        ↓
Logistic Regression
        ↓
class probabilities
```

Advantages:

- extremely lightweight;
- reuses the existing Memory Seed embedding stack;
- low inference latency;
- easy to retrain;
- probability output;
- simple to debug;
- strong baseline for linearly separable classes.

This should be the minimum-complexity baseline.

---

### 2. Model2Vec + XGBoost

Pipeline:

```text
decision text/context
        ↓
Model2Vec embedding
        ↓
XGBoost
        ↓
class probabilities
```

Advantages:

- can learn nonlinear boundaries over the embedding space;
- likely well suited to structured or semi-structured decision metadata;
- familiar and mature;
- very fast once trained;
- easy to retrain against the Memory Seed corpus.

This may be particularly strong when the task combines semantic features with structured fields such as:

- topic hierarchy;
- chronology;
- decision type;
- graph neighborhood;
- file/module metadata;
- ADR status;
- source type.

---

### 3. SetFit

SetFit should be treated as a distinct path rather than merely another classifier head.

Typical pipeline:

```text
labeled decision examples
        ↓
fine-tuned sentence transformer
        ↓
task-specific embedding space
        ↓
small classifier head
```

Unlike Model2Vec + classifier, SetFit changes the representation itself so that the embedding space becomes specialized for the Memory Seed labels.

Potential heads include:

- logistic regression;
- linear classifier;
- SVM;
- small neural classifier.

A useful tournament configuration is:

```text
SetFit encoder + linear/logistic head
```

This keeps the comparison clean.

---

### 4. Laya — Zero-Shot / General

Use Laya without Memory Seed-specific training as a general decision model.

Example tasks:

- topic classification;
- relationship classification;
- ADR significance;
- core-story relevance;
- support/contradiction classification;
- confidence scoring.

This tests whether a general typed-decision model performs sufficiently well without domain training.

---

### 5. Laya — Memory Seed Fine-Tuned

Fine-tune Laya on the existing curated corpus.

This is strategically important because the Memory Seed corpus is already close to the ideal training structure:

```text
state/context
+
typed question
+
known-good decision
```

A fine-tuned Laya model could become a specialist decision engine for Memory Seed.

---

### 6. Jev

Jev should remain in the tournament as the general decision-model baseline.

Its value proposition is different from the specialist models:

- generalized decision capability;
- no Memory Seed-specific training required;
- typed questions;
- probability outputs;
- useful benchmark for how far a general decision model can go.

The key question is not whether Jev is strong in general.

The relevant questions are:

> Can a generalized decision model outperform a specialist trained on Memory Seed's own curated decision history?

> More importantly for a hosted product: can a specialist trained on Memory Seed tasks generalize to a completely unseen project and ontology without retraining?

---

### 7. Optional Small LLM Baseline

A small inexpensive LLM through OpenRouter can act as an escalation/reference baseline.

This is useful because it measures whether dedicated classifiers are actually preserving enough semantic nuance.

Example:

```text
retrieved decision context
        ↓
small LLM
        ↓
structured JSON classification
```

This should not automatically become the production path. It exists to measure the value lost or gained by using specialist decision models.

## Tasks to Benchmark

The tournament should not use a single aggregated label. Each decision task should be evaluated independently.

Recommended tasks:

### Topic Assignment — Dynamic User Ontology

Topic assignment is not a normal fixed-label classification problem. Each project/user may define a different hierarchy of Areas and Activities, and a decision may require one Area plus one or more Activities.

The benchmark must therefore distinguish:

- **fixed-label topic classification** — useful only as a project-specific baseline;
- **candidate-conditioned ontology selection** — given the current project's topic names, descriptions and hierarchy, select the best Area and Activity candidate(s).

Jev is particularly relevant here because the candidate set can be supplied at inference time rather than baked into a fixed classifier head. Laya should be tested in the same candidate-conditioned form. A project-specific Logistic Regression/XGBoost classifier may still score highly on one corpus, but that result must not be mistaken for cross-project transferability.

### Relationship Classification

Predict relationships such as:

- supersedes;
- evolved_from;
- supports;
- contradicts;
- related;
- unrelated.

### ADR Significance

Predict whether a decision is architecturally significant enough to:

- create an ADR;
- amend an ADR;
- remain an ordinary decision.

### Storyline Relevance

Given a candidate node in a decision lineage, classify:

- critical path;
- supporting context;
- peripheral branch.

### Retrieval Relevance

Given a query/task and candidate decision, estimate whether that decision materially contributes to the current task.

### Governance Alignment

Estimate whether a decision appears aligned with:

- active ADRs;
- Constitution;
- known project constraints.

Governance alignment should initially be treated conservatively and should escalate uncertain or high-impact cases.


## Task Taxonomy: Fixed Schema vs Dynamic Schema

Do not force one model family across every Memory Seed decision task.

### Fixed-schema tasks

These use a stable label space across projects and are strong candidates for conventional supervised classifiers:

- relationship type (`supersedes`, `evolved_from`, `supports`, `contradicts`, etc.);
- ADR significance class;
- storyline role (`core`, `supporting`, `peripheral`);
- retrieval relevance bands;
- governance routing class.

For these tasks, Model2Vec + Logistic Regression, Model2Vec + XGBoost and SetFit may be extremely competitive.

### Dynamic-schema tasks

These depend on user/project state supplied at inference time:

- selecting an Area from the project's current Areas;
- selecting one or more Activities from the project's current Activities;
- respecting a project-specific topic hierarchy;
- choosing among newly created topic candidates the model never saw during training.

These tasks favor a **candidate-conditioned decision engine** such as Jev, Laya, or a future compatible model. The model should reason over the supplied ontology rather than memorize a fixed label vocabulary.

This distinction is important for product architecture: a model can be excellent on one user's fixed topic labels and still be unsuitable for a hosted Memory Seed service.

## Dataset Construction

Use already curated historical decisions.

Each example should preserve the information that would realistically be available at inference time.

Avoid leakage.

For example, when predicting a topic for Decision D100, do not expose metadata created after D100 if the production classifier would not have that information.

A training record might contain:

```yaml
decision_id: D100
text: ...
reason: ...
alternatives: ...
timestamp: ...
files: ...
candidate_topics:
  - retrieval
  - storage
  - curator
gold_topic: retrieval
```

For link classification:

```yaml
source_decision: D100
candidate_decision: D084
source_context: ...
candidate_context: ...
gold_relationship: supersedes
```

## Temporal Validation

A normal random train/test split is useful, but it is not sufficient.

Memory Seed should also use a temporal holdout.

Example:

```text
older decisions → training
newer decisions → validation/test
```

This answers a much more realistic question:

> If this model had existed at the time, would it have correctly classified the decisions that came later?

Recommended evaluation:

1. random stratified holdout;
2. temporal holdout;
3. difficult-disagreement set;
4. manually reviewed edge cases.


## Cross-Project Generalization Test

Cross-project transfer is a first-class success criterion, not an optional extra.

A Laya fine-tune should not primarily learn labels such as `retrieval`, `storage`, or `curator`. Instead, train the abstract task:

```text
decision/context
+ candidate topic names
+ candidate descriptions
+ hierarchy / parent relationships
→ best Area + best Activity candidate(s)
```

Evaluation should include:

1. **within-project holdout** — ordinary test split;
2. **temporal holdout** — later decisions unseen during training;
3. **ontology perturbation** — reorder candidates, rename IDs, add distractors, vary hierarchy depth;
4. **leave-one-project-out** — train on several projects and evaluate on an entirely unseen project/ontology;
5. **zero-shot new-topic test** — include valid candidate topics never observed during training.

The critical product metric is the final two tests.

If a fine-tuned Laya model performs well only on the project it was trained on, it is a project-specific specialist, not a reusable Memory Seed decision service. In that case Jev or another generalized candidate-conditioned model remains preferable for dynamic ontology tasks.

## Metrics

Do not select a winner using accuracy alone.

Track:

- accuracy;
- macro F1;
- per-class precision;
- per-class recall;
- confusion matrix;
- probability calibration;
- Brier score;
- expected calibration error;
- abstention performance;
- latency per decision;
- throughput;
- memory footprint;
- cold-start latency;
- retraining cost;
- operational complexity.

## Confidence and Abstention

A production classifier should be allowed to say:

```text
I am not confident enough to decide.
```

For each model, measure performance at thresholds such as:

- 70%;
- 80%;
- 90%;
- 95%.

This produces a coverage-versus-accuracy curve.

Example:

```text
95% confidence threshold
→ 68% of decisions automated
→ 98.7% accuracy on those automated decisions
→ remaining 32% escalated
```

This may be much more useful than maximizing raw accuracy.

## Tournament Output

For each task, produce a result table like:

| Model | Accuracy | Macro F1 | ECE | p95 Latency | Coverage @ 95% confidence |
|---|---:|---:|---:|---:|---:|
| Model2Vec + LR | | | | | |
| Model2Vec + XGBoost | | | | | |
| SetFit | | | | | |
| Laya zero-shot | | | | | |
| Laya fine-tuned | | | | | |
| Jev | | | | | |
| Small LLM | | | | | |

There does not need to be one universal winner.

Memory Seed may use different models for different tasks.

Example:

```text
topic classification        → Model2Vec + LR
relationship classification → XGBoost
storyline relevance         → fine-tuned Laya
governance ambiguity        → LLM escalation
```

## Architectural Requirement

The decision engine must remain pluggable.

Suggested interface:

```python
class DecisionEngine:
    def classify(self, task, state, candidates):
        ...
```

Adapters can implement:

```text
Model2VecLogisticAdapter
Model2VecXGBoostAdapter
SetFitAdapter
LayaAdapter
JevAdapter
LLMAdapter
```

This prevents Memory Seed from coupling its architecture to whichever model happens to be fashionable today.

## Recommendation

Build the benchmark harness before making a model commitment.

The existing curated corpus is likely more strategically valuable than any generic benchmark because it allows Memory Seed to select its decision layer empirically and continuously re-evaluate it as models change.
