# Proposal: Installer-Agnostic Process Shutdown and Safe Upgrade Workflow for MemorySeed and MemoryTrace

Status: Active proposal
Priority: Medium-High
Source: Promoted from `docs/1_Inbox/memory_seed_trace_upgrade_shutdown_proposal.md` on 2026-07-07.
Scope: Add safe process listing/shutdown and package-manager-aware upgrade commands for `memory-seed` and `memory-trace`.
Non-goals: Do not intercept native package-manager commands; do not kill unrelated Python, shell, editor, browser, or MCP processes.
Dependencies: Decide whether to add `psutil` as a runtime dependency or implement a narrower stdlib/platform-specific process layer first.
Acceptance criteria: `memory-seed processes|shutdown|upgrade` and `memory-trace processes|shutdown|upgrade` expose dry-run, JSON, confirmation, and manager-specific upgrade behavior with tests for process matching and non-matches.

Implementation note: This is not a quick single-pass change in full. A useful MVP can ship process discovery, `--json`, and `shutdown --dry-run`; destructive shutdown and upgrade execution should remain behind conservative tests and confirmation behavior.

## Summary

`memory-seed` and `memory-trace` should provide a safe CLI-assisted workflow that detects active package-owned processes, asks the user for confirmation, shuts down only matching MemorySeed/MemoryTrace processes, and then supports a safe upgrade path.

The key design principle is:

> Process management must be installer-agnostic. Upgrade execution may be package-manager-specific.

This avoids coupling MemorySeed and MemoryTrace only to `uv`, while still solving the immediate Windows issue where `uv tool upgrade memory-seed` cannot remove a locked executable because `memory-seed-mcp.exe` is still running.

Example failure:

```text
error: Failed to upgrade memory-seed
  Caused by: failed to remove file `C:\Users\johnn\AppData\Roaming\uv\tools\memory-seed\Lib\site-packages\../../Scripts/memory-seed-mcp.exe`:
  The process cannot access the file because it is being used by another process. (os error 32)
```

The same class of issue can affect `memory-trace` if its MCP server, CLI process, or package-owned Python process is running during upgrade.

---

## Problem

When an MCP server is active, the package executable can remain locked by the operating system.

On Windows, this can prevent package managers from replacing or deleting the executable during an upgrade. The user then has to manually identify and kill the relevant process tree before retrying the upgrade.

Observed active process pattern:

```text
uvx.exe             uvx --from memory-seed memory-seed-mcp --stdio
uv.exe              uv tool uvx --from memory-seed memory-seed-mcp --stdio
memory-seed-mcp.exe memory-seed-mcp.exe --stdio
python.exe          ...uv\tools\memory-seed\Scripts\python.exe...
```

Equivalent process-locking can occur with other installation methods, including:

```text
pipx
pip
editable installs
local virtual environments
standalone executable wrappers
```

This is a poor user experience because:

1. The error is technically correct but not actionable enough.
2. Users may not know which process is safe to kill.
3. Killing all Python, `uv`, or `uvx` processes is risky.
4. MCP clients may spawn multiple server instances.
5. The same issue can recur whenever either package is upgraded while active.
6. A `uv`-only solution would unnecessarily limit the package workflow.

---

## Goals

The implementation should provide:

1. A CLI command to list active MemorySeed/MemoryTrace processes.
2. A CLI command to shut down only package-owned processes.
3. An interactive `y/N` prompt before shutdown.
4. A non-interactive `--yes` mode for scripts.
5. A `--dry-run` mode for safe inspection.
6. A package-manager-aware upgrade wrapper.
7. Manual fallback instructions for `uv`, `pipx`, and `pip`.
8. Equivalent behaviour for both `memory-seed` and `memory-trace`.

---

## Non-Goals

This proposal does **not** require intercepting native package-manager commands such as:

```bash
uv tool upgrade memory-seed
```

