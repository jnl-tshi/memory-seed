---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_branch_session_fuse
title: "Branch-session fuse: branch-only, chronological, immutable relative to base"
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
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L153`

### Decision

memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram sidecars. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>` metadata.

### Reason

Chronological immutability relative to the base preserves append-only ordering when merging branch work. The branch metadata enables recovery and validation during structured fuse.

### Impact

Founded from the control file; implements the structural session merge capability.

### Constitution

- `constitution:v1#append-only` (governing)

### Awaiting review

- `mse_9c151e4gbkkv1w5v:d1` - memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram...

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram sidecars. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>` metadata.

#### Reason

Chronological immutability relative to the base preserves append-only ordering when merging branch work. The branch metadata enables recovery and validation during structured fuse.

#### Impact

Founded from the control file; implements the structural session merge capability.

### revision-accepted - 2026-08-06T21:03:00Z

```json
{
  "event_id": "adre_7eda798799d694bc5af4",
  "founding_source": ".memory-seed/index.md#L153",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L153.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L153 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_9c151e4gbkkv1w5v:d1",
  "event_id": "adre_982b43dd4057de3d794c",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

memory-seed session fuse --branch <branch> dry-runs and applies branch-local session entries and diagram sidecars. Imported entries must be branch-only, chronological, immutable relative to base, and carry `branch: <branch>` metadata.

#### Reason

Rests on the session decision that instituted it: "Git can merge text and preserve branch topology, but it does not validate `entry_id`, `branch:` provenance, append-only/session-order semantics, diagram sidecars, or existing-entry immutability." (mse_9c151e4gbkkv1w5v:d1). Establishes the fuse as Memory Seed-aware command with session-order and immutability semantics, not a git merge driver.

#### Impact

Founded from .memory-seed/index.md#L153; this revision moves the concern off that control-file line onto mse_9c151e4gbkkv1w5v:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
