---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_semantic_embeds_lexical_surface
title: Semantic scoring embeds the same surface (heading, tags, contexts, text) that lexical scoring reads
topics:
  - retrieval
created_at: 2026-09-26T16:18:17Z
user_initials: JNL
agent_type: claude
source: derived
---

# Semantic scoring embeds the same surface (heading, tags, contexts, text) that lexical scoring reads

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_hqasfw7847m20vz4:d1`

### Decision

semantic_text(chunk) composes heading_path, tags, contexts and text, and _semantic_scores embeds that composed surface rather than chunk.text alone. The lexical and semantic sides must be compared on the same content, and the test fixture keys off semantic_text so the two cannot drift apart.

### Reason

The lexical scorer weighted tags, contexts and heading_path while the embedding saw only the body, so blend weights were partly fitting a mismatch and raising the semantic weight degraded title-query accuracy. Removing the asymmetry makes the weight interpretable.

### Impact

Title accuracy holds at 58/60 across all semantic weights tested, and the semantic blend weight can be tuned meaningfully.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-26T16:18:17Z

```json
{
  "decision_ref": "mse_hqasfw7847m20vz4:d1",
  "event_id": "adre_4d8e4c3aa1903b3d271c",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

semantic_text(chunk) composes heading_path, tags, contexts and text, and _semantic_scores embeds that composed surface rather than chunk.text alone. The lexical and semantic sides must be compared on the same content, and the test fixture keys off semantic_text so the two cannot drift apart.

#### Reason

The lexical scorer weighted tags, contexts and heading_path while the embedding saw only the body, so blend weights were partly fitting a mismatch and raising the semantic weight degraded title-query accuracy. Removing the asymmetry makes the weight interpretable.

#### Impact

Title accuracy holds at 58/60 across all semantic weights tested, and the semantic blend weight can be tuned meaningfully.

### revision-accepted - 2026-09-26T16:18:43Z

```json
{
  "decision_ref": "mse_hqasfw7847m20vz4:d1",
  "event_id": "adre_b7375578844161cefd80",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_hz9vtbeqmkx9npva"
}
```

#### Decision

Accept mse_hqasfw7847m20vz4:d1.

#### Reason

JNL approved the sweep's Decision, Reason and Evidence proposal on 2026-09-26.

#### Impact

mse_hqasfw7847m20vz4:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
