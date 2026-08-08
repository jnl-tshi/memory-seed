---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_append_rule_is_an_invariant
title: The append rule is stated as an invariant, not as a mechanism
topics:
  - session-logging
  - agent-rules
created_at: 2026-08-08T03:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# The append rule is stated as an invariant, not as a mechanism

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

The agent contract states the append INVARIANT - an entry is added at the physical end of its file, never inserted above existing content, and chronological order holds - and does not mandate the tool that achieves it. Shell append and Python append mode are optional tips, not requirements.

### Why

The contract is read by any file-reading agent, so mandating `>>` assumed shell or Python access and was platform-unsafe: the shell example simply fails for an agent that edits files directly. Stating the invariant lets each agent satisfy it with whatever writing surface it has, while the property that actually matters - nothing is inserted above existing content - is unchanged. This is distinct from Constitution Invariant #2, which says the past IS append-only; this concern is about how that rule is expressed to the agents bound by it.

### How it evolved

The rule first shipped as a mechanism, requiring shell append or Python append mode as the method for writing session entries; it was then reframed as a vendor-neutral invariant with the mechanism demoted to an optional shell tip.

### Constitution

- `constitution:v1#append-only` (governing)
- `constitution:v1#model-independence` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#model-independence",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-e30b9c47:d1",
  "event_id": "adre_8e176ec34cf3f51cabda",
  "source": "derived",
  "supporting_decisions": [
    "ms-d15e8a03:d1"
  ],
  "update_entry_id": "ms-e30b9c47"
}
```

#### Decision

The agent contract states the append INVARIANT - an entry is added at the physical end of its file, never inserted above existing content, and chronological order holds - and does not mandate the tool that achieves it. Shell append and Python append mode are optional tips, not requirements.

#### Why

The contract is read by any file-reading agent, so mandating `>>` assumed shell or Python access and was platform-unsafe: the shell example simply fails for an agent that edits files directly. Stating the invariant lets each agent satisfy it with whatever writing surface it has, while the property that actually matters - nothing is inserted above existing content - is unchanged. This is distinct from Constitution Invariant #2, which says the past IS append-only; this concern is about how that rule is expressed to the agents bound by it.

#### Evolution

The rule first shipped as a mechanism, requiring shell append or Python append mode as the method for writing session entries; it was then reframed as a vendor-neutral invariant with the mechanism demoted to an optional shell tip.
