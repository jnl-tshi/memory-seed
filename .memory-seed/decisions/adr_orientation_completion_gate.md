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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

The SessionStart hook's injected pointer and AGENTS.md's Operating Mode section must state that completing the orientation chain (AGENTS.md -> agent-rules.md) is mandatory before any task action, not a numbered checklist a model can truncate for a task it judges simple.

### Reason

Transcript evidence from a targeted diagnostic replay showed two distinct failure shapes at two points in the same chain: one session never opened AGENTS.md at all, another opened it in full but never followed its own explicit next-step instruction to read agent-rules.md - which is where the actual session-logging rule lives. Both existing prompts read as sequential guidance, not a hard prerequisite, which a model treating its task as trivial can truncate without technically ignoring anything it looked at.

### Impact

Builds on the git-diff trigger (adr_session_log_trigger_enforcement) and its wording revisions, which addressed sessions that DID read the rules but reasoned around them. This ADR addresses a distinct, earlier-stage failure: sessions that never reach the rules at all.

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
