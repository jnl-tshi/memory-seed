---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_parent_first_sidecar_transaction
title: Parent-first recoverable sidecar transaction
topics:
  - session-fuse
  - feature-build
created_at: 2026-08-03T15:40:03Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Parent-first recoverable sidecar transaction

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_17d0qqh34a07qp5b:d2`

### Decision

Publish ADR ledger events with topic and lifecycle sidecars after the canonical session parent inside one recoverable transaction.

### Reason

The parent-first invariant prevents orphan enrichment, while structural reconciliation preserves independent ledger history and detects competing authority.

### Impact

Extends the parent-first decision-sidecar transaction to living ADR events and branch fusion.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-03T15:40:03Z

```json
{
  "decision_ref": "mse_d06t9bccm3yykfqs:d1",
  "event_id": "adre_f6786257035191a4352f",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_qbp1ndbnhezj34eb:d1",
      "relation_assertion": "link:mse_d06t9bccm3yykfqs:d1:evolves:mse_qbp1ndbnhezj34eb:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Decision

Publish the canonical session parent before topic, lifecycle, and ADR sidecars.

#### Reason

Interruptions can leave incomplete enrichment but never orphan sidecars that point to a missing parent.

#### Impact

Builds on staged recovery by making parent-first publication the governing transaction order.

### revision-accepted - 2026-08-03T15:40:04Z

```json
{
  "decision_ref": "mse_d06t9bccm3yykfqs:d1",
  "event_id": "adre_15968f9ec76140857b17",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Decision

Accept mse_d06t9bccm3yykfqs:d1.

#### Reason

Accepted as the parent-first transaction head before ADR-event integration.

#### Impact

mse_d06t9bccm3yykfqs:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-03T15:41:00

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d2",
  "event_id": "adre_9fb8d17e212bfc5a38df",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_d06t9bccm3yykfqs:d1",
      "relation_assertion": "link:mse_17d0qqh34a07qp5b:d2:evolves:mse_d06t9bccm3yykfqs:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Decision

Publish ADR ledger events with topic and lifecycle sidecars after the canonical session parent inside one recoverable transaction.

#### Reason

The parent-first invariant prevents orphan enrichment, while structural reconciliation preserves independent ledger history and detects competing authority.

#### Impact

Extends the parent-first decision-sidecar transaction to living ADR events and branch fusion.

### revision-accepted - 2026-08-03T15:41:11Z

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d2",
  "event_id": "adre_f3559625659a0a4767e7",
  "expected_authoritative_decision": "mse_d06t9bccm3yykfqs:d1",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Decision

Accept mse_17d0qqh34a07qp5b:d2.

#### Reason

Accepted after transactional writer and branch-fuse regression gates passed.

#### Impact

mse_17d0qqh34a07qp5b:d2 becomes the authoritative decision; later contrary evidence requires a successor revision.
