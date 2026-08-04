"""Run the scored agent-capture matrix: every (level x task) cell, N times, round-robin.

Order matters more than it looks. Cells are run **rep-major** - one repetition of every cell, then
the next repetition - and shuffled within each rep with a seed derived from the rep index. Two
reasons:

  - A budget-limited run stops *balanced*. Level-major order (all of L0, then all of L1, ...) leaves
    L3 empty if the budget runs out, and L3 is the kill-condition arm - the one whose absence would
    make the whole matrix unreadable.
  - Shuffling inside a rep keeps time-correlated drift (rate limiting, model routing, machine load)
    from lining up with level.

Runs are dispatched through run.py as subprocesses, so each trial's manifest, isolation fingerprint
and transcript handling are identical to a hand-run trial - this file only decides what to run and
in what order.

Usage:
  python experiments/agent-capture/batch.py --agent claude --reps 5 [--jobs 3] [--dry-run]
  python experiments/agent-capture/batch.py --agent claude --reps 5 --levels L0,L3 --tasks T1
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RUNS = HERE / "runs"
TASKS = HERE / "tasks"

LEVELS = ("L0", "L1", "L2", "L3")

_print_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{stamp}] {message}", flush=True)


def build_schedule(levels: list[str], tasks: list[str], reps: int) -> list[tuple[int, str, str]]:
    """Rep-major, shuffled within each rep. Deterministic given (levels, tasks, reps)."""
    schedule: list[tuple[int, str, str]] = []
    for rep in range(1, reps + 1):
        cells = [(rep, level, task) for level in levels for task in tasks]
        random.Random(rep).shuffle(cells)
        schedule.extend(cells)
    return schedule


def run_one(level: str, task: str, agent: str, timeout: int, model: str | None) -> dict:
    command = [
        sys.executable,
        str(HERE / "run.py"),
        "--agent",
        agent,
        "--level",
        level,
        "--task",
        task,
        "--timeout",
        str(timeout),
        *(["--model", model] if model else []),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = {"level": level, "task": task, "returncode": completed.returncode}
    # run.py prints a small JSON object first; recover run_id and isolation from it.
    try:
        start = completed.stdout.index("{")
        end = completed.stdout.index("}", start) + 1
        result.update(json.loads(completed.stdout[start:end]))
    except (ValueError, json.JSONDecodeError):
        result["stdout_tail"] = completed.stdout[-400:]
        result["stderr_tail"] = completed.stderr[-400:]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default="claude", choices=("claude", "codex"))
    parser.add_argument("--reps", type=int, required=True)
    parser.add_argument("--levels", default=",".join(LEVELS))
    parser.add_argument("--tasks", default=None, help="default: every task in tasks.json")
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--model", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    levels = [item.strip() for item in args.levels.split(",") if item.strip()]
    unknown = [item for item in levels if item not in LEVELS]
    if unknown:
        parser.error(f"unknown levels: {unknown}")

    manifest = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
    tasks = (
        [item.strip() for item in args.tasks.split(",") if item.strip()]
        if args.tasks
        else [task["id"] for task in manifest["tasks"]]
    )

    schedule = build_schedule(levels, tasks, args.reps)
    log(f"{len(schedule)} run(s): {len(levels)} level(s) x {len(tasks)} task(s) x {args.reps} rep(s)")

    if args.dry_run:
        for index, (rep, level, task) in enumerate(schedule, 1):
            print(f"{index:3}. rep{rep} {level} {task}")
        return 0

    RUNS.mkdir(exist_ok=True)
    results: list[dict] = []
    completed_count = 0

    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {
                pool.submit(run_one, level, task, args.agent, args.timeout, args.model): (
                    rep,
                    level,
                    task,
                )
                for rep, level, task in schedule
            }
            for future in as_completed(futures):
                rep, level, task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # keep the batch alive; one bad trial is not fatal
                    result = {"level": level, "task": task, "error": repr(exc)}
                result["rep"] = rep
                results.append(result)
                completed_count += 1
                flag = "" if result.get("parent_isolated", True) else "  !! PARENT TOUCHED"
                log(
                    f"{completed_count}/{len(schedule)} rep{rep} {level} {task} "
                    f"exit={result.get('exit_code', result.get('returncode'))}{flag}"
                )
    except KeyboardInterrupt:
        log("interrupted - keeping completed runs; rerun with the same arguments to top up")

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (RUNS / f"batch-{args.agent}-{stamp}.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    breached = [r for r in results if r.get("parent_isolated") is False]
    log(f"done: {len(results)} run(s); {len(breached)} with a parent-store change")
    log("next: python experiments/agent-capture/collect.py")
    return 1 if breached else 0


if __name__ == "__main__":
    raise SystemExit(main())