```bash
pipx upgrade memory-seed
```

```bash
python -m pip install --upgrade memory-seed
```

Those commands are owned by the package manager, not by MemorySeed or MemoryTrace.

Unless a package manager supports package-defined pre-upgrade hooks, `memory-seed` and `memory-trace` cannot automatically intercept direct upgrade calls.

Instead, the recommended upgrade path should become:

```bash
memory-seed upgrade
```

and:

```bash
memory-trace upgrade
```

Manual fallback commands should also be documented.

---

## Design Principle

The implementation should separate two responsibilities:

| Responsibility | Should be installer-agnostic? | Notes |
|---|---:|---|
| Process discovery | Yes | Should work regardless of install method. |
| Process shutdown | Yes | Should only match MemorySeed/MemoryTrace-owned processes. |
| Process dry-run | Yes | Should work without knowing the package manager. |
| Upgrade execution | No | Must use the correct package manager. |
| Upgrade recommendation | Partially | Can infer where possible, otherwise show options. |

---

## Proposed CLI Commands

## MemorySeed Commands

### List active processes

```bash
memory-seed processes
```

Lists active `memory-seed` processes.

Optional JSON mode:

```bash
memory-seed processes --json
```

---

### Shut down active processes

```bash
memory-seed shutdown
```

Interactively shuts down active `memory-seed` processes after asking for confirmation.

Non-interactive mode:

```bash
memory-seed shutdown --yes
```

Dry-run mode:

```bash
memory-seed shutdown --dry-run
```

JSON mode:

```bash
memory-seed shutdown --json
```

---

### Upgrade package

```bash
memory-seed upgrade
```

Detects active `memory-seed` processes, asks whether to shut them down, detects or requests the package manager, then runs the appropriate upgrade command.

Explicit package-manager modes:

```bash
memory-seed upgrade --manager uv
memory-seed upgrade --manager pipx
memory-seed upgrade --manager pip
```

Non-interactive mode:

```bash
memory-seed upgrade --yes --manager uv
```

Dry-run mode:

```bash
memory-seed upgrade --dry-run
```

---

## MemoryTrace Commands

### List active processes

```bash
memory-trace processes
```

Lists active `memory-trace` processes.

Optional JSON mode:

```bash
memory-trace processes --json
```

---

### Shut down active processes

```bash
memory-trace shutdown
```

Interactively shuts down active `memory-trace` processes after asking for confirmation.

Non-interactive mode:

```bash
memory-trace shutdown --yes
```

Dry-run mode:

```bash
memory-trace shutdown --dry-run
```

JSON mode:

```bash
memory-trace shutdown --json
```

---

### Upgrade package

```bash
memory-trace upgrade
```

Detects active `memory-trace` processes, asks whether to shut them down, detects or requests the package manager, then runs the appropriate upgrade command.

Explicit package-manager modes:

```bash
memory-trace upgrade --manager uv
memory-trace upgrade --manager pipx
memory-trace upgrade --manager pip
```

Non-interactive mode:

```bash
memory-trace upgrade --yes --manager uv
```

Dry-run mode:

```bash
memory-trace upgrade --dry-run
```

---

## Installer-Agnostic Shutdown Behaviour

The following commands should work regardless of how the package was installed:

```bash
memory-seed processes
memory-seed shutdown
memory-trace processes
memory-trace shutdown
```

They should work for packages installed through:

```text
uv
pipx
pip
poetry
hatch
editable local installs
virtual environments
standalone executable wrappers
```

The shutdown workflow should only require process inspection. It should not require knowing which package manager installed the package.

---

## Package-Manager-Aware Upgrade Behaviour

The `upgrade` command should be a convenience wrapper, not the only supported path.

Recommended upgrade commands:

