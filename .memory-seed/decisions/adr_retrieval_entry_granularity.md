---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_retrieval_entry_granularity
title: "Retrieval: entry-level chunks as default, with optional section granularity"
topics:
  - retrieval
  - memory-trace
  - control-plane
created_at: 2026-08-08T03:06:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Retrieval: entry-level chunks as default, with optional section granularity

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

The memory-retrieval service uses session entries (delimited by `##` headings) as the default coherent chunk boundary, with `entry_id` as the chunk id. Section granularity is optional for querying long or multi-topic entries. Rollup and windowing live in the service; the MCP surface adapts presentation only. The retrieval service is extracted from the MCP implementation - both run the same service code, with parity proven by tests.

### Why

A `##` entry is the coherent memory block carrying shared metadata, rationale, implementation and validation - separating a decision from its rationale loses too much context, so entry-level retrieval is the normal agent-memory behaviour. The service extraction lets retrieval and MCP evolve without drift, and parity tests lock the contract down.

### How it evolved

2026-05-26 established entry chunks as the default MCP memory unit; 2026-07-05 extracted the retrieval service from MCP, making MCP a wrapper with proven parity, and placed rollup in the service with the UI adapting only.

### Constitution

- `constitution:v1#single-source` (governing)
- `constitution:v1#minimal-context` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:06:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#single-source",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#minimal-context",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_pwwz3ys324ght2qs:d1",
  "event_id": "adre_93b4d4c00e0d495487e8",
  "source": "derived",
  "supporting_decisions": [
    "ms-845042c7:d1",
    "mse_3n3mp35ekz08t4zb:d2"
  ],
  "update_entry_id": "mse_pwwz3ys324ght2qs"
}
```

#### Decision

The memory-retrieval service uses session entries (delimited by `##` headings) as the default coherent chunk boundary, with `entry_id` as the chunk id. Section granularity is optional for querying long or multi-topic entries. Rollup and windowing live in the service; the MCP surface adapts presentation only. The retrieval service is extracted from the MCP implementation - both run the same service code, with parity proven by tests.

#### Why

A `##` entry is the coherent memory block carrying shared metadata, rationale, implementation and validation - separating a decision from its rationale loses too much context, so entry-level retrieval is the normal agent-memory behaviour. The service extraction lets retrieval and MCP evolve without drift, and parity tests lock the contract down.

#### Evolution

2026-05-26 established entry chunks as the default MCP memory unit; 2026-07-05 extracted the retrieval service from MCP, making MCP a wrapper with proven parity, and placed rollup in the service with the UI adapting only.
