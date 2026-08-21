# Proposal: Semantic Compression Benchmark

## Objective

Investigate whether Memory Seed decisions can be reduced into a small,
explicit representation of their core meaning that improves:

1.  comprehension,
2.  retrieval,
3.  relationship detection,
4.  context/token efficiency,

without introducing unnecessary semantic infrastructure.

This is an **experimental investigation first**, not a request to
implement a production semantic sidecar.

The central question is:

> What is the minimum semantic structure required to preserve or improve
> understanding of a Memory Seed decision while reducing the amount of
> context an agent must consume?

------------------------------------------------------------------------

## 1. Motivation

Memory Seed stores human-readable prose describing decisions,
observations, reasoning, and project history.

Prose is useful as canonical evidence, but it may be an inefficient
representation for machine retrieval and reasoning.

For example:

> We should move topic generation into a post-hoc sidecar because topics
> are derived metadata and we don't want ontology changes modifying
> canonical entries.

The underlying meaning can potentially be represented much more
compactly:

``` yaml
meaning:
  core: "Topic generation should happen post-hoc."
  because: "Topic assignments evolve over time."
  constraint: "Canonical entries should not be modified."
```

This representation may provide a cleaner substrate for retrieval and
reasoning while retaining the original prose as canonical evidence.

However, do not assume this representation is beneficial.

The purpose of this work is to **measure whether semantic compression
produces enough benefit to justify its complexity.**

------------------------------------------------------------------------

## 2. Research Questions

Primary question:

> Can a compact representation of a decision's meaning provide equal or
> better task performance than the original prose while using less
> context?

Secondary question:

> If semantic decomposition is useful, what is the smallest
> representation that captures most of the benefit?

We explicitly want to avoid building a sophisticated semantic system if
something much simpler provides equivalent performance.

------------------------------------------------------------------------

## 3. Core Principle

Treat the original Memory Seed entry as canonical evidence.

Any semantic representation must initially be:

-   derived,
-   regenerable,
-   non-canonical,
-   attributable to its source,
-   independently evaluable.

Do not modify the canonical entry format as part of this experiment.

If the concept proves useful, it may eventually become a derived
sidecar.

``` mermaid
graph TD
    A[Canonical Decision] -->|derive| B[Meaning Representation]
    B --> C[Retrieval]
    B --> D[Reasoning]
    B --> E[Relationship Detection]
    B --> F[Context Construction]
```

------------------------------------------------------------------------

## 4. Representations to Compare

Create an ablation experiment. Each source decision should have several
progressively richer representations.

### A --- Raw

Original decision/prose. This is the control.

### B --- Core

One sentence expressing the central proposition.

``` yaml
core: "Topic generation should happen post-hoc."
```

The sentence should answer:

> What is actually being asserted, decided, observed, or proposed?

### C --- Core + Why

``` yaml
core: "Topic generation should happen post-hoc."
because: "Topic assignments evolve over time."
```

### D --- Core + Why + Constraint

``` yaml
core: "Topic generation should happen post-hoc."
because: "Topic assignments evolve over time."
constraint: "Canonical entries should not be modified."
```

This is currently the leading candidate for a minimal **Meaning
Sidecar**.

### E --- Structured Semantic Representation

Only investigate this richer representation as an experimental upper
bound.

``` yaml
meaning:
  propositions:
    - subject: topics
      relation: are
      object: derived_metadata

    - subject: ontology
      relation: changes
      qualifier: over_time

    - subject: topic_generation
      relation: should_live_in
      object: sidecar

  relations:
    - source: topics_are_derived_metadata
      type: supports
      target: topic_generation_should_live_in_sidecar
```

Do not over-engineer this schema. Its purpose is to establish whether
deeper semantic decomposition produces material additional benefit over
B--D.

------------------------------------------------------------------------

## 5. Relevant Research

Before designing the experiment, perform a focused literature and
implementation review of:

-   Semantic Role Labeling
-   Open Information Extraction / proposition extraction
-   atomic fact decomposition
-   argument mining
-   Rhetorical Structure Theory
-   Discourse Representation Theory
-   controlled natural languages
-   Subject--Action--Object representations
-   Natural Semantic Metalanguage
-   Theme/Rheme and information structure
-   LLM claim decomposition
-   knowledge graph proposition extraction

The goal is not to reproduce these systems.

Determine what practical lessons they provide for extracting compact
meaning from Memory Seed decisions.

For each method document:

-   what it extracts,
-   advantages,
-   limitations,
-   implementation complexity,
-   relevance to Memory Seed.

Prefer recent practical approaches where appropriate.

------------------------------------------------------------------------

## 6. Dataset

