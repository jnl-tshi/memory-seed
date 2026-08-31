---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_skill_registry_and_generic_skills
title: Skills route through a deterministic registry, and seeded skills are written generic
topics:
  - skill-architecture
  - control-plane
created_at: 2026-08-07T22:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Skills route through a deterministic registry, and seeded skills are written generic

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_542z3qn0azma9mmx:d1`

### Decision

Skills route through a deterministic registry at .memory-seed/skills/index.md so fresh agents evaluate one map rather than loading all runbooks. Trigger logic lives in the registry, not scattered as prose. Skills shipped in the seed are written generic: no hardcoded output paths, no machine-specific tool locations, command patterns shown portably. Local skill registries can carry project-local entries like developer persona skills, but those are not exported to the seed.

### Reason

Reading every skill to evaluate triggers is expensive; the registry removes that cost. Moving all triggers to agent-rules.md was rejected for making the operating contract too large and less extensible. Generic skill content applies the same principle to bodies: a runbook with hardcoded paths only runs on one machine. Shipping skills in the seed requires them to work on any project.

### Impact

A registry was instituted as the deterministic skill trigger map. UI debugging checks were added to the developer persona and local registry. A skill was then generalized from project-local source code, establishing the pattern of stripping machine-specific paths and locations. The latest member unified diagram questions through the same registry without adding parallel logic.

### Constitution

- `constitution:v1#single-source` (governing)
- `constitution:v1#markdown-authority` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-07T22:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_542z3qn0azma9mmx:d1",
  "event_id": "adre_c44cd17a248c4c616169",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-0bd3d8b2:d1",
    "mse_vexkm8da35zj856x:d1",
    "mse_fp32yxbxy3k3r5x1:d1"
  ],
  "update_entry_id": "mse_542z3qn0azma9mmx"
}
```

#### Decision

`.memory-seed/skills/index.md` is the deterministic trigger registry: a fresh agent evaluates one map rather than loading every runbook, and new capabilities are routed by adding a registry entry rather than by prose scattered across skills. A skill shipped in the seed is written generic - no hardcoded paths, no machine-specific locations - so it is reusable in any project that installs it.

#### Reason

Trigger prose inside each skill cannot be evaluated without reading every skill, which is the cost the registry removes; moving trigger logic into `agent-rules.md` was rejected for making the operating contract too large and less extensible. Generic seed content is the same principle applied to the skill body: a runbook carrying one machine's paths is a runbook only that machine can run.

#### Impact

Founded from a 4-decision lineage chain, entirely `skill-architecture`, running 2026-05-26 to 2026-07-07: the seeded trigger registry, then registry entries as the way capabilities are added, then the generic-content rule for seeded skills. This concern was independently identified as missing on 2026-08-07 while routing `governing_adr`, where 12 skills were left unrouted for want of an ADR covering skill architecture itself.

### revision-rejected - 2026-08-08T23:19:00Z

```json
{
  "decision_ref": "mse_542z3qn0azma9mmx:d1",
  "event_id": "adre_152733d6457ac0961c50",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_542z3qn0azma9mmx:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_542z3qn0azma9mmx:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:19:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_542z3qn0azma9mmx:d1",
  "event_id": "adre_545126c58c329b74520b",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "ms-0bd3d8b2:d1",
    "mse_vexkm8da35zj856x:d1",
    "mse_fp32yxbxy3k3r5x1:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Skills route through a deterministic registry at .memory-seed/skills/index.md so fresh agents evaluate one map rather than loading all runbooks. Trigger logic lives in the registry, not scattered as prose. Skills shipped in the seed are written generic: no hardcoded output paths, no machine-specific tool locations, command patterns shown portably. Local skill registries can carry project-local entries like developer persona skills, but those are not exported to the seed.

#### Reason

Reading every skill to evaluate triggers is expensive; the registry removes that cost. Moving all triggers to agent-rules.md was rejected for making the operating contract too large and less extensible. Generic skill content applies the same principle to bodies: a runbook with hardcoded paths only runs on one machine. Shipping skills in the seed requires them to work on any project.

#### Impact

A registry was instituted as the deterministic skill trigger map. UI debugging checks were added to the developer persona and local registry. A skill was then generalized from project-local source code, establishing the pattern of stripping machine-specific paths and locations. The latest member unified diagram questions through the same registry without adding parallel logic.

### revision-accepted - 2026-08-08T23:19:40Z

```json
{
  "decision_ref": "mse_542z3qn0azma9mmx:d1",
  "event_id": "adre_e82cb403626965385d3d",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_542z3qn0azma9mmx:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_542z3qn0azma9mmx:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
