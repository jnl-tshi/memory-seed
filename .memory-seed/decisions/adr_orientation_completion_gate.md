---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_orientation_completion_gate
title: Orientation is a mandatory gate, not a numbered checklist
topics:
  - control-plane
  - bugfix
  - session-logging
created_at: 2026-08-31T23:46:17Z
user_initials: JNL
agent_type: claude
source: write-time
---

# Orientation is a mandatory gate, not a numbered checklist

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_wgssyj0541btgke4:d2`

### Decision

The orientation chain (AGENTS.md -> agent-rules.md) remains a mandatory gate before any task action for primary sessions. Delegated workers and subagents instead complete the orientation-lite gate: a digest-pinned subagent orientation skill, embedded in their Task Packet or read first when spawned without one, with full rules loaded on demand through a digest-verified path.

### Reason

Measured on 2026-09-24, embedded full baselines are 54-78% of every Task Packet. Workers receive project state from their orchestrator under the Worker Context Contract, and T3 moves session-write safety into the append tooling.

### Impact

Refines the gate by role without weakening it for primary sessions; the worker gate becomes a digest-verified lite skill instead of the full chain.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-31T23:46:17Z

```json
{
  "decision_ref": "mse_936gt0xp5hqjv55y:d1",
  "event_id": "adre_adde1f1d2de9799c17ff",
  "impact_provenance": "preserved",
  "source": "write-time",
  "supporting_decisions": [
    "mse_9xcwr1j80g755x16:d1"
  ],
  "update_entry_id": "mse_936gt0xp5hqjv55y"
}
```

#### Decision

The SessionStart hook's injected pointer and AGENTS.md's Operating Mode section must state that completing the orientation chain (AGENTS.md -> agent-rules.md) is mandatory before any task action, not a numbered checklist a model can truncate for a task it judges simple.

#### Reason

Transcript evidence from a targeted diagnostic replay showed two distinct failure shapes at two points in the same chain: one session never opened AGENTS.md at all, another opened it in full but never followed its own explicit next-step instruction to read agent-rules.md - which is where the actual session-logging rule lives. Both existing prompts read as sequential guidance, not a hard prerequisite, which a model treating its task as trivial can truncate without technically ignoring anything it looked at.

#### Impact

Builds on the git-diff trigger (adr_session_log_trigger_enforcement) and its wording revisions, which addressed sessions that DID read the rules but reasoned around them. This ADR addresses a distinct, earlier-stage failure: sessions that never reach the rules at all.

### revision-accepted - 2026-08-31T23:54:28Z

```json
{
  "decision_ref": "mse_936gt0xp5hqjv55y:d1",
  "event_id": "adre_84082982eaa5cec73cdd",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_4793ykbj05kxeht3"
}
```

#### Decision

Accept mse_936gt0xp5hqjv55y:d1.

#### Reason

JNL reviewed and approved directly, ahead of a validation run.

#### Impact

mse_936gt0xp5hqjv55y:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.

### revision-proposed - 2026-09-24T14:02:00

```json
{
  "decision_ref": "mse_wgssyj0541btgke4:d2",
  "event_id": "adre_598638c29dc55cecb01e",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_936gt0xp5hqjv55y:d1",
      "relation_assertion": "link:mse_wgssyj0541btgke4:d2:evolves:mse_936gt0xp5hqjv55y:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_wgssyj0541btgke4"
}
```

#### Decision

The orientation chain (AGENTS.md -> agent-rules.md) remains a mandatory gate before any task action for primary sessions. Delegated workers and subagents instead complete the orientation-lite gate: a digest-pinned subagent orientation skill, embedded in their Task Packet or read first when spawned without one, with full rules loaded on demand through a digest-verified path.

#### Reason

Measured on 2026-09-24, embedded full baselines are 54-78% of every Task Packet. Workers receive project state from their orchestrator under the Worker Context Contract, and T3 moves session-write safety into the append tooling.

#### Impact

Refines the gate by role without weakening it for primary sessions; the worker gate becomes a digest-verified lite skill instead of the full chain.

### revision-accepted - 2026-09-24T14:34:00

```json
{
  "decision_ref": "mse_wgssyj0541btgke4:d2",
  "event_id": "adre_9465059fd12f0eaafe18",
  "expected_authoritative_decision": "mse_936gt0xp5hqjv55y:d1",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_2948qnxwpxx87w7t"
}
```

#### Decision

Accept mse_wgssyj0541btgke4:d2.

#### Reason

JNL reviewed the worker-scoped revision and approved it directly on 2026-09-24.

#### Impact

mse_wgssyj0541btgke4:d2 becomes the authoritative decision; later contrary evidence must create a successor revision.
