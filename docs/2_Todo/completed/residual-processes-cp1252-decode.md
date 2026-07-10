> Status: RESOLVED 2026-07-10. The cp1252 decode risk was fixed the same day by background
> task `task_56a17f30` (strict UTF-8 + UnicodeDecodeError handling in `_iter_windows_processes`,
> `_iter_posix_processes`, `_terminate_windows_process`, plus forced UTF-8 console output),
> merged to main in `c6abdfe` and released in 2.17.0. Kept as the durable record.

# Residual: cp1252 subprocess-decode risk in `processes.py`

**Source:** same-class latent bug found while fixing the git-helper encoding bug (session entry `mse_azn6bejpd9xpmh3f`, merge commit `c522379`, 2026-07-10). Out of scope for the `session fuse` fix.
**Severity:** medium on Windows. Also spawned as a background task chip (`task_56a17f30`); this file is the durable inbox record.

## Problem

Three `subprocess.run(..., text=True)` calls in `memory_seed/processes.py` decode OS command output **without an explicit `encoding=`**, so on Windows they use the cp1252 locale default and can crash or mojibake on non-ASCII output — the same defect just fixed in `memory_seed/core.py`'s git helpers.

| Site | Function | Command |
|---|---|---|
| `processes.py:196` | `_iter_windows_processes` | PowerShell (JSON output) |
| `processes.py:228` | `_iter_posix_processes` | `ps -eo pid=,comm=,args=` |
| `processes.py:387` | `_terminate_windows_process` | `taskkill` |

`processes.py:196` is the sharpest: it parses PowerShell **JSON** whose fields (process name, command line) are used for matching in `memory-seed processes` / `memory-seed shutdown`. A wrong decode there could corrupt the match and cause shutdown to miss — or mis-target — a process.

## Proposed fix

Apply the convention the git helpers now use:

- Add `encoding="utf-8"` to each `subprocess.run` call.
- Catch `UnicodeDecodeError` alongside the existing `OSError` / `TimeoutExpired` handling, degrading to the same "unavailable/empty" result rather than crashing (mirrors `_git_text` / `_git_show_text` / `find_trailer_commits` in `core.py`).
- Add a focused regression test if practical (non-ASCII process/command name round-trip through `_iter_windows_processes`).

## Workflow note

Do this on a task branch and integrate with `git merge --no-ff` per the repo's branch-history workflow. Validate with `python -m unittest discover -s tests`.

## References

- `memory_seed/processes.py:196,228,387`.
- Fix precedent: `memory_seed/core.py` git helpers; session entry `mse_azn6bejpd9xpmh3f`.
