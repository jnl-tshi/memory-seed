---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_djvwtfx02kjr5j1n:d2`

### Decision

Documentation is organized into lifecycle-based folders where folder location indicates the proposal's status. Active proposals remain in the root planning directory; completed proposals move to a `completed/` folder. Cross-references are maintained across moves to preserve the reference graph and keep the overall documentation coherent.

### Reason

Comprehensive documentation of system functionality requires regular refresh to remain authoritative as features ship. Organizing proposals by completion status and fixing their cross-references maintains discoverability, prevents duplicate planning work on shipped items, and makes the active roadmap readable at a glance. The practice ensures that documentation stays current and that stale references don't mislead.

### Impact

The audit documentation was authored to provide comprehensive system specification with data-flow diagrams. It was then maintained across multiple release cycles to keep it current with new features and API changes. The documentation organization was systematized by creating a `completed/` folder for proposals of shipped features and repairing stale cross-references to preserve the reference graph. This pattern continues as the system evolves.

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
  "impact_provenance": "preserved",
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

#### Reason

The lanes had been reorganised ad hoc across several sessions, leaving stale cross-references and unclear boundaries. Making the folder the state, and enforcing it through a reusable skill, keeps the roadmap discoverable, prevents duplicate work, and makes proposal status readable without opening every document.

#### Impact

2026-07-02 separated completed work from active and fixed the cross-references it broke; 2026-07-03 reorganised placement and refreshed the audit; 2026-07-04 moved three implemented plans across; 2026-07-12 added the seeded `proposal_lifecycle` skill.

### revision-rejected - 2026-08-08T23:04:00Z

```json
{
  "decision_ref": "mse_djvwtfx02kjr5j1n:d2",
  "event_id": "adre_29412b768ea59dbef02e",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_djvwtfx02kjr5j1n:d2.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_djvwtfx02kjr5j1n:d2 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:04:20Z

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
  "event_id": "adre_36aa24d0bf21a3b7a5f1",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-a939b6b4:d2",
    "ms-4e1b8a07:d1",
    "mse_21d4kcx6g1vxt0ky:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Documentation is organized into lifecycle-based folders where folder location indicates the proposal's status. Active proposals remain in the root planning directory; completed proposals move to a `completed/` folder. Cross-references are maintained across moves to preserve the reference graph and keep the overall documentation coherent.

#### Reason

Comprehensive documentation of system functionality requires regular refresh to remain authoritative as features ship. Organizing proposals by completion status and fixing their cross-references maintains discoverability, prevents duplicate planning work on shipped items, and makes the active roadmap readable at a glance. The practice ensures that documentation stays current and that stale references don't mislead.

#### Impact

The audit documentation was authored to provide comprehensive system specification with data-flow diagrams. It was then maintained across multiple release cycles to keep it current with new features and API changes. The documentation organization was systematized by creating a `completed/` folder for proposals of shipped features and repairing stale cross-references to preserve the reference graph. This pattern continues as the system evolves.

### revision-accepted - 2026-08-08T23:04:40Z

```json
{
  "decision_ref": "mse_djvwtfx02kjr5j1n:d2",
  "event_id": "adre_ce3a167236641c37f5ae",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_djvwtfx02kjr5j1n:d2.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_djvwtfx02kjr5j1n:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.
