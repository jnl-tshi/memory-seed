# Proposal: Typed Memory Entries and ADR Sidecar Lifecycle Tracking

**Status:** Superseded 2026-07-16.
**Superseded by:** [`memory-seed-semantic-record-and-signal-foundation-plan.md`](../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md)
and [`adr-lifecycle-sidecar-contract.md`](../3_Spec/draft/adr-lifecycle-sidecar-contract.md). The successor
keeps authoritative ADR sidecars but replaces mutable generated YAML with append-only Markdown and derives
current status from transition replay.

**Project:** Memory Seed / Memory Trace  
**Status:** Proposed  
**Scope:** Entry typing and ADR-specific lifecycle tracking  
**Primary objective:** Introduce mandatory entry types and a narrow, deterministic mechanism for promoting and tracking architecture decisions without turning Memory Seed into a general workflow engine.

---

## 1. Executive Summary

Memory Seed currently captures chronological project memory, but entries do not have a mandatory semantic classification. This makes it harder for agents and Memory Trace to distinguish ordinary work logs from higher-signal records such as findings, handoffs, research outputs, or architecture decisions.

This proposal introduces:

1. A mandatory `type` field for all Memory Seed entries.
2. A deliberately small core type registry.
3. First-class support for Architecture Decision Records (ADRs).
4. ADR-specific sidecars that authoritatively track promotion, current status, status history, topics, and supersession.
5. Deterministic CLI and MCP workflows that create and update ADR sidecars.
6. Stable decision identifiers within entries so that references can target one exact decision when an entry contains several.
7. `decision-update` entries for interactions that evolve a decision without directly advancing implementation work.

The design is intentionally ADR-specific. It does not introduce generic lifecycle sidecars for every entry type. Future sidecars may be added only when justified by evidence and separate proposals.

---

## 2. Problem Statement

Memory Seed entries currently behave primarily as chronological records. This creates several limitations:

- Agents must infer the purpose of an entry from prose.
- Memory Trace cannot reliably distinguish logs, findings, research, decisions, or handoffs.
- A single session entry may contain several decisions, making entry-level references ambiguous.
- Significant architectural decisions can become buried in historical logs.
- ADRs may evolve through proposal, acceptance, rejection, or supersession, but Git history alone does not provide a clean semantic lifecycle.
- Rewriting historical entries to reflect later status would weaken their value as records of what was known at the time.
- A generic event-sourcing or workflow engine would exceed Memory Seed's current scope and introduce unnecessary complexity.

Memory Seed therefore needs a narrow semantic layer that preserves chronological records while allowing important project decisions to be promoted and pulled forward deterministically.

---

## 3. Design Principles

The proposed design follows these principles.

### 3.1 Keep source entries readable

Session files remain human-readable Markdown records. Entry metadata should be sufficient for indexing and linking without turning each entry into a large workflow object.

### 3.2 Preserve historical context

Original entries should not be rewritten simply because a decision later becomes authoritative. Promotion and lifecycle state belong outside the source entry.

### 3.3 Target exact decisions

An entry may contain multiple decisions. Any ADR reference must identify both:

- the source entry
- the exact decision within that entry

A bare entry ID is not sufficient when several decisions are present.

### 3.4 Keep ADR lifecycle narrow

ADR sidecars are introduced because architecture decisions are central to Memory Seed's mission of preserving project reasoning. This proposal does not generalise lifecycle tracking to plans, incidents, findings, or arbitrary user-defined types.

### 3.5 Use deterministic application logic

Agents and users should not manually edit ADR sidecars. CLI and MCP workflows must call shared core logic that:

- validates references
- creates IDs
- inserts transition references
- checks current state
- prevents stale or contradictory updates

### 3.6 Make important context easy to retrieve

ADRs should include topics so agents and Memory Trace can retrieve high-signal decisions relevant to a specific project area before expanding into lower-signal session records.