Use existing Memory Seed decisions as the evaluation corpus.

Identify approximately **100 representative decisions** if sufficient
data exists.

The sample should deliberately contain variation:

-   short decisions,
-   long decisions,
-   conversational decisions,
-   highly technical decisions,
-   decisions with explicit rationale,
-   decisions with implicit rationale,
-   decisions containing constraints,
-   related decisions,
-   superseded decisions,
-   contradictory/evolving decisions,
-   decisions requiring surrounding context to understand.

Do not simply select the easiest examples.

Record the selection methodology so the experiment is reproducible.

------------------------------------------------------------------------

## 7. Evaluation Tasks

Evaluate every representation against the same tasks.

### 7.1 Comprehension

Given the representation, ask questions about the original decision.

Examples:

-   What was decided?
-   Why was it decided?
-   What constraint influenced the decision?
-   What component is affected?
-   What behaviour should change?

Measure:

-   answer accuracy,
-   missing information,
-   hallucinated information.

Where possible, create reference answers from the canonical decision.

### 7.2 Retrieval

Create queries whose correct answer requires retrieving particular
historical decisions.

Compare retrieval using:

-   Raw
-   Core
-   Core + Why
-   Core + Why + Constraint
-   Structured semantics

Use the retrieval mechanisms already available or appropriate within
Memory Seed.

Measure where applicable:

-   Recall@K
-   Precision@K
-   MRR
-   nDCG

Do not change unrelated retrieval infrastructure merely to favour the
semantic representation.

### 7.3 Relationship Detection

Test whether representations improve identification of relationships
between decisions.

Relevant relationships include:

-   `supports`
-   `depends_on`
-   `contradicts`
-   `supersedes`
-   `evolves`
-   `related`

Use existing known relationships where available.

Measure:

-   precision,
-   recall,
-   F1,
-   false-positive rate.

Pay particular attention to decisions that express similar meaning using
different vocabulary.

Example:

> A: Canonical entries should remain immutable.

> B: Generated metadata must not alter source entries.

Semantic representations should theoretically make this relationship
easier to identify. Verify whether this actually happens.

### 7.4 Context Efficiency

Measure how much context is required to achieve useful task performance.

Record:

-   input tokens,
-   output tokens,
-   task accuracy.

Example:

  Representation              Input Tokens   Accuracy
  ------------------------- -------------- ----------
  Raw                                3,000       0.90
  Core                                 500       0.80
  Core + Why                           700       0.88
  Core + Why + Constraint              850       0.91
  Structured                         1,200       0.92

The numbers above are illustrative only.

Do not assume the semantic representations will win.

------------------------------------------------------------------------

## 8. Context Efficiency Metric

Explore a normalized measure conceptually equivalent to:

``` text
Context Efficiency = Task Performance / Context Consumed
```

The exact formulation should be chosen carefully because raw
accuracy/tokens may produce misleading values.

Investigate suitable normalization.

The goal is to answer:

> How much useful reasoning performance are we obtaining per unit of
> context?

Report both the composite metric and its underlying measurements so the
composite cannot hide regressions.

------------------------------------------------------------------------

## 9. Benefit vs Complexity

This is the primary decision criterion.

For every representation, estimate:

-   performance benefit,
-   token benefit,
-   generation cost,
-   storage cost,
-   implementation complexity,
-   maintenance complexity,
-   interpretability,
-   failure modes.

Then construct a **Benefit / Complexity frontier**.

We are looking for the elbow.

If `Core + Why` captures 95% of the measurable benefit of the structured
semantic representation, prefer `Core + Why`.

**Complexity must earn its existence.**

------------------------------------------------------------------------

## 10. Failure Analysis

Do not report only aggregate scores.

Identify cases where semantic compression removes important information.

Specifically investigate:

-   qualifiers disappearing,
-   uncertainty becoming certainty,
-   scope being lost,
-   temporal information disappearing,
-   causal relationships being invented,
-   multiple propositions being collapsed incorrectly,
-   agent-generated summaries subtly changing meaning,
-   domain terminology being oversimplified,
-   contradictions being hidden,
-   rationale being confused with evidence.

Semantic compression that makes information shorter but changes its
meaning is a failure.

------------------------------------------------------------------------

## 11. Semantic Fidelity

Introduce an explicit fidelity check.

For every derived representation ask:

> Could a reasonable reader infer something from this representation
> that is not supported by the source?

and:

> Did the representation remove information required to correctly
> understand the decision?

Track:

-   unsupported additions,
-   meaning omissions,
-   changed modality,
-   changed certainty,
-   changed scope,
-   changed causality.

