---
format: memory-seed-adr/2
schema_version: 2
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

Authoritative decision: `mse_crggn1ajkw05h8pt:d1`

### Decision

Each writing agent owns one persistent home worktree at <namespace>/home (<namespace>/<user>/home with 2+ participants); work happens on task branches named <agent>/<kind>/<topic> inside it; a second live session gets an overflow worktree that is removed after merge; after a merge the home is parked (detached at the merge commit), never removed.

### Reason

Fresh worktrees per session broke venvs, stranded folders, and on 2026-09-24 let a session gut its own launch worktree, blocking every later commit. The 2026-07-13 intent was already one durable worktree per agent; the per-session churn came from app defaults and a remove-after-merge Finish Contract.

### Impact

Sessions start on the primary checkout and claim the home with memory-seed worktree home --claim; merge-branch reports parked for homes; worktree GC never marks a home removable; overflow worktrees keep remove-after-merge cleanup.

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Worktree hygiene follows a strict naming and lifecycle convention: one worktree per session, one branch per task or feature. New branches follow the pattern `<agent>/<kind>/<topic>` to encode agent identity, work kind (fix, feature, docs, etc.), and topic area.

#### Reason

This convention ensures clear traceability between Git artifacts, session scope, and agent work. Agent-namespaced branches prevent collisions in shared environments and make it easy to identify which agent or session created which branch. Single worktree per session simplifies cleanup and lifecycle management.

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-accepted - 2026-08-06T21:31:00Z

```json
{
  "event_id": "adre_c5d20377e11567a8e9fa",
  "founding_source": ".memory-seed/index.md#L81",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L81.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L81 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-09-25T14:13:20Z

```json
{
  "decision_ref": "mse_crggn1ajkw05h8pt:d1",
  "event_id": "adre_bc9379f0173975ce3701",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_wk4tfxrxx16j989v"
}
```

#### Decision

Each writing agent owns one persistent home worktree at <namespace>/home (<namespace>/<user>/home with 2+ participants); work happens on task branches named <agent>/<kind>/<topic> inside it; a second live session gets an overflow worktree that is removed after merge; after a merge the home is parked (detached at the merge commit), never removed.

#### Reason

Fresh worktrees per session broke venvs, stranded folders, and on 2026-09-24 let a session gut its own launch worktree, blocking every later commit. The 2026-07-13 intent was already one durable worktree per agent; the per-session churn came from app defaults and a remove-after-merge Finish Contract.

#### Impact

Sessions start on the primary checkout and claim the home with memory-seed worktree home --claim; merge-branch reports parked for homes; worktree GC never marks a home removable; overflow worktrees keep remove-after-merge cleanup.

### revision-accepted - 2026-09-25T14:13:21Z

```json
{
  "decision_ref": "mse_crggn1ajkw05h8pt:d1",
  "event_id": "adre_9616d74aff628191c26c",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L81",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_wk4tfxrxx16j989v"
}
```

#### Decision

Accept mse_crggn1ajkw05h8pt:d1.

#### Reason

JNL explicitly approved acceptance of the home-worktree revision on 2026-09-25 after reviewing its Decision, Reason and Evidence.

#### Impact

mse_crggn1ajkw05h8pt:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
