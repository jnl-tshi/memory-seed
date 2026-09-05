---
tags:
  - memory-seed
  - skill
  - project-health
  - subprocesses
---

# Project Process Health

Use this project-only skill when a long-running local command stalls, the app becomes unexpectedly
slow, a task-packet export is interrupted, or the hourly hook reports a suspicious subprocess.

## Routine check

Run:

```text
python -X utf8 .memory-seed/hooks/project-process-health.py --force --json
```

The check samples Python processes for two seconds and reports only processes that are both old enough
to be plausible stragglers and actively consuming CPU. It is read-only. A clean result means the sample
found no matching process; it does not prove that every process on the machine is healthy.

## Before stopping anything

1. Re-run the forced check so the PID and CPU reading are current.
2. Distinguish an active test, worker, editor service, or user-started command from a stale project
   subprocess using its executable, start time, command line when available, and current task state.
3. Ask for live user approval naming the exact process group to stop.
4. Stop only the approved PIDs, then sample again and report what remains.

Never terminate from the hook. Never treat an empty command line as proof that a process is stale.

## Hourly hook

The project hook runs at session start, prompt submission, and turn end. A local state file throttles the
actual scan to once per hour. This is event-driven, so the check occurs on the first supported event after
the hour has elapsed rather than through a background scheduler.

This skill and hook belong only to the Memory Seed development repository. They have no seed twin and
must not be added to the reusable package inventory.
