---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_worktree_convention
title: Worktree=session, branch=task, agent-namespaced branch names
topics:
  - git-workflow
  - agent-collaboration
  - continuity
created_at: 2026-08-06T17:20:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Worktree=session, branch=task, agent-namespaced branch names

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L81`

### Decision

Worktree hygiene follows a strict naming and lifecycle convention: one worktree per session, one branch per task or feature. New branches follow the pattern `<agent>/<kind>/<topic>` to encode agent identity, work kind (fix, feature, docs, etc.), and topic area.

### Why

This convention ensures clear traceability between Git artifacts, session scope, and agent work. Agent-namespaced branches prevent collisions in shared environments and make it easy to identify which agent or session created which branch. Single worktree per session simplifies cleanup and lifecycle management.

### How it evolved

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#integration-mode` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:20:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#integration-mode",
      "role": "governing"
    }
  ],
  "event_id": "adre_dc8864697cadc43d713d",
  "founding_quote": "The worktree hygiene plan uses worktree=session, branch=task, and `<agent>/<kind>/<topic>` for new branches.",
  "founding_source": ".memory-seed/index.md#L81",
  "source": "derived"
}
```

#### Decision

Worktree hygiene follows a strict naming and lifecycle convention: one worktree per session, one branch per task or feature. New branches follow the pattern `<agent>/<kind>/<topic>` to encode agent identity, work kind (fix, feature, docs, etc.), and topic area.

#### Why

This convention ensures clear traceability between Git artifacts, session scope, and agent work. Agent-namespaced branches prevent collisions in shared environments and make it easy to identify which agent or session created which branch. Single worktree per session simplifies cleanup and lifecycle management.

#### Evolution

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:31:00Z

```json
{
  "event_id": "adre_c5d20377e11567a8e9fa",
  "founding_source": ".memory-seed/index.md#L81",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
