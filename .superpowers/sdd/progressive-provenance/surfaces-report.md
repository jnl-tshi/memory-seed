# Progressive Provenance Surfaces Report

- Base: `5c5dadf7793ee92fedc8018053d5e45156080026`
- Implementation head: `bd3ef5030b796369038375d25850fbceb08e5bb6`
- All implementation commits: `bd3ef5030b796369038375d25850fbceb08e5bb6`
- Scope: CLI/MCP adapters, ESR audit/reporting, boundary-facing tests, and this worker checkpoint only.

## Delivered

- CLI `provenance show`, `bind`, and `check` share one validation path with MCP `memory_decision_provenance` and `memory_decision_provenance_bind`.
- Bindings are append-only Markdown JSON events containing only validated reference data; projections are generated transiently from Git with 0–20 context lines (default 3).
- Runtime records select the owning sidecar. Retired and detached owners cannot append; descendant runtime writes are refused from a root surface while explicitly selected runtimes remain readable.
- ESR reports provenance sidecar/reference evidence and temporal-lineage classifications. The required cache path is explicitly ignored; Git commit clocks still do not prove calendar time.

## Exact tests

```text
python -X utf8 -m pytest -q tests/test_provenance.py tests/test_provenance_surfaces.py tests/test_esr.py tests/test_mcp_server.py
git diff --check
```

## API assumptions and concerns

- The fixed provenance engine is the sole schema/append-only authority; adapters only transport validated records.
- `.memory-seed/.temporal-lineage.json` is now explicitly ignored as required by the accepted ESR observable. ESR emits reachable-order, claimed-timestamp relation, and calendar-evidence classifications without network witnesses.
- No network witness is consulted. ESR labels Git-based ordering separately from independently witnessed calendar-time evidence.

## Task Packet reflection

The packet's explicit decision refs correctly constrained the work to public adapters and ESR aggregation. The allowlist required the temporal-cache integration to remain non-invasive: refusing an unignored cache is safer than silently editing `.gitignore`, while still exposing the required prerequisite.

## Round-one reviewer fix receipt

- Measured nested-runtime topology now controls active-pod write authority. A root cannot mint a writable pod identity by supplying a record, while explicit descendant and retired inspection works through both CLI runtime files and MCP runtime objects.
- Append-only evidence is now a Git-history prefix audit. Missing baseline evidence is `unverifiable`; deleted, reordered, malformed, or historically rewritten event streams are `violated`, never `true` by assertion.
- The approved cache ignore declaration was added, and ESR now publishes temporal classifications rather than only cache status.
- Tests cover hostile real nested runtime ownership, missing decision refs, unavailable Git, event deletion and cross-kind reordering, CLI parity, and cache-backed ESR classification output.

### Updated reflection

The review exposed that schema validation is not authority validation and that a parsed event list is not append-only proof. The fix keeps both guarantees at the surface boundary: filesystem topology authorizes ownership and Git anchors event order, while the engine remains the sole source of binding schema and projection semantics.

## Round-two reviewer fix receipt

- `_git_sidecar_baseline` now uses the shared Git-unavailable semantics. CLI `provenance check` and MCP `memory_decision_provenance_check` return a complete structured payload with `append_only.status: unverifiable` and `anchor: git-unavailable` instead of raising when Git cannot be launched or no repository is available.
- `memory_esr` now explicitly promises the actual boundary: it never repairs authoritative memory, but may update rebuildable ignored temporal-lineage and other derived cache state.
- Direct tests cover both unavailable-Git checks and the MCP tool-list contract.

### Updated reflection

An audit surface needs a vocabulary for absent evidence, not merely true and false. Making Git unavailability explicit preserves usable reference-audit output. Likewise, cache refresh is a legitimate derived write only when callers can distinguish it from an authoritative-memory repair.