| Installation method | Upgrade command |
|---|---|
| `uv tool install memory-seed` | `uv tool upgrade memory-seed` |
| `uv tool install memory-trace` | `uv tool upgrade memory-trace` |
| `pipx install memory-seed` | `pipx upgrade memory-seed` |
| `pipx install memory-trace` | `pipx upgrade memory-trace` |
| `pip install memory-seed` | `python -m pip install --upgrade memory-seed` |
| `pip install memory-trace` | `python -m pip install --upgrade memory-trace` |
| Editable/local dev install | Warn user; do not guess. |

---

## Package Manager Detection

The CLI should attempt package-manager detection, but should not overreach.

Suggested detection order:

```text
1. If executable path contains uv tool directories, prefer uv.
2. If executable path contains pipx venv directories, prefer pipx.
3. If running inside a virtual environment, suggest pip.
4. If installed editable or from local source, warn and ask for explicit manager.
5. If detection is ambiguous, show options instead of guessing.
```

Potential signals:

| Signal | Likely manager |
|---|---|
| Path contains `AppData\Roaming\uv\tools` | `uv` |
| Path contains `.local/share/uv/tools` | `uv` |
| Path contains `pipx\venvs` | `pipx` |
| Path contains `.local/pipx/venvs` | `pipx` |
| `sys.prefix != sys.base_prefix` | Virtual environment; likely `pip` or editable |
| Package metadata has editable source | Local editable install |

If detection fails, the command should output:

```text
Could not safely determine how memory-seed was installed.

Choose an upgrade command manually:

uv:
  uv tool upgrade memory-seed

pipx:
  pipx upgrade memory-seed

pip:
  python -m pip install --upgrade memory-seed
```

---

## Interactive UX

When active processes are found, the command should show a clear process table.

Example:

```text
Active memory-seed processes detected:

PID    Name                 Command
33088  memory-seed-mcp.exe  memory-seed-mcp --stdio
32176  uv.exe               uv tool uvx --from memory-seed memory-seed-mcp --stdio
33588  uvx.exe              uvx --from memory-seed memory-seed-mcp --stdio

These processes may block the upgrade.

Shut down these memory-seed processes now? [y/N]:
```

If the user enters `y`:

```text
Stopping memory-seed processes...
Stopped 3 processes.
```

If the user enters `n` or presses Enter:

```text
Upgrade cancelled because active memory-seed processes may block executable replacement.

Run:
memory-seed shutdown

Then retry:
memory-seed upgrade
```

The default should be `No`.

---

## Upgrade UX

If the manager is detected:

```text
Detected install manager: uv

Running:
uv tool upgrade memory-seed
```

If the manager is explicitly supplied:

```bash
memory-seed upgrade --manager pipx
```

Output:

```text
Using install manager: pipx

Running:
pipx upgrade memory-seed
```

If the manager cannot be detected:

```text
Could not safely determine how memory-seed was installed.

Choose one:

1. uv    -> uv tool upgrade memory-seed
2. pipx  -> pipx upgrade memory-seed
3. pip   -> python -m pip install --upgrade memory-seed
4. cancel

Upgrade with which manager? [1/2/3/4]:
```

For non-interactive environments, the command should require an explicit manager if detection fails:

```text
Could not safely determine install manager.
Re-run with one of:

memory-seed upgrade --yes --manager uv
memory-seed upgrade --yes --manager pipx
memory-seed upgrade --yes --manager pip
```

---

## Upgrade Flow

For:

```bash
memory-seed upgrade
```

The flow should be:

```text
1. Detect active memory-seed processes.
2. If processes are active:
   - Show process table.
   - Ask: "Shut down these memory-seed processes now? [y/N]"
3. If the user selects no:
   - Cancel upgrade.
   - Show manual recovery instructions.
4. If the user selects yes:
   - Terminate matching processes.
   - Verify they are gone.
5. Detect package manager.
6. If manager is detected:
   - Run matching upgrade command.
7. If manager is not detected:
   - Ask user to choose uv, pipx, pip, or cancel.
8. Return the package-manager command exit code.
```

