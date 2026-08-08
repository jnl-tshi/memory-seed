---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_session_layout_participant_gating
title: Per-user session files activate only at two or more participants
topics:
  - multi-user-sessions
  - session-logging
  - continuity
created_at: 2026-08-08T03:09:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Per-user session files activate only at two or more participants

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Per-user session files are written only when two or more participants are registered. A single configured user stays on the flat file, preserving the solo-first design. Reads discover both layouts, so the split is a write-time change rather than a migration, and an explicit `--user` bypasses the gate.

### Why

Identity and layout are separable: recording who wrote an entry should not force a file split until a second author actually exists. One configured user is declarative intent, not yet multi-user, so waiting for the second participant makes the layout move explicit and mechanical rather than a surprise. Dual-read means the change is reversible without touching history.

### How it evolved

2026-06-13 proposed the layout as deferred work; 2026-06-14 implemented dual-read discovery so both layouts resolve, then added user-aware session targets with opt-in local identity; participant-count gating followed on 2026-07-02.

### Constitution

- `constitution:v1#ownership` (governing)
- `constitution:v1#append-only` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:09:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-38098d7a:d1",
  "event_id": "adre_196731e4aa0b7c290bee",
  "source": "derived",
  "supporting_decisions": [
    "ms-41f4f32a:d1",
    "ms-3cad2a35:d2"
  ],
  "update_entry_id": "ms-38098d7a"
}
```

#### Decision

Per-user session files are written only when two or more participants are registered. A single configured user stays on the flat file, preserving the solo-first design. Reads discover both layouts, so the split is a write-time change rather than a migration, and an explicit `--user` bypasses the gate.

#### Why

Identity and layout are separable: recording who wrote an entry should not force a file split until a second author actually exists. One configured user is declarative intent, not yet multi-user, so waiting for the second participant makes the layout move explicit and mechanical rather than a surprise. Dual-read means the change is reversible without touching history.

#### Evolution

2026-06-13 proposed the layout as deferred work; 2026-06-14 implemented dual-read discovery so both layouts resolve, then added user-aware session targets with opt-in local identity; participant-count gating followed on 2026-07-02.
