---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_edge_kinds
title: Four never-merged edge kinds, forward-only and acyclic
topics:
  - lifecycle-edges
  - graph
created_at: 2026-08-06T17:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Four never-merged edge kinds, forward-only and acyclic

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L171`

### Decision

Lifecycle edges comprise four never-merged kinds: `replaces`, `evolves`, `related_entries`, and `evolved_by` (inverse). Edges are forward-only and acyclic by contract.

### Why

Four independent relationship claims deserve distinct semantic labels. Forward-only and acyclic structure ensures the edge graph is append-only and prevents cycles in artifact lineage.

### How it evolved

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#edge-kinds` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "governing"
    }
  ],
  "event_id": "adre_f7fceb0992180d5596b9",
  "founding_quote": "Evolution edges and artifact lineage (core shipped in 2.18.0; Trace continuity completed 2026-07-15): typed `evolves:` plus read-time `evolved_by`, inverse-field and continuity validation",
  "founding_source": ".memory-seed/index.md#L171",
  "source": "derived"
}
```

#### Decision

Lifecycle edges comprise four never-merged kinds: `replaces`, `evolves`, `related_entries`, and `evolved_by` (inverse). Edges are forward-only and acyclic by contract.

#### Why

Four independent relationship claims deserve distinct semantic labels. Forward-only and acyclic structure ensures the edge graph is append-only and prevents cycles in artifact lineage.

#### Evolution

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:10:00Z

```json
{
  "event_id": "adre_9f3c03fef3b77de88b8d",
  "founding_source": ".memory-seed/index.md#L171",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### context-added - 2026-08-08T18:00:00Z

```json
{
  "event_id": "adre_e051b73e16bd58be0ae2",
  "source": "derived",
  "supporting_decisions": [
    "mse_kdhw53hzp4nh8wwm:d1"
  ],
  "update_entry_id": "mse_9szn9geevrgdntng"
}
```

#### Reason

PROBE2: does a branch-modified ADR survive the merge now that writes are staged?
