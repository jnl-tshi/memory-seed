---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_safe_process_and_upgrade_workflow
title: "Safe process and upgrade workflow: discover, dry-run, then confirm"
topics:
  - upgrade-workflow
  - process-management
  - release-packaging
created_at: 2026-08-08T03:03:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Safe process and upgrade workflow: discover, dry-run, then confirm

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Process discovery is conservative and shared, exposed through `processes`, `shutdown --dry-run` and `upgrade --dry-run` with JSON output. Nothing destructive runs without a dry-run first and an explicit confirmation. Trace ships as the `memory-seed[trace]` extra, so upgrade is coordinated through the core package, and each worktree owns its own Trace process state.

### Why

Shutting down or upgrading the wrong process is unrecoverable in the moment, so inspection has to precede execution rather than accompany it. Coordinating upgrade through one package removes a second release to keep in step, and per-worktree ownership stops one worktree's upgrade from killing another's running UI.

### How it evolved

2026-07-08 implemented conservative process discovery with dry-run commands, then completed safe shutdown and upgrade behind a confirmation gate; 2026-07-12 pivoted to the `memory-seed[trace]` extra and resolved process ownership through the core package with per-worktree matching.

### Constitution

- `constitution:v1#prove-automation` (governing)
- `constitution:v1#immediate-value` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:03:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#prove-automation",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#immediate-value",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_etm5m5682sseasgm:d3",
  "event_id": "adre_ed24e3bdfce8634fa584",
  "source": "derived",
  "supporting_decisions": [
    "mse_2rvggg1jy6y4m1g3:d1",
    "mse_zx704zcr1sd3k91n:d1"
  ],
  "update_entry_id": "mse_etm5m5682sseasgm"
}
```

#### Decision

Process discovery is conservative and shared, exposed through `processes`, `shutdown --dry-run` and `upgrade --dry-run` with JSON output. Nothing destructive runs without a dry-run first and an explicit confirmation. Trace ships as the `memory-seed[trace]` extra, so upgrade is coordinated through the core package, and each worktree owns its own Trace process state.

#### Why

Shutting down or upgrading the wrong process is unrecoverable in the moment, so inspection has to precede execution rather than accompany it. Coordinating upgrade through one package removes a second release to keep in step, and per-worktree ownership stops one worktree's upgrade from killing another's running UI.

#### Evolution

2026-07-08 implemented conservative process discovery with dry-run commands, then completed safe shutdown and upgrade behind a confirmation gate; 2026-07-12 pivoted to the `memory-seed[trace]` extra and resolved process ownership through the core package with per-worktree matching.
