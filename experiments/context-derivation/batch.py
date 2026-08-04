"""Deterministically schedule the frozen 288-cell context experiment."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
TASKS = HERE / "generated" / "live-tasks.json"
sys.path.insert(0, str(HERE))
from contracts import AGENTS, ARMS, MAX_AGENT_CONCURRENCY, MAX_TOTAL_CONCURRENCY, REPETITIONS, SCHEDULE_SEED, TASK_COUNT, live_execution_approved  # noqa: E402
from run import codex_interactive_ready  # noqa: E402


def task_ids(path: Path = TASKS) -> list[str]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8")); items = data.get("tasks", data)
        return [x.get("task_id", x.get("id")) for x in items]
    return [f"CTX-{i:02d}" for i in range(1, TASK_COUNT + 1)]


def build_schedule(tasks: Iterable[str] | None = None, *, seed: int = SCHEDULE_SEED) -> list[dict[str, Any]]:
    """Rep-major shuffled schedule.  Every frozen cell occurs exactly once."""
    ids = list(tasks or task_ids())
    if len(ids) != TASK_COUNT: raise ValueError(f"frozen matrix requires {TASK_COUNT} tasks, got {len(ids)}")
    cells: list[dict[str, Any]] = []
    for repetition in range(1, REPETITIONS + 1):
        chunk = [{"task_id": task_id, "arm": arm, "agent": agent, "repetition": repetition}
                 for task_id in ids for arm in ARMS for agent in AGENTS]
        random.Random(seed + repetition).shuffle(chunk)
        cells.extend(chunk)
    return cells


def cell_key(cell: dict[str, Any]) -> tuple[str, str, str, int]:
    return (cell["task_id"], cell["arm"], cell["agent"], int(cell["repetition"]))


def completed_cells(runs: Path = RUNS) -> Counter[tuple[str, str, str, int]]:
    result: Counter[tuple[str, str, str, int]] = Counter()
    if not runs.exists(): return result
    for path in runs.glob("*/RUN_MANIFEST.json"):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: continue
        # A top-up replaces only recorded harness/provider/timeout failures.  A substantive
        # non-zero response remains a completed observation.
        if value.get("failure_classification") in {"timeout", "provider_throttled", "provider_outage", "harness_error"}: continue
        key = (value.get("task_id"), value.get("arm"), value.get("agent"), value.get("repetition"))
        result[key] += 1
    return result


def top_up(schedule: list[dict[str, Any]], counts: Counter[tuple[str, str, str, int]]) -> list[dict[str, Any]]:
    remaining = Counter(counts); output = []
    for cell in schedule:
        key = cell_key(cell)
        if remaining[key]: remaining[key] -= 1
        else: output.append(cell)
    return output


def _parse_result(done: subprocess.CompletedProcess[str], cell: dict[str, Any]) -> dict[str, Any]:
    result = dict(cell); result["returncode"] = done.returncode
    for line in reversed(done.stdout.splitlines()):
        try:
            payload = json.loads(line)
            if isinstance(payload, dict): result.update(payload); break
        except json.JSONDecodeError: pass
    result["stdout_tail"] = done.stdout[-500:]; result["stderr_tail"] = done.stderr[-500:]
    return result


def run_cell(cell: dict[str, Any], *, model_by_agent: dict[str, str], cli_versions: dict[str, str], effort_by_agent: dict[str, str | None], timeout: int, tasks_path: Path = TASKS) -> dict[str, Any]:
    command = [sys.executable, str(HERE / "run.py"), "--owner-approved", "--task", cell["task_id"], "--arm", cell["arm"], "--agent", cell["agent"], "--repetition", str(cell["repetition"]), "--model", model_by_agent[cell["agent"]], "--cli-version", cli_versions[cell["agent"]], "--timeout", str(timeout), "--tasks", str(tasks_path)]
    if effort_by_agent.get(cell["agent"]):
        command.extend(["--effort", str(effort_by_agent[cell["agent"]])])
    done = subprocess.run(command, cwd=HERE.parents[1], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return _parse_result(done, cell)


def _run_queue(cells: list[dict[str, Any]], *, agent: str, jobs: int, model_by_agent: dict[str, str], cli_versions: dict[str, str], effort_by_agent: dict[str, str | None], timeout: int, backoff: float, tasks_path: Path = TASKS, runner=run_cell) -> list[dict[str, Any]]:
    """Run ordered waves, decreasing only this agent's future concurrency after a 429.

    We intentionally do not pre-submit the entire queue: doing so makes a later
    concurrency reduction fictional.  Each wave starts in list order; results are
    placed back at their original positions, independent of completion order.
    """
    results: list[dict[str, Any] | None] = [None] * len(cells)
    concurrency, offset = jobs, 0
    while offset < len(cells):
        wave = cells[offset : offset + concurrency]
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(runner, cell, model_by_agent=model_by_agent, cli_versions=cli_versions, effort_by_agent=effort_by_agent, timeout=timeout, tasks_path=tasks_path) for cell in wave]
            wave_results = [future.result() for future in futures]
        throttled = False
        for index, (cell, result) in enumerate(zip(wave, wave_results)):
            result["agent"] = agent; result["queue_concurrency"] = concurrency
            if result.get("failure_classification") == "provider_throttled":
                throttled = True
                time.sleep(backoff)
                # The exact same cell is retried; unscheduled cells never move.
                result = runner(cell, model_by_agent=model_by_agent, cli_versions=cli_versions, effort_by_agent=effort_by_agent, timeout=timeout, tasks_path=tasks_path)
                result["agent"] = agent; result["queue_concurrency"] = concurrency
                result["throttle_retry"] = True
            results[offset + index] = result
        if throttled:
            concurrency = max(1, concurrency - 1)
        offset += len(wave)
    return [result for result in results if result is not None]


def run_parallel(schedule: list[dict[str, Any]], *, jobs_per_agent: int = MAX_AGENT_CONCURRENCY, model_by_agent: dict[str, str], cli_versions: dict[str, str], effort_by_agent: dict[str, str | None], timeout: int = 900, throttle_backoff: float = 30.0, tasks_path: Path = TASKS, runner=run_cell) -> list[dict[str, Any]]:
    if jobs_per_agent > MAX_AGENT_CONCURRENCY: raise ValueError("per-agent concurrency exceeds frozen limit")
    if jobs_per_agent * len(AGENTS) > MAX_TOTAL_CONCURRENCY: raise ValueError("total concurrency exceeds frozen limit")
    groups = {agent: [c for c in schedule if c["agent"] == agent] for agent in AGENTS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(AGENTS)) as pools:
        futures = [pools.submit(_run_queue, groups[a], agent=a, jobs=jobs_per_agent, model_by_agent=model_by_agent, cli_versions=cli_versions, effort_by_agent=effort_by_agent, timeout=timeout, backoff=throttle_backoff, tasks_path=tasks_path, runner=runner) for a in AGENTS]
        # Pool completion is intentionally irrelevant to reporting order.
        by_key = {cell_key(row): row for future in futures for row in future.result()}
        return [by_key[cell_key(cell)] for cell in schedule]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--claude-model", required=True); parser.add_argument("--codex-model", required=True)
    parser.add_argument("--claude-cli-version", required=True); parser.add_argument("--codex-cli-version", required=True)
    parser.add_argument("--codex-effort", required=True, choices=("low", "medium", "high", "xhigh", "max", "ultra"))
    parser.add_argument("--jobs-per-agent", type=int, default=MAX_AGENT_CONCURRENCY); parser.add_argument("--timeout", type=int, default=900); parser.add_argument("--top-up", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--owner-approved", action="store_true", help="required before paid/scored execution"); parser.add_argument("--throttle-backoff", type=float, default=30.0); parser.add_argument("--tasks", default=str(TASKS))
    args = parser.parse_args(argv); tasks_path = Path(args.tasks); schedule = build_schedule(task_ids(tasks_path))
    if args.top_up: schedule = top_up(schedule, completed_cells())
    if args.dry_run:
        print(json.dumps(schedule, indent=2)); return 0
    if not args.owner_approved:
        parser.error("--owner-approved is required for non-dry-run execution")
    if not live_execution_approved(HERE):
        parser.error("gold/preregistration approval, a frozen candidate, and pinned live matrix are required")
    if not tasks_path.is_file():
        parser.error(f"materialized live tasks are missing: {tasks_path}")
    if not codex_interactive_ready():
        parser.error(
            "Codex interactive arms require an owner-approved harness privilege broker; "
            "the batch is blocked before any provider call"
        )
    RUNS.mkdir(exist_ok=True)
    results = run_parallel(schedule, jobs_per_agent=args.jobs_per_agent, model_by_agent={"claude": args.claude_model, "codex": args.codex_model}, cli_versions={"claude": args.claude_cli_version, "codex": args.codex_cli_version}, effort_by_agent={"claude": None, "codex": args.codex_effort}, timeout=args.timeout, throttle_backoff=args.throttle_backoff, tasks_path=tasks_path)
    (RUNS / "batch-results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
