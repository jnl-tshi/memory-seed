---
format: memory-seed-adr/1
schema_version: 1
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

Authoritative decision: `founding:.memory-seed/index.md#L106`

### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance reports, deliberately separated from `docs/` which holds product specification and implementation lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than being copied; a document has one canonical home.

### Why

This separation preserves single-source authority for business strategy while keeping `docs/` focused on product and implementation. Moving documents (not copying) ensures consistency and eliminates duplication.

### How it evolved

Founded from the control file. Session decision mse_5y962348e85x7grr (2026-08-03) registered `business/` in the runtime index's Topology section after the area was created but initially undocumented, correcting a gap in agent orientation.

### Constitution

- `constitution:v1#single-source` (governing)

### Awaiting review

- `mse_08nhq28nkm2ecpt4:d1` - Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance...

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
  "source": "derived",
  "supporting_decisions": [
    "mse_5y962348e85x7grr:d1"
  ]
}
```

#### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance reports, deliberately separated from `docs/` which holds product specification and implementation lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than being copied; a document has one canonical home.

#### Why

This separation preserves single-source authority for business strategy while keeping `docs/` focused on product and implementation. Moving documents (not copying) ensures consistency and eliminates duplication.

#### Evolution

Founded from the control file. Session decision mse_5y962348e85x7grr (2026-08-03) registered `business/` in the runtime index's Topology section after the area was created but initially undocumented, correcting a gap in agent orientation.

### revision-accepted - 2026-08-06T21:04:00Z

```json
{
  "event_id": "adre_2a218ce4048716282a9f",
  "founding_source": ".memory-seed/index.md#L106",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

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
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Commercial strategy material lives in `business/` as authoritative dossiers and supporting provenance reports, deliberately separated from `docs/` which holds product specification and implementation lifecycle. Documents move from `docs/4_Reference/` into `business/` rather than being copied; a document has one canonical home.

#### Why

Rests on the session decision that instituted it: "move rather than copy them out of `docs/4_Reference/`" (mse_08nhq28nkm2ecpt4:d1). Explicitly institutes the policy requiring documents to move rather than be copied between business/ and docs/.

#### Evolution

Founded from .memory-seed/index.md#L106; this revision moves the concern off that control-file line onto mse_08nhq28nkm2ecpt4:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
