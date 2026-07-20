---
title: "Memory Seed Initial Exploration Proposals"
status: "superseded"
superseded_by: "mse_ddba1ztxqhasfbwf"
superseded_on: "2026-07-16"
---

# Memory Seed Initial Exploration Proposals

**Status:** Superseded 2026-07-16
**Split into:** semantic-record foundation, workflow evidence/review workbench, semantic Trace projections,
and the deferred agent skill/workflow architecture proposal.

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## Included proposals

1. [Agent-Workflow Observability](./agent-workflow-observability-exploration.md)
2. [Memory Signal Hierarchy](./memory-signal-hierarchy-exploration.md)
3. [Agent Skill and Workflow Architecture](../8_Deferred/agent-skill-workflow-architecture-proposal.md)
4. [Idea-to-Ship Trace Model](./idea-to-ship-trace-model-exploration.md)
5. [Type-Specific Memory Trace Projections](./type-specific-trace-projections-exploration.md)

## Shared instruction

These documents capture promising directions from the conversation. They should be placed in an exploratory or inbox area, not `docs/todo/`.

Each proposal contains:

- a problem statement
- an initial architectural direction
- scope boundaries
- risks
- open questions
- required exploration
- explicit promotion criteria

A proposal should move to `todo` only after its own promotion gate has been satisfied and a narrower implementation plan has been produced.

## Suggested exploration order

```text
1. Agent-workflow observability
2. Memory signal hierarchy
3. Agent skill and workflow architecture
4. Idea-to-ship trace model
5. Type-specific Trace projections
```

The first two have the greatest potential to affect Memory Seed's long-term product role and retrieval architecture. The remaining proposals depend partly on those conclusions.
