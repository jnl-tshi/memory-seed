---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_mcp_decision_envelope_review
title: MCP decision envelope and mandatory ADR review
topics:
  - schema
  - mcp-tools
created_at: 2026-08-03T15:40:01Z
user_initials: JNL
agent_type: codex
source: write-time
---

# MCP decision envelope and mandatory ADR review

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_17d0qqh34a07qp5b:d1`

### Decision

Require content-bound living ADR review before any MCP write that evolves or replaces a lineage member.

### Why

The LLM must review every affected concern and the exact immutable draft before the transaction mutates session or sidecar state.

### How it evolved

Evolves the shared decision envelope from atomic semantic authorship into a fail-closed multi-ADR review transaction.

### Awaiting review

- `mse_axkrkd339br970kw:d2` - Require content-bound living ADR review before any CLI or MCP session append that evolves or replaces a...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-03T15:40:01Z

```json
{
  "decision_ref": "mse_ddeat5w29spep3qw:d1",
  "event_id": "adre_7fa98ce0fbc78c300c2f",
  "predecessors": [
    {
      "decision": "mse_z7rfq8x5qjfbyzdc:d1",
      "relation_assertion": "link:mse_ddeat5w29spep3qw:d1:evolves:mse_z7rfq8x5qjfbyzdc:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Decision

Use one decision envelope and require content-bound ADR review before lineage-linked writes.

#### Why

One authoring transaction keeps narrative, semantic sidecars, and review outcomes consistent.

#### Evolution

Extends the original decision-sidecar envelope with a fail-closed living ADR review gate.

### revision-accepted - 2026-08-03T15:40:02Z

```json
{
  "decision_ref": "mse_ddeat5w29spep3qw:d1",
  "event_id": "adre_6b8b0c9e9f21abdcaa7f",
  "source": "write-time",
  "update_entry_id": "mse_kbc2mq9972ppy1vw"
}
```

#### Reason

Accepted as the historical governing head before mandatory-review dogfooding.

### revision-proposed - 2026-08-03T15:41:00

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d1",
  "event_id": "adre_b07b33bccf8c6edc2690",
  "predecessors": [
    {
      "decision": "mse_ddeat5w29spep3qw:d1",
      "relation_assertion": "link:mse_17d0qqh34a07qp5b:d1:evolves:mse_ddeat5w29spep3qw:d1"
    },
    {
      "decision": "mse_z7rfq8x5qjfbyzdc:d1",
      "relation_assertion": "link:mse_17d0qqh34a07qp5b:d1:evolves:mse_z7rfq8x5qjfbyzdc:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Decision

Require content-bound living ADR review before any MCP write that evolves or replaces a lineage member.

#### Why

The LLM must review every affected concern and the exact immutable draft before the transaction mutates session or sidecar state.

#### Evolution

Evolves the shared decision envelope from atomic semantic authorship into a fail-closed multi-ADR review transaction.

### revision-accepted - 2026-08-03T15:41:10Z

```json
{
  "decision_ref": "mse_17d0qqh34a07qp5b:d1",
  "event_id": "adre_a4230ddf644860ac66e7",
  "expected_authoritative_decision": "mse_ddeat5w29spep3qw:d1",
  "source": "write-time",
  "update_entry_id": "mse_17d0qqh34a07qp5b"
}
```

#### Reason

Accepted after the mandatory review receipt and zero-write first-call proof.

### revision-proposed - 2026-08-10T13:00:00

```json
{
  "decision_ref": "mse_axkrkd339br970kw:d2",
  "event_id": "adre_bf87a3552d2336562fde",
  "predecessors": [
    {
      "decision": "mse_17d0qqh34a07qp5b:d1",
      "relation_assertion": "link:mse_axkrkd339br970kw:d2:evolves:mse_17d0qqh34a07qp5b:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_axkrkd339br970kw"
}
```

#### Decision

Require content-bound living ADR review before any CLI or MCP session append that evolves or replaces a lineage member.

#### Why

Every public session-write surface must review the same complete concern context and exact immutable draft before mutation.

#### Evolution

Extends the accepted MCP gate into one shared append preflight while preserving the zero-write first call and parent-first transaction.
