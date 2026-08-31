---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_link_retraction
title: "Append-only link retraction via retracts: blocks"
topics:
  - lifecycle-edges
  - graph
created_at: 2026-08-06T19:02:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Append-only link retraction via retracts: blocks

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_fsdq53qa5ak68xqh:d1`

### Decision

Published lifecycle edges are never edited in place. A downgrade or removal is expressed by appending a new sidecar block declaring `retracts: <kind> <ref> [(date)]`; the reader unions all edges then subtracts the retracted ones, and `links check` validates violations. A downgrade combines a retract of the old kind with a fresh edge of the new kind in a single authored block.

### Reason

The session's fuse forbids reopening published blocks, so correction must append rather than edit. The retraction mechanism makes the change non-destructive and auditable—the history shows both the original edge and the correction. The twin-retract fix ensures that multi-form edges (arrow-prefixed refs appearing as both entry-level and decision-level) are completely removed. The conversion of five hand-audited downgrades from in-place edits restored constitutional compliance with Invariant #2 (append-only).

### Impact

The initial mechanism allowed retracting edges by kind and ref, optionally pinned by the original declaration date. Then the mechanism was applied retroactively to fix five published sidecar edits that violated the append-only invariant, surfacing and fixing a bug where arrow-prefixed bare refs survived as decision-level edges even when their entry-level twins were retracted.

### Constitution

- `constitution:v1#link-corrections` (governing)
- `constitution:v1#append-only` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#link-corrections",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "event_id": "adre_6f52afacbbafd2eb9bd7",
  "founding_quote": "Correct a published lifecycle edge (downgrade or remove) through an append-only `retracts:` block",
  "founding_source": ".memory-seed/policy.md#L43",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_c3a4z35t4m4rjf1n:d1",
    "mse_fsdq53qa5ak68xqh:d1"
  ]
}
```

#### Decision

A published lifecycle edge is never edited in place. A downgrade or removal is expressed by appending a NEW sidecar block declaring `retracts: <kind> <ref> [(date)]`; the reader unions all edges then subtracts the retracted ones, and `links check` validates malformed, dangling and forward-only violations. A downgrade is a retract of the old kind plus a fresh edge of the new kind, authored together. `session merge-branch` refuses in-place edits to published link sidecars, and that guard is not to be bypassed.

#### Reason

Append-only is the corpus invariant, so a correction must be an addition rather than a rewrite: the evidence that an edge was once asserted is itself worth keeping. The gap surfaced when the fuse correctly refused hand-audit edits and the only way through was bypassing the guard. Editing blocks in place was rejected for defeating that guard and deleting them for destroying evidence; a combined shorthand was deferred as less legible than an explicit retract-plus-readd pair.

#### Impact

Built 2026-07-25 as the sanctioned correction path after the fuse refused in-place sidecar edits, then exercised the same evening by converting five hand-audit downgrades back to append-only retracts, which also exposed and fixed the arrow-bare twin-edge reader bug.

### revision-accepted - 2026-08-06T21:18:00Z

```json
{
  "event_id": "adre_f978d4981c9714587f86",
  "founding_source": ".memory-seed/policy.md#L43",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/policy.md#L43.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/policy.md#L43 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:09:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#link-corrections",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_c3a4z35t4m4rjf1n:d1",
  "event_id": "adre_74b690147dce1ccc4d13",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

A published lifecycle edge is never edited in place. A downgrade or removal is expressed by appending a NEW sidecar block declaring `retracts: <kind> <ref> [(date)]`; the reader unions all edges then subtracts the retracted ones, and `links check` validates malformed, dangling and forward-only violations. A downgrade is a retract of the old kind plus a fresh edge of the new kind, authored together. `session merge-branch` refuses in-place edits to published link sidecars, and that guard is not to be bypassed.

#### Reason

Rests on the session decision that instituted it: "Added an append-only `retracts:` mechanism to link sidecars so a published lifecycle edge can be downgraded or removed" (mse_c3a4z35t4m4rjf1n:d1). Introduced the append-only retracts mechanism enabling non-destructive correction of published lifecycle edges.

#### Impact

Founded from .memory-seed/policy.md#L43; this revision moves the concern off that control-file line onto mse_c3a4z35t4m4rjf1n:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:28:00Z

```json
{
  "decision_ref": "mse_c3a4z35t4m4rjf1n:d1",
  "event_id": "adre_e1b2fb1fdfcb66ac55e9",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_c3a4z35t4m4rjf1n:d1.

#### Reason

Wording retired and the anchor moved. This revision rested on mse_c3a4z35t4m4rjf1n:d1, but mse_fsdq53qa5ak68xqh:d1 is a later decision in the same chain that had already moved the concern past it. A shift in the most recent authoritative decision triggers a regenerated summary, so both land together.

#### Impact

mse_c3a4z35t4m4rjf1n:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:28:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#link-corrections",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_fsdq53qa5ak68xqh:d1",
  "event_id": "adre_1eca97b427ba9d13218d",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_c3a4z35t4m4rjf1n:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Published lifecycle edges are never edited in place. A downgrade or removal is expressed by appending a new sidecar block declaring `retracts: <kind> <ref> [(date)]`; the reader unions all edges then subtracts the retracted ones, and `links check` validates violations. A downgrade combines a retract of the old kind with a fresh edge of the new kind in a single authored block.

#### Reason

The session's fuse forbids reopening published blocks, so correction must append rather than edit. The retraction mechanism makes the change non-destructive and auditable—the history shows both the original edge and the correction. The twin-retract fix ensures that multi-form edges (arrow-prefixed refs appearing as both entry-level and decision-level) are completely removed. The conversion of five hand-audited downgrades from in-place edits restored constitutional compliance with Invariant #2 (append-only).

#### Impact

The initial mechanism allowed retracting edges by kind and ref, optionally pinned by the original declaration date. Then the mechanism was applied retroactively to fix five published sidecar edits that violated the append-only invariant, surfacing and fixing a bug where arrow-prefixed bare refs survived as decision-level edges even when their entry-level twins were retracted.

### revision-accepted - 2026-08-08T23:28:40Z

```json
{
  "decision_ref": "mse_fsdq53qa5ak68xqh:d1",
  "event_id": "adre_7fcd9d718d484950871d",
  "expected_authoritative_decision": "founding:.memory-seed/policy.md#L43",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_fsdq53qa5ak68xqh:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_fsdq53qa5ak68xqh:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
