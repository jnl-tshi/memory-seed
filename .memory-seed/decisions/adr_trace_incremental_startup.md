---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_trace_incremental_startup
title: Trace startup incremental; immutable git derivations persist
topics:
  - memory-trace
  - performance
  - seed-core
created_at: 2026-08-06T17:11:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Trace startup incremental; immutable git derivations persist

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L83`

### Decision

Memory Trace startup is incremental: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and file-entry index is lazy.

### Why

Incremental startup drastically improves performance. Warm start reduced from 44.25s to ~308ms; persisted derivations and lazy indexing enable efficient rebuilds and reconciliation.

### How it evolved

Implemented 2026-07-21 (mse_42e8zzd7); completed the derived-projection plan's final deferred piece.

### Constitution

- `constitution:v1#markdown-authority` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:11:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "event_id": "adre_e9d0e103353c2c5dc178",
  "founding_quote": "Memory Trace startup is incremental as of 2026-07-21: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and the file-entry index is lazy.",
  "founding_source": ".memory-seed/index.md#L83",
  "source": "derived"
}
```

#### Decision

Memory Trace startup is incremental: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and file-entry index is lazy.

#### Why

Incremental startup drastically improves performance. Warm start reduced from 44.25s to ~308ms; persisted derivations and lazy indexing enable efficient rebuilds and reconciliation.

#### Evolution

Implemented 2026-07-21 (mse_42e8zzd7); completed the derived-projection plan's final deferred piece.

### revision-accepted - 2026-08-06T21:29:00Z

```json
{
  "event_id": "adre_50fd63670bdba836dc6c",
  "founding_source": ".memory-seed/index.md#L83",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
