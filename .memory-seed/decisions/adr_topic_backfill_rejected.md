---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_azhh0f71css624jc:d1`

### Decision

Scored automated topic backfill is rejected. What is adopted and proven is an UNSCORED SWARM: batches of ~12 entries, one worker per batch, judging every decision unit and writing final attributions directly, with no agreement gate against previously authored tags.

### Reason

The 2026-07-27 campaign judged 1,030 decision units and wrote 2,013 attributions (95% carrying both axes). It was a haiku swarm - 58 batches of 12 entries, one worker each - not human adjudication. What made it succeed was dropping the agreement gate: the pre-axes authored tags encode a different question, so agreeing with them was never evidence of a right answer. Two pilot runs that DID score against those tags fell short at 0.583 and 0.613.

### Impact

Corrects this ADR's founding description, which said a human worker judged the 1,030 units. That never happened, and left standing it blocks the one method with a track record.

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Automated topic backfill with scoring gates is rejected. Manual, curated attribution is adopted: one worker per batch judges all decision units and writes final topic assignments without automated scoring.

#### Reason

Two pilot runs scored macro-recall at 58.3% and 61.3% against a 0.70 gate, falling short. The curated-evidence premise succeeded: a human worker with swarm output as evidence judged 1,030 units and wrote 2,013 attributions (95% carrying both axes).

#### Impact

Founded from the control file; no session lineage attached yet.

### revision-rejected - 2026-08-06T18:02:00Z

```json
{
  "event_id": "adre_38822848ebcbc20dd0f5",
  "founding_source": ".memory-seed/index.md#L187",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Reject founding:.memory-seed/index.md#L187.

#### Reason

Two pilot runs scored macro-recall at 58.3% and 61.3% against a 0.70 gate, falling short. The curated-evidence premise succeeded: a human worker with swarm output as evidence judged 1,030 units and wrote 2,013 attributions (95% carrying both axes).

#### Impact

founding:.memory-seed/index.md#L187 is not adopted and the current authoritative decision remains unchanged.

### context-added - 2026-08-07T05:21:00Z

```json
{
  "event_id": "adre_f3f9b1809e3ee0ee1f5f",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_25zzy3cmdjgrsf69:d2"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Record the supplied decisions as context for this ADR.

#### Reason

Expresses the curated-evidence premise this concern adopted in place of scored automation: a slug is promoted only where the corpus literally authored it.

#### Impact

This adds supporting context only; it does not change ADR membership, status, or authority.

### revision-proposed - 2026-08-07T17:35:16Z

```json
{
  "decision_ref": "mse_azhh0f71css624jc:d1",
  "event_id": "adre_47f1e23209e418f6c5d5",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_azhh0f71css624jc"
}
```

#### Decision

Scored automated topic backfill is rejected. What is adopted and proven is an UNSCORED SWARM: batches of ~12 entries, one worker per batch, judging every decision unit and writing final attributions directly, with no agreement gate against previously authored tags.

#### Reason

The 2026-07-27 campaign judged 1,030 decision units and wrote 2,013 attributions (95% carrying both axes). It was a haiku swarm - 58 batches of 12 entries, one worker each - not human adjudication. What made it succeed was dropping the agreement gate: the pre-axes authored tags encode a different question, so agreeing with them was never evidence of a right answer. Two pilot runs that DID score against those tags fell short at 0.583 and 0.613.

#### Impact

Corrects this ADR's founding description, which said a human worker judged the 1,030 units. That never happened, and left standing it blocks the one method with a track record.

### revision-accepted - 2026-08-07T17:36:09Z

```json
{
  "decision_ref": "mse_azhh0f71css624jc:d1",
  "event_id": "adre_ec71672eb5ed71e1f9dd",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_azhh0f71css624jc"
}
```

#### Decision

Accept mse_azhh0f71css624jc:d1.

#### Reason

JNL accepted the correction: the 1,030-unit campaign was a haiku swarm, not human adjudication, so the adopted method is the unscored swarm.

#### Impact

mse_azhh0f71css624jc:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
