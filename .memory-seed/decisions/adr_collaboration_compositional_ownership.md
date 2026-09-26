---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_collaboration_compositional_ownership
title: "Collaboration stages are split: Superpowers runs fan-out and SDD, Memory Seed owns repo controls"
topics:
  - control-plane
created_at: 2026-09-26T16:18:16Z
user_initials: JNL
agent_type: claude
source: derived
---

# Collaboration stages are split: Superpowers runs fan-out and SDD, Memory Seed owns repo controls

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_xpjr3zv6wthje8sk:d1`

### Decision

Multi-agent collaboration uses compositional ownership. Superpowers is invoked directly for independent read-only diagnostic fan-out and multi-task same-session SDD and review. Memory Seed retains guarded worktrees, parallel code-writing ownership, durable session memory, session-aware integration, consent gates and cleanup.

### Reason

Superpowers' execution engine is stronger and has behavioral-eval and field-failure evidence, while Memory Seed's advantages are deterministic repository-boundary controls such as worktree identity, base pinning, Task Packets, integration_mode and fail-closed cleanup.

### Impact

Memory Seed does not reimplement SDD or review loops, and does not replace its own worktree or integration safeguards with an external system.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-26T16:18:16Z

```json
{
  "decision_ref": "mse_xpjr3zv6wthje8sk:d1",
  "event_id": "adre_897fa217d83864ca1395",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Multi-agent collaboration uses compositional ownership. Superpowers is invoked directly for independent read-only diagnostic fan-out and multi-task same-session SDD and review. Memory Seed retains guarded worktrees, parallel code-writing ownership, durable session memory, session-aware integration, consent gates and cleanup.

#### Reason

Superpowers' execution engine is stronger and has behavioral-eval and field-failure evidence, while Memory Seed's advantages are deterministic repository-boundary controls such as worktree identity, base pinning, Task Packets, integration_mode and fail-closed cleanup.

#### Impact

Memory Seed does not reimplement SDD or review loops, and does not replace its own worktree or integration safeguards with an external system.

### revision-accepted - 2026-09-26T16:18:42Z

```json
{
  "decision_ref": "mse_xpjr3zv6wthje8sk:d1",
  "event_id": "adre_8e98fe7e0b25d4313eef",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Accept mse_xpjr3zv6wthje8sk:d1.

#### Reason

JNL approved the sweep's Decision, Reason and Evidence proposal on 2026-09-26.

#### Impact

mse_xpjr3zv6wthje8sk:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