For:

```bash
memory-trace upgrade
```

The flow should be identical, replacing `memory-seed` with `memory-trace`.

---

## Process Matching Rules

The shutdown command must be conservative. It should only target processes that clearly belong to the relevant package.

## MemorySeed Matching

Match processes where the executable path or command line contains one of:

```text
memory-seed
memory-seed-mcp
uvx --from memory-seed
uv tool uvx --from memory-seed
pipx run memory-seed
```

Examples that should match:

```text
memory-seed-mcp.exe --stdio
uvx --from memory-seed memory-seed-mcp --stdio
uv tool uvx --from memory-seed memory-seed-mcp --stdio
pipx run memory-seed memory-seed-mcp --stdio
C:\Users\johnn\AppData\Roaming\uv\tools\memory-seed\Scripts\python.exe ...
C:\Users\johnn\.local\pipx\venvs\memory-seed\Scripts\python.exe ...
```

## MemoryTrace Matching

Match processes where the executable path or command line contains one of:

```text
memory-trace
memory-trace-mcp
uvx --from memory-trace
uv tool uvx --from memory-trace
pipx run memory-trace
```

Examples that should match:

```text
memory-trace-mcp.exe --stdio
uvx --from memory-trace memory-trace-mcp --stdio
uv tool uvx --from memory-trace memory-trace-mcp --stdio
pipx run memory-trace memory-trace-mcp --stdio
C:\Users\johnn\AppData\Roaming\uv\tools\memory-trace\Scripts\python.exe ...
C:\Users\johnn\.local\pipx\venvs\memory-trace\Scripts\python.exe ...
```

---

## Safety Rules

The implementation must satisfy these rules:

1. Do not kill generic `python.exe`, `uv.exe`, `uvx.exe`, `pipx.exe`, or shell processes unless the command line or executable path clearly contains the target package name.
2. Do not kill unrelated MCP servers.
3. Do not kill Codex, Claude, VS Code, terminal, browser, or shell processes.
4. Default interactive answer must be `No`.
5. `--yes` must be required for non-interactive shutdown.
6. `--dry-run` must be available before destructive action.
7. Failed shutdown must stop the upgrade.
8. The process table should be displayed before shutdown unless `--json` is used.
9. The command should return a non-zero exit code if shutdown or upgrade fails.
10. The command should report remaining blocking PIDs if any process could not be stopped.
11. If install-manager detection is ambiguous, the upgrade command should ask rather than guess.
12. In non-interactive mode, `--manager` should be required when detection fails.

---

## Platform Behaviour

## Windows

Use Python process inspection where possible, preferably through `psutil`.

Shutdown order:

```text
1. Find matching package processes.
2. Attempt graceful termination.
3. Wait briefly.
4. Force kill remaining matching processes after confirmation.
5. Re-check process list.
6. Continue upgrade only if no blocking processes remain.
```

Manual fallback for MemorySeed:

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.ExecutablePath -like "*memory-seed*" -or
    $_.CommandLine -like "*memory-seed*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
  }
```

Manual fallback for MemoryTrace:

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.ExecutablePath -like "*memory-trace*" -or
    $_.CommandLine -like "*memory-trace*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
  }
```

## macOS and Linux

Use `psutil` internally for portability.

Manual fallback for MemorySeed:

```bash
pkill -f "memory-seed"
```

Manual fallback for MemoryTrace:

```bash
pkill -f "memory-trace"
```

The implementation should avoid relying only on platform-specific shell commands internally. `psutil` gives a more portable and testable process-management layer.

---

## Proposed Implementation Shape

If `memory-seed` and `memory-trace` live in separate packages, each can contain a small package-local CLI process module.

Example:

```text
src/memory_seed/cli/processes.py
src/memory_trace/cli/processes.py
```

If both packages live in the same repository or can share an internal utility package, prefer:

```text
src/memory_common/processes.py
```

