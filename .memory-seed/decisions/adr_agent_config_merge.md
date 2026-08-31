---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L124`

### Decision

Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project configuration rather than overwriting.

### Reason

Most projects already have .claude/settings.json with permissions, model, and other settings. Using seed-file copy would fail on existing projects or silently wipe their configuration.

### Impact

Founded May 2026 (ms-56fdf2ad); merge pattern established in core.py _merge_claude_hook and _merge_codex_hook functions.

### Constitution

- `constitution:v1#single-source` (governing)

### Awaiting review

- `ms-7c4e1f9a:d1` - Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project...

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project configuration rather than overwriting.

#### Reason

Most projects already have .claude/settings.json with permissions, model, and other settings. Using seed-file copy would fail on existing projects or silently wipe their configuration.

#### Impact

Founded May 2026 (ms-56fdf2ad); merge pattern established in core.py _merge_claude_hook and _merge_codex_hook functions.

### revision-accepted - 2026-08-06T21:00:00Z

```json
{
  "event_id": "adre_86af263c06df74dff10c",
  "founding_source": ".memory-seed/index.md#L124",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L124.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L124 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "decision_ref": "ms-7c4e1f9a:d1",
  "event_id": "adre_c6654ffe4a81556ed3dc",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Handle agent config files as JSON/TOML merge targets during init/update, preserving existing project configuration rather than overwriting.

#### Reason

Rests on the session decision that instituted it: "Handle `.claude/settings.json` as a JSON merge rather than a seed file copy." (ms-7c4e1f9a:d1). Establishes the core principle that agent-config must merge rather than be seed-copied to avoid clobbering existing project settings.

#### Impact

Founded from .memory-seed/index.md#L124; this revision moves the concern off that control-file line onto ms-7c4e1f9a:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
