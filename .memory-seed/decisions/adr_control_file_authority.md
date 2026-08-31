---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_control_file_authority
title: Control-file authority partition (index/policy/skills/sessions)
topics:
  - control-plane
created_at: 2026-08-06T19:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Control-file authority partition (index/policy/skills/sessions)

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_p2dgz4af43dhxs4p:d2`

### Decision

A declared ratified Constitution governs the lower control plane. The index routes topology, state, inheritance, and authority; policy states concise executable constraints; accepted ADR heads own durable rationale and evolution; sessions retain chronological evidence; projections remain derived.

### Reason

The prior partition left formal constitutional precedence ambiguous and duplicated decision rationale across current control files.

### Impact

Converges the founding control-file partition onto an explicit session decision and adds Constitution-first precedence while preserving concern ownership.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "event_id": "adre_8b0fc1fcc70d17a0e9e7",
  "founding_quote": "`.memory-seed/index.md` owns topology, active state, inheritance rules, and skill pointers.",
  "founding_source": ".memory-seed/policy.md#L49",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_ddba1ztxqhasfbwf:d1",
    "ms-845042c7:d3"
  ]
}
```

#### Decision

Memory Seed partitions control-plane authority by file rather than centralising it. `.memory-seed/index.md` owns topology, active state, durable context, inheritance rules and skill pointers; `.memory-seed/policy.md` owns behavioural constraints only; `.memory-seed/skills/*.md` own task runbooks; `.memory-seed/sessions/` owns chronological history and rationale. Current control files are the active authority, session entries are evidence and rationale, and registries, indexes and Trace views are derived projections of them.

#### Reason

One file per concern keeps each surface small enough for a fresh agent to load and keeps unrelated edits from colliding. Session history is deliberately not authority: when it conflicts with current files and no clear supersession boundary exists, agents must ask rather than infer. The complementary ADR contract keeps the curated synopsis and lineage in the ADR while original entries keep detailed rationale, so nothing derived can claim authorship.

#### Impact

Established with the earliest runtime layout, tightened on 2026-05-26 by the rule that current files are active authority and history is evidence, and again on 2026-07-16 when Constitution v1.1 partitioned Markdown authority by concern.

### revision-accepted - 2026-08-06T21:05:00Z

```json
{
  "event_id": "adre_da1cac49a9b8de875ddb",
  "founding_source": ".memory-seed/policy.md#L49",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/policy.md#L49.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/policy.md#L49 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-11T12:02:00Z

```json
{
  "decision_ref": "mse_p2dgz4af43dhxs4p:d2",
  "event_id": "adre_d92f945c1df80aed70bf",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Decision

A declared ratified Constitution governs the lower control plane. The index routes topology, state, inheritance, and authority; policy states concise executable constraints; accepted ADR heads own durable rationale and evolution; sessions retain chronological evidence; projections remain derived.

#### Reason

The prior partition left formal constitutional precedence ambiguous and duplicated decision rationale across current control files.

#### Impact

Converges the founding control-file partition onto an explicit session decision and adds Constitution-first precedence while preserving concern ownership.

### revision-accepted - 2026-08-11T12:02:30Z

```json
{
  "decision_ref": "mse_p2dgz4af43dhxs4p:d2",
  "event_id": "adre_462d2eb444952d39b159",
  "expected_authoritative_decision": "founding:.memory-seed/policy.md#L49",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Decision

Accept mse_p2dgz4af43dhxs4p:d2.

#### Reason

Ratifies Constitution-first control-file authority.

#### Impact

mse_p2dgz4af43dhxs4p:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.
