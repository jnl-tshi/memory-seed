"""Parallel, resumable offline strategy sweep."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

from contracts import TASK_SCHEMA, canonical_json, fingerprint, load_json, require_schema
import strategies as strategies_module
from strategies import clear_resolution_caches, normalize_strategy, resolve_strategy, stable_result, strategy_fingerprint


SHARD_SCHEMA = "context-sweep-shard.v1"


def shard_name(task: Mapping[str, Any], strategy: Mapping[str, Any]) -> str:
    digest = strategy_fingerprint(strategy).split(":", 1)[1]
    return f"{task['task_id']}--{digest}.json"


def resolver_implementation_fingerprint() -> str:
    """Fingerprint the exact experiment and production resolver Python sources."""
    import memory_seed

    timeline_builder = strategies_module._timeline_builder()
    timeline_module = importlib.import_module(timeline_builder.__module__)
    groups = (
        ("experiment", Path(strategies_module.__file__).resolve().parent),
        ("memory_seed", Path(memory_seed.__file__).resolve().parent),
        ("memory_trace", Path(timeline_module.__file__).resolve().parent),
    )
    digest = hashlib.sha256()
    for label, root in groups:
        paths = (
            [root / "strategies.py", root / "contracts.py"]
            if label == "experiment"
            else sorted(root.rglob("*.py"))
        )
        for path in paths:
            if not path.is_file():
                continue
            relative = path.name if label == "experiment" else path.relative_to(root).as_posix()
            data = path.read_bytes()
            digest.update(f"{label}/{relative}\0{len(data)}\0".encode("utf-8"))
            digest.update(data)
    return "sha256:" + digest.hexdigest()


def _valid_resume(
    path: Path,
    task: Mapping[str, Any],
    strategy: Mapping[str, Any],
    runtime_fingerprint: str,
    resolver_fingerprint: str,
) -> bool:
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        value.get("schema") == SHARD_SCHEMA
        and value.get("task_id") == task.get("task_id")
        and value.get("strategy_fingerprint") == strategy_fingerprint(strategy)
        and value.get("task_fingerprint") == fingerprint(task)
        and value.get("runtime_fingerprint") == runtime_fingerprint
        and value.get("resolver_fingerprint") == resolver_fingerprint
        and value.get("deterministic") is True
        and value.get("repeat_fingerprint") == (value.get("result") or {}).get("fingerprint")
    )


def _write_unique(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the atomic sibling short enough for Windows worktree paths. The
    # destination already carries the task and strategy identity.
    fd, temporary = tempfile.mkstemp(prefix="shard-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(payload) + "\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _resolve_job(job: tuple[dict[str, Any], dict[str, Any], str, str, str]) -> str:
    task, strategy, root, corpus_fingerprint, resolver_fingerprint = job
    first = resolve_strategy(task, strategy, root)
    clear_resolution_caches()
    second = resolve_strategy(task, strategy, root)
    deterministic = stable_result(first) == stable_result(second)
    payload = {
        "schema": SHARD_SCHEMA,
        "task_id": task["task_id"],
        "task_fingerprint": fingerprint(task),
        "runtime_fingerprint": corpus_fingerprint,
        "resolver_fingerprint": resolver_fingerprint,
        "strategy": normalize_strategy(strategy),
        "strategy_fingerprint": strategy_fingerprint(strategy),
        "deterministic": deterministic,
        "result": first,
        "repeat_fingerprint": second["fingerprint"],
        "timings_ms": [first["elapsed_ms"], second["elapsed_ms"]],
    }
    return canonical_json(payload)


def task_runtime(task: Mapping[str, Any], fixture_base: str | Path) -> Path:
    """Resolve a task's fixture runtime without assuming one global corpus."""
    fixture = Path(str(task["fixture"]))
    runtime = fixture.resolve() if fixture.is_absolute() else (Path(fixture_base) / fixture).resolve()
    if not (runtime / ".memory-seed").is_dir():
        raise ValueError(f"fixture runtime is missing .memory-seed: {runtime}")
    return runtime


