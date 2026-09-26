---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_full_draft_canonical_compression_rejected
title: Full DRAFT decisions stay canonical and rankable; measured compression and lexical repair rejected
topics:
  - retrieval
created_at: 2026-09-26T16:18:14Z
user_initials: JNL
agent_type: claude
source: derived
---

# Full DRAFT decisions stay canonical and rankable; measured compression and lexical repair rejected

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_sc1vzy95cabj74zz:d1`

### Decision

The complete DRAFT decision remains the canonical, rankable unit. The tested compact selectors, query-evidence front door, and lexical normalization repair are not shipped as performance improvements. Any further compaction must come from a separate natural-authoring study that removes duplicated prose without deleting decision, reason, boundary, alternative, or exact-identifier evidence, evaluated on a new sealed set.

### Reason

Sealed measurements showed raw text ranks best, compact selectors lost semantic MRR and critical boundaries, the safer D/R/A view missed the 20% median context-reduction gate, and identifier normalization changed scores but zero target ranks.

### Impact

Retrieval and display keep full decision prose with no semantic sidecar or compact view shipped; proposals to shorten decisions need a new sealed evaluation first.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-26T16:18:14Z

```json
{
  "decision_ref": "mse_sc1vzy95cabj74zz:d1",
  "event_id": "adre_d673aa53a5f14689c510",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_27f36hwt896hncf8:d1",
    "mse_rdtwf7sc4pexq9km:d1"
  ],
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

The complete DRAFT decision remains the canonical, rankable unit. The tested compact selectors, query-evidence front door, and lexical normalization repair are not shipped as performance improvements. Any further compaction must come from a separate natural-authoring study that removes duplicated prose without deleting decision, reason, boundary, alternative, or exact-identifier evidence, evaluated on a new sealed set.

#### Reason

Sealed measurements showed raw text ranks best, compact selectors lost semantic MRR and critical boundaries, the safer D/R/A view missed the 20% median context-reduction gate, and identifier normalization changed scores but zero target ranks.

#### Impact

Retrieval and display keep full decision prose with no semantic sidecar or compact view shipped; proposals to shorten decisions need a new sealed evaluation first.

### revision-accepted - 2026-09-26T16:18:38Z

```json
{
  "decision_ref": "mse_sc1vzy95cabj74zz:d1",
  "event_id": "adre_4147060f4b0425ba7c60",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Accept mse_sc1vzy95cabj74zz:d1.

#### Reason

JNL approved the sweep's Decision, Reason and Evidence proposal on 2026-09-26.

#### Impact

mse_sc1vzy95cabj74zz:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
