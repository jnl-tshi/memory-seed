---
title: "Initial Proposal: Memory Signal Hierarchy"
status: "superseded"
replaced_by: "../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md"
replaced_on: "2026-07-16"
---

# Initial Proposal: Memory Signal Hierarchy

**Status:** Superseded 2026-07-16
**Superseded by:** [`memory-seed-semantic-record-and-signal-foundation-plan.md`](../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md)
**Related systems:** Retrieval, MCP context collection, Memory Trace, entry types, topics

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## 1. Summary

This proposal explores whether Memory Seed should use entry type, status, verification, and topic relevance to prioritise project memory.

The core hypothesis is:

> Agents should begin with compact, authoritative, high-signal memory and expand into detailed chronological evidence only when necessary.

Mandatory entry types create the basis for this hierarchy, but the ranking logic has not yet been designed or validated.

## 2. Problem

A chronological memory system can accumulate many useful entries while still becoming difficult to retrieve from efficiently.

Without signal-aware retrieval:

- accepted decisions may be buried beneath routine session logs
- research conclusions may be mixed with speculative notes
- agents may spend tokens re-reading low-value context
- obsolete decisions may be retrieved alongside active ones
- a topic match may be treated as equally important regardless of entry purpose
- Trace may present all related records with no meaningful priority

This is not primarily a storage problem. It is a context-selection problem.

## 3. Proposed Direction

Memory Seed could define a retrieval hierarchy using a small number of explicit signals:

- entry `type`
- ADR status
- verification state where applicable
- topic match
- relationship distance
- recency
- supersession or invalidation state
- direct relevance to the active artifact or component

A possible conceptual order is:

```text
accepted ADRs
→ decision updates and verified findings
→ current research and planning
→ relevant handoffs
→ session logs
→ superseded, rejected, or invalidated material
```

This ordering must not be treated as universally correct. It is a starting hypothesis for testing.

## 4. Retrieval Model

A staged retrieval strategy could be:

### Stage 1: Governing context

Retrieve accepted ADRs and other authoritative entries matching the active topics.

### Stage 2: Explanatory context

Retrieve decision updates, verified findings, and research-planning entries linked to those decisions.

### Stage 3: Operational context

Retrieve handoffs and recent session logs related to the current task.

### Stage 4: Evidence expansion

Follow relationships into historical logs, rejected alternatives, superseded decisions, tests, and implementation artifacts only when required.

This provides progressive disclosure for project memory.

## 5. Authority Versus Relevance

The system must not conflate authority with relevance.

An accepted ADR may be authoritative but irrelevant to the current task. A recent session log may be highly relevant but not authoritative.

Retrieval should therefore consider at least two dimensions:

| Dimension | Question |
|---|---|
| Authority | How strongly should this record govern future work? |
| Relevance | How closely does this record match the current task? |

Additional dimensions may include freshness, verification, and relationship proximity.

## 6. Potential Ranking Inputs

Candidate deterministic inputs include:

```yaml
type: architecture-decision
status: accepted
topics:
  - retrieval
relationships:
  affects:
    - memory_seed/retrieval.py
```

Potential derived inputs include:

- exact topic overlap
- direct relationship to active file or component
- active versus superseded ADR
- verified versus unverified finding
- unresolved handoff
- age of session log
- number of relationship hops

Semantic similarity may still be used, but it should operate after deterministic filtering where possible.

## 7. Potential User Value

### Agents

- lower context consumption
- fewer repeated investigations
- more consistent adherence to current decisions
- better distinction between evidence and speculation

### Memory Trace users

- clearer ordering of relevant information
- high-signal summaries before chronological detail
- visible distinction between governing, supporting, and historical records

### Project maintainers

- easier detection of stale or contradictory context
- greater confidence in what agents are likely to retrieve

## 8. Risks

### Over-ranking ADRs

Not every task should begin with architecture decisions.

**Mitigation:** combine authority with task relevance rather than using a fixed global order.

### Hidden context

Aggressive ranking may suppress minority evidence or historical nuance.

**Mitigation:** make expansion paths explicit and preserve access to all underlying entries.

### False precision

A numerical score may imply more certainty than the underlying metadata supports.

**Mitigation:** prefer transparent ranking rules and reason labels over opaque scores.

### Type gaming

Agents might choose high-signal types to increase retrieval priority.

**Mitigation:** validate types and constrain promotion workflows.

### Premature taxonomy

The current type set may not be sufficient to support a robust hierarchy.

**Mitigation:** prototype with existing types before expanding the registry.

## 9. Questions Requiring Further Exploration

1. Which entry types should be treated as authoritative, supporting, operational, or historical?
2. Should ranking be global or query-specific?
3. How should rejected and superseded ADRs be included?
4. How should recent session logs compete with older accepted decisions?
5. Is verification status needed for findings in the first version?
6. How should relationship distance affect ranking?
7. Can simple deterministic rules outperform embedding-only retrieval?
8. How should retrieval explain why an entry was selected?
9. What token budgets should be assigned to each retrieval layer?
10. How should users override or inspect ranking behaviour?

## 10. Required Exploration Before Promotion

Before promotion to `todo`, complete:

- retrieval analysis using real Memory Seed entries
- comparison of chronological, semantic-only, and type-aware retrieval
- definition of authority and relevance dimensions
- prototype context packages for at least five real tasks
- token-use comparison
- failure analysis for missing and over-prioritised context
- treatment of superseded and rejected decisions
- user-facing explanation model for Trace and MCP responses

## 11. Promotion Gate

Promote only if testing shows that:

1. Type-aware retrieval improves answer quality or reduces context usage.
2. The ranking rules are understandable and inspectable.
3. No new large metadata burden is required.
4. Historical evidence remains easily accessible.
5. The model performs better than topic plus recency alone.

## 12. Initial Recommendation

Continue exploration with retrieval experiments.

The idea is high value because it converts entry typing from passive classification into practical context control. It should not become an implementation item until ranking behaviour has been evaluated against real project queries.
