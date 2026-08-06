---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_topic_backfill_rejected
title: Scored topic auto-backfill rejected; curated-evidence premise adopted
topics:
  - topic-vocabulary
  - decision-harvest
created_at: 2026-08-06T17:02:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Scored topic auto-backfill rejected; curated-evidence premise adopted

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Rejected**

Authoritative decision: not yet accepted

### Decision

Automated topic backfill with scoring gates is rejected. Manual, curated attribution is adopted: one worker per batch judges all decision units and writes final topic assignments without automated scoring.

### Why

Two pilot runs scored macro-recall at 58.3% and 61.3% against a 0.70 gate, falling short. The curated-evidence premise succeeded: a human worker with swarm output as evidence judged 1,030 units and wrote 2,013 attributions (95% carrying both axes).

### How it evolved

Founded from the control file; no session lineage attached yet.

### Constitution

- `constitution:v1#prove-automation` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#prove-automation",
      "role": "governing"
    }
  ],
  "event_id": "adre_fdfb0dd13aad3c2fe2a9",
  "founding_quote": "Decision-level topic judgment swarm — **the scored auto-backfill was piloted twice and explicitly ABORTED (2026-07-26)**: two pilot runs scored macro-recall 0.583 and 0.613 against a 0.70 gate",
  "founding_source": ".memory-seed/index.md#L187",
  "source": "derived"
}
```

#### Decision

Automated topic backfill with scoring gates is rejected. Manual, curated attribution is adopted: one worker per batch judges all decision units and writes final topic assignments without automated scoring.

#### Why

Two pilot runs scored macro-recall at 58.3% and 61.3% against a 0.70 gate, falling short. The curated-evidence premise succeeded: a human worker with swarm output as evidence judged 1,030 units and wrote 2,013 attributions (95% carrying both axes).

#### Evolution

Founded from the control file; no session lineage attached yet.

### revision-rejected - 2026-08-06T18:02:00Z

```json
{
  "event_id": "adre_38822848ebcbc20dd0f5",
  "founding_source": ".memory-seed/index.md#L187",
  "source": "derived"
}
```

#### Reason

Two pilot runs scored macro-recall at 58.3% and 61.3% against a 0.70 gate, falling short. The curated-evidence premise succeeded: a human worker with swarm output as evidence judged 1,030 units and wrote 2,013 attributions (95% carrying both axes).