Suggested shared data model:

```python
from dataclasses import dataclass
from typing import Literal


@dataclass
class ManagedProcess:
    pid: int
    name: str
    exe: str | None
    cmdline: list[str]
    package: Literal["memory-seed", "memory-trace"]
```

Suggested install-manager model:

```python
from dataclasses import dataclass
from typing import Literal


InstallManager = Literal["uv", "pipx", "pip", "unknown"]


@dataclass
class InstallDetection:
    manager: InstallManager
    confidence: Literal["high", "medium", "low"]
    reason: str
    executable_path: str | None = None
```

Suggested core functions:

```python
def find_managed_processes(package: str) -> list[ManagedProcess]:
    """Return active processes clearly owned by the selected package."""
    ...


def print_process_table(processes: list[ManagedProcess]) -> None:
    """Render a human-readable process table."""
    ...


def terminate_processes(
    processes: list[ManagedProcess],
    graceful_timeout_seconds: float = 3.0,
    force: bool = True,
) -> ShutdownResult:
    """Terminate matching processes and report successes/failures."""
    ...


def detect_install_manager(package: str) -> InstallDetection:
    """Detect the likely package manager used to install the package."""
    ...


def build_upgrade_command(package: str, manager: str) -> list[str]:
    """Return the package-manager-specific upgrade command."""
    ...


def run_upgrade_command(command: list[str]) -> int:
    """Run the selected upgrade command and return the exit code."""
    ...
```

Suggested shutdown result model:

```python
@dataclass
class ShutdownResult:
    stopped: list[ManagedProcess]
    failed: list[ManagedProcess]
    remaining: list[ManagedProcess]
```

---

## CLI Option Design

Recommended command options:

```bash
memory-seed processes
memory-seed processes --json

memory-seed shutdown
memory-seed shutdown --yes
memory-seed shutdown --dry-run
memory-seed shutdown --json

memory-seed upgrade
memory-seed upgrade --yes
memory-seed upgrade --dry-run
memory-seed upgrade --manager uv
memory-seed upgrade --manager pipx
memory-seed upgrade --manager pip
```

Equivalent commands should exist for:

```bash
memory-trace
```

---

## Dry Run Behaviour

For:

```bash
memory-seed shutdown --dry-run
```

Output should look like:

```text
Would stop 4 memory-seed processes:

PID    Name                 Command
33088  memory-seed-mcp.exe  memory-seed-mcp --stdio
32176  uv.exe               uv tool uvx --from memory-seed memory-seed-mcp --stdio
33588  uvx.exe              uvx --from memory-seed memory-seed-mcp --stdio
32788  python.exe           ...uv\tools\memory-seed\Scripts\python.exe...
```

No process should be stopped.

For:

```bash
memory-seed upgrade --dry-run
```

Output should show:

```text
Would stop the listed memory-seed processes.

Detected install manager:
uv

Would then run:
uv tool upgrade memory-seed
```

No process should be stopped and no upgrade should be performed.

---

## JSON Behaviour

For:

```bash
memory-seed processes --json
```

Example output:

```json
[
  {
    "pid": 33088,
    "name": "memory-seed-mcp.exe",
    "package": "memory-seed",
    "exe": "C:\\Users\\johnn\\AppData\\Roaming\\uv\\tools\\memory-seed\\Scripts\\memory-seed-mcp.exe",
    "cmdline": ["memory-seed-mcp", "--stdio"]
  }
]
```

For:

```bash
memory-seed upgrade --dry-run --json
```

Example output:

```json
{
  "package": "memory-seed",
  "active_processes": [
    {
      "pid": 33088,
      "name": "memory-seed-mcp.exe",
      "package": "memory-seed",
      "exe": "C:\\Users\\johnn\\AppData\\Roaming\\uv\\tools\\memory-seed\\Scripts\\memory-seed-mcp.exe",
      "cmdline": ["memory-seed-mcp", "--stdio"]
    }
  ],
  "install_detection": {
    "manager": "uv",
    "confidence": "high",
    "reason": "Executable path is inside uv tools directory"
  },
  "upgrade_command": ["uv", "tool", "upgrade", "memory-seed"],
  "dry_run": true
}
```

