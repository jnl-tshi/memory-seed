---
entry_id: mse_3n3mp35ekz08t4zb
title: Retrieval service consumer topology (Trail Phase 1)
---

```mermaid
flowchart TD
  SC["semantic_cache.py<br/>parser + ranker (shared substrate)"]
  RS["retrieval.py<br/>public service: search_memory / get_chunk /<br/>rollup / diagram sidecars"]
  MCP["mcp_server.py<br/>thin JSON-RPC wrapper<br/>(byte-identical tool contract)"]
  LENSE["lense.py<br/>in-package UI (maintenance-only)"]
  TRAIL["future companion UI package<br/>(imports the frozen service in Phase 2)"]

  SC --> RS
  RS --> MCP
  RS --> LENSE
  RS -.-> TRAIL
```
