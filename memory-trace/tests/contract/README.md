# Memory Trace API contract fixtures

Roadmap Phase 1 ("versioned API contract") deliverables that live as committed artifacts rather
than only as code: the filtered `/api/v1/*` OpenAPI schema and the TypeScript types generated
from it. Both are regeneratable, like the Phase 0 synthetic datasets and the Trail golden
fixture - they document the current contract, they aren't hand-maintained.

## Files

| File | What it is |
|---|---|
| `export_openapi.py` | Builds a real app against the deterministic 48-entry synthetic corpus, filters `app.openapi()` down to `/api/v1/*` paths and the component schemas they reference (legacy `/api/*` shapes never leak in), writes `openapi.v1.json`. |
| `openapi.v1.json` | The filtered schema (committed, for review/diff visibility). |
| `types.ts` | TypeScript types generated from `openapi.v1.json` via `openapi-typescript` - types only, no request/fetch client. A future React client (Phase 2+) picks its own data-fetching library (the frontend proposal names TanStack Query); generating a full client now would presume that choice. |

Contract behavior itself (v1/legacy parity, 404 parity, `provenance_class` default, named
component schemas) is asserted in `../test_v1_api_contract.py`, not here.

## Regenerating

After any `/api/v1/*` route or `memory_trace/models.py` change:

```powershell
$env:PYTHONPATH = ".;memory-trace"
python memory-trace/tests/contract/export_openapi.py
npx openapi-typescript memory-trace/tests/contract/openapi.v1.json -o memory-trace/tests/contract/types.ts
```

`openapi-typescript` is a root-level gitignored dev dependency (`npm install --save-dev
openapi-typescript`), matching the existing Playwright convention.

## Why filter to v1 only

The legacy unversioned `/api/*` routes have no `response_model` (they return plain dicts), so
they'd show up in the raw OpenAPI document as untyped/minimal entries. Since the whole point of
this contract is to give a not-yet-built React client something stable and fully-typed to consume,
the export keeps only `/api/v1/*` paths and their transitively-referenced schemas.
