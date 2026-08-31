---
format: memory-seed-adr/2
schema_version: 2
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

Authoritative decision: `mse_dvzh6fkn4d98cd6y:d1`

### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML frontmatter. The bidirectional graph is assembled at read time, with inbound backlinks computed only from resolvable outbound references. The `link suggest` command provides read-only suggestions, and `link add` is constrained to adding edges from the current or newest entry only. Backfilling edges between pre-existing entries is deferred; no historical entry is ever edited to record an inbound link.

### Reason

An edge lives in its source entry's YAML, so generating one from an existing entry would rewrite history, colliding with append-only chronology. Forward-only authoring plus bidirectional read-time traversal captures relationships without editing history. Derived edges already populate the graph, so explicit links are a curated overlay. Keeping edges in Markdown preserves it as the single source of truth.

### Impact

The complete approach was established as a single decision encompassing forward-only authoring, read-time bidirectional traversal, and the constraint that links can only be added from current or newest entries.

### Constitution

- `constitution:v1#append-only` (governing)
- `constitution:v1#edge-kinds` (supporting)

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
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_dvzh6fkn4d98cd6y:d1"
  ]
}
```

#### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is assembled at READ time, with inbound backlinks computed only from resolvable outbound refs. `build_related_entry_graph()` owns that assembly, and the read-only `link suggest` / `link show` surfaces expose it. No historical entry is ever edited to record an inbound link.

#### Reason

An inbound edge recorded on the target would mean editing a published entry, which append-only forbids; deriving the same edge at read time gives the identical old-to-new view with zero append-only tension. Restricting backlinks to resolvable refs keeps a typo or a deleted target from manufacturing a phantom edge. Backfill between pre-existing entries was deliberately deferred rather than shipped alongside.

#### Impact

Founded from the control file with the write-time-only P1 scope chosen precisely because it carried zero append-only tension; backfill and a `link add` writer were deferred to P2.

### revision-accepted - 2026-08-06T21:15:00Z

```json
{
  "event_id": "adre_952f3b113b15339eb4b9",
  "founding_source": ".memory-seed/index.md#L174",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L174.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L174 becomes the authoritative decision; later contrary evidence requires a successor revision.

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
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML; the bidirectional graph is assembled at READ time, with inbound backlinks computed only from resolvable outbound refs. `build_related_entry_graph()` owns that assembly, and the read-only `link suggest` / `link show` surfaces expose it. No historical entry is ever edited to record an inbound link.

#### Reason

Rests on the session decision that instituted it: "**bidirectional read-time traversal** as the canonical graph-read model" (mse_dvzh6fkn4d98cd6y:d1). Institutes the forward-only authoring strategy with bidirectional read-time traversal.

#### Impact

Founded from .memory-seed/index.md#L174; this revision moves the concern off that control-file line onto mse_dvzh6fkn4d98cd6y:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:09:00Z

```json
{
  "decision_ref": "mse_dvzh6fkn4d98cd6y:d1",
  "event_id": "adre_61d989ce954db2c1f13f",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_dvzh6fkn4d98cd6y:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_dvzh6fkn4d98cd6y:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:09:20Z

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
  "event_id": "adre_728b4539a2d13814ab1d",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Related-entry edges are authored forward-only in the writing entry's own YAML frontmatter. The bidirectional graph is assembled at read time, with inbound backlinks computed only from resolvable outbound references. The `link suggest` command provides read-only suggestions, and `link add` is constrained to adding edges from the current or newest entry only. Backfilling edges between pre-existing entries is deferred; no historical entry is ever edited to record an inbound link.

#### Reason

An edge lives in its source entry's YAML, so generating one from an existing entry would rewrite history, colliding with append-only chronology. Forward-only authoring plus bidirectional read-time traversal captures relationships without editing history. Derived edges already populate the graph, so explicit links are a curated overlay. Keeping edges in Markdown preserves it as the single source of truth.

#### Impact

The complete approach was established as a single decision encompassing forward-only authoring, read-time bidirectional traversal, and the constraint that links can only be added from current or newest entries.

### revision-accepted - 2026-08-08T23:09:40Z

```json
{
  "decision_ref": "mse_dvzh6fkn4d98cd6y:d1",
  "event_id": "adre_eef4300e34c332a53cf5",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L174",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_dvzh6fkn4d98cd6y:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_dvzh6fkn4d98cd6y:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