---

## 4. Proposed Core Entry Types

Every new Memory Seed entry must declare a type from the controlled registry.

```yaml
type: session-log
```

The initial core types are:

| Type | Purpose |
|---|---|
| `session-log` | Chronological record of work performed during a session |
| `architecture-decision` | Entry created specifically to record an architectural decision |
| `decision-update` | Entry recording a change to the status, interpretation, or governance of an ADR |
| `finding` | Evidence-backed discovery, conclusion, contradiction, or validated observation |
| `research-planning` | Research reports, proposals, evaluated recommendations, and implementation planning |
| `handoff` | Compact transfer of working context to another agent, user, or session |

The registry should remain deliberately small.

Project-defined extensions may be considered later, but uncontrolled type creation should not be permitted in the initial implementation.

---

## 5. Separation of Type, Topic, Status, and Relationships

These concepts must remain independent.

| Field | Meaning |
|---|---|
| `type` | What kind of memory record is this? |
| `topics` | Which project areas does the record concern? |
| ADR sidecar status | What is the current lifecycle state of the promoted architecture decision? |
| relationships | How does the entry connect to other entries and artifacts? |
| author | Who or what created the entry? |

Example:

```yaml
id: entry-01J2XYZ
type: session-log
topics:
  - storage
  - retrieval
author: jean
```

An entry's `type` records its original role. A later ADR promotion does not require changing that type.

---

## 6. Decision Identity Within Entries

### 6.1 Why decision-level identity is required

A session log may contain several decisions:

- Markdown remains the source of truth.
- SQLite will provide the local index.
- Memory Trace will remain a separate package.

If an ADR sidecar referenced only the entry ID, it would be unclear which decision had been promoted.

### 6.2 Decision declarations

Entries that contain explicit decisions should declare them in metadata:

```yaml
---
id: entry-01J2XYZ
type: session-log
topics:
  - storage
  - retrieval

decisions:
  - id: decision-storage-source
    title: Markdown remains the source of truth
    topics:
      - storage
      - source-of-truth

  - id: decision-local-index
    title: SQLite will provide the local index
    topics:
      - storage
      - indexing
      - local-first
---
```

The corresponding Markdown sections should use deterministic anchors:

```markdown
## Decision: Markdown remains the source of truth
<a id="decision-storage-source"></a>

...

## Decision: SQLite will provide the local index
<a id="decision-local-index"></a>

...
```

### 6.3 Decision references

A full decision reference is:

```yaml
decision_ref:
  entry_id: entry-01J2XYZ
  decision_id: decision-local-index
```

The compact form may be:

```text
entry-01J2XYZ#decision-local-index
```

CLI and MCP operations must reject ambiguous references when the entry contains more than one declared decision.

---

## 7. ADR Creation and Promotion

ADRs may originate in two ways.

### 7.1 Direct ADR creation

An agent or user knowingly creates an entry dedicated to an architecture decision:

```yaml
---
id: entry-01J2ADR
type: architecture-decision
topics:
  - storage
  - indexing

decisions:
  - id: decision-local-index
    title: Use SQLite for the local index
    topics:
      - storage
      - indexing
      - local-first
---
```

The ADR sidecar is created in the same workflow.

### 7.2 Promotion from an existing entry

A decision originally recorded in a `session-log`, `finding`, or `research-planning` entry may later be promoted.

Promotion does not mutate the historical source entry. The presence of an ADR sidecar referencing the entry and decision ID is what establishes the ADR.

```text
Source entry
  └── exact decision anchor
          └── promoted through ADR sidecar
```

This preserves the source entry's original type and historical meaning.

---

## 8. ADR Identity

The ADR must have an identity separate from the source entry.

This is necessary because one entry may contain several decisions and therefore produce several ADRs.

```text
entry-01J2XYZ
├── decision-storage-source → adr-01J2SOURCE
└── decision-local-index    → adr-01J2LOCALINDEX
```

