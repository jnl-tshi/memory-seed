---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_business_separation
title: business/ separate from docs/; documents move, never copy
topics:
  - documentation
  - governance-profile
  - decision-harvest
created_at: 2026-08-06T17:16:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# business/ separate from docs/; documents move, never copy

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_5y962348e85x7grr:d1`

### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance, strictly separated from `docs/` which holds product specification and lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than copied; each document has one canonical home. The area is documented in the runtime index's Topology section with its dossier-versus-provenance convention, three areas, move-not-copy rule, and validation scope.

### Reason

The `business/` area exists as maintained source of truth for commercial strategy with an established move-not-copy convention. Docs README treats a document's folder as its lifecycle state, so duplicates create ambiguity. The area needed visibility in the index so anyone orienting from there would learn of the whole commercial-strategy tree, which is load-bearing for active work.

### Impact

The first member instituted the move-not-copy policy, establishing `business/` as authoritative for commercial materials and rejecting copying which violates the area's convention. The second member extended this by making the area discoverable through the runtime index, documenting its structure, dossier-versus-provenance split, and validation boundaries.

### Constitution

- `constitution:v1#single-source` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:16:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "event_id": "adre_421c61b9e55183cefcf4",
  "founding_quote": "**Business knowledge area: `business/`** — commercial strategy, kept deliberately separate from `docs/`, which holds product specification and implementation lifecycle.",
  "founding_source": ".memory-seed/index.md#L106",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_5y962348e85x7grr:d1"
  ]
}
```

#### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance reports, deliberately separated from `docs/` which holds product specification and implementation lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than being copied; a document has one canonical home.

#### Reason

This separation preserves single-source authority for business strategy while keeping `docs/` focused on product and implementation. Moving documents (not copying) ensures consistency and eliminates duplication.

#### Impact

Founded from the control file. Session decision mse_5y962348e85x7grr (2026-08-03) registered `business/` in the runtime index's Topology section after the area was created but initially undocumented, correcting a gap in agent orientation.

### revision-accepted - 2026-08-06T21:04:00Z

```json
{
  "event_id": "adre_2a218ce4048716282a9f",
  "founding_source": ".memory-seed/index.md#L106",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L106.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L106 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:30:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_08nhq28nkm2ecpt4:d1",
  "event_id": "adre_22f0248b4f3f13a935ce",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance reports, deliberately separated from `docs/` which holds product specification and implementation lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than being copied; a document has one canonical home.

#### Reason

Rests on the session decision that instituted it: "move rather than copy them out of `docs/4_Reference/`" (mse_08nhq28nkm2ecpt4:d1). Explicitly institutes the policy requiring documents to move rather than be copied between business/ and docs/.

#### Impact

Founded from .memory-seed/index.md#L106; this revision moves the concern off that control-file line onto mse_08nhq28nkm2ecpt4:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:25:00Z

```json
{
  "decision_ref": "mse_08nhq28nkm2ecpt4:d1",
  "event_id": "adre_f3f497762a2d5f0fbf37",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_08nhq28nkm2ecpt4:d1.

#### Reason

Wording retired and the anchor moved. This revision rested on mse_08nhq28nkm2ecpt4:d1, but mse_5y962348e85x7grr:d1 is a later decision in the same chain that had already moved the concern past it. A shift in the most recent authoritative decision triggers a regenerated summary, so both land together.

#### Impact

mse_08nhq28nkm2ecpt4:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:25:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_5y962348e85x7grr:d1",
  "event_id": "adre_9f399da9d7071d608ca4",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_08nhq28nkm2ecpt4:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance, strictly separated from `docs/` which holds product specification and lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than copied; each document has one canonical home. The area is documented in the runtime index's Topology section with its dossier-versus-provenance convention, three areas, move-not-copy rule, and validation scope.

#### Reason

The `business/` area exists as maintained source of truth for commercial strategy with an established move-not-copy convention. Docs README treats a document's folder as its lifecycle state, so duplicates create ambiguity. The area needed visibility in the index so anyone orienting from there would learn of the whole commercial-strategy tree, which is load-bearing for active work.

#### Impact

The first member instituted the move-not-copy policy, establishing `business/` as authoritative for commercial materials and rejecting copying which violates the area's convention. The second member extended this by making the area discoverable through the runtime index, documenting its structure, dossier-versus-provenance split, and validation boundaries.

### revision-accepted - 2026-08-08T23:25:40Z

```json
{
  "decision_ref": "mse_5y962348e85x7grr:d1",
  "event_id": "adre_94bfa960e8b3d23ddda1",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L106",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_5y962348e85x7grr:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_5y962348e85x7grr:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
