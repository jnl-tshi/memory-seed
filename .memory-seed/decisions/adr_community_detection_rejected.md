---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_community_detection_rejected
title: Topology-community detection measured and rejected
topics:
  - memory-trace
  - graph
  - design-evaluation
created_at: 2026-08-06T17:13:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Topology-community detection measured and rejected

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Rejected**

Authoritative decision: not yet accepted

### Decision

Reject topology-community detection for graph layout based on corpus-density measurement. The feature does not gate B0b acceptance.

### Why

Measured corpus density and found community detection does not improve layout effectiveness for this corpus. Alternative force-based layout achieves the required visualization quality.

### How it evolved

Measured and rejected 2026-07-26 (mse_fud39yw86e7v2uy); decision recorded to document evaluation rather than defer the feature.

### Constitution

- `constitution:v1#evidence-first` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:13:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#evidence-first",
      "role": "governing"
    }
  ],
  "event_id": "adre_088fcbc7220e403c32ee",
  "founding_quote": "Topology-community detection was measured and closed 2026-07-26 (rejected, not deferred)",
  "founding_source": ".memory-seed/index.md#L73",
  "source": "derived"
}
```

#### Decision

Reject topology-community detection for graph layout based on corpus-density measurement. The feature does not gate B0b acceptance.

#### Why

Measured corpus density and found community detection does not improve layout effectiveness for this corpus. Alternative force-based layout achieves the required visualization quality.

#### Evolution

Measured and rejected 2026-07-26 (mse_fud39yw86e7v2uy); decision recorded to document evaluation rather than defer the feature.

### revision-rejected - 2026-08-06T18:13:00Z

```json
{
  "event_id": "adre_2d123bf3b2c150098ecf",
  "founding_source": ".memory-seed/index.md#L73",
  "source": "derived"
}
```

#### Reason

Measured corpus density and found community detection does not improve layout effectiveness for this corpus. Alternative force-based layout achieves the required visualization quality.

### context-added - 2026-08-07T05:22:00Z

```json
{
  "event_id": "adre_3b40e48ffd4d4744a18d",
  "source": "derived",
  "supporting_decisions": [
    "mse_3yvakpxdshc95e68:d1"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Reason

Records the implemented alternative and states plainly that Louvain/Leiden are not implemented - the concrete form of the rejection this concern holds.
