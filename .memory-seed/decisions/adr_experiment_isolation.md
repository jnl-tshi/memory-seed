---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_experiment_isolation
title: Experiment fixture isolation is structural via nearest-runtime discovery
topics:
  - testing
  - seed-core
  - functionality-audit
created_at: 2026-08-06T17:17:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Experiment fixture isolation is structural via nearest-runtime discovery

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L107`

### Decision

Experimental fixtures achieve isolation through structural design via nearest-runtime discovery. Each generated fixture is a standalone git repository with its own `.memory-seed/` runtime. Fixture runtimes are throwaway sub-project runtimes deliberately not individually registered in the parent index.

### Why

Isolation is structural and was proven at build time: a fixture write left the parent corpus counts unchanged. Nearest-runtime discovery provides automatic, predictable fixture isolation without requiring manual registration or explicit isolation machinery.

### How it evolved

Founded from the control file; outlined in the agent-capture experiment specification. Session decision mse_vaz9d3h7x4bcmd1t:d1 (2026-08-04) narrowed isolation assertion to the parent session store specifically, refining the validation claim while preserving structural isolation.

### Constitution

- `constitution:v1#authority` (governing)
- `constitution:v1#prove-automation` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:17:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "event_id": "adre_88cc5c2e833623560d62",
  "founding_quote": "Isolation is structural (nearest-runtime discovery) and was proven at build time: a fixture write left the parent corpus counts unchanged.",
  "founding_source": ".memory-seed/index.md#L107",
  "source": "derived"
}
```

#### Decision

Experimental fixtures achieve isolation through structural design via nearest-runtime discovery. Each generated fixture is a standalone git repository with its own `.memory-seed/` runtime. Fixture runtimes are throwaway sub-project runtimes deliberately not individually registered in the parent index.

#### Why

Isolation is structural and was proven at build time: a fixture write left the parent corpus counts unchanged. Nearest-runtime discovery provides automatic, predictable fixture isolation without requiring manual registration or explicit isolation machinery.

#### Evolution

Founded from the control file; outlined in the agent-capture experiment specification. Session decision mse_vaz9d3h7x4bcmd1t:d1 (2026-08-04) narrowed isolation assertion to the parent session store specifically, refining the validation claim while preserving structural isolation.

### revision-accepted - 2026-08-06T21:13:00Z

```json
{
  "event_id": "adre_6dbed6aaba81a0747e0e",
  "founding_source": ".memory-seed/index.md#L107",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
