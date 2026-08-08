---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_documentation_lane_structure
title: "Documentation lanes: folder is lifecycle state, with a skill codifying the flow"
topics:
  - documentation
  - proposal-lifecycle
  - session-logging
created_at: 2026-08-08T03:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Documentation lanes: folder is lifecycle state, with a skill codifying the flow

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Documentation folders are lifecycle lanes - intake, active planning, live spec, reference, and terminal outcomes. An active proposal carries a status block and completion criteria; a completed one moves lane with its supersession pointers intact. A seeded `proposal_lifecycle` skill codifies the flow and its gates.

### Why

The lanes had been reorganised ad hoc across several sessions, leaving stale cross-references and unclear boundaries. Making the folder the state, and enforcing it through a reusable skill, keeps the roadmap discoverable, prevents duplicate work, and makes proposal status readable without opening every document.

### How it evolved

2026-07-02 separated completed work from active and fixed the cross-references it broke; 2026-07-03 reorganised placement and refreshed the audit; 2026-07-04 moved three implemented plans across; 2026-07-12 added the seeded `proposal_lifecycle` skill.

### Constitution

- `constitution:v1#folder-lifecycle` (governing)
- `constitution:v1#single-source` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#folder-lifecycle",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_djvwtfx02kjr5j1n:d2",
  "event_id": "adre_8f99c580500fd5affb85",
  "source": "derived",
  "supporting_decisions": [
    "ms-a939b6b4:d2",
    "ms-4e1b8a07:d1",
    "mse_21d4kcx6g1vxt0ky:d1"
  ],
  "update_entry_id": "mse_djvwtfx02kjr5j1n"
}
```

#### Decision

Documentation folders are lifecycle lanes - intake, active planning, live spec, reference, and terminal outcomes. An active proposal carries a status block and completion criteria; a completed one moves lane with its supersession pointers intact. A seeded `proposal_lifecycle` skill codifies the flow and its gates.

#### Why

The lanes had been reorganised ad hoc across several sessions, leaving stale cross-references and unclear boundaries. Making the folder the state, and enforcing it through a reusable skill, keeps the roadmap discoverable, prevents duplicate work, and makes proposal status readable without opening every document.

#### Evolution

2026-07-02 separated completed work from active and fixed the cross-references it broke; 2026-07-03 reorganised placement and refreshed the audit; 2026-07-04 moved three implemented plans across; 2026-07-12 added the seeded `proposal_lifecycle` skill.
