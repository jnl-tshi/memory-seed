---
title: "Initial Proposal: Agent-Workflow Observability"
status: "superseded"
replaced_by: "../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md"
replaced_on: "2026-07-16"
---

# Initial Proposal: Agent-Workflow Observability

**Status:** Superseded 2026-07-16
**Superseded by:** [`memory-seed-workflow-evidence-and-review-workbench-plan.md`](../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md)
**Related systems:** Memory Seed, Memory Trace, MCP, CLI, control plane

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## 1. Summary

This proposal explores whether Memory Seed should become the durable observability layer for professional agentic development workflows.

The core hypothesis is:

> Workflow tools define what an agent is expected to do; Memory Seed should preserve what actually happened, why it happened, and which artifacts resulted.

This would position Memory Seed between agent orchestration and human review. It would not execute the workflow itself. Instead, it would capture enough structured evidence for Memory Trace and future agents to reconstruct the course of work.

## 2. Problem

Modern coding-agent workflows are increasingly structured around recurring stages such as:

```text
clarification
→ research
→ decision
→ specification
→ ticketing
→ implementation
→ testing
→ review
→ commit
```

However, the durable record is fragmented across:

- chat transcripts
- local agent context
- issue trackers
- commits and pull requests
- generated specifications
- temporary worktrees
- tool logs
- human memory

This creates several problems:

- A workflow can appear complete even when stages were skipped.
- Agent and subagent findings may be accepted without verification.
- Important reasoning can remain trapped in one context window.
- Work performed across branches or worktrees can become difficult to reconcile.
- Git shows file changes but not the reasoning path that produced them.
- Issue trackers show work state but not necessarily the evidence behind it.

## 3. Proposed Direction

Memory Seed would record a lightweight set of workflow observations as typed entries and relationships.

Potential observations include:

- a design clarification occurred
- research was completed
- a finding was verified
- an ADR was proposed or updated
- a specification was produced
- a ticket was created or unblocked
- implementation began or completed
- tests were run
- code review was completed
- a commit or pull request implemented a decision
- a handoff transferred work to another session or agent

The model should prioritise semantic events over raw tool telemetry.

### Example

```yaml
---
id: entry-01WORKFLOW
type: session-log
topics:
  - retrieval
  - agent-workflow

workflow:
  stage: implementation
  action: completed

relationships:
  implements:
    - adr-01RETRIEVAL
  resolves:
    - issue-142
  produced:
    - commit:8c31e2
---
```

The exact schema is deliberately unresolved at this stage.

## 4. Scope Boundary

The proposal does **not** suggest that Memory Seed should become:

- an agent scheduler
- a workflow engine
- a replacement for GitHub Issues, Linear, Jira, or Git
- a general telemetry platform
- a complete OpenTelemetry implementation
- a tool that stores every agent tool call
- a system that blocks work whenever a preferred process is not followed

The intended role is durable reasoning observability, not workflow enforcement.

## 5. Potential User Value

### Project maintainers

- See how a feature moved from idea to implementation.
- Detect when a consequential change lacks recorded reasoning.
- Understand which work remains unverified.
- Review agent work without reading every session transcript.

### Future agents

- Load the relevant decisions, findings, specifications, and implementation evidence.
- Avoid repeating investigations.
- Distinguish authoritative decisions from incidental discussion.
- Resume work across context boundaries.

### Teams and project managers

- Follow decision and implementation timelines.
- Identify stalled or incomplete work.
- Understand contributions across multiple users and agents.
- Inspect the provenance behind a project direction.

## 6. Candidate Trace Views

Potential views include:

- expected versus observed workflow
- feature journey from idea to commit
- unverified findings
- decisions without implementation
- implementation without linked decision context
- handoffs that were never resumed
- worktree or branch contributions by agent
- evidence chain for a selected artifact

These are product hypotheses, not committed UI requirements.

## 7. Risks

### Scope expansion

Workflow observability could become an excuse to model every process used by every team.

**Mitigation:** begin with a small set of semantic relationships that directly support reasoning reconstruction.

### Excessive logging

Capturing too much detail would increase noise and storage without improving understanding.

**Mitigation:** record meaningful project events, not raw execution telemetry.

### False certainty

The absence of a recorded stage does not always prove that the stage did not occur.

**Mitigation:** distinguish “not observed” from “did not happen.”

### Integration complexity

Issue trackers, Git, MCP clients, local agents, and CI systems expose different identifiers and event models.

**Mitigation:** start with Memory Seed-native entries and Git references before external integrations.

## 8. Questions Requiring Further Exploration

1. Which workflow observations deliver the highest value with the least metadata?
2. Should workflow stage be a field, a relationship, or inferred from entry type?
3. Which observations should be written automatically and which require agent judgement?
4. How should verification of subagent findings be represented?
5. How should workflow evidence be reconciled across branches and worktrees?
6. What is the minimum useful Trace view?
7. How much can be derived from existing entry types and relationships without a new schema?
8. Should expected workflow definitions live in skills, configuration, or project documents?
9. How should Memory Seed avoid competing with issue trackers?
10. What measurable user outcomes would prove that observability is useful?

## 9. Required Exploration Before Promotion

Before this proposal can move to `todo`, complete:

- a current-state audit of Memory Seed entry and relationship capabilities
- analysis of at least three real Memory Seed development journeys
- comparison with Git, issue trackers, agent traces, and observability tools
- a minimal event/relationship model
- a prototype Trace timeline using existing project history
- noise and storage analysis
- a clear scope boundary between observation and orchestration
- success metrics and failure criteria

## 10. Promotion Gate

Promote this proposal to `todo` only if exploration demonstrates that:

1. A small semantic model can reconstruct useful workflow history.
2. The feature adds value beyond Git and issue trackers.
3. It does not require recording raw tool telemetry.
4. It can be implemented without making Memory Seed a workflow engine.
5. At least one high-value Trace view is validated with real project data.

## 11. Initial Recommendation

Continue exploration.

This idea has strong strategic value and could become a core differentiator, but it is too broad to implement directly from the current discussion. The next step should be a focused research and data-model exercise, not a feature ticket.
