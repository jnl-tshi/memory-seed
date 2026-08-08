---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_forward_only_edges
title: Forward-only authoring with read-time bidirectional traversal
topics:
  - related-entries
  - graph
created_at: 2026-08-06T20:01:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Forward-only authoring with read-time bidirectional traversal

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L174`

### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is assembled at READ time, with inbound backlinks computed only from resolvable outbound refs. `build_related_entry_graph()` owns that assembly, and the read-only `link suggest` / `link show` surfaces expose it. No historical entry is ever edited to record an inbound link.

### Why

An inbound edge recorded on the target would mean editing a published entry, which append-only forbids; deriving the same edge at read time gives the identical old-to-new view with zero append-only tension. Restricting backlinks to resolvable refs keeps a typo or a deleted target from manufacturing a phantom edge. Backfill between pre-existing entries was deliberately deferred rather than shipped alongside.

### How it evolved

Founded from the control file with the write-time-only P1 scope chosen precisely because it carried zero append-only tension; backfill and a `link add` writer were deferred to P2.

### Constitution

- `constitution:v1#append-only` (governing)
- `constitution:v1#edge-kinds` (supporting)

### Awaiting review

- `mse_dvzh6fkn4d98cd6y:d1` - Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "supporting"
    }
  ],
  "event_id": "adre_266d027c023e46ad91ac",
  "founding_quote": "Forward-only authoring + read-time bidirectional traversal preserves append-only",
  "founding_source": ".memory-seed/index.md#L174",
  "source": "derived",
  "supporting_decisions": [
    "mse_dvzh6fkn4d98cd6y:d1"
  ]
}
```

#### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is assembled at READ time, with inbound backlinks computed only from resolvable outbound refs. `build_related_entry_graph()` owns that assembly, and the read-only `link suggest` / `link show` surfaces expose it. No historical entry is ever edited to record an inbound link.

#### Why

An inbound edge recorded on the target would mean editing a published entry, which append-only forbids; deriving the same edge at read time gives the identical old-to-new view with zero append-only tension. Restricting backlinks to resolvable refs keeps a typo or a deleted target from manufacturing a phantom edge. Backfill between pre-existing entries was deliberately deferred rather than shipped alongside.

#### Evolution

Founded from the control file with the write-time-only P1 scope chosen precisely because it carried zero append-only tension; backfill and a `link add` writer were deferred to P2.

### revision-accepted - 2026-08-06T21:15:00Z

```json
{
  "event_id": "adre_952f3b113b15339eb4b9",
  "founding_source": ".memory-seed/index.md#L174",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:34:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#edge-kinds",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_dvzh6fkn4d98cd6y:d1",
  "event_id": "adre_2a61df9ff684a67c566f",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is assembled at READ time, with inbound backlinks computed only from resolvable outbound refs. `build_related_entry_graph()` owns that assembly, and the read-only `link suggest` / `link show` surfaces expose it. No historical entry is ever edited to record an inbound link.

#### Why

Rests on the session decision that instituted it: "**bidirectional read-time traversal** as the canonical graph-read model" (mse_dvzh6fkn4d98cd6y:d1). Institutes the forward-only authoring strategy with bidirectional read-time traversal.

#### Evolution

Founded from .memory-seed/index.md#L174; this revision moves the concern off that control-file line onto mse_dvzh6fkn4d98cd6y:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
