# Progressive Provenance Surfaces Report

- Base: `5c5dadf7793ee92fedc8018053d5e45156080026`
- Implementation head: `bd3ef5030b796369038375d25850fbceb08e5bb6`
- All implementation commits: `bd3ef5030b796369038375d25850fbceb08e5bb6`
- Scope: CLI/MCP adapters, ESR audit/reporting, boundary-facing tests, and this worker checkpoint only.

## Delivered

- CLI `provenance show`, `bind`, and `check` share one validation path with MCP `memory_decision_provenance` and `memory_decision_provenance_bind`.
- Bindings are append-only Markdown JSON events containing only validated reference data; projections are generated transiently from Git with 0–20 context lines (default 3).
- Runtime records select the owning sidecar. Retired and detached owners cannot append; descendant runtime writes are refused from a root surface while explicitly selected runtimes remain readable.
- ESR reports provenance sidecar/reference evidence and temporal-lineage status. It does not claim Git commit clocks prove calendar time, and it will not modify `.gitignore` to publish a derived cache.

## Exact tests

```text
python -X utf8 -m pytest -q tests/test_provenance.py tests/test_provenance_surfaces.py tests/test_esr.py tests/test_mcp_server.py
git diff --check
```

## API assumptions and concerns

- The fixed provenance engine is the sole schema/append-only authority; adapters only transport validated records.
- A temporal cache is refreshed only when `.memory-seed/.temporal-lineage.json` is already ignored. ESR reports `cache-unignored` otherwise, rather than extending an unscoped tracked-file policy.
- No network witness is consulted. ESR labels Git-based ordering separately from independently witnessed calendar-time evidence.

## Task Packet reflection

The packet's explicit decision refs correctly constrained the work to public adapters and ESR aggregation. The allowlist required the temporal-cache integration to remain non-invasive: refusing an unignored cache is safer than silently editing `.gitignore`, while still exposing the required prerequisite.
