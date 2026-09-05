from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


STATE_PATH = Path(".memory-seed/.project-process-health-state.json")
INTERVAL_SECONDS = 60 * 60
SAMPLE_SECONDS = 2
MINIMUM_AGE_SECONDS = 10 * 60
MINIMUM_CPU_SECONDS = 0.5


def _load_last_check() -> float:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return float(data.get("last_check_epoch", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 0


def _save_last_check(now: float) -> None:
    payload = {
        "last_check_epoch": now,
        "last_check_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
    }
    try:
        STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _windows_sample() -> list[dict[str, object]]:
    script = rf"""
$first = Get-Process -Name python,python3 -ErrorAction SilentlyContinue |
  Select-Object Id,CPU,StartTime,Path
Start-Sleep -Seconds {SAMPLE_SECONDS}
$second = Get-Process -Name python,python3 -ErrorAction SilentlyContinue |
  Select-Object Id,CPU,StartTime,Path
$now = Get-Date
$rows = foreach ($current in $second) {{
  $before = $first | Where-Object Id -eq $current.Id
  if ($null -ne $before) {{
    $details = Get-CimInstance Win32_Process -Filter "ProcessId=$($current.Id)" -ErrorAction SilentlyContinue
    [pscustomobject]@{{
      pid = $current.Id
      cpu_delta = [math]::Round(($current.CPU - $before.CPU), 3)
      age_seconds = [math]::Round(($now - $current.StartTime).TotalSeconds)
      executable = $current.Path
      command_line = $details.CommandLine
    }}
  }}
}}
@($rows) | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    return payload if isinstance(payload, list) else [payload]


def find_suspicious_processes() -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    try:
        rows = _windows_sample()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []
    return [
        row
        for row in rows
        if float(row.get("cpu_delta") or 0) >= MINIMUM_CPU_SECONDS
        and float(row.get("age_seconds") or 0) >= MINIMUM_AGE_SECONDS
        and int(row.get("pid") or 0) != os.getpid()
    ]


def _hook_output(agent: str, message: str) -> dict[str, object]:
    if agent == "codex":
        return {"hookSpecificOutput": {"additionalContext": message}}
    return {"systemMessage": message}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="codex")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    now = time.time()
    if not args.force and now - _load_last_check() < INTERVAL_SECONDS:
        return 0

    suspicious = find_suspicious_processes()
    _save_last_check(now)
    if args.json:
        print(json.dumps({"checked": True, "suspicious": suspicious}, indent=2))
        return 0
    if not suspicious:
        return 0

    summary = ", ".join(
        f"PID {row['pid']} used {row['cpu_delta']} CPU seconds during the sample"
        for row in suspicious
    )
    message = (
        "Project process-health check found possible stale Python subprocesses: "
        f"{summary}. Load the project_process_health skill, remeasure, and obtain live approval "
        "before stopping anything."
    )
    print(json.dumps(_hook_output(args.agent, message)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
