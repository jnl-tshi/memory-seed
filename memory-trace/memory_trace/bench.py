"""Repeatable performance harness for the Memory Trace projection pipeline.

Times each stage of the cache/enrichment pipeline separately and counts the
git subprocesses each stage spawns, so a regression in either shows up as a
number, not a feeling. Run against any corpus:

    python -m memory_trace.bench --cwd .            # stage table
    python -m memory_trace.bench --cwd . --json out.json
    python -m memory_trace.bench --cwd . --skip-rebuild --skip-http

The subprocess counts (unlike wall times) are deterministic for a given
corpus, which is what the regression tests assert on: "no git work per
historical item" means the count must stay flat as history grows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from . import service as service_module
from .graph_projection import project_trace_graph
from .service import TraceCache, TraceService, create_app


class SubprocessCounter:
    """Counts subprocess.run invocations globally while active.

    Patches the shared subprocess module attribute so every caller (service.py
    and memory_seed core alike) is counted; the original is always restored.
    """

    def __init__(self) -> None:
        self.count = 0
        self.commands: list[str] = []

    @contextmanager
    def active(self):
        original = subprocess.run

        def counting_run(*args: Any, **kwargs: Any):
            self.count += 1
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, (list, tuple)):
                self.commands.append(" ".join(str(part) for part in argv[:6]))
            return original(*args, **kwargs)

        subprocess.run = counting_run  # type: ignore[assignment]
        try:
            yield self
        finally:
            subprocess.run = original  # type: ignore[assignment]


def _timed(fn: Callable[[], Any]) -> tuple[float, int, Any]:
    """Run ``fn`` returning (seconds, git_subprocess_count, result)."""
    counter = SubprocessCounter()
    with counter.active():
        started = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - started
    return elapsed, counter.count, result


def run_benchmark(
    cwd: str | Path = ".",
    *,
    include_rebuild: bool = True,
    include_http: bool = True,
    include_file_index: bool = True,
) -> dict[str, Any]:
    """Execute every stage against ``cwd`` and return the report dict.

    Stage semantics:
    - cold stages (entry_commit_map, trailer_merges, file_entry_index,
      full_rebuild) measure the from-scratch cost with in-process memos
      cleared, i.e. what a fresh server launch pays;
    - warm stages (freshness_check, trail/graph projections, http_warm)
      measure steady-state request cost against an already-built cache.
    """
    from memory_seed.semantic_cache import extract_memory_chunks

    cache = TraceCache(cwd)
    svc = TraceService(cache)
    root = cache.runtime.workspace_root
    report: dict[str, Any] = {"cwd": str(root), "stages": {}}

    def record(name: str, seconds: float, subprocesses: int, detail: str = "") -> None:
        report["stages"][name] = {
            "seconds": round(seconds, 4),
            "git_subprocesses": subprocesses,
            "detail": detail,
        }

    # Ensure a current cache exists so warm stages measure the steady state.
    seconds, procs, _ = _timed(cache.ensure_current)
    record("initial_ensure_current", seconds, procs, "cold if no cache existed")

    # Warm freshness check: force a real check (bypass the TTL memo).
    cache._fresh_until = 0.0
    seconds, procs, _ = _timed(cache.ensure_current)
    record("freshness_check_warm", seconds, procs, "TTL bypassed; no rebuild expected")

    seconds, procs, entries = _timed(lambda: extract_memory_chunks(cwd, granularity="entry"))
    record("parse_entries", seconds, procs, f"{len(entries)} entries")
    seconds, procs, sections = _timed(lambda: extract_memory_chunks(cwd, granularity="section"))
    record("parse_sections", seconds, procs, f"{len(sections)} sections")

    seconds, procs, commit_map = _timed(lambda: service_module._entry_commit_map(root))
    record("entry_commit_map", seconds, procs, f"{len(commit_map)} attributed entries")

    seconds, procs, main_shas = _timed(lambda: service_module._first_parent_main_shas(root))
    record("first_parent_shas", seconds, procs, f"{len(main_shas)} trunk commits")

    # Cold trailer walk: snapshot and clear the process-wide fork-point memo so
    # this measures what a fresh process pays, then restore it.
    memo_snapshot = dict(service_module._FORK_POINT_MEMO)
    service_module._FORK_POINT_MEMO.clear()
    try:
        seconds, procs, merges = _timed(lambda: service_module._first_parent_trailer_commits(root))
        record("trailer_merges_cold", seconds, procs, f"{len(merges)} merge events")
    finally:
        service_module._FORK_POINT_MEMO.update(memo_snapshot)

    if include_file_index:
        seconds, procs, index = _timed(lambda: service_module._file_entry_index(root, commit_map))
        record("file_entry_index_cold", seconds, procs, f"{len(index)} paths")

    trail_edges = ("branch", "supersedes", "evolves", "related")
    seconds, procs, trail = _timed(lambda: svc.graph(edge_types=trail_edges, limit=1000))
    record("trail_projection_warm", seconds, procs, f"{len(trail.get('nodes', []))} nodes")

    graph_edges = ("related", "supersedes", "evolves", "topic")
    seconds, procs, graph = _timed(
        lambda: project_trace_graph(svc.graph(edge_types=graph_edges, limit=60))
    )
    record("graph_projection_warm", seconds, procs, f"{len(graph.get('nodes', []))} nodes")

    if include_rebuild:
        memo_snapshot = dict(service_module._FORK_POINT_MEMO)
        service_module._FORK_POINT_MEMO.clear()
        try:
            seconds, procs, _ = _timed(cache.rebuild)
            record("full_rebuild_cold", seconds, procs, "forced, fork memo cleared")
        finally:
            service_module._FORK_POINT_MEMO.update(memo_snapshot)

    if include_http:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            report["stages"]["http"] = {"seconds": None, "detail": "fastapi test client unavailable"}
        else:
            app = create_app(cwd)
            client = TestClient(app)
            for name, url in (
                ("http_runtime", "/api/v1/runtime"),
                ("http_facets", "/api/v1/facets"),
                ("http_trail", "/api/v1/trail?limit=1000"),
                ("http_graph", "/api/v1/graph/projection?limit=60&edge_types=related,supersedes,evolves,topic"),
            ):
                seconds, procs, response = _timed(lambda url=url: client.get(url))
                record(name, seconds, procs, f"status {response.status_code}")

    return report


def format_report(report: dict[str, Any]) -> str:
    lines = [f"Memory Trace benchmark - {report['cwd']}", ""]
    header = f"{'stage':<28}{'seconds':>10}{'git procs':>11}  detail"
    lines.append(header)
    lines.append("-" * len(header))
    for name, stage in report["stages"].items():
        seconds = stage.get("seconds")
        seconds_text = f"{seconds:.3f}" if isinstance(seconds, (int, float)) else "-"
        procs = stage.get("git_subprocesses", "-")
        lines.append(f"{name:<28}{seconds_text:>10}{procs:>11}  {stage.get('detail', '')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark the Memory Trace projection pipeline")
    parser.add_argument("--cwd", default=".", help="project directory (default: .)")
    parser.add_argument("--json", dest="json_path", default=None, help="also write the report as JSON")
    parser.add_argument("--skip-rebuild", action="store_true", help="skip the forced full rebuild stage")
    parser.add_argument("--skip-http", action="store_true", help="skip the HTTP request stages")
    parser.add_argument("--skip-file-index", action="store_true", help="skip the cold file-entry-index stage")
    args = parser.parse_args(argv)

    report = run_benchmark(
        args.cwd,
        include_rebuild=not args.skip_rebuild,
        include_http=not args.skip_http,
        include_file_index=not args.skip_file_index,
    )
    print(format_report(report))
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON written to {args.json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
