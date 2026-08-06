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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

### Why

Preserves audit trail of control-plane evolution and enables recovery if a replacement is found to be incorrect or incomplete.

### How it evolved

Founded from the control file; no session lineage attached yet.

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
  "source": "derived"
}
```

#### Decision

Archive prior control-plane snapshots under .memory-seed/archive/<version>/ before replacing reusable versioned artifacts.

#### Why

Preserves audit trail of control-plane evolution and enables recovery if a replacement is found to be incorrect or incomplete.

#### Evolution

Founded from the control file; no session lineage attached yet.
