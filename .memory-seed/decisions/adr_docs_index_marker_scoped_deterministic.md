---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_docs_index_marker_scoped_deterministic
title: docs check/index are read-only gates; generated docs regions are marker-scoped and deterministic
topics:
  - docs-lifecycle
created_at: 2026-09-26T16:18:14Z
user_initials: JNL
agent_type: claude
source: derived
---

# docs check/index are read-only gates; generated docs regions are marker-scoped and deterministic

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_s0rh0b60tv8ssjzd:d1`

### Decision

`memory-seed docs check` validates links, lifecycle pointers and spec_binding/folder agreement, and `docs index --check` regenerates lane indexes in memory and fails CI when stale. Generated content lives only inside marker regions so hand-written prose survives, and output ordering must be a platform-independent total order (casefold, name).

### Reason

Hand-maintained counts and unguarded link rewrites drifted repeatedly, and a Windows/Linux sort difference showed generation must be byte-deterministic to serve as a gate.

### Impact

A stale or broken docs index fails verify CI on any platform, while lane README prose outside the markers is never overwritten.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-26T16:18:14Z

```json
{
  "decision_ref": "mse_s0rh0b60tv8ssjzd:d1",
  "event_id": "adre_752a181691947093804a",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_5nr2pvjyrs92bvj2:d1",
    "mse_ntkt6m0pqd0g8c9j:d1"
  ],
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

`memory-seed docs check` validates links, lifecycle pointers and spec_binding/folder agreement, and `docs index --check` regenerates lane indexes in memory and fails CI when stale. Generated content lives only inside marker regions so hand-written prose survives, and output ordering must be a platform-independent total order (casefold, name).

#### Reason

Hand-maintained counts and unguarded link rewrites drifted repeatedly, and a Windows/Linux sort difference showed generation must be byte-deterministic to serve as a gate.

#### Impact

A stale or broken docs index fails verify CI on any platform, while lane README prose outside the markers is never overwritten.

### revision-accepted - 2026-09-26T16:18:40Z

```json
{
  "decision_ref": "mse_s0rh0b60tv8ssjzd:d1",
  "event_id": "adre_e4315724f132714c481b",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Accept mse_s0rh0b60tv8ssjzd:d1.

#### Reason

JNL approved the sweep's Decision, Reason and Evidence proposal on 2026-09-26.

#### Impact

mse_s0rh0b60tv8ssjzd:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
