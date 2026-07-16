# Initial Proposal: Agent Skill and Workflow Architecture

**Status:** Exploration candidate  
**Promotion state:** Not ready for `todo`  
**Related systems:** Agent skills, MCP, CLI, control plane, session logging

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## 1. Summary

This proposal explores a formal architecture for Memory Seed's agent-facing skills and workflows.

The core hypothesis is:

> High-level agent workflows should orchestrate small deterministic operations and reusable reasoning disciplines, rather than requiring the model to manually compose low-level commands.

The proposal is influenced by the distinction between user-invoked orchestration skills and model-invoked reusable skills observed in professional agent workflow repositories.

## 2. Problem

As Memory Seed adds capabilities, agents may need to perform increasingly complex sequences:

- inspect project configuration
- find topics
- create a typed entry
- generate deterministic anchors
- validate relationships
- promote a decision to an ADR
- update an ADR sidecar
- collect relevant context
- record the session result

If these actions are exposed only as individual CLI or MCP functions, agents must remember the correct sequence and invariants.

This creates failure modes such as:

- skipped validation
- inconsistent IDs
- duplicate sidecar updates
- direct file edits
- incomplete session records
- workflow differences between Claude, Codex, and other clients
- duplicated logic across skills, MCP, and CLI

## 3. Proposed Architecture

The architecture should separate four layers.

### Layer 1: Core domain logic

Deterministic application functions implement invariants.

Examples:

```text
create_entry
validate_entry
create_adr
promote_decision_to_adr
transition_adr
collect_context
```

### Layer 2: Adapters

CLI and MCP expose the same core functions.

```text
CLI ─┐
     ├── shared core application logic
MCP ─┘
```

No business rule should exist only in one adapter.

### Layer 3: Reusable model-invoked disciplines

Small skills provide reusable judgement where deterministic code is insufficient.

Potential examples:

- identify consequential decisions
- distinguish facts from decisions
- select relevant topics
- assess whether an ADR is warranted
- summarise a completed session

### Layer 4: User-invoked workflows

High-level skills orchestrate complete user goals.

Potential examples:

- record current work
- promote a decision to ADR
- update an ADR
- collect project decision context
- hand off work
- close a development session

## 4. Example Workflow

### Promote a decision to ADR

```text
User invokes ADR promotion workflow
    ↓
Skill locates candidate entry and exact decision
    ↓
Model confirms the decision is ADR-worthy
    ↓
MCP calls deterministic promotion operation
    ↓
Core logic creates ADR ID and sidecar
    ↓
Validator confirms topics and references
    ↓
Workflow reports the result
```

The model makes the semantic judgement. Deterministic code performs the state mutation.

## 5. Router Skill

As workflows grow, users and agents may not remember which one applies.

A router skill could map user intent to the correct workflow:

```text
"I made an important storage decision"
    → promote decision to ADR

"Summarise what we completed"
    → close session

"What governs retrieval?"
    → collect decision context by topic
```

The router should remain descriptive rather than becoming a second implementation layer.

## 6. Skill Design Principles

Potential principles include:

- predictable process over identical output
- explicit completion criteria
- minimal descriptions for automatic invocation
- one source of truth for each behaviour
- progressive disclosure of specialised reference material
- semantic judgement in skills
- state mutation in deterministic code
- no direct sidecar editing
- adapters must not duplicate core rules
- workflows should produce or update durable memory where appropriate

## 7. Potential Skill Categories

### User-invoked workflows

- `setup-memory-seed`
- `record-session`
- `promote-adr`
- `update-adr`
- `collect-context`
- `handoff-session`
- `audit-memory-state`

### Model-invoked disciplines

- `decision-identification`
- `topic-selection`
- `adr-worthiness`
- `session-summarisation`
- `evidence-verification`
- `relationship-selection`

These names are illustrative only.

## 8. Potential User Value

- consistent behaviour across different agents
- fewer manual steps
- reduced risk of invalid state
- easier onboarding
- lower cognitive burden
- clearer boundaries between model judgement and code execution
- reusable workflows for the Memory Seed ecosystem

## 9. Risks

### Skill proliferation

Too many skills create discovery and context-load problems.

**Mitigation:** use a small number of user workflows and a router.

### Logic duplication

The same rule may be encoded in skills, CLI, MCP, and documentation.

**Mitigation:** keep mutation and validation rules in the core application layer.

### Over-orchestration

Rigid workflows may make simple tasks slower.

**Mitigation:** distinguish narrow direct operations from multi-step workflows.

### Cross-agent inconsistency

Different agent platforms may support skills differently.

**Mitigation:** define portable workflow contracts and keep deterministic operations platform-neutral.

### Premature abstraction

The architecture may be designed before actual recurring workflows are known.

**Mitigation:** derive the first workflow set from observed usage.

## 10. Questions Requiring Further Exploration

1. Which user goals recur often enough to justify bundled workflows?
2. Which semantic judgements should be model-invoked skills?
3. How should workflows be represented across Claude, Codex, and other clients?
4. Which instructions belong in `AGENTS.md`, skills, or core documentation?
5. How should router invocation remain reliable without excessive context?
6. What completion criteria should each workflow enforce?
7. How should workflows report partial failure?
8. How should session logging be integrated without becoming mandatory noise?
9. Should workflows be versioned alongside schemas?
10. How can existing Memory Seed MCP tools be reorganised without breaking clients?

## 11. Required Exploration Before Promotion

Before promotion to `todo`, complete:

- inventory of current CLI, MCP, and skill responsibilities
- identification of the five most frequent multi-step user workflows
- duplication analysis across adapters
- prototype of one end-to-end workflow using shared core logic
- cross-agent portability assessment
- context-load analysis for user- and model-invoked skills
- failure and rollback model
- proposed router map
- compatibility plan for existing commands and tools

## 12. Promotion Gate

Promote only if:

1. At least three recurring workflows are demonstrated from real use.
2. Shared core logic can serve CLI and MCP without duplication.
3. The workflow reduces agent error compared with manual tool composition.
4. The number of skills remains small and understandable.
5. Cross-agent support is feasible without platform-specific forks.

## 13. Initial Recommendation

Explore this as a control-plane and developer-experience design topic.

It should not be implemented as a broad skill rewrite until current workflows have been inventoried and one representative workflow has been prototyped end to end.
