---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_mcp_metadata_and_filters
title: "MCP retrieval metadata and filters: read-only, applied before ranking"
topics:
  - mcp-tools
  - multi-user-sessions
  - retrieval
created_at: 2026-08-08T03:02:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# MCP retrieval metadata and filters: read-only, applied before ranking

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

`memory_search` and `memory_get_chunk` expose per-entry user, session date, path and file hash as read-only metadata. `memory_search` accepts user and date-range filters, applied BEFORE ranking. `exclude_superseded` is opt-in and never defaults on. No ranking weight is derived from a filter.

### Why

Filtering before ranking keeps retrieval deterministic and each constraint orthogonal, so a client can compose them without the ranker quietly reinterpreting the result. `exclude_superseded` stays opt-in because retrieval must never hide live history by default.

### How it evolved

2026-06-15 planned the metadata and filter surface and added user and date filters; the same day shipped the read-only filterable API over the session layout; 2026-07-04 completed the contract with the opt-in `exclude_superseded` filter.

### Constitution

- `constitution:v1#retrieval-transparency` (governing)
- `constitution:v1#evidence-first` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#retrieval-transparency",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#evidence-first",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_dbt6c32kk5dk55xs:d1",
  "event_id": "adre_494a9e50a43cf40551a7",
  "source": "derived",
  "supporting_decisions": [
    "mse_77cn2v0rg9na3w0v:d2",
    "mse_ztcsrx4hw0b6kxdv:d2"
  ],
  "update_entry_id": "mse_dbt6c32kk5dk55xs"
}
```

#### Decision

`memory_search` and `memory_get_chunk` expose per-entry user, session date, path and file hash as read-only metadata. `memory_search` accepts user and date-range filters, applied BEFORE ranking. `exclude_superseded` is opt-in and never defaults on. No ranking weight is derived from a filter.

#### Why

Filtering before ranking keeps retrieval deterministic and each constraint orthogonal, so a client can compose them without the ranker quietly reinterpreting the result. `exclude_superseded` stays opt-in because retrieval must never hide live history by default.

#### Evolution

2026-06-15 planned the metadata and filter surface and added user and date filters; the same day shipped the read-only filterable API over the session layout; 2026-07-04 completed the contract with the opt-in `exclude_superseded` filter.
