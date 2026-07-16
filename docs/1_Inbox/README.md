# Memory Seed Initial Exploration Proposals

**Status:** Exploration bundle  
**Promotion state:** None of these proposals is ready for `docs/todo/`

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## Included proposals

1. [Agent-Workflow Observability](./01-agent-workflow-observability.md)
2. [Memory Signal Hierarchy](./02-memory-signal-hierarchy.md)
3. [Agent Skill and Workflow Architecture](./03-agent-skill-workflow-architecture.md)
4. [Idea-to-Ship Trace Model](./04-idea-to-ship-trace-model.md)
5. [Type-Specific Memory Trace Projections](./05-type-specific-trace-projections.md)

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
