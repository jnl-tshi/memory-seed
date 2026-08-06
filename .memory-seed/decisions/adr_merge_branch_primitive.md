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

Authoritative decision: `founding:.memory-seed/index.md#L172`

### Decision

Branch integration is one explicit CLI wrapper, `memory-seed session merge-branch --branch <branch>`, which sequences fuse dry-run, `git merge --no-ff --no-commit`, session-path reset to base content, fuse apply, staging and the merge commit. It fails closed: fuse issues abort before any merge state exists. It is deliberately NOT a git merge driver and not an enforcement-only pre-commit hook.

### Why

Git can merge text and preserve branch topology, but it cannot validate entry_id, branch provenance, or append-only session order - so raw line-merges landed session entries out of chronological order twice in a single day when the manual dry-run/apply dance was skipped. Making the correct sequence a single command removes the opportunity to skip a step, while keeping it an explicit command (rather than a driver that fires invisibly on every merge) keeps the Memory-Seed-aware validation visible and refusable.

### How it evolved

Founded on the position that fuse is an explicit integration command rather than a Git union merge driver, then hardened into the one-step wrapper after the two out-of-order incidents.

### Constitution

- `constitution:v1#write-surface-parity` (governing)
- `constitution:v1#append-only` (supporting)

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
