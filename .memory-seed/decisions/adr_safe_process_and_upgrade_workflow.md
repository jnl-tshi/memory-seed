---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_etm5m5682sseasgm:d3`

### Decision

Process discovery is conservative and shared, exposed through processes, shutdown --dry-run and upgrade --dry-run with JSON output. Nothing destructive runs without a dry-run first and an explicit confirmation. Trace ships as the memory-seed[trace] extra so upgrade is coordinated through the core package. Each worktree owns its own Trace process state, and memory-trace upgrade targets the owning memory-seed package while process matching still targets active memory-trace UI processes.

### Reason

Shutting down or upgrading the wrong process is unrecoverable in the moment, so inspection must precede execution rather than accompany it. Coordinating upgrade through one package removes a second release to keep in step. Per-worktree process ownership stops one worktree's upgrade from killing another's running UI. Confirmation-gating with explicit manager execution and failed-shutdown blocking ensure safe destructive operations.

### Impact

The decision began with conservative process discovery and dry-run commands for both shutdown and upgrade. It then evolved to implement confirmation-gating with default-no behavior, --yes flag, failed-shutdown blocking, and explicit package-manager execution. Finally it resolved process ownership by routing memory-trace upgrade through the owning memory-seed package.

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
  "impact_provenance": "preserved",
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

#### Reason

Shutting down or upgrading the wrong process is unrecoverable in the moment, so inspection has to precede execution rather than accompany it. Coordinating upgrade through one package removes a second release to keep in step, and per-worktree ownership stops one worktree's upgrade from killing another's running UI.

#### Impact

2026-07-08 implemented conservative process discovery with dry-run commands, then completed safe shutdown and upgrade behind a confirmation gate; 2026-07-12 pivoted to the `memory-seed[trace]` extra and resolved process ownership through the core package with per-worktree matching.

### revision-rejected - 2026-08-08T23:16:00Z

```json
{
  "decision_ref": "mse_etm5m5682sseasgm:d3",
  "event_id": "adre_0a44a33a1ed18281ab6a",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_etm5m5682sseasgm:d3.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_etm5m5682sseasgm:d3 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:16:20Z

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
  "event_id": "adre_479c8425b2bb631d3f6a",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_2rvggg1jy6y4m1g3:d1",
    "mse_zx704zcr1sd3k91n:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Process discovery is conservative and shared, exposed through processes, shutdown --dry-run and upgrade --dry-run with JSON output. Nothing destructive runs without a dry-run first and an explicit confirmation. Trace ships as the memory-seed[trace] extra so upgrade is coordinated through the core package. Each worktree owns its own Trace process state, and memory-trace upgrade targets the owning memory-seed package while process matching still targets active memory-trace UI processes.

#### Reason

Shutting down or upgrading the wrong process is unrecoverable in the moment, so inspection must precede execution rather than accompany it. Coordinating upgrade through one package removes a second release to keep in step. Per-worktree process ownership stops one worktree's upgrade from killing another's running UI. Confirmation-gating with explicit manager execution and failed-shutdown blocking ensure safe destructive operations.

#### Impact

The decision began with conservative process discovery and dry-run commands for both shutdown and upgrade. It then evolved to implement confirmation-gating with default-no behavior, --yes flag, failed-shutdown blocking, and explicit package-manager execution. Finally it resolved process ownership by routing memory-trace upgrade through the owning memory-seed package.

### revision-accepted - 2026-08-08T23:16:40Z

```json
{
  "decision_ref": "mse_etm5m5682sseasgm:d3",
  "event_id": "adre_87a4f41b91fa9cd20c76",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_etm5m5682sseasgm:d3.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_etm5m5682sseasgm:d3 becomes the authoritative decision; later contrary evidence requires a successor revision.
