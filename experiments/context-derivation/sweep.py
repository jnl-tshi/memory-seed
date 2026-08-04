"""Parallel, resumable offline strategy sweep."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

from contracts import TASK_SCHEMA, canonical_json, load_json, require_schema
from strategies import normalize_strategy, resolve_strategy, stable_result, strategy_fingerprint


SHARD_SCHEMA = "context-sweep-shard.v1"


def shard_name(task: Mapping[str, Any], strategy: Mapping[str, Any]) -> str:
    digest = strategy_fingerprint(strategy).split(":", 1)[1]
    return f"{task['task_id']}--{digest}.json"


def _valid_resume(path: Path, task: Mapping[str, Any], strategy: Mapping[str, Any]) -> bool:
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
        and value.get("deterministic") is True
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


def _resolve_job(job: tuple[dict[str, Any], dict[str, Any], str]) -> str:
    task, strategy, root = job
    first = resolve_strategy(task, strategy, root)
    second = resolve_strategy(task, strategy, root)
    deterministic = stable_result(first) == stable_result(second)
    payload = {
        "schema": SHARD_SCHEMA,
        "task_id": task["task_id"],
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
    return fixture.resolve() if fixture.is_absolute() else (Path(fixture_base) / fixture).resolve()


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
    pending, paths = [], []
    for task in sorted(normalized_tasks, key=lambda item: item["task_id"]):
        for strategy in sorted(normalized_strategies, key=strategy_fingerprint):
            path = output / shard_name(task, strategy)
            paths.append(path)
            if not (resume and _valid_resume(path, task, strategy)):
                pending.append((task, strategy, str(task_runtime(task, runtime)), path))
    cpu_default = max(1, (os.cpu_count() or 2) - 1)
    count = min(8, cpu_default, workers or cpu_default)
    jobs = [(task, strategy, root) for task, strategy, root, _ in pending]
    if count == 1:
        encoded = map(_resolve_job, jobs)
        for (_, _, _, path), raw in zip(pending, encoded):
            _write_unique(path, json.loads(raw))
    elif jobs:
        with ProcessPoolExecutor(max_workers=count) as executor:
            for (_, _, _, path), raw in zip(pending, executor.map(_resolve_job, jobs)):
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
