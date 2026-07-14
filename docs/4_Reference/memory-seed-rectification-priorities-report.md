---
tags:
  - memory-seed
  - reference
  - audit
---

<!-- Reference source material (user drop 2026-07-14); triaged to 4_Reference — a critique/audit with
     embedded action items, not one buildable plan; split any approved item into its own 1_Inbox
     proposal. NET-NEW: an entry-type taxonomy (Evidence/Interpretation/Decision/...), a content-
     trust-level taxonomy, and an outcome-comparison benchmark harness.
     OVERLAPS (already shipped/covered): two-stage capture (session logs + memory_consolidation),
     retrieval-over-graph (blueprint), trust/security (8_Deferred hosted-security + risk_signaling).
     Net-new items surfaced in docs/2_Todo/0_NEXT_STEPS.md "Captured strategic input". -->

# Memory Seed: Top 10 Rectification Priorities

## Purpose

This document identifies the ten highest-priority actions required to prevent Memory Seed from falling prey to its most credible structural, technical, product, and market weaknesses.

The priorities are ordered by importance, with **1** representing the highest priority.

---

## 1. Define one primary job the product must perform

Memory Seed currently risks being interpreted as a documentation system, knowledge graph, agent-memory layer, project-management tool, Git companion, or audit platform.

The project needs one dominant product promise:

> **Memory Seed preserves the decisions, evidence, and project context that future humans and agents need to continue work without repeating prior investigation.**

Everything else should support that job.

### Required actions

- Define the primary user, triggering situation, and desired outcome.
- Separate core capabilities from future extensions.
- Reject features that do not materially improve project-context continuity.
- Ensure Memory Trace, MCP, CLI, topics, and Git integration remain interfaces to the same core job.

### Core success test

A user or agent returning to a project should be able to answer:

1. What is currently true?
2. Why is it true?
3. What evidence supports it?
4. What should be reconsidered before changing it?

---

## 2. Prove that Memory Seed improves outcomes

The largest strategic risk is building a sophisticated system whose value feels plausible but remains unproven.

Memory Seed needs benchmarks comparing work with and without the system.

### Measure

- Time required to resume an interrupted task
- Time required to understand an unfamiliar subsystem
- Percentage of previous decisions correctly recovered
- Repeated investigations avoided
- Incorrect assumptions introduced by agents
- Relevant context retrieved
- Stale or misleading context retrieved
- Time required to prepare a handoff
- Accuracy of project-history questions
- Unnecessary reversals or duplicated changes

### Recommended evaluation

Compare the same task under three conditions:

1. Repository only
2. Repository plus ordinary documentation
3. Repository plus Memory Seed

Evaluate speed, correctness, context recovery, and duplicated work.

Avoid treating internal activity metrics such as entry count, graph density, or relationship count as proof of value unless they correlate with measurable outcomes.

---

## 3. Make capture nearly automatic, but require confirmation for durable knowledge

Manual capture will be abandoned. Fully automatic capture will create noise and false records.

Memory Seed should use a two-stage model.

### Stage 1: automatic session capture

Automatically record:

- Files changed
- Commits created
- Commands run
- Agents used
- Tools called
- Topics suggested
- Documents referenced
- Explicit user instructions
- Test outcomes

This is an activity record, not yet trusted project knowledge.

### Stage 2: promoted durable memory

At meaningful boundaries, propose a compact record containing:

- Decision
- Rationale
- Evidence
- Current status
- Rejected alternatives
- Consequences
- Conditions for reconsideration
- Relevant files or commits
- Unresolved questions

A user or authorised agent should confirm or edit the record before it becomes durable knowledge.

---

## 4. Establish a clear authority and lifecycle model

Memory Seed must distinguish current knowledge from historical statements.

### Minimum lifecycle states

- `proposed`
- `accepted`
- `implemented`
- `verified`
- `superseded`
- `deprecated`
- `rejected`
- `archived`

### Minimum authority properties

- Author
- Approver
- Creation date
- Last verification date
- Confidence
- Scope
- Source evidence
- Superseded-by relationship
- Applicable versions, branches, or components
- Whether the entry is descriptive or normative

A later entry should explicitly supersede or qualify an earlier entry rather than silently replacing it.

### Retrieval rule

Current, verified, scoped entries should rank above:

- Old entries
- Unreviewed summaries
- Historical alternatives
- Raw session logs
- Unverified model-generated content

---

## 5. Separate evidence, interpretation, decision, and instruction

These information types should not be stored or presented as if they carry equal authority.

### Recommended entry types

| Type | Meaning |
|---|---|
| Evidence | What was observed or referenced |
| Interpretation | What someone concluded from the evidence |
| Decision | What the project chose to do |
| Instruction | What future contributors or agents must follow |
| Activity | What occurred during a session |
| Hypothesis | What is suspected but not yet established |
| Outcome | What happened after implementation |

### Example

```yaml
type: decision
status: accepted
decision: Use SQLite for the local index
rationale:
  - Works offline
  - Requires no separate service
evidence:
  - benchmark: docs/evaluations/index-benchmark.md
supersedes:
  - mem_01HF...
reconsider_when:
  - Repository exceeds 500,000 entries
```

