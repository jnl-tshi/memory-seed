---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_archive_before_replace
title: Archive control-plane snapshots before replacing versioned artifacts
topics:
  - control-plane
  - release
  - process-management
created_at: 2026-08-06T17:09:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Archive control-plane snapshots before replacing versioned artifacts

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_903jqy9v4pr8g388:d2`

### Decision

Before replacing versioned artifacts during a release, prior control-plane snapshots must be archived under .memory-seed/archive/<version>/ as a required procedure step.

### Reason

Version bumps affect reusable procedure files across many control-plane documents, and archiving prior snapshots preserves the historical record and enables rollback or auditing of changes across versions. This precondition was mentioned informally but lacked an owned procedure step.

### Impact

First implemented during the 2.5→2.6 version bump by archiving the true 2.5 reusable procedure files to .memory-seed/archive/2.5/ before replacement. Later formalized into release_publishing.md as a required step in the full version-bump and release procedure.

### Constitution

- `constitution:v1#append-only` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:09:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "event_id": "adre_7087b33014647f6e8468",
  "founding_quote": "Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts.",
  "founding_source": ".memory-seed/policy.md#L74",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

#### Reason

Preserves audit trail of control-plane evolution and enables recovery if a replacement is found to be incorrect or incomplete.

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:02:00Z

```json
{
  "event_id": "adre_fe66e7e85d4a55bfbd32",
  "founding_source": ".memory-seed/policy.md#L74",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/policy.md#L74.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/policy.md#L74 becomes the authoritative decision; later contrary evidence requires a successor revision.

### context-added - 2026-08-07T05:20:00Z

```json
{
  "event_id": "adre_da9cb524e97d74ca89a1",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-757053d4:d4"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Record the supplied decisions as context for this ADR.

#### Reason

An instance of the archive-before-replace rule being followed: the 2.5 reusable procedure files were archived before the 2.6 control plane replaced them. Evidence of the practice, not the decision establishing it.

#### Impact

This adds supporting context only; it does not change ADR membership, status, or authority.

### revision-proposed - 2026-08-08T19:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_903jqy9v4pr8g388:d2",
  "event_id": "adre_9bf59d8b04b1cc4adfe0",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

#### Reason

Rests on the session decision that instituted it: "the operator-owned archive snapshot step" (mse_903jqy9v4pr8g388:d2). Formally establishes archive snapshot as a required procedure step in release_publishing.md before version-bump replacement.

#### Impact

Founded from .memory-seed/policy.md#L74; this revision moves the concern off that control-file line onto mse_903jqy9v4pr8g388:d2, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:01:00Z

```json
{
  "decision_ref": "mse_903jqy9v4pr8g388:d2",
  "event_id": "adre_90ad3319c38d461805ab",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_903jqy9v4pr8g388:d2.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_903jqy9v4pr8g388:d2 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:01:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_903jqy9v4pr8g388:d2",
  "event_id": "adre_83d73517693d82b25ea0",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-757053d4:d4"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Before replacing versioned artifacts during a release, prior control-plane snapshots must be archived under .memory-seed/archive/<version>/ as a required procedure step.

#### Reason

Version bumps affect reusable procedure files across many control-plane documents, and archiving prior snapshots preserves the historical record and enables rollback or auditing of changes across versions. This precondition was mentioned informally but lacked an owned procedure step.

#### Impact

First implemented during the 2.5→2.6 version bump by archiving the true 2.5 reusable procedure files to .memory-seed/archive/2.5/ before replacement. Later formalized into release_publishing.md as a required step in the full version-bump and release procedure.

### revision-accepted - 2026-08-08T23:01:40Z

```json
{
  "decision_ref": "mse_903jqy9v4pr8g388:d2",
  "event_id": "adre_d2b707293f4e3303e720",
  "expected_authoritative_decision": "founding:.memory-seed/policy.md#L74",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_903jqy9v4pr8g388:d2.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_903jqy9v4pr8g388:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.
