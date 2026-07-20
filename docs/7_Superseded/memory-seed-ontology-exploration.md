---
title: "Proposal: A Minimal Operational Ontology for Memory Seed"
date: "2026-07-18"
project: "memory-seed"
status: "superseded"
superseded_on: "2026-07-20"
superseded_by: "../4_Reference/INBOX-CAPABILITY-CROSSWALK.md"
---

# Proposal: A Minimal Operational Ontology for Memory Seed

**Status:** Explore further before promotion to ADR  
**Date:** 2026-07-18  
**Related documents:** [Index](memory-seed-ontology-evidence-set-index-exploration.md), [Evidence Model](evidence-model-and-packets-exploration.md), [Decision Supersession](decision-supersession-and-evolution-exploration.md)

## Summary

Memory Seed should define a small operational ontology that represents the project concepts on which users and agents must reason and act.

The ontology should not attempt to model every project fact. It should formalize only the entities and relationships required to:

- retrieve relevant project memory;
- distinguish documents from the decisions inside them;
- explain why decisions were made or changed;
- construct timelines and evidence trails;
- support predictable agent actions;
- power Memory Trace views without making the entry format excessively noisy.

## Problem

A file-oriented system can store useful information while leaving its meaning implicit. An agent may see an ADR, proposal, session entry, or comment, but still need to infer:

- which decision is being referenced;
- whether that decision is active;
- what evidence supports it;
- which later decision changed it;
- which topic or project area it affects;
- what actions are valid.

When these concepts remain implicit, retrieval becomes dependent on prose interpretation. This increases token use, ambiguity, and stochastic variation.

## Proposal

Define a minimal ontology consisting of first-class entities, typed relationships, core properties, and permitted actions.

The ontology should be independent of storage. Markdown and YAML may remain the source format, but they should serialize an underlying conceptual model.

## Design principles

1. **Model reality, not file layout.**  
   A decision is not the same thing as the ADR file containing it.

2. **Prefer a small stable core.**  
   New entity types require demonstrated retrieval, interface, governance, or automation value.

3. **Allow progressive formalization.**  
   Narrative content remains valid. Structure is added where it reduces ambiguity or decision effort.

4. **Make important references addressable.**  
   Agents should reference a specific decision, claim, evidence item, or section rather than a whole file when possible.

5. **Every formal relationship must enable an operation.**  
   A relationship should support retrieval, validation, navigation, access control, status resolution, or context assembly.

## Proposed core entities

| Entity | Purpose | Minimum identity |
|---|---|---|
| `Entry` | A recorded unit of project memory | Entry ID |
| `Decision` | A specific conclusion or constraint | Decision ID |
| `Evidence` | Support, contradiction, qualification, or observation | Evidence ID |
| `Topic` | A deterministic project neighbourhood | Topic ID or canonical name |
| `Artifact` | A referenced file, code location, issue, PR, diagram, or external source | Stable locator |
| `Actor` | A human, agent, team, or system participating in an action | Actor ID |
| `Claim` | A proposition that may require evidence | Claim ID, optional in the first implementation |
| `BenchmarkTask` | A repeatable question or task used to evaluate retrieval and reasoning | Task ID |

`Claim` and `BenchmarkTask` may initially remain implementation concepts rather than mandatory entry metadata.

## Proposed core relationships

| Relationship | Source → target | Meaning |
|---|---|---|
| `contains` | Entry → Decision | The entry records the decision |
| `supports` | Evidence → Decision or Claim | The evidence increases support |
| `contradicts` | Evidence → Decision or Claim | The evidence weakens or conflicts |
| `qualifies` | Evidence → Decision or Claim | The evidence narrows applicability |
| `supersedes` | Decision → Decision | A later decision replaces all or part of an earlier one |
| `updates` | Decision → Decision | A later decision modifies without fully replacing |
| `depends_on` | Decision → Decision or Artifact | The source requires the target |
| `relates_to` | Entry or Decision → Topic | Membership in a project neighbourhood |
| `derived_from` | Evidence → Artifact or Entry | Provenance of the evidence |
| `authored_by` | Entry or Decision → Actor | Primary authorship |
| `affected_by` | Decision → Evidence | Evidence contributed to a change |
| `evaluated_by` | Decision or retrieval policy → BenchmarkTask | Connects a design to its evaluation |

## Decision identity

An ADR may contain several conclusions. References should therefore resolve to a decision-level identifier.

