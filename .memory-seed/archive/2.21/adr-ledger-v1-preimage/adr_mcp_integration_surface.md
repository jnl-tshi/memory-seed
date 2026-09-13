---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_mcp_integration_surface
title: "MCP integration: per-agent config placement, upsert semantics, and a gated write surface"
topics:
  - mcp-tools
  - cli
created_at: 2026-08-07T22:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# MCP integration: per-agent config placement, upsert semantics, and a gated write surface

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Each agent's MCP config goes where that agent actually reads it - Claude in project-root `.mcp.json`, Codex in `.codex/config.toml` - written on init unconditionally rather than gated on a PATH probe. Merges upsert: a matching command is overwritten, a different one under the same key is left alone. The MCP write surface is gated, with `memory_session_append` the only authoring path, inheriting the same write-time guards as the CLI.

### Why

Config placement is per-agent because each vendor discovers servers differently, and writing to the wrong file fails silently. Upsert-on-matching-command protects a user's own server that happens to share our key while still keeping ours current. Unconditional write avoids a PATH probe that is wrong at init time anyway. The write surface is gated because an ungated pair let MCP writes bypass guards the CLI enforced - the write-surface parity rule.

### How it evolved

Founded from an 11-decision lineage chain, entirely `mcp-tools`, running 2026-05-29 to 2026-07-19: unconditional write and hook-time detection, then upsert semantics, then per-vendor placement for Claude and Codex, then the gated write surface.

### Constitution

- `constitution:v1#ownership` (governing)
- `constitution:v1#write-surface-parity` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-07T22:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#write-surface-parity",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_vzsef0fmpsde2jh4:d1",
  "event_id": "adre_6cfc49a43e7c18b8352a",
  "source": "derived",
  "supporting_decisions": [
    "ms-4c8e2a17:d1",
    "ms-4c8e2a17:d2",
    "ms-4c8e2a17:d4",
    "ms-7b3f1e92:d3",
    "ms-6a09aea8:d1",
    "ms-2cd452e4:d1",
    "ms-2cd452e4:d2",
    "mse_81v7vk4x5ys3k2n0:d3"
  ],
  "update_entry_id": "mse_vzsef0fmpsde2jh4"
}
```

#### Decision

Each agent's MCP config goes where that agent actually reads it - Claude in project-root `.mcp.json`, Codex in `.codex/config.toml` - written on init unconditionally rather than gated on a PATH probe. Merges upsert: a matching command is overwritten, a different one under the same key is left alone. The MCP write surface is gated, with `memory_session_append` the only authoring path, inheriting the same write-time guards as the CLI.

#### Why

Config placement is per-agent because each vendor discovers servers differently, and writing to the wrong file fails silently. Upsert-on-matching-command protects a user's own server that happens to share our key while still keeping ours current. Unconditional write avoids a PATH probe that is wrong at init time anyway. The write surface is gated because an ungated pair let MCP writes bypass guards the CLI enforced - the write-surface parity rule.

#### Evolution

Founded from an 11-decision lineage chain, entirely `mcp-tools`, running 2026-05-29 to 2026-07-19: unconditional write and hook-time detection, then upsert semantics, then per-vendor placement for Claude and Codex, then the gated write surface.

### context-added - 2026-08-08T04:00:00Z

```json
{
  "event_id": "adre_c402b1b822ac3cf585e7",
  "source": "derived",
  "supporting_decisions": [
    "ms-6eeb512f:d1",
    "ms-a3f91c2b:d1"
  ],
  "update_entry_id": "mse_g9xegd9ct9sns5s4"
}
```

#### Reason

Attaching two chain members omitted when the supporting list was written by hand. The growth check found them: the chain carries 11 decisions and the ADR named 9.
