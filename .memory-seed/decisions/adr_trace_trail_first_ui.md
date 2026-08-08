---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_trace_trail_first_ui
title: Memory Trace is Trail-first, with search a function over the open view
topics:
  - memory-trace
  - ui-design
  - graph
created_at: 2026-08-08T03:11:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Memory Trace is Trail-first, with search a function over the open view

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Trail is the primary chronological evidence surface and Graph is secondary for exploration; the generic timeline is retired. Search is a function over whichever view is open rather than a destination of its own, returning a ranked dropdown plus in-place highlighting. The React workspace ships additively at its own route against v1 API contracts while the vanilla client keeps serving the root.

### Why

Trail reads chronology without the temporal noise a generic timeline adds, which is why it earned the primary slot on use rather than on design taste. Search as a function keeps attention on the view the reader chose instead of throwing them into a third place. Shipping React additively avoids maintaining two clients that both claim to be current.

### How it evolved

2026-07-11 implemented the Trail's git-graph style and refined lane allocation, resting-edge treatment and selection; the timeline was then retired and search became a function over views; 2026-07-15 promoted the graph workspace proposals; 2026-07-16 shipped the React workspace and Cytoscape shell.

### Constitution

- `constitution:v1#immediate-value` (governing)
- `constitution:v1#expose-before-rank` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:11:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#immediate-value",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#expose-before-rank",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_rqkgatgt5eh55yb8:d1",
  "event_id": "adre_f0ef12ceca95e5c4ba44",
  "source": "derived",
  "supporting_decisions": [
    "mse_loe4c3vbaeeq22dt:d1",
    "mse_rsjbgk4qnyrtvv09:d1"
  ],
  "update_entry_id": "mse_rqkgatgt5eh55yb8"
}
```

#### Decision

Trail is the primary chronological evidence surface and Graph is secondary for exploration; the generic timeline is retired. Search is a function over whichever view is open rather than a destination of its own, returning a ranked dropdown plus in-place highlighting. The React workspace ships additively at its own route against v1 API contracts while the vanilla client keeps serving the root.

#### Why

Trail reads chronology without the temporal noise a generic timeline adds, which is why it earned the primary slot on use rather than on design taste. Search as a function keeps attention on the view the reader chose instead of throwing them into a third place. Shipping React additively avoids maintaining two clients that both claim to be current.

#### Evolution

2026-07-11 implemented the Trail's git-graph style and refined lane allocation, resting-edge treatment and selection; the timeline was then retired and search became a function over views; 2026-07-15 promoted the graph workspace proposals; 2026-07-16 shipped the React workspace and Cytoscape shell.
