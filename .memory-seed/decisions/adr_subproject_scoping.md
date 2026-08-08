---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_subproject_scoping
title: Sub-project runtime scoping and inheritance defaults
topics:
  - control-plane
created_at: 2026-08-06T19:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Sub-project runtime scoping and inheritance defaults

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/policy.md#L78`

### Decision

A sub-project is a normal folder carrying its own nested `.memory-seed/` runtime, never a folder nested inside the root runtime. The nested runtime scopes work under its containing folder: active state is local by default, detailed session logs stay in the nearest runtime, and parent active state is not read unless the sub-project index explicitly links to it. Parent policy and parent skills are inherited by default; local skill files exist only to override parent behaviour or to hold genuinely local runbooks.

### Why

Runtime discovery walks upward to the nearest `.memory-seed/`, so co-locating the runtime with the folder it governs makes scope a property of position rather than configuration. Keeping detail local preserves runtime isolation while a coordination summary keeps the root aware of cross-project consequences; mirroring sub-project sessions upward was rejected as duplicated noise. Inheriting by default keeps a sub-project small, with an explicit index override as the single escape hatch.

### How it evolved

Recorded 2026-05-26 alongside the deterministic skill trigger registry, which set the local-logs and parent-summary split, and reinforced when the restored v1.4 guardrails added explicit sub-project inheritance-conflict guidance.

### Constitution

- `constitution:v1#authority` (governing)
- `constitution:v1#ownership` (supporting)

### Awaiting review

- `ms-0bd3d8b2:d2` - A sub-project is a normal folder carrying its own nested `.memory-seed/` runtime, never a folder nested...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "event_id": "adre_afd079601ed2e4ae78fa",
  "founding_quote": "A nested `.memory-seed/` runtime scopes work under its containing folder.",
  "founding_source": ".memory-seed/policy.md#L78",
  "source": "derived",
  "supporting_decisions": [
    "ms-0bd3d8b2:d2",
    "ms-f776aff0:d1"
  ]
}
```

#### Decision

A sub-project is a normal folder carrying its own nested `.memory-seed/` runtime, never a folder nested inside the root runtime. The nested runtime scopes work under its containing folder: active state is local by default, detailed session logs stay in the nearest runtime, and parent active state is not read unless the sub-project index explicitly links to it. Parent policy and parent skills are inherited by default; local skill files exist only to override parent behaviour or to hold genuinely local runbooks.

#### Why

Runtime discovery walks upward to the nearest `.memory-seed/`, so co-locating the runtime with the folder it governs makes scope a property of position rather than configuration. Keeping detail local preserves runtime isolation while a coordination summary keeps the root aware of cross-project consequences; mirroring sub-project sessions upward was rejected as duplicated noise. Inheriting by default keeps a sub-project small, with an explicit index override as the single escape hatch.

#### Evolution

Recorded 2026-05-26 alongside the deterministic skill trigger registry, which set the local-logs and parent-summary split, and reinforced when the restored v1.4 guardrails added explicit sub-project inheritance-conflict guidance.

### revision-accepted - 2026-08-06T21:25:00Z

```json
{
  "event_id": "adre_8ca415eacd7b46454612",
  "founding_source": ".memory-seed/policy.md#L78",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:12:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-0bd3d8b2:d2",
  "event_id": "adre_7f32ad4ecbda93f1e4b8",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

A sub-project is a normal folder carrying its own nested `.memory-seed/` runtime, never a folder nested inside the root runtime. The nested runtime scopes work under its containing folder: active state is local by default, detailed session logs stay in the nearest runtime, and parent active state is not read unless the sub-project index explicitly links to it. Parent policy and parent skills are inherited by default; local skill files exist only to override parent behaviour or to hold genuinely local runbooks.

#### Why

Rests on the session decision that instituted it: "Detailed session logs remain in the nearest active runtime; parent/root memory gets only" (ms-0bd3d8b2:d2). This decision established the scoping rule that sub-projects keep detailed logs locally while parent gets coordination summaries.

#### Evolution

Founded from .memory-seed/policy.md#L78; this revision moves the concern off that control-file line onto ms-0bd3d8b2:d2, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