Semantic fidelity should be treated as a hard constraint rather than
merely another optimization metric.

------------------------------------------------------------------------

## 12. Architecture Constraint

Do not introduce this into canonical Memory Seed architecture during the
experiment.

Keep experimental outputs isolated.

If successful, the eventual architecture may resemble:

``` text
decision.md
    |
    +-- topics sidecar
    +-- links sidecar
    +-- ADR sidecar
    +-- meaning sidecar
```

But this proposal does **not** authorize implementation of that
architecture.

The experiment must establish whether the sidecar deserves to exist
first.

------------------------------------------------------------------------

## 13. Key Decision

The final report must explicitly answer:

> Does Memory Seed benefit enough from a derived meaning representation
> to justify adding one?

If yes:

> What is the minimum representation that captures most of the
> measurable benefit?

Possible outcomes include:

-   A. No semantic layer required.
-   B. Core sentence only.
-   C. Core + rationale.
-   D. Core + rationale + constraint.
-   E. Rich proposition representation.
-   F. Different representation discovered during research.

Outcome A is a completely valid result.

Do not bias the investigation toward implementation.

------------------------------------------------------------------------

## 14. Deliverables

Create an isolated research area following existing repository
conventions.

At minimum produce:

``` text
README.md
research.md
experiment-design.md
results.md
recommendation.md
```

Also include experimental scripts/data where appropriate.

### README.md

Explain:

-   hypothesis,
-   research question,
-   experiment,
-   current status.

### research.md

Summarize relevant semantic decomposition approaches and their
applicability to Memory Seed.

### experiment-design.md

Define:

-   dataset selection,
-   representations,
-   evaluation tasks,
-   metrics,
-   controls,
-   model configuration,
-   reproducibility methodology.

### results.md

Contain actual measured results.

Prefer tables and plots over qualitative descriptions.

### recommendation.md

Give a direct recommendation:

``` text
BUILD
BUILD MINIMAL VERSION
INVESTIGATE FURTHER
DO NOT BUILD
```

Explain the evidence supporting the recommendation.

------------------------------------------------------------------------

## 15. Experimental Discipline

Control variables wherever possible.

Use:

-   the same source decisions,
-   the same queries,
-   the same evaluation questions,
-   the same retrieval configuration,
-   the same model where comparisons require a model,
-   fixed seeds where applicable,
-   recorded prompts,
-   recorded model/version information.

Separate **representation improvement** from **model improvement**.

We need to know whether the representation itself provides value.

------------------------------------------------------------------------

## 16. Repository Investigation First

Before creating implementation code:

1.  inspect the current Memory Seed repository,
2.  understand the entry/decision schema,
3.  inspect existing sidecars,
4.  inspect retrieval architecture,
5.  inspect linking/relationship functionality,
6.  inspect existing benchmarks/experiments,
7.  identify reusable infrastructure,
8.  identify architectural conflicts with this proposal.

Do not duplicate existing mechanisms.

Document anything already present that overlaps with this concept.

------------------------------------------------------------------------

## 17. Scope Guardrail

Avoid turning this into a general-purpose knowledge representation
project.

The question is deliberately narrow:

> Can Memory Seed represent the meaning of its decisions more compactly
> and explicitly in a way that measurably improves downstream use?

Do not introduce:

-   a new ontology system,
-   a general knowledge graph framework,
-   a custom semantic language,
-   complex reasoning engines,
-   production migrations,

unless experimental evidence demonstrates that they are necessary.

Prefer the smallest thing that works.

------------------------------------------------------------------------

## 18. Initial Execution Plan

### Phase 1 --- Repository audit

Understand what Memory Seed already provides.

### Phase 2 --- Focused research

Investigate existing semantic decomposition approaches.

### Phase 3 --- Dataset construction

Select representative decisions and establish reference data.

### Phase 4 --- Representation generation

Generate A--E representations.

### Phase 5 --- Benchmark

Run comprehension, retrieval, relationship and context-efficiency
experiments.

### Phase 6 --- Ablation analysis

Determine which semantic fields actually contribute useful performance.

### Phase 7 --- Failure analysis

Examine semantic distortion and information loss.

### Phase 8 --- Recommendation

Identify the minimum viable representation, or conclude that no semantic
sidecar is justified.

------------------------------------------------------------------------

## Success Criterion

This investigation succeeds even if the conclusion is:

> Do not build this.

The desired output is evidence about whether explicit semantic
compression improves Memory Seed.

The ideal result is not the richest semantic representation.

It is:

> **The smallest representation that preserves meaning while producing a
> measurable improvement in how efficiently humans or agents can
> retrieve, understand, and reason over Memory Seed decisions.**