Each ADR sidecar therefore contains:

```yaml
adr_id: adr-01J2LOCALINDEX
```

The ADR ID becomes the stable identity used by transition, query, supersession, and Trace workflows.

---

## 9. ADR Sidecar

### 9.1 Purpose

The ADR sidecar is an authoritative, machine-maintained record of:

- ADR identity
- source decision reference
- title
- topics
- current status
- ordered transition history
- supersession relationships

It is not merely a rebuildable cache.

This is necessary because promotion may exist only through the sidecar. The source entry may remain an ordinary session log with no indication that one contained decision later became architecturally authoritative.

### 9.2 Location

Use one sidecar per ADR:

```text
.memory-seed/
├── sessions/
├── inbox/
├── indexes/
└── state/
    └── adrs/
        ├── adr-01J2SOURCE.yaml
        └── adr-01J2LOCALINDEX.yaml
```

A single central ADR status file should be avoided because it would create unnecessary conflicts when independent agents update unrelated decisions.

### 9.3 Proposed sidecar schema

```yaml
# GENERATED MEMORY SEED STATE
# Do not edit manually.
# Modify through Memory Seed CLI or MCP workflows.

schema_version: 1

adr_id: adr-01J2LOCALINDEX

source:
  entry_id: entry-01J2XYZ
  decision_id: decision-local-index

title: Use SQLite for the local index

topics:
  - storage
  - indexing
  - local-first

current_status: accepted

transitions:
  - from: null
    to: proposed
    changed_at: 2026-07-16T14:20:00Z
    update_entry_id: entry-01J2ADR

  - from: proposed
    to: accepted
    changed_at: 2026-07-16T16:10:00Z
    update_entry_id: entry-01J2UPDATE

supersedes: []
superseded_by: null
```

### 9.4 Duplication policy

The sidecar may duplicate:

- ADR title
- topics
- current status
- transition timestamps

This duplication is justified because the sidecar is an authoritative, script-maintained index used for fast deterministic retrieval.

The sidecar should not duplicate substantial rationale or evidence. Those belong in the referenced entries.

---

## 10. ADR Status Model

Draft status is not required. Draft material will generally remain in the inbox or unpromoted project documents.

The initial ADR statuses are:

- `proposed`
- `accepted`
- `rejected`
- `superseded`

Initial transitions:

```text
proposed → accepted
proposed → rejected
accepted → superseded
```

The implementation should remain conservative. Additional statuses such as `deprecated`, `withdrawn`, or `reopened` should require a later justified change.

### 10.1 Supersession

A superseded ADR must identify its replacement:

```yaml
current_status: superseded
superseded_by: adr-01J2REPLACEMENT
```

The replacement should contain the reciprocal relationship:

```yaml
supersedes:
  - adr-01J2LOCALINDEX
```

The workflow should validate both sides deterministically.

---

## 11. Decision-Update Entries

### 11.1 Purpose

`decision-update` is a real entry type.

Some interactions do not progress implementation but materially evolve a decision. Examples include:

- accepting or rejecting an ADR
- reconsidering assumptions
- confirming evidence
- narrowing scope
- superseding an earlier decision
- documenting why a proposal did not proceed

These interactions are valuable project memory and should be logged explicitly.

### 11.2 Proposed schema

```yaml
---
id: entry-01J2UPDATE
type: decision-update

adr_id: adr-01J2LOCALINDEX

topics:
  - storage
  - indexing
  - local-first

transition:
  from: proposed
  to: accepted

created_at: 2026-07-16T16:10:00Z
author: jean
---
```

The body contains the full reasoning:

```markdown
## Reason

SQLite was accepted after confirming that the index can be rebuilt
from Markdown sources without requiring a separate service.

## Evidence

- The local rebuild prototype completed successfully.
- Concurrent network writes are outside the initial release scope.
- The adapter boundary allows later enterprise storage options.
```

