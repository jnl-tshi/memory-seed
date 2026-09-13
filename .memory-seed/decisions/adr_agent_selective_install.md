---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_agent_selective_install
title: Agent-selective install driven by project.yaml; remove strips only our entries
topics:
  - cli
  - control-plane
created_at: 2026-08-06T20:04:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Agent-selective install driven by project.yaml; remove strips only our entries

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L199`

### Decision

`init` installs only the chosen agents' files; the selected set persists in `.memory-seed/project.yaml` under `agents:` and is respected by `doctor` and `update`. A central `KNOWN_AGENTS` registry maps each slug to its routing file, merge operations and uninstall operations. Removal uses generic strippers that remove only Memory Seed's own entries, delete a config file only when nothing of value remains, and back up first.

### Reason

Agents share configuration files, so a blanket install or a blanket removal would write or destroy config the project owns. Stripping ours-only means uninstalling one agent never disturbs a foreign server entry or another agent's block. One registry as the single source of truth for slug to operations keeps init, update, doctor and uninstall from drifting into different ideas of what an agent installs.

### Impact

Founded from the control file: the central registry landed with per-agent tagging of routing files, and `agents add/remove` followed with strip-in-place uninstall.

### Constitution

- `constitution:v1#ownership` (governing)
- `constitution:v1#single-source` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:04:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "event_id": "adre_03f47419360cbc37d3a8",
  "founding_quote": "`init` installs only the chosen agents' files; the set is persisted in `.memory-seed/project.yaml`",
  "founding_source": ".memory-seed/index.md#L199",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-1bcfcc91:d1",
    "ms-1bcfcc91:d3"
  ]
}
```

#### Decision

`init` installs only the chosen agents' files; the selected set persists in `.memory-seed/project.yaml` under `agents:` and is respected by `doctor` and `update`. A central `KNOWN_AGENTS` registry maps each slug to its routing file, merge operations and uninstall operations. Removal uses generic strippers that remove only Memory Seed's own entries, delete a config file only when nothing of value remains, and back up first.

#### Reason

Agents share configuration files, so a blanket install or a blanket removal would write or destroy config the project owns. Stripping ours-only means uninstalling one agent never disturbs a foreign server entry or another agent's block. One registry as the single source of truth for slug to operations keeps init, update, doctor and uninstall from drifting into different ideas of what an agent installs.

#### Impact

Founded from the control file: the central registry landed with per-agent tagging of routing files, and `agents add/remove` followed with strip-in-place uninstall.

### revision-accepted - 2026-08-06T21:01:00Z

```json
{
  "event_id": "adre_fecf27c2124be1e2c1d8",
  "founding_source": ".memory-seed/index.md#L199",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L199.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L199 becomes the authoritative decision; later contrary evidence requires a successor revision.
