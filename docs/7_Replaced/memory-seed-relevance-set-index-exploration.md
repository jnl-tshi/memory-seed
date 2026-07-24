---
title: "Memory Seed Relevance and Deterministic Agent Behaviour"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
replaced_on: "2026-07-20"
replaced_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Memory Seed Relevance and Deterministic Agent Behaviour

> **Pre-triage correction (2026-07-18):** Treat this set as a hypothesis library, not an integrated
> implementation programme. See [`../INBOX-ASSESSMENT.md`](../4_Reference/INBOX-ASSESSMENT.md). Existing narrow sidecar
> contracts and append-only Markdown authority remain binding; a common manifest may only be a rebuildable
> coverage projection. Mandatory intent metadata, historical backfill, and constitutional wording require
> separate evidence and approval.

**Status:** Initial proposal set  
**Scope:** Memory Seed and Memory Trace  
**Purpose:** Establish a coherent architecture for relevance, high-signal knowledge lenses, and consistent behaviour across different LLM providers.

## Executive summary

Memory Seed already has several mechanisms for reducing the cost of recovering project context:

- the canonical entry timeline answers **what happened**;
- topic, semantic, lexical, recency, and importance signals help find likely relevant entries;
- derived relationship edges expose provenance, evolution, replacement, and supersession;
- ADR sidecars expose architecturally significant decisions;
- diagram sidecars expose visual representations for human review.

The next architectural step is not to add an ontology for every possible relationship. It is to formalise a smaller, more practical principle:

> When an agent repeatedly has to infer the same useful property from the timeline, that property is a candidate for either first-class metadata or a derived lens.

This proposal set separates that idea into five documents:

1. **Constitutional principles**  
   Defines the system-level principles that should guide future design decisions.

2. **Lens and sidecar architecture**  
   Defines what a lens is, when it belongs in metadata, when it belongs in a sidecar, and how it relates to the canonical timeline.

3. **Deterministic sidecar generation and reconciliation**  
   Defines how Memory Seed can achieve minimum acceptable behaviour across stochastic and vendor-diverse agents.

4. **Entry intent metadata and branch lifecycle**  
   Defines a controlled intent field that records why an entry exists and makes branch progress and missing work queryable.

5. **High-signal lens roadmap**  
   Evaluates additional lenses that could reduce repeated inference and improve future decisions.

## Recommended reading order

1. `01-constitutional-principles-for-deterministic-agent-systems.md`
2. `02-sidecar-lens-architecture.md`
3. `03-deterministic-sidecar-generation-and-reconciliation.md`
4. `04-entry-intent-metadata-and-branch-lifecycle.md`
5. `05-high-signal-knowledge-lenses-roadmap.md`

## Core terminology

### Canonical timeline

The append-only sequence of Memory Seed entries. It is the primary historical record and the source of truth for what occurred.

### Entry metadata

Information known or intentionally declared when an entry is written. Examples include author, timestamp, branch, topics, intent, and explicitly recorded relationships.

### Lens

A focused representation of timeline evidence designed to answer a recurring question with less retrieval and reasoning effort.

A lens is justified when it removes a repeated inference that humans or agents would otherwise have to perform.

### Sidecar

A separately stored representation linked to one or more canonical entries. A sidecar may be generated at write time or retroactively, but it must preserve traceability to its supporting evidence.

### Transformation

A process that creates, updates, validates, promotes, or reconciles a representation.

Examples include:

- ADR extraction;
- diagram generation;
- relationship derivation;
- validation of sidecar coverage;
- promotion of an inferred relationship into an authoritative relationship.

### Declared knowledge

Knowledge asserted at the point of writing by the actor performing the work. It belongs in canonical metadata when practical.

### Derived knowledge

Knowledge inferred, aggregated, visualised, or discovered from existing entries. It normally belongs in a sidecar until explicitly promoted.

## Architectural summary

The proposal set recommends the following split:

| Information | Preferred location | Reason |
|---|---|---|
| Author, time, branch, topics | Entry metadata | Known at write time |
| Work intent | Entry metadata | Declared by the actor performing the work |
| Explicit `evolves` relationship | Entry metadata | Authoritative relationship known when written |
| `evolved-by`, `superseded-by`, `replaced-by` | Derived relationship sidecar | Reverse or inferred relationships |
| ADR representation | ADR sidecar | High-signal derived view over one or more entries |
| Mermaid or other diagram | Diagram sidecar | Alternate visual representation |
| Assumptions, open questions, tensions | Candidate sidecars | Derived and potentially retroactive |
| Branch lifecycle status | Computed view | Inferred from the sequence of declared entry intents |

## Recommended implementation order

1. Adopt the constitutional principles.
2. Document the metadata-versus-sidecar decision rule.
3. Add controlled entry intent metadata.
4. Define sidecar eligibility contracts.
5. Add sidecar manifests and coverage auditing.
6. Add reconciliation and provider conformance tests.
7. Pilot one additional lens before expanding the lens catalogue.

## Explicit non-goals

This proposal set does not recommend:

- constructing a comprehensive project ontology;
- forcing every branch through an identical workflow;
- generating every possible sidecar for every entry;
- treating generated sidecars as independent sources of truth;
- requiring agents to infer intent that the author can declare directly;
- replacing semantic or lexical retrieval with graph traversal.

The intended architecture is layered rather than exclusive: lexical, semantic, metadata, graph, and lens-based retrieval should reinforce one another.