### 11.3 One update per ADR

A `decision-update` entry should normally update exactly one ADR.

This keeps:

- sidecar insertion deterministic
- validation simple
- decision timelines understandable
- conflict resolution bounded

---

## 12. Topic-Based Decision Context

Topics are required on ADR sidecars because ADRs are high-signal sources for future agents.

Example:

```yaml
topics:
  - storage
  - indexing
  - local-first
```

A targeted retrieval workflow can then operate as follows:

```text
Find accepted ADRs matching topic: retrieval
    ↓
Read matching sidecars
    ↓
Resolve exact source decisions
    ↓
Resolve linked decision-update entries
    ↓
Optionally collect supporting findings and session logs
    ↓
Return bounded decision context to the agent
```

This allows agents to collect architectural context before scanning lower-signal chronological records.

Topic validation must use the existing or proposed controlled topic index.

---

## 13. Relationship Model

Relationships should remain directed and stored once. Inverse edges should be generated by indexing and Trace rather than manually duplicated.

Relevant relationships include:

| Relationship | Meaning |
|---|---|
| `derived-from` | Decision emerged from another entry or artifact |
| `changes-status-of` | Decision-update entry changes an ADR's state |
| `supersedes` | ADR replaces an earlier ADR |
| `implemented-by` | ADR is realised by an implementation artifact |
| `verified-by` | ADR or its consequences are validated by evidence or tests |
| `related-to` | General association where no stronger semantic edge applies |

The ADR sidecar contains lifecycle-critical relationships. Broader supporting relationships remain in the source and update entries.

---

## 14. Deterministic Core Operations

The shared application layer should expose narrow functions:

```text
create_adr
promote_decision_to_adr
transition_adr
supersede_adr
get_adr
find_adrs_by_topic
validate_adr_sidecars
collect_adr_context
```

CLI and MCP interfaces must call the same implementation rather than maintaining separate behaviour.

### 14.1 Create ADR

```text
Create architecture-decision entry
    ↓
Generate entry ID
    ↓
Generate decision ID
    ↓
Generate ADR ID
    ↓
Create proposed sidecar
    ↓
Validate references and topics
```

### 14.2 Promote decision

```text
Resolve source entry
    ↓
Resolve exact decision ID
    ↓
Generate ADR ID
    ↓
Copy title and topics into sidecar
    ↓
Set initial status to proposed
    ↓
Validate uniqueness and references
```

### 14.3 Transition ADR

```text
Read ADR sidecar
    ↓
Validate expected current status
    ↓
Create decision-update entry
    ↓
Generate update entry ID
    ↓
Append update entry ID to sidecar transition history
    ↓
Update current status
    ↓
Validate final state
```

### 14.4 Supersede ADR

```text
Create or identify replacement ADR
    ↓
Create decision-update entry
    ↓
Transition original ADR to superseded
    ↓
Set superseded_by on original
    ↓
Set supersedes on replacement
    ↓
Validate reciprocal references
```

### 14.5 Collect decision context

```text
Filter sidecars by topic and status
    ↓
Resolve source entry and decision anchors
    ↓
Resolve decision-update entries
    ↓
Resolve supporting relationships
    ↓
Return bounded high-signal context
```

---

## 15. Agent-Facing Workflows

Agents should usually invoke bundled workflows rather than manually composing low-level functions.

Recommended workflows include:

- **Record architecture decision**
- **Promote existing decision**
- **Review and transition ADR**
- **Supersede ADR**
- **Collect architecture context by topic**
- **Validate ADR state**

These workflows should:

- minimise reliance on free-form LLM reasoning
- prompt only for decisions that cannot be derived
- discover facts through code and repository inspection
- use deterministic scripts for writes
- return explicit completion criteria

The system should prefer deterministic insertion and validation wherever possible.

---

## 16. Concurrency and Worktrees

