---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_worktree_reconciliation_skill
title: "Dirty-worktree reconciliation is one core skill: session evidence first, Git verified, scoped process kills"
topics:
  - skill-architecture
created_at: 2026-09-26T16:18:15Z
user_initials: JNL
agent_type: claude
source: derived
---

# Dirty-worktree reconciliation is one core skill: session evidence first, Git verified, scoped process kills

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_qwdxewzk4hbnf7ks:d1`

### Decision

A single core worktree_reconciliation skill owns pre-cleanup worktree assessment: branch-local Memory Seed orientation and session evidence first, Git verification second, one descriptive summary per worktree, and exact live approval before any deletion. Immediate post-merge source-worktree cleanup stays in agent_collaboration. Windows lock recovery may stop only freshly verified lock-owning helper subtrees, protects every other process (including the owning app, IDE and app server) without vendor-name lists, and requires separate exact-process authorization to cross that boundary.

### Reason

Git cannot express workstream intent, so session evidence must precede Git verification, while Git stays the authority on content presence and deletion safety. Deletion authority and process-interruption authority have different blast radii, and vendor executable names encode one incident rather than a reusable safety boundary.

### Impact

Worktree cleanup requires a per-worktree assessment and live approval, and lock recovery never terminates processes by executable name or outside the verified helper subtree.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-26T16:18:15Z

```json
{
  "decision_ref": "mse_qwdxewzk4hbnf7ks:d1",
  "event_id": "adre_ed67d99cf7b7480709cf",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_4js48v9fpg8pbwq7:d1",
    "mse_nw47r0vpcj5tr2pj:d1"
  ],
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

A single core worktree_reconciliation skill owns pre-cleanup worktree assessment: branch-local Memory Seed orientation and session evidence first, Git verification second, one descriptive summary per worktree, and exact live approval before any deletion. Immediate post-merge source-worktree cleanup stays in agent_collaboration. Windows lock recovery may stop only freshly verified lock-owning helper subtrees, protects every other process (including the owning app, IDE and app server) without vendor-name lists, and requires separate exact-process authorization to cross that boundary.

#### Reason

Git cannot express workstream intent, so session evidence must precede Git verification, while Git stays the authority on content presence and deletion safety. Deletion authority and process-interruption authority have different blast radii, and vendor executable names encode one incident rather than a reusable safety boundary.

#### Impact

Worktree cleanup requires a per-worktree assessment and live approval, and lock recovery never terminates processes by executable name or outside the verified helper subtree.

### revision-accepted - 2026-09-26T16:18:41Z

```json
{
  "decision_ref": "mse_qwdxewzk4hbnf7ks:d1",
  "event_id": "adre_23a71a2849866c4f94fc",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Accept mse_qwdxewzk4hbnf7ks:d1.

#### Reason

JNL approved the sweep's Decision, Reason and Evidence proposal on 2026-09-26.

#### Impact

mse_qwdxewzk4hbnf7ks:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
