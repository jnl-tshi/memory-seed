---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_agent_config_merge
title: Agent-config JSON/TOML merge, never seed-copy
topics:
  - cli
  - control-plane
  - process-correction
created_at: 2026-08-06T17:08:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Agent-config JSON/TOML merge, never seed-copy

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project configuration rather than overwriting.

### Why

Most projects already have .claude/settings.json with permissions, model, and other settings. Using seed-file copy would fail on existing projects or silently wipe their configuration.

### How it evolved

Founded May 2026 (ms-56fdf2ad); merge pattern established in core.py _merge_claude_hook and _merge_codex_hook functions.

### Constitution

- `constitution:v1#single-source` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:08:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "event_id": "adre_fcb2b52919bfb8aa8420",
  "founding_quote": "`.claude/settings.json` and `.codex/hooks.json` are handled as JSON merge targets during init/update — not seed file copies — so existing agent config is preserved.",
  "founding_source": ".memory-seed/index.md#L124",
  "source": "derived"
}
```

#### Decision

Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project configuration rather than overwriting.

#### Why

Most projects already have .claude/settings.json with permissions, model, and other settings. Using seed-file copy would fail on existing projects or silently wipe their configuration.

#### Evolution

Founded May 2026 (ms-56fdf2ad); merge pattern established in core.py _merge_claude_hook and _merge_codex_hook functions.
