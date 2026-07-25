---
title: "Proposal: Information-Theoretic Evolution of Memory Seed"
date: "2026-07-25"
project: "memory-seed"
status: "superseded"
replaced_on: "2026-07-25"
replaced_by: "../4_Reference/information-theoretic-evolution-disposition.md"
---

# Proposal: Information-Theoretic Evolution of Memory Seed

> Retired on arrival, 2026-07-25: dispositioned through the same crosswalk discipline as the
> 2026-07-20 inbox sets (see `replaced_by`). The text below is the proposal as received, verbatim.

## Purpose

This proposal describes a set of architectural refinements for Memory Seed inspired by information theory, graph theory, and knowledge representation. These ideas are intended as design lenses rather than strict algorithms.

---

# Core Design Principles

These principles should become architectural constraints that every future component follows.

1. Every layer should reduce future uncertainty while preserving reconstructability.
2. Confidence must come from deterministic evidence, not model intuition.
3. Every derived artifact must preserve provenance back to the originating entries.
4. Compress aggressively, expand only when necessary.
5. Prefer deterministic heuristics over probabilistic intuition whenever evidence is available.
6. Information should always become progressively higher signal as it moves upward through the system.

---

# Knowledge Hierarchy

Rather than viewing sidecars as independent processors, they can be viewed as progressively higher abstraction layers.

```text
Raw Session

        │
        ▼

Individual Entries
(atomic observations)

        │
        ▼

Topics
(group related decisions)

        │
        ▼

Architectural Decision Records (ADRs)
(compressed architectural knowledge)

        │
        ▼

Constitution
(project-wide architectural principles)
```

Each level is a compressed representation of the level beneath it while remaining reconstructable.

---

# Information Theory

## Entropy

Entropy measures uncertainty.

Within Memory Seed, entropy can be viewed as:

> "How uncertain is the system about which previous knowledge is relevant?"

A useful edge is one that significantly reduces this uncertainty.

Rather than asking:

> Are these entries similar?

The system instead asks:

> Does this relationship meaningfully reduce uncertainty during future retrieval?

---

## Redundancy

Redundancy is often misunderstood as duplicated information.

Within information theory it is better thought of as **independent evidence**.

For Memory Seed this means:

- multiple entries independently support the same ADR
- different retrieval paths reach the same architectural conclusion
- losing one edge does not lose the knowledge

Healthy redundancy produces robustness rather than duplication.

---

## Channel Capacity

An LLM context window is effectively a communication channel.

The channel has limited capacity.

Every unnecessary token occupies bandwidth that could have contained higher-value information.

Therefore retrieval should aim to provide:

- the minimum sufficient context
- with the maximum explanatory power

The objective becomes:

> Maximise information per token.

---

## Minimum Description Length (MDL)

Minimum Description Length provides one of the strongest design principles for Memory Seed.

An ADR should be:

> The shortest description that still allows the original reasoning to be reconstructed.

An even more useful design heuristic is:

> If a summary does not reduce future uncertainty, it probably does not belong in long-term memory.

MDL therefore becomes both:

- a compression goal
- a quality metric

---

## Information Bottleneck Principle

The Information Bottleneck shifts the question from:

> How do I compress?

to

> What information is actually necessary?

Every retrieval stage should ask:

- Does this information change the answer?
- If not, discard it.

This naturally produces increasingly high-signal context.

---

## Knowledge Distillation

Knowledge distillation is closely related to ADR generation.

Rather than summarising text, the objective is to preserve decision-making ability.

A good ADR allows someone to reach the same architectural conclusion as reading every supporting entry.

The ADR therefore captures:

- reasoning
- trade-offs
- architectural implications

while remaining dramatically smaller than the underlying evidence.

---

# Graph Theory

## Centrality

Centrality measures importance within a graph.

Different centrality metrics reveal different kinds of importance.

### Degree Centrality

Measures the number of direct connections.

Useful for identifying local hubs.

---

### Betweenness Centrality

Measures how often a node lies on shortest paths.

Useful for identifying bridge nodes that connect otherwise separate areas of knowledge.

---

### Closeness Centrality

Measures how quickly a node can reach every other node.

Useful for finding highly accessible knowledge.

---

### Eigenvector Centrality / PageRank

Measures influence.

Connections to important nodes increase importance.

This is particularly useful for ADRs.

---

## Proposed Graph Layout

Instead of a single global force-directed graph:

- ADRs become local gravitational centres.
- Decisions cluster around ADRs.
- Topics create higher-level neighbourhoods.
- Constitution principles sit above ADRs as the highest abstraction layer.

Centrality should influence:

- node size
- gravitational pull
- visual prominence

rather than absolute positioning alone.

---

# Deterministic Confidence

Confidence should never be based upon model intuition.

Confidence should instead be computed from independent deterministic evidence.

Example heuristic:

| Evidence | Score |
|-----------|------:|
| Semantic similarity | 1 |
| Shared topic | +1 |
| Shared files | +1 |
| Explicit reference | +1 |
| Shared ADR | +1 |
| Human confirmation | +2 |

The important property is not the exact numbers.

The important property is:

- deterministic
- reproducible
- explainable

Every confidence score should be inspectable.

The system should always be able to explain:

> "This relationship received a confidence of 5 because it shared two files, one topic, and contained an explicit reference."

Avoid double-counting correlated evidence.

Independent evidence should contribute independently.

---

# Sidecars as Information Lenses

Rather than viewing sidecars as utilities, they can be viewed as information-processing lenses.

## Extraction

Extract latent structure.

Examples:

- Topics
- Links

Question:

> What relationships exist?

---

## Compression

Create higher-order knowledge.

Example:

- ADRs

Question:

> What is the smallest representation that preserves architectural understanding?

---

## Representation

Improve human understanding.

Example:

- Diagrams

Question:

> How can this knowledge be understood more quickly?

---

## Governance

The Constitution becomes the governing layer.

Rather than being automatically modified:

- recurring ADR patterns generate proposals
- proposals are reviewed
- accepted proposals evolve the Constitution

The Constitution therefore remains a deliberate architectural document rather than an automatically changing summary.

---

# Information Gain

One useful future metric is **Information Gain**.

Each sidecar should justify its existence by reducing uncertainty.

Questions to ask:

- Did this generated edge improve retrieval?
- Did this ADR eliminate ambiguity?
- Did this topic reduce search space?
- Did this diagram improve comprehension?

If the answer is no, the artifact should not exist.

---

# Provenance

Every derived artifact must retain complete provenance.

Nothing should become detached from its evidence.

Every:

- edge
- topic
- ADR
- diagram
- constitutional proposal

should always be traceable back to the entries that produced it.

This preserves explainability while making future refinement deterministic.

---

# Summary

Memory Seed can be viewed as a progressive knowledge refinement pipeline.

```text
Evidence
        │
        ▼
Relationships
        │
        ▼
Topics
        │
        ▼
Architectural Decisions
        │
        ▼
Constitution
```

Each layer should:

- reduce uncertainty
- increase information density
- preserve provenance
- remain reconstructable

This becomes the guiding philosophy for the entire system.

> **Every layer should reduce future uncertainty while preserving reconstructability.**

This single principle captures the essence of the information-theoretic approach to Memory Seed.
