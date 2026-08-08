---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_edge_confidence
title: edge_confidence on machine-suggested edges; consumers fade low tiers
topics:
  - lifecycle-edges
  - graph
created_at: 2026-08-06T19:03:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# edge_confidence on machine-suggested edges; consumers fade low tiers

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L186`

### Decision

Every machine-suggested lifecycle edge carries a structured `edge_confidence` entry of `{ref, confidence, tier}` keyed to the exact edge token, stored as YAML rather than prose. `links check` tolerates it as an unknown sibling key with no parser change. Consumers read it: the Trace graph and Trail fade low-confidence edges by opacity so an unverified suggestion never renders as settled fact, while authored edges carry no confidence attribute and render at full strength.

### Why

Discarding low-confidence edges would waste judged work, but writing them indistinguishably from human-authored edges would let a guess masquerade as fact; marking them structurally keeps both. Structured YAML lets a later stage weight or filter without re-parsing prose. Fading them in the view the user actually looks at is what delivers the guarantee, and omitting the attribute rather than nulling it avoids a coercion trap that would silently dim authored edges.

### How it evolved

Introduced 2026-07-25 during the 1,108-pair link campaign with consumption deliberately deferred; the backend read path threading confidence into the graph payload landed the same day, and the client fade in graph and Trail completed it.

### Constitution

- `constitution:v1#provenance` (governing)
- `constitution:v1#explainability` (supporting)

### Awaiting review

- `mse_p4xd3wqf214nqtmv:d2` - Every machine-suggested lifecycle edge carries a structured `edge_confidence` entry of `{ref, confidence,...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T19:03:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#explainability",
      "role": "supporting"
    }
  ],
  "event_id": "adre_6b80b5542587c1c82cfa",
  "founding_quote": "Each machine-suggested edge carries a structured **`edge_confidence`** field",
  "founding_source": ".memory-seed/index.md#L186",
  "source": "derived",
  "supporting_decisions": [
    "mse_p4xd3wqf214nqtmv:d2",
    "mse_7a6wgm62nty5ynkh:d1"
  ]
}
```

#### Decision

Every machine-suggested lifecycle edge carries a structured `edge_confidence` entry of `{ref, confidence, tier}` keyed to the exact edge token, stored as YAML rather than prose. `links check` tolerates it as an unknown sibling key with no parser change. Consumers read it: the Trace graph and Trail fade low-confidence edges by opacity so an unverified suggestion never renders as settled fact, while authored edges carry no confidence attribute and render at full strength.

#### Why

Discarding low-confidence edges would waste judged work, but writing them indistinguishably from human-authored edges would let a guess masquerade as fact; marking them structurally keeps both. Structured YAML lets a later stage weight or filter without re-parsing prose. Fading them in the view the user actually looks at is what delivers the guarantee, and omitting the attribute rather than nulling it avoids a coercion trap that would silently dim authored edges.

#### Evolution

Introduced 2026-07-25 during the 1,108-pair link campaign with consumption deliberately deferred; the backend read path threading confidence into the graph payload landed the same day, and the client fade in graph and Trail completed it.

### revision-accepted - 2026-08-06T21:09:00Z

```json
{
  "event_id": "adre_ed92b42170e5d59b6820",
  "founding_source": ".memory-seed/index.md#L186",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:04:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#provenance",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#explainability",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_p4xd3wqf214nqtmv:d2",
  "event_id": "adre_1cad7090e743f3f16547",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Every machine-suggested lifecycle edge carries a structured `edge_confidence` entry of `{ref, confidence, tier}` keyed to the exact edge token, stored as YAML rather than prose. `links check` tolerates it as an unknown sibling key with no parser change. Consumers read it: the Trace graph and Trail fade low-confidence edges by opacity so an unverified suggestion never renders as settled fact, while authored edges carry no confidence attribute and render at full strength.

#### Why

Rests on the session decision that instituted it: "Each campaign edge carries its model confidence in a new `edge_confidence:` list of `{ref, confidence, tier}` mappings" (mse_p4xd3wqf214nqtmv:d2). Created the structured edge_confidence field that the ADR governs.

#### Evolution

Founded from .memory-seed/index.md#L186; this revision moves the concern off that control-file line onto mse_p4xd3wqf214nqtmv:d2, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
