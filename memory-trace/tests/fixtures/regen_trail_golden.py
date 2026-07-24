"""Regenerate trail-golden-48.json without a browser (cheap-tooling P8).

The Phase 0 procedure required serving the synthetic corpus and reading
``window.memoryTraceDebug.trailModel(graph)`` in a live browser - so the
fixture rotted whenever the model changed (it had been stale since the
lane-order change). This driver replaces that: it generates the deterministic
corpus, computes the SAME graph payload the app requests (trail edge types,
limit 1000), and runs the real app.js through the node vm harness
(regen_trail_golden.mjs) to capture the model.

    PYTHONPATH=".;memory-trace" python memory-trace/tests/fixtures/regen_trail_golden.py

Requires node on PATH. Deterministic: same corpus (count=48, seed=20260711),
same app.js -> byte-identical fixture.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent
STATIC = FIXTURES.parent.parent / "memory_trace" / "static"
GOLDEN = FIXTURES / "trail-golden-48.json"
COUNT, SEED = 48, 20260711
# Mirrors app.js loadGraph for the Trail: TRAIL_EDGE_TYPES + full-corpus limit.
TRAIL_EDGE_TYPES = ("branch", "replaces", "evolves", "related")


def main() -> int:
    from memory_trace.service import TraceCache, TraceService

    # mkdtemp + ignore_errors cleanup, not TemporaryDirectory: on Windows the
    # sqlite cache can still hold its file handle at teardown.
    corpus_dir = tempfile.mkdtemp(prefix="mseed-golden-corpus-")
    cache_dir = tempfile.mkdtemp(prefix="mseed-golden-cache-")
    try:
        subprocess.run(
            [sys.executable, str(FIXTURES / "generate_synthetic.py"), str(COUNT), corpus_dir, str(SEED)],
            check=True,
        )
        os.environ["MEMORY_SEED_LENSE_CACHE_ROOT"] = cache_dir
        service = TraceService(TraceCache(corpus_dir))
        graph = service.graph(granularity="entry", edge_types=TRAIL_EDGE_TYPES, limit=1000)

        graph_path = Path(cache_dir) / "graph.json"
        model_path = Path(cache_dir) / "model.json"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        subprocess.run(
            ["node", str(FIXTURES / "regen_trail_golden.mjs"), str(STATIC / "app.js"), str(graph_path), str(model_path)],
            check=True,
        )
        model = json.loads(model_path.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(corpus_dir, ignore_errors=True)
        shutil.rmtree(cache_dir, ignore_errors=True)

    fixture = {
        "fixture": f"generate_synthetic.py count={COUNT} seed={SEED}",
        "captured_from": "vanilla app.js trailModel via regen_trail_golden.mjs (node vm harness)",
        "node_count": sum(1 for item in model["items"] if item["kind"] == "node"),
        "edge_count": len(graph["edges"]),
        "total": model["total"],
        "laneCount": model["laneCount"],
        "items": model["items"],
        "laneOf": model["laneOf"],
        "spans": model["spans"],
        "linkRows": model["linkRows"],
        "lifecycle": model["lifecycle"],
    }
    GOLDEN.write_bytes((json.dumps(fixture, indent=1) + "\n").encode("utf-8"))  # LF, not platform newline
    print(f"wrote {GOLDEN} ({fixture['node_count']} nodes, laneCount {fixture['laneCount']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
