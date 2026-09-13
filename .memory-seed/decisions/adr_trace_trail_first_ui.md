---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_p2dgz4af43dhxs4p:d3`

### Decision

Trail remains the primary chronological evidence surface and Graph remains secondary for exploration; the generic timeline stays retired. Search remains a function over the active view. React is the sole supported Memory Trace frontend, with `/next` retained only as a bookmark-compatible redirect.

### Reason

The interaction contract remains current, but the additive React/vanilla migration clause contradicts the accepted frontend cutover and current implementation.

### Impact

Retains the Trail-first and search-in-view choices while replacing the obsolete dual-client migration state with the 2026-08-11 React-only decision.

### Awaiting review

- `mse_rqkgatgt5eh55yb8:d1` - Trail is the primary chronological evidence surface and Graph is secondary for exploration; the generic...

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
  "impact_provenance": "preserved",
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

#### Reason

Trail reads chronology without the temporal noise a generic timeline adds, which is why it earned the primary slot on use rather than on design taste. Search as a function keeps attention on the view the reader chose instead of throwing them into a third place. Shipping React additively avoids maintaining two clients that both claim to be current.

#### Impact

2026-07-11 implemented the Trail's git-graph style and refined lane allocation, resting-edge treatment and selection; the timeline was then retired and search became a function over views; 2026-07-15 promoted the graph workspace proposals; 2026-07-16 shipped the React workspace and Cytoscape shell.

### revision-proposed - 2026-08-11T12:00:00

```json
{
  "decision_ref": "mse_p2dgz4af43dhxs4p:d3",
  "event_id": "adre_d614eb09e4b9c9fc26d3",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_rqkgatgt5eh55yb8:d1",
      "relation_assertion": "link:mse_p2dgz4af43dhxs4p:d3:evolves:mse_rqkgatgt5eh55yb8:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Decision

Trail remains the primary chronological evidence surface and Graph remains secondary for exploration; the generic timeline stays retired. Search remains a function over the active view. React is the sole supported Memory Trace frontend, with `/next` retained only as a bookmark-compatible redirect.

#### Reason

The interaction contract remains current, but the additive React/vanilla migration clause contradicts the accepted frontend cutover and current implementation.

#### Impact

Retains the Trail-first and search-in-view choices while replacing the obsolete dual-client migration state with the 2026-08-11 React-only decision.

### revision-accepted - 2026-08-11T12:03:00Z

```json
{
  "decision_ref": "mse_p2dgz4af43dhxs4p:d3",
  "event_id": "adre_a286de090075d1711051",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Decision

Accept mse_p2dgz4af43dhxs4p:d3.

#### Reason

Ratifies the reconciled React-only form of the concern.

#### Impact

mse_p2dgz4af43dhxs4p:d3 becomes the authoritative decision; later contrary evidence requires a successor revision.