This distinction reduces the risk of generated interpretation being mistaken for binding instruction.

---

## 6. Build retrieval quality before expanding the graph UI

The graph is not the core product. Reliable retrieval is.

### Prioritise

- Hybrid keyword and semantic search
- Topic filtering
- File, commit, participant, and date filters
- Current-versus-historical ranking
- Provenance display
- Superseded-entry handling
- Evidence-backed summaries
- Retrieval confidence
- Explanations of why an entry was selected
- Small, bounded context packages for agents

### Required answer behaviour

Users should be able to inspect:

- Which entries were used
- Why they were considered relevant
- Which source files support the answer
- Whether the entries are current
- Whether conflicting records exist
- Whether the answer contains model inference

The graph should support navigation through retrieved evidence rather than substitute for retrieval.

---

## 7. Introduce aggressive memory hygiene and deliberate forgetting

A successful memory system cannot retain everything with equal weight indefinitely.

### Implement

- Temporary versus durable entry classes
- Retention rules for raw session logs
- Periodic stale-entry checks
- Duplicate detection
- Contradiction detection
- Topic consolidation
- Entry promotion and demotion
- Archival of superseded material
- Redaction and permanent deletion
- Summarisation of low-value historical detail
- Broken-link and orphan detection

### Suggested hierarchy

```text
Raw activity
    ↓
Session summary
    ↓
Reviewed memory
    ↓
Durable decision or knowledge
    ↓
Superseded or archived history
```

Only a small fraction of recorded activity should become permanent high-priority memory.

---

## 8. Treat security and trust boundaries as core architecture

Because agents consume Memory Seed content, stored text can influence future actions. Memory files therefore form part of the execution trust boundary.

### Suggested trust levels

- `system-policy`
- `project-policy`
- `approved-decision`
- `reviewed-memory`
- `unreviewed-agent-output`
- `external-content`
- `raw-transcript`
- `untrusted-import`

Agents should treat evidence and historical content as data, not executable instructions.

### Required safeguards

- Secret detection before writing
- Sensitive-data redaction
- Prompt-injection classification
- Clear origin metadata
- Integrity checks for trusted records
- Permission controls for shared projects
- Audit history for edits and approvals
- Restricted access to confidential memories
- Safe rendering of external content
- Protection against memory entries overriding higher-level instructions

---

## 9. Keep the architecture narrow and integration-light

Memory Seed should avoid becoming responsible for every part of the development workflow.

### It should own

- Memory schema
- Validation
- Lifecycle state
- Provenance
- Retrieval
- Context packaging
- Local storage
- Memory-specific permissions
- Stable CLI and MCP contracts

### It should integrate with rather than duplicate

- Git history
- Pull requests
- Issue tracking
- Code review
- Authentication providers
- Editor blame
- Git worktree management
- General document editing
- Project planning
- Team messaging

Each integration should answer:

> Does this materially improve the capture, validation, retrieval, or application of project memory?

If not, it should remain outside the core product.

---

## 10. Create immediate user value before relying on long-term memory benefits

The long-term promise of institutional memory is not enough to drive daily adoption.

Each session should produce immediate value.

### High-value immediate outcomes

- Resume the previous session with one command
- Generate a grounded handoff
- Produce a pull-request summary from recorded work
- Show unresolved questions from the last session
- Restore relevant files, decisions, and commands
- Explain what changed since the user last worked on the project
- Prepare bounded context for a new agent
- Detect contradictions with accepted decisions
- Identify previously attempted work
- Generate a concise progress report

### Desired workflow

```text
User records memory
    ↓
User immediately saves time
    ↓
Project accumulates durable knowledge
    ↓
Future users and agents also benefit
```

---

## Priority Summary

| Priority | Rectification | Primary risk addressed |
|---:|---|---|
| 1 | Define one primary product job | Product ambiguity |
| 2 | Prove measurable outcome improvement | Unvalidated value |
| 3 | Automate capture and review durable memory | Adoption burden and noise |
| 4 | Establish authority and lifecycle semantics | Stale and conflicting memory |
| 5 | Separate evidence, interpretation, decisions, and instructions | Trust and conceptual ambiguity |
| 6 | Prioritise retrieval quality over graph sophistication | Weak practical usefulness |
| 7 | Build memory hygiene and forgetting | Accumulating noise |
| 8 | Design security and trust boundaries early | Prompt injection and data exposure |
| 9 | Restrict architectural and integration scope | Execution complexity |
| 10 | Deliver value during every session | Delayed-benefit adoption failure |

---

## Recommended Implementation Sequence

### Phase 1: Establish the foundation

- Primary job definition
- Entry-type model
- Authority and lifecycle model
- Capture-versus-promotion distinction
- Initial evaluation benchmark

### Phase 2: Make it useful and trustworthy

- High-quality retrieval
- Provenance and citation
- Immediate session-resumption workflows
- Security trust levels
- Memory hygiene

### Phase 3: Expand interfaces and collaboration

- Memory Trace graph
- Multi-user annotations
- Hosted synchronization
- Additional Git and project-management integrations
- Advanced AI synthesis

> **Do not scale the amount, presentation, or distribution of memory until Memory Seed can reliably distinguish useful current knowledge from noisy historical activity.**
