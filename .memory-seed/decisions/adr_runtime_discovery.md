---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_runtime_discovery
title: Runtime discovery walks to the nearest .memory-seed
topics:
  - control-plane
  - agent-rules
created_at: 2026-08-06T17:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Runtime discovery walks to the nearest .memory-seed

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L120`

### Decision

Runtime discovery uses nearest-ancestor `.memory-seed/` directory, walking upward from current working directory to find the active runtime.

### Reason

Canonical runtime location enables portable memory systems and supports nested sub-project runtimes with automatic scoping.

### Impact

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#authority` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    }
  ],
  "event_id": "adre_53ef3803d1d2dae27212",
  "founding_quote": "Runtime discovery walks upward from `cwd` and uses the nearest `.memory-seed/`.",
  "founding_source": ".memory-seed/index.md#L120",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Runtime discovery uses nearest-ancestor `.memory-seed/` directory, walking upward from current working directory to find the active runtime.

#### Reason

Canonical runtime location enables portable memory systems and supports nested sub-project runtimes with automatic scoping.

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:22:00Z

```json
{
  "event_id": "adre_ad94b19d6358fdc0c727",
  "founding_source": ".memory-seed/index.md#L120",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L120.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L120 becomes the authoritative decision; later contrary evidence requires a successor revision.