def runtime_fingerprint(runtime: Path, task: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    candidates = [path for path in (runtime / ".memory-seed").rglob("*") if path.is_file()]
    candidates.extend(path for path in (runtime / "CONSTITUTION.md", runtime / "docs" / "CONSTITUTION.md") if path.is_file())
    for hinted in (task.get("resolver_hints") or {}).get("paths", []):
        path = (runtime / str(hinted)).resolve()
        try:
            path.relative_to(runtime.resolve())
        except ValueError:
            raise ValueError(f"hinted path escapes fixture runtime: {hinted}")
        if path.is_file():
            candidates.append(path)
        elif path.is_dir():
            candidates.extend(item for item in path.rglob("*") if item.is_file())
    for path in sorted(set(candidates)):
        digest.update(path.relative_to(runtime).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def run_sweep(
    tasks: Sequence[Mapping[str, Any]],
    strategies: Sequence[Mapping[str, Any]],
    runtime: str | Path,
    output_dir: str | Path,
    *,
    workers: int | None = None,
    resume: bool = True,
) -> list[Path]:
    """Resolve every task/strategy cell and write exactly one JSON shard."""
    normalized_tasks: list[dict[str, Any]] = []
    for task in tasks:
        require_schema(task, TASK_SCHEMA)
        normalized_tasks.append(dict(task))
    normalized_strategies = [dict(strategy) for strategy in strategies]
    for strategy in normalized_strategies:
        normalize_strategy(strategy)
    # strategy_id is a label, not part of the normalized policy identity.
    # Collapse aliases before scheduling so no two workers can target one shard.
    normalized_strategies = list({
        strategy_fingerprint(strategy): strategy for strategy in normalized_strategies
    }.values())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    runtime_by_task = {task["task_id"]: task_runtime(task, runtime) for task in normalized_tasks}
    runtime_fingerprints = {
        task["task_id"]: runtime_fingerprint(runtime_by_task[task["task_id"]], task)
        for task in normalized_tasks
    }
    resolver_fingerprint = resolver_implementation_fingerprint()
    pending, paths = [], []
    for task in sorted(normalized_tasks, key=lambda item: item["task_id"]):
        for strategy in sorted(normalized_strategies, key=strategy_fingerprint):
            path = output / shard_name(task, strategy)
            paths.append(path)
            task_root = runtime_by_task[task["task_id"]]
            corpus_fingerprint = runtime_fingerprints[task["task_id"]]
            if not (
                resume
                and _valid_resume(
                    path, task, strategy, corpus_fingerprint, resolver_fingerprint
                )
            ):
                pending.append((
                    task, strategy, str(task_root), corpus_fingerprint,
                    resolver_fingerprint, path,
                ))
    cpu_default = max(1, (os.cpu_count() or 2) - 1)
    count = min(8, cpu_default, workers or cpu_default)
    jobs = [
        (task, strategy, root, corpus_fingerprint, implementation_fingerprint)
        for task, strategy, root, corpus_fingerprint, implementation_fingerprint, _ in pending
    ]
    if count == 1:
        encoded = map(_resolve_job, jobs)
        for (_, _, _, _, _, path), raw in zip(pending, encoded):
            _write_unique(path, json.loads(raw))
    elif jobs:
        with ProcessPoolExecutor(max_workers=count) as executor:
            for (_, _, _, _, _, path), raw in zip(pending, executor.map(_resolve_job, jobs)):
                _write_unique(path, json.loads(raw))
    return paths


def _rows(value: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value]
    if isinstance(value, Mapping) and isinstance(value.get(key), list):
        return [dict(item) for item in value[key]]
    raise ValueError(f"expected a list or object containing {key!r}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--strategies", required=True)
    parser.add_argument(
        "--fixture-base", "--runtime", dest="fixture_base", required=True,
        help="base directory for relative task.fixture paths",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)
    paths = run_sweep(
        _rows(load_json(args.tasks), "tasks"),
        _rows(load_json(args.strategies), "strategies"),
        args.fixture_base, args.output, workers=args.workers, resume=not args.no_resume,
    )
    print(canonical_json({"shards": len(paths), "output": str(Path(args.output).resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
