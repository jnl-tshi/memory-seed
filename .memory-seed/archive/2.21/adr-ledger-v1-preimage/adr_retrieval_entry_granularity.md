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
Status: **Accepted**

Authoritative decision: `mse_pwwz3ys324ght2qs:d1`

### Decision

The memory-retrieval service uses session entries delimited by ## headings as the default coherent chunk boundary, with entry_id as the chunk id. Section-level granularity is optional for querying long or multi-topic entries. Entry-level results are collapsed into rollups where section matches drive an entry's score but never appear as separate selectable records. The retrieval service is extracted from the MCP implementation with both running the same service code, and parity is proven by tests.

### Why

A ## entry is the coherent memory block carrying shared metadata, rationale, implementation, and validation together - separating a decision from its rationale loses too much context. Heading-level chunking was rejected because it fragments this coherence. Service extraction lets retrieval and MCP evolve independently without drift, with parity tests locking down the contract. Rollup grouping preserves section highlights as metadata while keeping results organized around entries.

### How it evolved

The decision began with establishing ## entries as the default chunk boundary and rejecting heading-level chunking. It then evolved to extract retrieval service logic into its own module with MCP as a thin wrapper, proven identical by parity tests. Finally it added rollup logic to collapse ranked section results into entry-level rollups with section matches preserved as highlight metadata.

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

### revision-rejected - 2026-08-08T23:15:00Z

```json
{
  "decision_ref": "mse_pwwz3ys324ght2qs:d1",
  "event_id": "adre_28e66483e717d39ac5d0",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:15:20Z

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
  "event_id": "adre_267faf8eaa6e7e2243b4",
  "source": "derived",
  "supporting_decisions": [
    "ms-845042c7:d1",
    "mse_3n3mp35ekz08t4zb:d2"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The memory-retrieval service uses session entries delimited by ## headings as the default coherent chunk boundary, with entry_id as the chunk id. Section-level granularity is optional for querying long or multi-topic entries. Entry-level results are collapsed into rollups where section matches drive an entry's score but never appear as separate selectable records. The retrieval service is extracted from the MCP implementation with both running the same service code, and parity is proven by tests.

#### Why

A ## entry is the coherent memory block carrying shared metadata, rationale, implementation, and validation together - separating a decision from its rationale loses too much context. Heading-level chunking was rejected because it fragments this coherence. Service extraction lets retrieval and MCP evolve independently without drift, with parity tests locking down the contract. Rollup grouping preserves section highlights as metadata while keeping results organized around entries.

#### Evolution

The decision began with establishing ## entries as the default chunk boundary and rejecting heading-level chunking. It then evolved to extract retrieval service logic into its own module with MCP as a thin wrapper, proven identical by parity tests. Finally it added rollup logic to collapse ranked section results into entry-level rollups with section matches preserved as highlight metadata.

### revision-accepted - 2026-08-08T23:15:40Z

```json
{
  "decision_ref": "mse_pwwz3ys324ght2qs:d1",
  "event_id": "adre_acf2132e530520482dcb",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
