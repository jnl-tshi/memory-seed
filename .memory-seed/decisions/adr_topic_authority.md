---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_topic_authority
title: Topic sidecar is the topic authority (sidecar > authored > hashtag)
topics:
  - topic-vocabulary
  - memory-trace
created_at: 2026-08-06T19:04:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Topic sidecar is the topic authority (sidecar > authored > hashtag)

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L158`

### Decision

The topic sidecar is the topic authority, not a derived overlay. Topic resolution follows strict precedence - sidecar attributions first, then the entry's authored `topics:` field, then hashtag and heading axes - instead of unioning sidecar and authored topics. Where an entry has sidecar attributions, those are its topics. Nothing authored is edited or deleted on disk; only which reading a consumer is shown changes, which is what keeps the switch reversible.

### Why

A union is right while sidecars are sparse enrichment, but wrong once the sidecar carries a complete two-axis reading of every decision, because unioning re-admits the coarse pre-axis label the sweep exists to supersede and leaves a reader unable to tell which classification the corpus currently believes. The authored YAML stays intact and readable as what its author wrote. Inferring topics from link neighbours was removed for the same reason: link structure explains relationships, not classification.

### How it evolved

Adopted 2026-07-27 when the two-axis decision-level attribution campaign completed and the union stopped being correct, then extended 2026-07-31 by making authored sidecars the only Trace and MCP topic truth and dropping link-neighbour inference.

### Constitution

- `constitution:v1#provenance` (governing)
- `constitution:v1#topic-vocabulary` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:04:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#topic-vocabulary",
      "role": "supporting"
    }
  ],
  "event_id": "adre_c4ca2febea5b8590e02b",
  "founding_quote": "**The topic sidecar is now the topic authority, not a derived overlay**",
  "founding_source": ".memory-seed/index.md#L158",
  "source": "derived",
  "supporting_decisions": [
    "mse_8qmv0m07sy95vjm9:d1",
    "mse_ypmrtzfmw4qwtbnn:d1"
  ]
}
```

#### Decision

The topic sidecar is the topic authority, not a derived overlay. Topic resolution follows strict precedence - sidecar attributions first, then the entry's authored `topics:` field, then hashtag and heading axes - instead of unioning sidecar and authored topics. Where an entry has sidecar attributions, those are its topics. Nothing authored is edited or deleted on disk; only which reading a consumer is shown changes, which is what keeps the switch reversible.

#### Why

A union is right while sidecars are sparse enrichment, but wrong once the sidecar carries a complete two-axis reading of every decision, because unioning re-admits the coarse pre-axis label the sweep exists to supersede and leaves a reader unable to tell which classification the corpus currently believes. The authored YAML stays intact and readable as what its author wrote. Inferring topics from link neighbours was removed for the same reason: link structure explains relationships, not classification.

#### Evolution

Adopted 2026-07-27 when the two-axis decision-level attribution campaign completed and the union stopped being correct, then extended 2026-07-31 by making authored sidecars the only Trace and MCP topic truth and dropping link-neighbour inference.

### revision-accepted - 2026-08-06T21:26:00Z

```json
{
  "event_id": "adre_5f9ed5e4084e2b7b5f7c",
  "founding_source": ".memory-seed/index.md#L158",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
