---
format: memory-seed-adr/1
schema_version: 1
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

Authoritative decision: `founding:.memory-seed/policy.md#L74`

### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

### Why

Preserves audit trail of control-plane evolution and enables recovery if a replacement is found to be incorrect or incomplete.

### How it evolved

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#append-only` (governing)

### Awaiting review

- `mse_903jqy9v4pr8g388:d2` - Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable...

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
  "source": "derived"
}
```

#### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

#### Why

Preserves audit trail of control-plane evolution and enables recovery if a replacement is found to be incorrect or incomplete.

#### Evolution

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:02:00Z

```json
{
  "event_id": "adre_fe66e7e85d4a55bfbd32",
  "founding_source": ".memory-seed/policy.md#L74",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### context-added - 2026-08-07T05:20:00Z

```json
{
  "event_id": "adre_da9cb524e97d74ca89a1",
  "source": "derived",
  "supporting_decisions": [
    "ms-757053d4:d4"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Reason

An instance of the archive-before-replace rule being followed: the 2.5 reusable procedure files were archived before the 2.6 control plane replaced them. Evidence of the practice, not the decision establishing it.

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
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

#### Why

Rests on the session decision that instituted it: "the operator-owned archive snapshot step" (mse_903jqy9v4pr8g388:d2). Formally establishes archive snapshot as a required procedure step in release_publishing.md before version-bump replacement.

#### Evolution

Founded from .memory-seed/policy.md#L74; this revision moves the concern off that control-file line onto mse_903jqy9v4pr8g388:d2, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
