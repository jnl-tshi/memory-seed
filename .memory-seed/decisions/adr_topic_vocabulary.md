---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_topic_vocabulary
title: Controlled topic vocabulary with axis hierarchy and seed/live parity
topics:
  - topic-vocabulary
  - governance-profile
  - schema
created_at: 2026-08-06T17:21:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Controlled topic vocabulary with axis hierarchy and seed/live parity

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L158`

### Decision

`topics:` is a first-class entry field resolved against the project-local `.memory-seed/topics.yaml` registry, which implements a two-axis hierarchical vocabulary. The starter vocabulary shipped with Memory Seed is domain-neutral and flat, carrying two axes: areas and activities. Authored topics rank in a declared precedence order with sidecar and inferred topics.

### Why

A controlled vocabulary ensures consistent topic use across the corpus and enables coherent navigation and filtering. Two axes (area and activity) remain orthogonal and domain-neutral, supporting software projects, legal matters, research, and other domains. Flat starter vocabulary respects the principle that depth is earned through concentration.

### How it evolved

Implemented 2026-07-15; redesigned into two-axis hierarchy 2026-07-26/27. Session decision mse_zhf4a0fsgwh47c9j:d1 (2026-07-26) shipped the neutral starter vocabulary, replacing a software-centric starter that had no area axis at all.

### Constitution

- `constitution:v1#topic-vocabulary` (governing)
- `constitution:v1#metadata-curation` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:21:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#topic-vocabulary",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#metadata-curation",
      "role": "supporting"
    }
  ],
  "event_id": "adre_9f0b8b2dcedffab463ac",
  "founding_quote": "Indexed topics (completed 2026-07-15; **redesigned into a two-axis hierarchy 2026-07-26/27**): `topics:` is a first-class entry field resolved against the deploy-once project-local `.memory-seed/topics.yaml`",
  "founding_source": ".memory-seed/index.md#L158",
  "source": "derived"
}
```

#### Decision

`topics:` is a first-class entry field resolved against the project-local `.memory-seed/topics.yaml` registry, which implements a two-axis hierarchical vocabulary. The starter vocabulary shipped with Memory Seed is domain-neutral and flat, carrying two axes: areas and activities. Authored topics rank in a declared precedence order with sidecar and inferred topics.

#### Why

A controlled vocabulary ensures consistent topic use across the corpus and enables coherent navigation and filtering. Two axes (area and activity) remain orthogonal and domain-neutral, supporting software projects, legal matters, research, and other domains. Flat starter vocabulary respects the principle that depth is earned through concentration.

#### Evolution

Implemented 2026-07-15; redesigned into two-axis hierarchy 2026-07-26/27. Session decision mse_zhf4a0fsgwh47c9j:d1 (2026-07-26) shipped the neutral starter vocabulary, replacing a software-centric starter that had no area axis at all.

### revision-accepted - 2026-08-06T21:27:00Z

```json
{
  "event_id": "adre_87597b0d07f3b19b8c8d",
  "founding_source": ".memory-seed/index.md#L158",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
