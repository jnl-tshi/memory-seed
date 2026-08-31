---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_legacy_agents_compat
title: Legacy .AGENTS/ compatibility retained until intentional removal
topics:
  - control-plane
  - agent-collaboration
  - memory-repair
created_at: 2026-08-06T17:19:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Legacy .AGENTS/ compatibility retained until intentional removal

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/policy.md#L22`

### Decision

Legacy `.AGENTS/` projects continue to be supported in code. Compatibility is preserved unless intentionally removed through an explicit deprecation process, ensuring that existing projects remain functional across version updates.

### Why

Removing legacy support silently breaks existing projects. Backward compatibility ensures smooth adoption and gives projects clear signal when a legacy feature is being retired. Ours-only deletion logic (only removing entries we authored, not foreign customizations) protects user investments.

### How it evolved

Founded from the control file; control-plane policy ratified 2.3.0+. Session decision ms-6a09aea8:d2 (2026-06-03) implemented the specific legacy compatibility mechanism: stripping the obsolete `mcpServers` block from `.claude/settings.json` only when Memory Seed authored the entry.

### Constitution

- `constitution:v1#ownership` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:19:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    }
  ],
  "event_id": "adre_dc4a4f10c07c80fe2846",
  "founding_quote": "Preserve compatibility for legacy `.AGENTS/` projects in code unless intentionally removing a legacy path.",
  "founding_source": ".memory-seed/policy.md#L22",
  "source": "derived"
}
```

#### Decision

Legacy `.AGENTS/` projects continue to be supported in code. Compatibility is preserved unless intentionally removed through an explicit deprecation process, ensuring that existing projects remain functional across version updates.

#### Why

Removing legacy support silently breaks existing projects. Backward compatibility ensures smooth adoption and gives projects clear signal when a legacy feature is being retired. Ours-only deletion logic (only removing entries we authored, not foreign customizations) protects user investments.

#### Evolution

Founded from the control file; control-plane policy ratified 2.3.0+. Session decision ms-6a09aea8:d2 (2026-06-03) implemented the specific legacy compatibility mechanism: stripping the obsolete `mcpServers` block from `.claude/settings.json` only when Memory Seed authored the entry.

### revision-accepted - 2026-08-06T21:17:00Z

```json
{
  "event_id": "adre_71773f40862a785d6e64",
  "founding_source": ".memory-seed/policy.md#L22",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
