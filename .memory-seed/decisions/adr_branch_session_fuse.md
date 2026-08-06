---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_branch_session_fuse
title: Branch-session fuse: branch-only, chronological, immutable relative to base
topics:
  - git-workflow
  - branch-history
created_at: 2026-08-06T17:06:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Branch-session fuse: branch-only, chronological, immutable relative to base

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram sidecars. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>` metadata.

### Why

Chronological immutability relative to the base preserves append-only ordering when merging branch work. The branch metadata enables recovery and validation during structured fuse.

### How it evolved

Founded from the control file; implements the structural session merge capability.

### Constitution

- `constitution:v1#append-only` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:06:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "event_id": "adre_9dba1ec5d307cd3cf330",
  "founding_quote": "Branch-session fuse (current unreleased worktree): `memory-seed session fuse --branch <branch>` dry-runs branch-local session entries and diagram sidecars before promotion, and `--apply` writes only during an in-progress `git merge --no-ff --no-commit <branch>`. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>`.",
  "founding_source": ".memory-seed/index.md#L153",
  "source": "derived"
}
```

#### Decision

memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram sidecars. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>` metadata.

#### Why

Chronological immutability relative to the base preserves append-only ordering when merging branch work. The branch metadata enables recovery and validation during structured fuse.

#### Evolution

Founded from the control file; implements the structural session merge capability.