One sidecar per ADR reduces conflicts between unrelated work.

Concurrent transitions on the same ADR remain possible and must use optimistic concurrency.

A transition request must include the expected current state:

```text
transition adr-01J2LOCALINDEX
from: proposed
to: accepted
```

The operation must fail if the current state is no longer `proposed`.

This protects against:

- stale agent context
- parallel contradictory decisions
- worktree divergence
- accidental repeated transitions

After merges, ADR validation should detect contradictory or duplicated transition histories.

---

## 17. Sidecar Protection and Integrity

The sidecar is authoritative but physically stored in a Git repository, so it cannot be made literally uneditable.

The intended contract should be enforced through:

- generated-file warnings
- CLI/MCP-only documented write operations
- schema validation
- pre-commit validation
- CI validation
- optimistic concurrency checks
- optional integrity metadata in a later version

Direct user or LLM editing of sidecars is unsupported.

Validation should flag sidecars that could not have resulted from an allowed workflow.

---

## 18. Validation Rules

The validator should ensure:

### Entry typing

- every new entry has a `type`
- the type exists in the controlled registry
- required type-specific fields are present

### Decision identity

- declared decision IDs are unique within the entry
- deterministic anchors exist for declared decisions
- decision references resolve to a real entry and decision

### ADR sidecars

- ADR IDs are unique
- source entry exists
- source decision exists
- topics exist in the topic index
- current status is valid
- transition sequence is valid
- transition timestamps are ordered
- every `update_entry_id` resolves
- update entries target the same ADR
- latest transition matches `current_status`
- superseded ADRs identify a replacement
- reciprocal supersession references agree

### Concurrency

- requested `from` state matches the actual current state
- duplicate update entry IDs are rejected
- repeated identical transitions are rejected unless explicitly supported

---

## 19. Memory Trace Requirements

Trace implementation is deferred, but the data model must support these future views.

### 19.1 Active ADR view

Display accepted ADRs, filterable by topic.

### 19.2 Proposed decision view

Separate unresolved proposed ADRs from accepted governing decisions.

### 19.3 ADR lifecycle timeline

Display:

- proposal
- acceptance or rejection
- later supersession
- linked decision-update entries

### 19.4 Supersession chain

Allow users to follow:

```text
ADR-0012 → superseded by ADR-0021 → superseded by ADR-0034
```

### 19.5 Decision pull-forward

When viewing a topic, component, file, session, or implementation timeline, Trace should surface relevant accepted ADRs even though their source entries occurred earlier.

### 19.6 Context collection

Trace and MCP should be able to create bounded decision-context packages for agents by:

- topic
- status
- component
- related entries
- implementation artifact

These requirements should be documented now but delivered in a later Trace-specific implementation phase.

---

## 20. Migration

### 20.1 Existing entries

Existing entries should be migrated conservatively:

```yaml
type: session-log
```

The migration should not automatically classify historical entries as findings, plans, or ADRs.

### 20.2 ADR discovery

A discovery tool may identify potential architectural decisions:

```text
Possible ADR candidate:
entry-01J2XYZ#decision-local-index
```

However, candidate detection must not create authority.

Promotion requires an explicit CLI or MCP workflow that creates the ADR sidecar.

### 20.3 Compatibility period

During migration, the validator may support a temporary compatibility mode for legacy entries without `type`. New entries should require `type` immediately once the schema version changes.

---

## 21. Explicit Scope Exclusions

The initial implementation does not include:

- generic lifecycle sidecars
- sidecars for plans, incidents, findings, or handoffs
- arbitrary user-defined state machines
- independent lifecycle-event graph nodes
- multi-approver governance
- cryptographic approval records
- regulatory audit workflows
- automatic ADR promotion
- automatic architectural compliance enforcement
- LLM or user direct sidecar modification
- general-purpose event sourcing
- automatic rewriting of historical entry types

These exclusions are deliberate protections against scope creep.

