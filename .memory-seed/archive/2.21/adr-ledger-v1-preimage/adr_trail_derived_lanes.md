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

Authoritative decision: `mse_37fpco0vvunilz5k:d1`

### Decision

Trail generates display lanes derived from lifecycle edges and branch intervals without requiring authored graph edges. Each branch receives the lowest available lane via greedy interval packing, with lanes freed when the branch's visible lifecycle ends.

### Why

The design implements a git-graph timeline format (vertical orientation, straight lanes, fixed row height) based on research of conventional git-graph tools. User direction called for an interactive gitgraph appearance reminiscent of GitKraken and similar tools, with recent-window focus and minimal UI chrome to support dense, readable git history.

### How it evolved

The single decision rebuilt Memory Trace's Trail view from a shared force-layout graph into a vertical git-graph timeline, establishing the lane-assignment algorithm and visual encoding: lifecycle arcs in a left gutter, branch tip chips marking each branch's timeline, day separators for temporal scoping, and a 60-entry bounded window with client-side loading.

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

### revision-proposed - 2026-08-08T19:16:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_37fpco0vvunilz5k:d1",
  "event_id": "adre_37f3190fa60d1a7a4c7b",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Trail generates continuity lanes derived from lifecycle edges without requiring or adding authored graph edges.

#### Why

Rests on the session decision that instituted it: "one straight lane per branch via interval coloring (lowest free lane, freed when the branch's visible life ends)" (mse_37fpco0vvunilz5k:d1). This decision rebuilt Trail as a git-graph timeline and established the algorithm for deriving lanes from branch intervals without authored graph edges.

#### Evolution

Founded from .memory-seed/index.md#L171; this revision moves the concern off that control-file line onto mse_37fpco0vvunilz5k:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:24:00Z

```json
{
  "decision_ref": "mse_37fpco0vvunilz5k:d1",
  "event_id": "adre_c2ebe943e97c0a4279a0",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:24:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_37fpco0vvunilz5k:d1",
  "event_id": "adre_ffdc6aa593d18f493ea8",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Trail generates display lanes derived from lifecycle edges and branch intervals without requiring authored graph edges. Each branch receives the lowest available lane via greedy interval packing, with lanes freed when the branch's visible lifecycle ends.

#### Why

The design implements a git-graph timeline format (vertical orientation, straight lanes, fixed row height) based on research of conventional git-graph tools. User direction called for an interactive gitgraph appearance reminiscent of GitKraken and similar tools, with recent-window focus and minimal UI chrome to support dense, readable git history.

#### Evolution

The single decision rebuilt Memory Trace's Trail view from a shared force-layout graph into a vertical git-graph timeline, establishing the lane-assignment algorithm and visual encoding: lifecycle arcs in a left gutter, branch tip chips marking each branch's timeline, day separators for temporal scoping, and a 60-entry bounded window with client-side loading.

### revision-accepted - 2026-08-08T23:24:40Z

```json
{
  "decision_ref": "mse_37fpco0vvunilz5k:d1",
  "event_id": "adre_9410f63d74627d0fa3c5",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L171",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