Example:

```yaml
entry_id: adr-0042

decisions:
  - id: dec-0042-01
    title: Use Mermaid for overlapping diagram use cases
    status: active

  - id: dec-0042-02
    title: Reserve D2 for capabilities not adequately covered by Mermaid
    status: active
```

A later entry should reference `dec-0042-02`, not merely `adr-0042`, when only the second decision changes.

## Proposed actions

The ontology becomes operational when entities have valid actions.

| Action | Target | Intended effect |
|---|---|---|
| `promote` | Proposal or decision candidate | Changes lifecycle state after validation |
| `supersede` | Decision | Replaces a specified scope |
| `update` | Decision | Adds or modifies a limited aspect |
| `attach_evidence` | Decision or claim | Adds traceable support or contradiction |
| `validate_topics` | Entry or repository | Confirms topic membership against the topic index |
| `assemble_context` | Task, decision, or topic | Produces a deterministic evidence packet |
| `trace` | Decision | Returns predecessors, successors, evidence, and affected artifacts |
| `challenge` | Decision or claim | Records a structured objection or conflicting evidence |

## Minimal serialization example

```yaml
entry_id: session-2026-07-18-jean-01
type: research-and-planning
topics:
  - ontology
  - retrieval
  - benchmarking

decisions:
  - id: dec-2026-07-18-01
    title: Treat evidence as a first-class concept
    status: candidate
    relationships:
      supports:
        - ev-2026-07-18-01
      relates_to:
        - ontology
        - retrieval
```

The first implementation should avoid repeating information that can be inferred reliably from file structure or indexes.

## Ontology boundary

The ontology should include a concept only when at least one of the following is true:

- users need to search or filter by it;
- the system must validate it;
- an agent must take a distinct action on it;
- it affects permissions or lifecycle;
- it is needed to assemble context;
- it is required to explain decision history;
- it appears in a benchmark.

This boundary prevents the ontology from becoming a comprehensive but unusable model of the project.

## Expected benefits

### More reliable references

Specific decisions and evidence can be cited without ambiguity.

### Storage independence

Markdown layout, sidecars, indexes, or future databases can evolve without changing the conceptual contract.

### Deterministic retrieval

Retrieval can follow typed relationships rather than relying entirely on semantic similarity.

### Better Memory Trace interfaces

Trail, graph, topic neighbourhoods, and evidence views can share one model.

### Safer agent action

Agents can understand which actions are valid for proposals, decisions, evidence, and superseded records.

## Trade-offs

| Trade-off | Consequence |
|---|---|
| More structure | Additional authoring and validation work |
| Stable IDs | Identity-management requirements |
| Typed relationships | Schema evolution and migration |
| Explicit lifecycle | More rules for agents to follow |
| Storage independence | Need for a resolver layer between YAML and domain objects |

## Risks and mitigations

### Risk: Ontology inflation

**Mitigation:** require an operational justification for every entity and relationship.

### Risk: Entry noise

**Mitigation:** keep the mandatory core minimal and allow generated or sidecar metadata where appropriate.

### Risk: Ontology becomes a second source of truth

**Mitigation:** define canonical ownership of each field and generate derived views where possible.

### Risk: Agents produce structurally valid but semantically weak links

**Mitigation:** benchmark relationship precision and require evidence for high-impact changes.

## Questions for exploration

1. Should `Decision` be mandatory for all decision-bearing entries or only ADRs and decision updates?
2. Which relationships must be explicit, and which may be inferred?
3. Should evidence be embedded, sidecar-based, or hybrid?
4. How should partial supersession be represented?
5. Which lifecycle states are genuinely necessary?
6. Which ontology elements should appear in the entry YAML versus generated indexes?

## Recommended prototype

Model ten existing project entries using only:

- Entry
- Decision
- Evidence
- Topic
- Artifact
- `contains`
- `supports`
- `supersedes`
- `relates_to`
- `derived_from`

Measure:

- metadata added per entry;
- unresolved ambiguity;
- retrieval usefulness;
- ability to render a decision trail;
- authoring corrections required.

## Promotion criteria

Promote this proposal to an ADR only if:

1. The minimal model represents at least three different workflows without adding ad hoc fields.
2. Decision-level references materially reduce ambiguity.
3. The ontology enables at least one useful deterministic retrieval operation.
4. The metadata burden is acceptable.
5. The same ontology supports both CLI/MCP behaviour and Memory Trace presentation.
