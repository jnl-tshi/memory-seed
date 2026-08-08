---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_merge_branch_primitive
title: session merge-branch is the one-step integration primitive, not a git merge driver
topics:
  - git-workflow
  - session-fuse
created_at: 2026-08-06T20:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# session merge-branch is the one-step integration primitive, not a git merge driver

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_dr5eprnhrctqeeg3:d1`

### Decision

Current authoritative decision for this concern: `mse_dr5eprnhrctqeeg3:d1`. See the source decision for its full statement.

### Why

No lifecycle edge has carried this decision forward, so it remains current. Related decisions are recorded as supporting context only - the contract keeps related references out of lineage semantics.

### How it evolved

Re-anchored from the control-file founding onto its session decision; related decisions recorded as context: mse_v26pem9hsvsbjbge:d3.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#write-surface-parity",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "event_id": "adre_c52de32a7351a02eed33",
  "founding_quote": "One-step branch integration (current unreleased worktree)",
  "founding_source": ".memory-seed/index.md#L172",
  "source": "derived",
  "supporting_decisions": [
    "mse_dr5eprnhrctqeeg3:d1",
    "mse_9c151e4gbkkv1w5v:d1"
  ]
}
```

#### Decision

Branch integration is one explicit CLI wrapper, `memory-seed session merge-branch --branch <branch>`, which sequences fuse dry-run, `git merge --no-ff --no-commit`, session-path reset to base content, fuse apply, staging and the merge commit. It fails closed: fuse issues abort before any merge state exists. It is deliberately NOT a git merge driver and not an enforcement-only pre-commit hook.

#### Why

Git can merge text and preserve branch topology, but it cannot validate entry_id, branch provenance, or append-only session order - so raw line-merges landed session entries out of chronological order twice in a single day when the manual dry-run/apply dance was skipped. Making the correct sequence a single command removes the opportunity to skip a step, while keeping it an explicit command (rather than a driver that fires invisibly on every merge) keeps the Memory-Seed-aware validation visible and refusable.

#### Evolution

Founded on the position that fuse is an explicit integration command rather than a Git union merge driver, then hardened into the one-step wrapper after the two out-of-order incidents.

### revision-accepted - 2026-08-06T21:20:00Z

```json
{
  "event_id": "adre_48efed23f793af01c1d5",
  "founding_source": ".memory-seed/index.md#L172",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-07T01:00:00Z

```json
{
  "decision_ref": "mse_dr5eprnhrctqeeg3:d1",
  "event_id": "adre_2014f8c7d421d848f0f7",
  "source": "derived",
  "supporting_decisions": [
    "mse_v26pem9hsvsbjbge:d3"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Current authoritative decision for this concern: `mse_dr5eprnhrctqeeg3:d1`. See the source decision for its full statement.

#### Why

No lifecycle edge has carried this decision forward, so it remains current. Related decisions are recorded as supporting context only - the contract keeps related references out of lineage semantics.

#### Evolution

Re-anchored from the control-file founding onto its session decision; related decisions recorded as context: mse_v26pem9hsvsbjbge:d3.

### revision-accepted - 2026-08-07T03:00:00Z

```json
{
  "decision_ref": "mse_dr5eprnhrctqeeg3:d1",
  "event_id": "adre_db0cd093162d58ddc446",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L172",
  "source": "derived",
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Reason

Approved by JNL 2026-08-07: attach the related integration decision; head converges onto the ADR's own decision.

### context-added - 2026-08-08T04:01:00Z

```json
{
  "event_id": "adre_2cd4d88a99201691eeda",
  "source": "derived",
  "supporting_decisions": [
    "mse_81v7vk4x5ys3k2n0:d1",
    "mse_azn6bejpd9xpmh3f:d2",
    "mse_kq3ba0cy9nkpqkm0:d1",
    "mse_vm7trfd4dbd5yvnn:d1",
    "mse_w2fk7qnx4t9b3vmh:d1",
    "mse_x6qgkg61dnq26bk4:d1",
    "mse_znfnyxssvhz5srz9:d1"
  ],
  "update_entry_id": "mse_g9xegd9ct9sns5s4"
}
```

#### Reason

Attaching the seven session-fuse chain members this concern was never given. Founded from a lineage pass that carried only one related decision, so it named 1 of its chain's 8 members.
