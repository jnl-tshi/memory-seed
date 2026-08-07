---
format: memory-seed-adr/1
schema_version: 1
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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

`.memory-seed/skills/index.md` is the deterministic trigger registry: a fresh agent evaluates one map rather than loading every runbook, and new capabilities are routed by adding a registry entry rather than by prose scattered across skills. A skill shipped in the seed is written generic - no hardcoded paths, no machine-specific locations - so it is reusable in any project that installs it.

### Why

Trigger prose inside each skill cannot be evaluated without reading every skill, which is the cost the registry removes; moving trigger logic into `agent-rules.md` was rejected for making the operating contract too large and less extensible. Generic seed content is the same principle applied to the skill body: a runbook carrying one machine's paths is a runbook only that machine can run.

### How it evolved

Founded from a 4-decision lineage chain, entirely `skill-architecture`, running 2026-05-26 to 2026-07-07: the seeded trigger registry, then registry entries as the way capabilities are added, then the generic-content rule for seeded skills. This concern was independently identified as missing on 2026-08-07 while routing `governing_adr`, where 12 skills were left unrouted for want of an ADR covering skill architecture itself.

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

#### Why

Trigger prose inside each skill cannot be evaluated without reading every skill, which is the cost the registry removes; moving trigger logic into `agent-rules.md` was rejected for making the operating contract too large and less extensible. Generic seed content is the same principle applied to the skill body: a runbook carrying one machine's paths is a runbook only that machine can run.

#### Evolution

Founded from a 4-decision lineage chain, entirely `skill-architecture`, running 2026-05-26 to 2026-07-07: the seeded trigger registry, then registry entries as the way capabilities are added, then the generic-content rule for seeded skills. This concern was independently identified as missing on 2026-08-07 while routing `governing_adr`, where 12 skills were left unrouted for want of an ADR covering skill architecture itself.
