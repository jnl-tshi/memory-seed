"""Export the /api/v1/* OpenAPI schema for TypeScript type generation.

Builds a real app against the deterministic synthetic corpus (so the export
never depends on this repo's own session log), then filters the full
OpenAPI document down to v1 paths and the component schemas they actually
reference - the legacy unversioned routes' shapes never leak into the
generated client types.

Regenerate after any /api/v1/* or memory_trace/models.py change:

    PYTHONPATH=memory-trace python memory-trace/tests/contract/export_openapi.py
    npx openapi-typescript memory-trace/tests/contract/openapi.v1.json \\
        -o memory-trace/tests/contract/types.ts

(see README.md in this directory for the Windows/PowerShell form).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(FIXTURES))

from generate_synthetic import generate  # noqa: E402

from memory_trace.service import create_app  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "openapi.v1.json"


def _collect_schema_refs(node: object, refs: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            _collect_schema_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_schema_refs(item, refs)


def filtered_v1_schema(full_schema: dict) -> dict:
    v1_paths = {path: item for path, item in full_schema["paths"].items() if path.startswith("/api/v1")}

    refs: set[str] = set()
    _collect_schema_refs(v1_paths, refs)
    # Referenced schemas can themselves reference others (e.g. GraphResponse ->
    # GraphNode -> ProvenanceClass); keep expanding until the set is stable.
    all_schemas = full_schema["components"]["schemas"]
    frontier = set(refs)
    while frontier:
        newly_found: set[str] = set()
        for name in frontier:
            _collect_schema_refs(all_schemas.get(name, {}), newly_found)
        frontier = newly_found - refs
        refs |= newly_found

    return {
        "openapi": full_schema["openapi"],
        "info": {**full_schema["info"], "title": "Memory Trace API", "version": "v1"},
        "paths": v1_paths,
        "components": {"schemas": {name: all_schemas[name] for name in sorted(refs) if name in all_schemas}},
    }


def main() -> int:
    corpus_dir = Path(tempfile.mkdtemp(prefix="memory-trace-openapi-export-"))
    cache_dir = Path(tempfile.mkdtemp(prefix="memory-trace-openapi-export-cache-"))
    try:
        generate(48, corpus_dir)
        os.environ["MEMORY_SEED_LENSE_CACHE_ROOT"] = str(cache_dir)
        app = create_app(corpus_dir, rebuild_cache=True)
        schema = filtered_v1_schema(app.openapi())
        OUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {OUT_PATH} ({len(schema['paths'])} paths, {len(schema['components']['schemas'])} schemas)")
        return 0
    finally:
        shutil.rmtree(corpus_dir, ignore_errors=True)
        shutil.rmtree(cache_dir, ignore_errors=True)
        os.environ.pop("MEMORY_SEED_LENSE_CACHE_ROOT", None)


if __name__ == "__main__":
    raise SystemExit(main())
