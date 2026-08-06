---
format: memory-seed-adr/1
schema_version: 1
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

Authoritative decision: `founding:.memory-seed/policy.md#L49`

### Decision

Memory Seed partitions control-plane authority by file rather than centralising it. `.memory-seed/index.md` owns topology, active state, durable context, inheritance rules and skill pointers; `.memory-seed/policy.md` owns behavioural constraints only; `.memory-seed/skills/*.md` own task runbooks; `.memory-seed/sessions/` owns chronological history and rationale. Current control files are the active authority, session entries are evidence and rationale, and registries, indexes and Trace views are derived projections of them.

### Why

One file per concern keeps each surface small enough for a fresh agent to load and keeps unrelated edits from colliding. Session history is deliberately not authority: when it conflicts with current files and no clear supersession boundary exists, agents must ask rather than infer. The complementary ADR contract keeps the curated synopsis and lineage in the ADR while original entries keep detailed rationale, so nothing derived can claim authorship.

### How it evolved

Established with the earliest runtime layout, tightened on 2026-05-26 by the rule that current files are active authority and history is evidence, and again on 2026-07-16 when Constitution v1.1 partitioned Markdown authority by concern.

### Constitution

- `constitution:v1#authority` (governing)
- `constitution:v1#single-source` (supporting)

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
  "source": "derived",
  "supporting_decisions": [
    "mse_ddba1ztxqhasfbwf:d1",
    "ms-845042c7:d3"
  ]
}
```

#### Decision

Memory Seed partitions control-plane authority by file rather than centralising it. `.memory-seed/index.md` owns topology, active state, durable context, inheritance rules and skill pointers; `.memory-seed/policy.md` owns behavioural constraints only; `.memory-seed/skills/*.md` own task runbooks; `.memory-seed/sessions/` owns chronological history and rationale. Current control files are the active authority, session entries are evidence and rationale, and registries, indexes and Trace views are derived projections of them.

#### Why

One file per concern keeps each surface small enough for a fresh agent to load and keeps unrelated edits from colliding. Session history is deliberately not authority: when it conflicts with current files and no clear supersession boundary exists, agents must ask rather than infer. The complementary ADR contract keeps the curated synopsis and lineage in the ADR while original entries keep detailed rationale, so nothing derived can claim authorship.

#### Evolution

Established with the earliest runtime layout, tightened on 2026-05-26 by the rule that current files are active authority and history is evidence, and again on 2026-07-16 when Constitution v1.1 partitioned Markdown authority by concern.

### revision-accepted - 2026-08-06T21:05:00Z

```json
{
  "event_id": "adre_da1cac49a9b8de875ddb",
  "founding_source": ".memory-seed/policy.md#L49",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