---

## Documentation Additions

## MemorySeed Documentation

Add a section similar to:

```markdown
## Upgrading MemorySeed

Recommended:

```bash
memory-seed upgrade
```

If you know the installer:

```bash
memory-seed upgrade --manager uv
memory-seed upgrade --manager pipx
memory-seed upgrade --manager pip
```

If the upgrade is blocked by active MCP processes:

```bash
memory-seed shutdown
```

Then run the appropriate upgrade command:

```bash
uv tool upgrade memory-seed
```

or:

```bash
pipx upgrade memory-seed
```

or:

```bash
python -m pip install --upgrade memory-seed
```

To inspect active MemorySeed processes:

```bash
memory-seed processes
```

For non-interactive environments:

```bash
memory-seed upgrade --yes --manager uv
```
```

## MemoryTrace Documentation

Add a section similar to:

```markdown
## Upgrading MemoryTrace

Recommended:

```bash
memory-trace upgrade
```

If you know the installer:

```bash
memory-trace upgrade --manager uv
memory-trace upgrade --manager pipx
memory-trace upgrade --manager pip
```

If the upgrade is blocked by active MCP processes:

```bash
memory-trace shutdown
```

Then run the appropriate upgrade command:

```bash
uv tool upgrade memory-trace
```

or:

```bash
pipx upgrade memory-trace
```

or:

```bash
python -m pip install --upgrade memory-trace
```

To inspect active MemoryTrace processes:

```bash
memory-trace processes
```

For non-interactive environments:

```bash
memory-trace upgrade --yes --manager uv
```
```

---

## Testing Plan

## Unit Tests

Test process matching against sample command lines.

MemorySeed matches:

```text
uvx --from memory-seed memory-seed-mcp --stdio
uv tool uvx --from memory-seed memory-seed-mcp --stdio
pipx run memory-seed memory-seed-mcp --stdio
memory-seed-mcp.exe --stdio
C:\Users\johnn\AppData\Roaming\uv\tools\memory-seed\Scripts\python.exe ...
C:\Users\johnn\.local\pipx\venvs\memory-seed\Scripts\python.exe ...
```

MemoryTrace matches:

```text
uvx --from memory-trace memory-trace-mcp --stdio
uv tool uvx --from memory-trace memory-trace-mcp --stdio
pipx run memory-trace memory-trace-mcp --stdio
memory-trace-mcp.exe --stdio
C:\Users\johnn\AppData\Roaming\uv\tools\memory-trace\Scripts\python.exe ...
C:\Users\johnn\.local\pipx\venvs\memory-trace\Scripts\python.exe ...
```

Non-matches:

```text
python.exe unrelated_script.py
uvx --from other-package other-server
pipx run other-package other-server
claude.exe
code.exe
node.exe
memory-other-mcp.exe --stdio
```

## Install Manager Detection Tests

Test likely `uv` detection:

```text
C:\Users\johnn\AppData\Roaming\uv\tools\memory-seed\Scripts\memory-seed.exe
/home/user/.local/share/uv/tools/memory-seed/bin/memory-seed
```

Test likely `pipx` detection:

```text
C:\Users\johnn\.local\pipx\venvs\memory-seed\Scripts\memory-seed.exe
/home/user/.local/pipx/venvs/memory-seed/bin/memory-seed
```

Test ambiguous detection:

```text
.venv/bin/memory-seed
.venv\Scripts\memory-seed.exe
```

Expected result for ambiguous detection:

```text
manager: unknown
confidence: low
action: ask user or require --manager
```

## CLI Tests

Test:

