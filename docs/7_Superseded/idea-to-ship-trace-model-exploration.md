# Initial Proposal: Idea-to-Ship Trace Model

**Status:** Superseded 2026-07-16
**Superseded by:** [`memory-seed-workflow-evidence-and-review-workbench-plan.md`](../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md)
**Related systems:** Entry types, relationships, Memory Trace, issue trackers, Git

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## 1. Summary

This proposal explores a coherent trace model connecting an idea to the artifacts and outcomes that result from it.

The core hypothesis is:

> Typed entries and relationships should allow Memory Trace to reconstruct the meaningful journey from initial intent through research, decisions, planning, implementation, review, and delivery.

This proposal is broader than ADR tracking but should reuse the mandatory entry-type foundation.

## 2. Problem

Project knowledge is usually distributed across disconnected artifacts:

```text
conversation
research report
ADR
specification
issue
branch
commit
pull request
test
release
```

Even when each artifact exists, their relationships are often implicit.

This makes it difficult to answer:

- Why was this feature created?
- Which research informed it?
- Which decisions constrained it?
- Which tickets implemented it?
- Which commit or pull request delivered it?
- Did the implementation match the decision?
- What remains incomplete?
- Which session should a future agent read?

## 3. Proposed Trace

A conceptual journey could be:

```text
idea
→ clarification
→ research and findings
→ decision or ADR
→ research-planning entry
→ implementation tickets
→ session logs
→ tests and review
→ commit or pull request
→ release or outcome
```

Memory Seed should not require every project to follow this exact process. The trace model should represent relationships when they exist.

## 4. Candidate Relationship Vocabulary

Potential relationships include:

| Relationship | Example |
|---|---|
| `derived-from` | ADR derived from research entry |
| `informed-by` | Plan informed by finding |
| `proposes` | Planning entry proposes a change |
| `governed-by` | Implementation governed by ADR |
| `decomposed-into` | Plan decomposed into tickets |
| `implements` | Commit implements ticket or ADR |
| `verified-by` | Change verified by tests or review |
| `supersedes` | New decision replaces old decision |
| `continued-by` | Handoff continued by later session |
| `produced` | Session produced artifact |
| `resolved-by` | Finding or issue resolved by change |

The final vocabulary must remain small and directed.

## 5. Trace Unit

The model should determine what represents the main traceable unit.

Candidates include:

- feature
- decision
- issue
- topic
- workstream
- user-defined objective

A likely approach is not to create a new universal “feature” object initially. Trace may instead begin from any entry or artifact and follow typed relationships.

## 6. Example

```text
Research-planning entry
    ├── informed-by → Finding
    ├── proposes → ADR
    └── decomposed-into → Issue 142

ADR
    └── governed-by ← Implementation session

Issue 142
    ├── implemented-by → Commit 8c31e2
    └── verified-by → Test report

Commit 8c31e2
    └── reviewed-in → PR 87
```

Memory Trace could present this as a chronological trail, relationship graph, or evidence panel.

## 7. Relationship to Existing Tools

The model should reference external artifacts rather than copy them unnecessarily.

Examples:

```yaml
relationships:
  implements:
    - github_issue: 142
  produced:
    - git_commit: 8c31e2
```

Git and issue trackers remain authoritative for their native objects. Memory Seed preserves the reasoning links between them.

## 8. Potential User Value

### Developers and agents

- understand the origin and constraints of a task
- identify the correct context before implementation
- avoid contradicting accepted decisions
- determine what evidence is still missing

### Project managers

- see how a proposal progressed
- identify stalled transitions
- inspect decision-to-delivery lead time
- understand dependencies and unresolved work

### Reviewers

- compare implementation with originating decisions and plans
- navigate directly to supporting evidence

## 9. Risks

### Universal process assumption

Projects use different development methods.

**Mitigation:** model relationships, not a mandatory fixed sequence.

### Relationship overload

Too many edge types could make entries noisy and graphs unreadable.

**Mitigation:** define a minimal vocabulary and derive visual groupings.

### Duplicate project-management data

Memory Seed could begin copying issue states or pull-request data.

**Mitigation:** store references and reasoning context, not full external records.

### Incomplete traces

Many historical artifacts will lack links.

**Mitigation:** allow partial traces and distinguish explicit from inferred relationships.

### Excessive automation

Agents may create weak relationships simply to complete a workflow.

**Mitigation:** validate relationship targets and require semantically meaningful edge selection.

## 10. Questions Requiring Further Exploration

1. What is the minimum relationship set needed to reconstruct useful journeys?
2. Should Trace begin from entry, topic, artifact, or workstream?
3. Which relationships are explicit and which may be inferred?
4. How should external Git and issue references be normalised?
5. Should specifications and tickets remain external artifacts or typed Memory Seed entries?
6. How should partial or conflicting traces be displayed?
7. How can traces remain useful without requiring every workflow stage?
8. What relationship directions and inverse labels should be used?
9. How should worktrees and parallel agents appear?
10. Which metrics, if any, should be derived from the trace?

## 11. Required Exploration Before Promotion

Before promotion to `todo`, complete:

- analysis of at least three complete Memory Seed development journeys
- inventory of current relationship fields and external artifact references
- minimal relationship vocabulary proposal
- prototype trace generation from existing repository data
- evaluation of explicit versus inferred links
- interaction design sketch for trail and graph views
- incomplete-trace handling
- scope boundary with GitHub, Git, and project-management tools

## 12. Promotion Gate

Promote only if:

1. A small relationship vocabulary can reconstruct useful histories.
2. Existing artifacts can be referenced without duplication.
3. The model supports multiple workflows rather than enforcing one.
4. At least one real project journey is materially easier to understand in Trace.
5. Relationship creation can be partially automated without producing low-quality edges.

## 13. Initial Recommendation

Explore through real historical reconstruction.

The idea is strategically important, but the model should be derived from actual Memory Seed project journeys rather than designed entirely in the abstract.