---

## 22. Risks and Mitigations

### 22.1 Metadata complexity

**Risk:** Entry typing, decision anchors, ADR IDs, and sidecars increase schema complexity.

**Mitigation:** Keep the type registry small, limit sidecars to ADRs, and provide bundled workflows rather than manual file editing.

### 22.2 Sidecar drift

**Risk:** A sidecar may disagree with referenced entries.

**Mitigation:** Only shared core logic may write sidecars. Pre-commit and CI validation should enforce transition and reference integrity.

### 22.3 Ambiguous decision references

**Risk:** An ADR may reference an entry containing several decisions.

**Mitigation:** Require `entry_id + decision_id`. Reject bare entry references when ambiguous.

### 22.4 Concurrent transitions

**Risk:** Two agents may change the same ADR in separate worktrees.

**Mitigation:** Require expected current status and reject stale transitions.

### 22.5 Type-taxonomy growth

**Risk:** New types may proliferate and fragment retrieval.

**Mitigation:** Maintain a controlled core registry and require separate justification for additions.

### 22.6 ADR overproduction

**Risk:** Agents may promote minor decisions into ADRs.

**Mitigation:** ADR workflows should require the decision to be consequential, cross-cutting, costly to reverse, or surprising without context.

---

## 23. Implementation Phases

### Phase 1: Mandatory entry types

- Add `type` to the entry schema.
- Create the initial controlled type registry.
- Update session-writing tools.
- Add migration support for legacy entries.
- Add type validation.

### Phase 2: Decision identity

- Add decision declarations to entry metadata.
- Generate deterministic decision anchors.
- Add exact decision resolution by `entry_id + decision_id`.
- Validate anchor and metadata consistency.

### Phase 3: ADR sidecars

- Add ADR ID generation.
- Add ADR sidecar schema.
- Implement direct ADR creation.
- Implement promotion of existing decisions.
- Add topic copying and validation.

### Phase 4: ADR transitions

- Implement `decision-update` entries.
- Implement `transition_adr`.
- Implement optimistic concurrency.
- Implement supersession and reciprocal validation.

### Phase 5: Retrieval and validation

- Implement topic-based ADR search.
- Implement ADR context collection.
- Add pre-commit and CI validation.
- Add repair guidance for invalid sidecars.

### Phase 6: Trace integration

Deferred to a separate proposal or implementation plan:

- active ADR views
- transition timelines
- supersession chains
- decision pull-forward
- topic-based architecture context

---

## 24. Acceptance Criteria

The proposal is successfully implemented when:

1. Every new Memory Seed entry has a validated type.
2. Existing entries can be migrated to `session-log` without content loss.
3. One entry can declare multiple uniquely addressable decisions.
4. A specific decision can be promoted without mutating the source entry.
5. Each promoted decision receives a unique ADR ID and sidecar.
6. ADR sidecars contain validated topics and current status.
7. Status changes create `decision-update` entries automatically.
8. Transition entry IDs are inserted into sidecars deterministically.
9. Invalid or stale transitions are rejected.
10. Superseded ADRs reference their replacements reciprocally.
11. Agents can retrieve accepted ADRs by topic.
12. Direct sidecar edits are detected by validation.
13. CLI and MCP workflows use the same core implementation.
14. No generic lifecycle framework is introduced.

---

## 25. Final Recommendation

Adopt mandatory entry typing and ADR-specific sidecars.

The proposed design gives Memory Seed a stronger semantic model without abandoning its Markdown-native, chronological architecture. It allows architecture decisions to be promoted from ordinary project memory, tracked through a narrow lifecycle, surfaced by topic, and pulled forward by Memory Trace.

The key boundary is equally important:

> ADR sidecars are a specialised mechanism for preserving authoritative project reasoning, not the beginning of a general workflow or event-sourcing platform.

That boundary should remain explicit throughout implementation.