1. `processes` prints matching process table.
2. `processes --json` returns valid JSON.
3. `shutdown --dry-run` does not stop anything.
4. `shutdown` asks for confirmation.
5. `shutdown` with default Enter does not stop anything.
6. `shutdown --yes` skips confirmation.
7. `upgrade` cancels if the user declines shutdown.
8. `upgrade --yes --manager uv` shuts down processes and invokes `uv tool upgrade <package>`.
9. `upgrade --yes --manager pipx` shuts down processes and invokes `pipx upgrade <package>`.
10. `upgrade --yes --manager pip` shuts down processes and invokes `python -m pip install --upgrade <package>`.
11. Failed shutdown prevents upgrade.
12. Remaining blocking PIDs are reported.
13. Ambiguous manager detection asks the user in interactive mode.
14. Ambiguous manager detection fails clearly in non-interactive mode without `--manager`.

## Manual Windows Test

1. Start MemorySeed MCP through an MCP client.
2. Run:

```powershell
memory-seed processes
```

3. Confirm active `memory-seed` processes are listed.
4. Run:

```powershell
memory-seed upgrade
```

5. Confirm the interactive shutdown prompt appears.
6. Select `y`.
7. Confirm only MemorySeed processes are stopped.
8. Confirm the package-manager detection step appears.
9. Confirm the correct upgrade command runs.

Repeat the same test for `memory-trace`.

---

## Recommended Codex Implementation Prompt

Implement installer-agnostic process shutdown and package-manager-aware upgrade commands for both `memory-seed` and `memory-trace`.

Add CLI commands:

```bash
memory-seed processes
memory-seed shutdown
memory-seed upgrade

memory-trace processes
memory-trace shutdown
memory-trace upgrade
```

Requirements:

- `processes` lists active package-owned processes.
- `processes --json` returns machine-readable process data.
- `shutdown` works regardless of whether the package was installed through `uv`, `pipx`, `pip`, a virtual environment, or an editable install.
- `shutdown` interactively asks before stopping processes.
- `shutdown --yes` skips the prompt.
- `shutdown --dry-run` lists matching processes without killing them.
- `shutdown --json` emits structured process and shutdown results.
- `upgrade` detects active processes, prompts to shut them down, then detects or asks for an install manager.
- `upgrade --manager uv` invokes `uv tool upgrade <package>`.
- `upgrade --manager pipx` invokes `pipx upgrade <package>`.
- `upgrade --manager pip` invokes `python -m pip install --upgrade <package>`.
- `upgrade --yes` performs non-interactive shutdown before upgrade.
- `upgrade --dry-run` shows what would be stopped and what upgrade command would run.
- If the user declines shutdown, cancel the upgrade.
- If install-manager detection is ambiguous, ask the user in interactive mode.
- If install-manager detection is ambiguous in non-interactive mode, fail with a clear message requiring `--manager`.
- Never kill unrelated Python, `uv`, `uvx`, `pipx`, MCP, Codex, Claude, VS Code, terminal, browser, or shell processes.
- Only kill processes whose executable path or command line clearly contains the target package name.
- Use a shared implementation where practical so MemorySeed and MemoryTrace have identical behaviour.
- Add unit tests for process matching, install-manager detection, shutdown confirmation behaviour, dry-run behaviour, JSON output, and upgrade command flow.
- Add docs explaining the recommended upgrade path and manual fallback commands for `uv`, `pipx`, and `pip`.

---

## Conclusion

The safest and most flexible design is:

```bash
memory-seed shutdown
memory-trace shutdown
```

as installer-agnostic process-management commands, plus:

```bash
memory-seed upgrade
memory-trace upgrade
```

as package-manager-aware convenience wrappers.

This avoids coupling the packages to `uv`, while still supporting the immediate `uv tool upgrade` failure mode. It also gives users clear manual recovery commands when they prefer to run their own package-manager upgrade directly.
