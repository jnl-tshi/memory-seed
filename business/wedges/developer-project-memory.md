---
title: "Developer Project-Memory Wedge"
status: active-hypothesis
last_reviewed: "2026-08-01"
next_review_due: "2026-10-01"
confidence: medium
---

# Developer project-memory wedge

## Purpose and current conclusion

This dossier defines Memory Seed's initial market wedge: **Git-native, decision-centric project memory
for developers and human-AI engineering teams**.

Memory Seed should enter through the recurring failure to preserve what was decided, why it was decided,
which evidence supported it, and what later replaced it across coding-agent sessions. It should not enter
as a generic chatbot memory, coding agent, project board, or enterprise search product.

## Initial customer and user

### Primary early user

- A developer or technical founder using more than one coding agent.
- Works in a Git repository over weeks or months.
- Repeatedly re-explains architecture, constraints, prior attempts, and project status.
- Values local control, readable files, portability, and evidence more than fully passive capture.

### First team buyer

- Engineering lead, platform lead, or AI enablement lead responsible for consistent agent behaviour.
- Needs onboarding, shared decisions, provenance, auditability, and handover across people and agents.
- Can adopt repository-local tooling without a broad enterprise-data integration project.

### Later enterprise buyer

- Platform engineering, developer experience, AI governance, or engineering productivity.
- Requires policy, permissions, reporting, support, controlled rollout, and deployment options.

## Problem statement

Coding agents are increasingly capable of real delegated work, but project context remains fragmented
across chats, branches, tickets, documents, tools, and individual memory. The failure is not just recall:
teams cannot reliably determine which decision is authoritative, why it exists, what evidence supports
it, or whether a later decision superseded it.

## Wedge promise

> One inspectable project memory, using the same plumbing for humans and agents.

The entry product should make four jobs materially easier:

1. Resume a project or task without reconstructing context manually.
2. Give a new human or agent the current decisions, constraints, risks, and recent state.
3. Trace a decision to evidence and see how it evolved or was superseded.
4. Move between coding agents without surrendering project memory to one vendor.

## Differentiators to prove

- Git-native Markdown as the durable, portable authority.
- Decisions, evidence, provenance, evolution, and supersession as first-class objects.
- One memory model exposed to humans, CLI workflows, and MCP-capable agents.
- Local-first operation with an optional managed path.
- Explicit governance and inspectability rather than opaque extraction alone.

These are hypotheses until customer evidence shows they affect adoption, retention, willingness to pay,
or switching behaviour.

## Adoption path

1. **Solo/local:** seed one repository and recover context across agent sessions.
2. **Multi-agent:** use the same project memory from Codex, Claude Code, Gemini, Cursor, and other clients.
3. **Team:** share decisions, onboarding, handovers, and reviewable agent work through Git.
4. **Managed team:** add hosted indexing, collaboration, policy, reporting, and administration.
5. **Enterprise:** add deployment control, permissions, compliance evidence, and support.

## Alternatives considered

| Alternative wedge | Why it is not first |
|---|---|
| Generic agent-memory API | Crowded and vulnerable to model-provider or hyperscaler bundling |
| Personal “remember everything” assistant | Requires passive capture, broad connectors, and consumer trust beyond the current product |
| Project-management board for agents | Competes with established systems and makes project state—not reasoning—the primary object |
| Enterprise search/context layer | Large integration burden and long sales cycle before the core decision-memory value is proven |
| Coding agent or orchestration platform | Places Memory Seed against better-capitalized execution products instead of beneath them |

## Evidence currently supporting the wedge

### Sourced market evidence

- Competitors increasingly describe memory as production agent infrastructure; see the
  [competitor landscape](../market/competitor-landscape.md).
- The cloud-native developer population provides a large technically compatible entry segment; see
  [market size](../market/market-size.md).
- Published competitor pricing supports free/open-source entry followed by paid individual and team
  tiers; see [competitor pricing](../market/competitor-pricing.md).

### Internal product evidence

- Memory Seed already implements repository-local Markdown memory, deterministic onboarding,
  session history, multi-agent routing, MCP retrieval, and human inspection surfaces.
- Existing market-fit and strategic reports repeatedly converge on portable project memory rather
  than another coding agent as the strongest position.

These observations demonstrate product-problem alignment, not product-market fit.

## Validation requirements

Before broadening the wedge, collect evidence from at least:

- 20 structured interviews across solo developers, technical founders, engineering leads, and AI/platform leads.
- 10 active repositories using Memory Seed for at least four weeks.
- Measured time-to-first-value and successful second-session recovery.
- Weekly retention, repositories retained, agent surfaces used, and memory retrieval frequency.
- At least five attempts to buy, including objections and preferred pricing unit.
- Direct comparisons against plain `AGENTS.md`, vendor chat memory, and at least one memory API.

## Failure and pivot signals

- Users value onboarding instructions but do not return to stored decisions.
- Git-authored memory is experienced as maintenance work rather than saved work.
- Passive capture consistently outperforms deliberate project records for the target job.
- Cross-agent portability does not influence tool choice or willingness to pay.
- Teams will pay only for a broader project-management, search, or observability product.

## Related dossiers

- [Market size](../market/market-size.md)
- [Competitor landscape](../market/competitor-landscape.md)
- [Competitor pricing](../market/competitor-pricing.md)
- [Earlier strategic synthesis](memory-seed-strategic-synthesis-report.md)
- [Earlier market-fit report](../market/memory-seed-market-fit-report.md)

## Unresolved validation questions

- Is the beachhead solo developers, technical founders, or an engineering-platform team?
- Is the decisive paid feature hosted retrieval, team governance, Memory Trace, or handover reporting?
- How much deliberate authoring can users tolerate before passive assistance becomes necessary?
- Which outcome is easiest to measure: reduced re-explanation, faster onboarding, fewer repeated mistakes,
  or more trustworthy agent delegation?

## Change log

- **2026-08-01:** Created the living wedge dossier and defined the initial customer, promise,
  alternatives, validation requirements, and pivot signals.

