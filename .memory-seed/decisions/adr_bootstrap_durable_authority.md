---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_bootstrap_durable_authority
title: Bootstrap durable decisions through ADR authority
topics:
  - control-plane
  - governance-profile
created_at: 2026-08-11T12:01:00Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Bootstrap durable decisions through ADR authority

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_nyqqq37hrgp6qcp3:d1`

### Decision

Bootstrap creates proposed ADRs for future-session constraints, records the first session, accepts only confirmed choices, and keeps the index and policy thin. A declared ratified Constitution governs lower layers; Constitution-free projects remain valid.

### Why

One concern head prevents duplicated bootstrap rationale, while the confirmation boundary prevents inferred assumptions from becoming policy and the optional Constitution boundary avoids imposing project governance where none is needed.

### How it evolved

Extends the initial durable-decision pipeline with the confirmed Constitution-optional precedence rule and establishes the combined contract as the 2.20 baseline.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-11T12:01:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#control-plane-precedence",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_p2dgz4af43dhxs4p:d1",
  "event_id": "adre_a3d78cce15873ec6d6eb",
  "source": "write-time",
  "supporting_decisions": [
    "mse_p2dgz4af43dhxs4p:d2"
  ],
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Decision

Bootstrap turns future-session constraints into proposed ADR concerns, ratifies confirmed choices through the first session, and keeps index and policy as thin links and executable rules.

#### Why

A single append-only concern head prevents bootstrap rationale from diverging across index, policy, and session history.

#### Evolution

Establishes the bootstrap authority pipeline and its confirmed-versus-proposed boundary.

### revision-accepted - 2026-08-11T12:01:30Z

```json
{
  "decision_ref": "mse_p2dgz4af43dhxs4p:d1",
  "event_id": "adre_fb794114d82da9dd2837",
  "source": "write-time",
  "update_entry_id": "mse_p2dgz4af43dhxs4p"
}
```

#### Reason

Ratified by JNL through the approved implementation plan.

### revision-proposed - 2026-08-11T12:30:00

```json
{
  "decision_ref": "mse_nyqqq37hrgp6qcp3:d1",
  "event_id": "adre_0d04f9a3d58cc3ebde33",
  "predecessors": [
    {
      "decision": "mse_p2dgz4af43dhxs4p:d1",
      "relation_assertion": "link:mse_nyqqq37hrgp6qcp3:d1:evolves:mse_p2dgz4af43dhxs4p:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_nyqqq37hrgp6qcp3"
}
```

#### Decision

Bootstrap creates proposed ADRs for future-session constraints, records the first session, accepts only confirmed choices, and keeps the index and policy thin. A declared ratified Constitution governs lower layers; Constitution-free projects remain valid.

#### Why

One concern head prevents duplicated bootstrap rationale, while the confirmation boundary prevents inferred assumptions from becoming policy and the optional Constitution boundary avoids imposing project governance where none is needed.

#### Evolution

Extends the initial durable-decision pipeline with the confirmed Constitution-optional precedence rule and establishes the combined contract as the 2.20 baseline.

### revision-accepted - 2026-08-11T12:31:00Z

```json
{
  "decision_ref": "mse_nyqqq37hrgp6qcp3:d1",
  "event_id": "adre_e62f62c45db30abc8640",
  "expected_authoritative_decision": "mse_p2dgz4af43dhxs4p:d1",
  "source": "write-time",
  "update_entry_id": "mse_nyqqq37hrgp6qcp3"
}
```

#### Reason

Ratifies the complete 2.20 bootstrap authority baseline.
