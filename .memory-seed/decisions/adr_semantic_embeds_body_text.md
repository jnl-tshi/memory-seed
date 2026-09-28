---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_semantic_embeds_body_text
title: Semantic scoring embeds the body text only; the composed surface was measured and reverted
topics:
  - retrieval
created_at: 2026-09-28T07:20:28Z
user_initials: JNL
agent_type: claude
source: derived
---

# Semantic scoring embeds the body text only; the composed surface was measured and reverted

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_wz1aec7859rk0h67:d1`

### Decision

semantic_text(chunk) embeds chunk.text alone. It stays a named function whose docstring carries the ablation, so the composed-surface idea can be re-tested cheaply rather than re-argued.

### Reason

Holding everything else fixed and varying only the embedded surface, the composed heading+tags+contexts+body surface scored 130/180 paraphrase recall@8 against 132/180 body-only (p = 0.48) and changed no title answer. The earlier 58/60 title claim compared runs with different recency settings.

### Impact

Supersedes adr_semantic_embeds_lexical_surface. Semantic and lexical sides read different surfaces by measured choice; a near-miss title probe set would be needed before revisiting it.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-09-28T07:20:28Z

```json
{
  "decision_ref": "mse_wz1aec7859rk0h67:d1",
  "event_id": "adre_47b759e7b862bf9948c8",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_09h6y7z24fkfvp4t"
}
```

#### Decision

semantic_text(chunk) embeds chunk.text alone. It stays a named function whose docstring carries the ablation, so the composed-surface idea can be re-tested cheaply rather than re-argued.

#### Reason

Holding everything else fixed and varying only the embedded surface, the composed heading+tags+contexts+body surface scored 130/180 paraphrase recall@8 against 132/180 body-only (p = 0.48) and changed no title answer. The earlier 58/60 title claim compared runs with different recency settings.

#### Impact

Supersedes adr_semantic_embeds_lexical_surface. Semantic and lexical sides read different surfaces by measured choice; a near-miss title probe set would be needed before revisiting it.

### revision-accepted - 2026-09-28T07:20:29Z

```json
{
  "decision_ref": "mse_wz1aec7859rk0h67:d1",
  "event_id": "adre_4ecaf857372a7b8a07e0",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_09h6y7z24fkfvp4t"
}
```

#### Decision

Accept mse_wz1aec7859rk0h67:d1.

#### Reason

JNL chose on 2026-09-28 to supersede the embedded-surface ADR and promote this one, accepting it now: the ablation is settled and the code already matches.

#### Impact

mse_wz1aec7859rk0h67:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
