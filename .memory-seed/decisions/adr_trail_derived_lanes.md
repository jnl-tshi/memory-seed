---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_trail_derived_lanes
title: Trail derives display lanes without authored graph edges
topics:
  - memory-trace
  - trail
  - graph
created_at: 2026-08-06T17:12:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Trail derives display lanes without authored graph edges

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L171`

### Decision

Trail generates continuity lanes derived from lifecycle edges without requiring or adding authored graph edges.

### Why

Reduces manual edge annotation burden; derived lanes stay synchronized with true causality and evolution chain topology without user needing to draw additional edges.

### How it evolved

Shipped in Wave 1 (2026-07-15) as part of Trace continuity features; plan documented in docs/5_Completed/evolution-edges-plan.md.

### Constitution

- `constitution:v1#markdown-authority` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:12:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "event_id": "adre_6e9d23649def2cb039fb",
  "founding_quote": "Trail derives display lanes without adding authored graph edges.",
  "founding_source": ".memory-seed/index.md#L171",
  "source": "derived"
}
```

#### Decision

Trail generates continuity lanes derived from lifecycle edges without requiring or adding authored graph edges.

#### Why

Reduces manual edge annotation burden; derived lanes stay synchronized with true causality and evolution chain topology without user needing to draw additional edges.

#### Evolution

Shipped in Wave 1 (2026-07-15) as part of Trace continuity features; plan documented in docs/5_Completed/evolution-edges-plan.md.

### revision-accepted - 2026-08-06T21:30:00Z

```json
{
  "event_id": "adre_4d4d1d741f0f77e7522a",
  "founding_source": ".memory-seed/index.md#L171",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
