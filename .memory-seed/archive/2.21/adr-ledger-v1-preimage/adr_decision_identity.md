---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_decision_identity
title: Decision identity is (entry_id, dN)
topics:
  - schema
  - graph
created_at: 2026-08-06T16:30:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Decision identity is (entry_id, dN)

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_kdhw53hzp4nh8wwm:d1`

### Decision

A decision's identity is the pair (entry_id, dN). Both ends of a lifecycle edge name their decision: targets as `<entry_id>:dN` (explicit `:d1` even for single-decision entries), sources with a `dN ->` prefix whenever the writing entry carries two or more. Decision-level edges are a distinct edge set - never projected up to their entries.

### Why

A bare entry id is ambiguous the moment an entry carries a second decision, and the write path is the only place the ambiguity can be refused cheaply - the write refuses an unnamed end where the ref is still unwritten, while published bare ids stay legal history. Downstream, decision-level identity is what makes decision-scoped topics, lifecycle lineage and ADR membership addressable at all.

### How it evolved

Write-time `:dN` refs landed the morning of 2026-07-24 (mse_888p3x61z0kev9cp:d1); the mandate hardened both ends that afternoon; retrieval began serving decision granularity with canonical `mse_x:dN` chunk ids on 2026-08-05 (mse_qeht233q9ebvf2ms:d1).

### Constitution

- `constitution:v1#edge-kinds` (governing)
- `constitution:v1#explainability` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T16:30:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#explainability",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_kdhw53hzp4nh8wwm:d1",
  "event_id": "adre_d127bc9cb8ec50b64107",
  "source": "derived",
  "supporting_decisions": [
    "mse_888p3x61z0kev9cp:d1",
    "mse_qeht233q9ebvf2ms:d1"
  ],
  "update_entry_id": "mse_kdhw53hzp4nh8wwm"
}
```

#### Decision

A decision's identity is the pair (entry_id, dN). Both ends of a lifecycle edge name their decision: targets as `<entry_id>:dN` (explicit `:d1` even for single-decision entries), sources with a `dN ->` prefix whenever the writing entry carries two or more. Decision-level edges are a distinct edge set - never projected up to their entries.

#### Why

A bare entry id is ambiguous the moment an entry carries a second decision, and the write path is the only place the ambiguity can be refused cheaply - the write refuses an unnamed end where the ref is still unwritten, while published bare ids stay legal history. Downstream, decision-level identity is what makes decision-scoped topics, lifecycle lineage and ADR membership addressable at all.

#### Evolution

Write-time `:dN` refs landed the morning of 2026-07-24 (mse_888p3x61z0kev9cp:d1); the mandate hardened both ends that afternoon; retrieval began serving decision granularity with canonical `mse_x:dN` chunk ids on 2026-08-05 (mse_qeht233q9ebvf2ms:d1).

### revision-accepted - 2026-08-06T16:31:00Z

```json
{
  "decision_ref": "mse_kdhw53hzp4nh8wwm:d1",
  "event_id": "adre_6c001d21ba2a5e16f164",
  "source": "derived",
  "update_entry_id": "mse_kdhw53hzp4nh8wwm"
}
```
