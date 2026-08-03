"""Run one agent-capture trial: copy a fixture template, launch a headless session inside it.

The run directory is the readout. Whatever the session recorded lands in the run's own
`.memory-seed/sessions/` (nearest-runtime discovery, launched with cwd = run dir), and the
transcript is preserved alongside it. Nothing is written to the parent repo.

Usage:
  python experiments/agent-capture/run.py --level L0 --task T1 [--model MODEL] [--dry-run]
                                          [--timeout 900] [--extra-arg FLAG ...]

Notes:
- `--dangerously-skip-permissions` is a harness constant: headless runs cannot answer permission
  prompts. It is identical across all arms, so it differences out; PREREGISTRATION.md records it.
- `--extra-arg` exists for smoke-probe debugging (e.g. MCP trust flags) and any flag used must be
  promoted into the manifest-recorded constants before real arms run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
RUNS = HERE / "runs"
TASKS = HERE / "tasks"

LEVELS = ("L0", "L1", "L2", "L3")


def load_task(task_id: str) -> dict:
    manifest = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"unknown task {task_id!r}; known: {[t['id'] for t in manifest['tasks']]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", required=True, choices=LEVELS)
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent", default="claude")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--extra-arg", action="append", default=[])
    args = parser.parse_args()

    task = load_task(args.task)
    brief = (TASKS / task["brief"]).read_text(encoding="utf-8")

    template = TEMPLATES / f"{args.agent}-{args.level}"
    if not template.is_dir():
        raise SystemExit(f"template missing: {template} - run generate_fixtures.py first")

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{args.agent}-{args.level}-{args.task}-{stamp}"
    run_dir = RUNS / run_id
    RUNS.mkdir(exist_ok=True)
    shutil.copytree(template, run_dir)

    command = [
        "claude",
        "-p",
        brief,
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        *(["--model", args.model] if args.model else []),
        *args.extra_arg,
    ]

    manifest: dict = {
        "run_id": run_id,
        "level": args.level,
        "task": args.task,
        "agent": args.agent,
        "model": args.model,
        "template": str(template.relative_to(HERE)),
        "command": command[:2] + ["<brief elided>"] + command[3:],
        "started_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    if args.dry_run:
        manifest["dry_run"] = True
        print(json.dumps(manifest, indent=2))
        shutil.rmtree(
            run_dir,
            onerror=lambda func, target, _exc: (os.chmod(target, stat.S_IWRITE), func(target)),
        )
        return 0

    try:
        completed = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=args.timeout,
            shell=False,
        )
        manifest["exit_code"] = completed.returncode
        (run_dir / "transcript.json").write_text(completed.stdout, encoding="utf-8")
        if completed.stderr:
            (run_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        manifest["exit_code"] = None
        manifest["timed_out"] = True
        (run_dir / "transcript.json").write_text(exc.stdout or "", encoding="utf-8")
        if exc.stderr:
            (run_dir / "stderr.log").write_text(exc.stderr, encoding="utf-8")
    finally:
        manifest["finished_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        (run_dir / "RUN_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps({k: manifest.get(k) for k in ("run_id", "exit_code", "timed_out")}, indent=2))
    print(f"readout: {run_dir / '.memory-seed' / 'sessions'}")
    return 0 if manifest.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
