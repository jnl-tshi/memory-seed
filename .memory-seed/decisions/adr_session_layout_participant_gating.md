---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `ms-38098d7a:d1`

### Decision

Per-user session files are written only when a user identity is explicitly configured via .memory-seed/local.yaml, MEMORY_SEED_USER environment variable, or command-line argument. Installs without user configuration remain on the flat session file. The split is a write-time change with no migration; reads discover both layouts, and an explicit --user flag bypasses the opt-in gate.

### Reason

Identity and layout are separable: recording who wrote an entry should not force a file split until a second author exists. A single configured user represents deliberate intent rather than an active multi-user state, so waiting for explicit user configuration makes the layout change explicit and mechanical. Dual-read capability ensures reversibility without touching history.

### Impact

An initial proposal refined the multi-user approach for future implementation. Phase 1 added read-side compatibility for both file layouts without changing write targets. The final member implemented the write-side decision: opt-in user identity enables per-user files, while no-user installs stay on the legacy flat file.

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
  "impact_provenance": "preserved",
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

#### Reason

Identity and layout are separable: recording who wrote an entry should not force a file split until a second author actually exists. One configured user is declarative intent, not yet multi-user, so waiting for the second participant makes the layout move explicit and mechanical rather than a surprise. Dual-read means the change is reversible without touching history.

#### Impact

2026-06-13 proposed the layout as deferred work; 2026-06-14 implemented dual-read discovery so both layouts resolve, then added user-aware session targets with opt-in local identity; participant-count gating followed on 2026-07-02.

### revision-rejected - 2026-08-08T23:18:00Z

```json
{
  "decision_ref": "ms-38098d7a:d1",
  "event_id": "adre_76593aaff7773033c56a",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject ms-38098d7a:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

ms-38098d7a:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:18:20Z

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
  "event_id": "adre_a86de0ad8b52b6a5f13f",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-41f4f32a:d1",
    "ms-3cad2a35:d2"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Per-user session files are written only when a user identity is explicitly configured via .memory-seed/local.yaml, MEMORY_SEED_USER environment variable, or command-line argument. Installs without user configuration remain on the flat session file. The split is a write-time change with no migration; reads discover both layouts, and an explicit --user flag bypasses the opt-in gate.

#### Reason

Identity and layout are separable: recording who wrote an entry should not force a file split until a second author exists. A single configured user represents deliberate intent rather than an active multi-user state, so waiting for explicit user configuration makes the layout change explicit and mechanical. Dual-read capability ensures reversibility without touching history.

#### Impact

An initial proposal refined the multi-user approach for future implementation. Phase 1 added read-side compatibility for both file layouts without changing write targets. The final member implemented the write-side decision: opt-in user identity enables per-user files, while no-user installs stay on the legacy flat file.

### revision-accepted - 2026-08-08T23:18:40Z

```json
{
  "decision_ref": "ms-38098d7a:d1",
  "event_id": "adre_f9247964776bcdd856e3",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept ms-38098d7a:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

ms-38098d7a:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
