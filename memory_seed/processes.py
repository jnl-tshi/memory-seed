from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Literal, Sequence


PackageName = Literal["memory-seed", "memory-trace"]
InstallManager = Literal["uv", "pipx", "pip", "unknown"]
Confidence = Literal["high", "medium", "low"]

PACKAGE_COMMANDS = {"processes", "shutdown", "upgrade"}
SUPPORTED_PACKAGES = {"memory-seed", "memory-trace"}


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    exe: str | None
    cmdline: tuple[str, ...]


@dataclass(frozen=True)
class ManagedProcess:
    pid: int
    name: str
    exe: str | None
    cmdline: tuple[str, ...]
    package: str


@dataclass(frozen=True)
class InstallDetection:
    manager: InstallManager
    confidence: Confidence
    reason: str
    executable_path: str | None = None


@dataclass(frozen=True)
class ShutdownResult:
    stopped: tuple[ManagedProcess, ...]
    failed: tuple[ManagedProcess, ...]
    remaining: tuple[ManagedProcess, ...]


def normalize_package(package: str) -> PackageName:
    if package not in SUPPORTED_PACKAGES:
        raise ValueError(f"Unsupported package: {package}")
    return package  # type: ignore[return-value]


def _package_token_re(package: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-z0-9])" + re.escape(package.lower()) + r"(?![a-z0-9])")


def _contains_package_token(value: str | None, package: str) -> bool:
    if not value:
        return False
    return _package_token_re(package).search(value.lower().replace("_", "-")) is not None


def process_matches_package(process: ProcessInfo, package: str) -> bool:
    package = normalize_package(package)
    command = " ".join(str(part) for part in process.cmdline if part)
    return any(
        _contains_package_token(value, package)
        for value in (process.name, process.exe, command)
    )


def find_managed_processes(
    package: str,
    *,
    snapshots: Iterable[ProcessInfo] | None = None,
    current_pid: int | None = None,
) -> list[ManagedProcess]:
    package = normalize_package(package)
    current_pid = os.getpid() if current_pid is None else current_pid
    matches: list[ManagedProcess] = []
    for process in snapshots if snapshots is not None else iter_system_processes():
        if process.pid == current_pid:
            continue
        if not process_matches_package(process, package):
            continue
        if _is_package_control_command(process, package):
            continue
        matches.append(
            ManagedProcess(
                pid=process.pid,
                name=process.name,
                exe=process.exe,
                cmdline=process.cmdline,
                package=package,
            )
        )
    return matches


def _is_package_control_command(process: ProcessInfo, package: str) -> bool:
    """Avoid targeting the active package CLI wrapper that is running this workflow."""

    normalized_tokens = [_normalize_token(part) for part in process.cmdline if part]
    if not normalized_tokens:
        return False
    package_module = package + ".cli"
    package_cli_tokens = {package, f"{package}.exe", f"{package}.cmd", f"{package}.ps1", package_module}
    has_package_cli = any(token in package_cli_tokens for token in normalized_tokens)
    has_control_command = any(token in PACKAGE_COMMANDS for token in normalized_tokens)
    return has_package_cli and has_control_command


def _normalize_token(value: object) -> str:
    token = str(value).replace("\\", "/").rsplit("/", 1)[-1].lower().replace("_", "-")
    if token.endswith(".py"):
        token = token[:-3]
    return token


def managed_process_to_dict(process: ManagedProcess) -> dict[str, object]:
    return {
        "pid": process.pid,
        "name": process.name,
        "exe": process.exe,
        "cmdline": list(process.cmdline),
        "package": process.package,
    }


def install_detection_to_dict(detection: InstallDetection) -> dict[str, object]:
    return {
        "manager": detection.manager,
        "confidence": detection.confidence,
        "reason": detection.reason,
        "executable_path": detection.executable_path,
    }


def shutdown_result_to_dict(result: ShutdownResult) -> dict[str, object]:
    return {
        "stopped": [managed_process_to_dict(process) for process in result.stopped],
        "failed": [managed_process_to_dict(process) for process in result.failed],
        "remaining": [managed_process_to_dict(process) for process in result.remaining],
    }


def iter_system_processes() -> list[ProcessInfo]:
    psutil_processes = _iter_psutil_processes()
    if psutil_processes is not None:
        return psutil_processes
    if os.name == "nt":
        return _iter_windows_processes()
    return _iter_posix_processes()


def _iter_psutil_processes() -> list[ProcessInfo] | None:
    try:
        import psutil  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None

    processes: list[ProcessInfo] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            info = proc.info
            pid = int(info.get("pid") or 0)
            name = str(info.get("name") or "")
            exe = info.get("exe")
            raw_cmdline = info.get("cmdline") or ()
        except (psutil.Error, ValueError, TypeError):
            continue
        processes.append(ProcessInfo(pid=pid, name=name, exe=exe, cmdline=_cmdline_tuple(raw_cmdline)))
    return processes


def _iter_windows_processes() -> list[ProcessInfo]:
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    processes: list[ProcessInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            pid = int(row.get("ProcessId") or 0)
        except (TypeError, ValueError):
            continue
        command_line = row.get("CommandLine") or ""
        processes.append(
            ProcessInfo(
                pid=pid,
                name=str(row.get("Name") or ""),
                exe=row.get("ExecutablePath"),
                cmdline=_split_command_line(str(command_line)),
            )
        )
    return processes


def _iter_posix_processes() -> list[ProcessInfo]:
    try:
        result = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    processes: list[ProcessInfo] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        name = parts[1]
        cmdline = _split_command_line(parts[2] if len(parts) > 2 else name)
        processes.append(ProcessInfo(pid=pid, name=name, exe=None, cmdline=cmdline))
    return processes


def _cmdline_tuple(value: Sequence[object] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        return _split_command_line(value)
    return tuple(str(part) for part in value if part is not None)


def _split_command_line(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        return tuple(shlex.split(value, posix=(os.name != "nt")))
    except ValueError:
        return (value,)


def format_process_table(processes: Sequence[ManagedProcess]) -> str:
    if not processes:
        return ""
    rows = [
        (str(process.pid), process.name or "-", " ".join(process.cmdline) or process.exe or "-")
        for process in processes
    ]
    pid_width = max(len("PID"), *(len(row[0]) for row in rows))
    name_width = max(len("Name"), *(len(row[1]) for row in rows))
    lines = [f"{'PID':<{pid_width}}  {'Name':<{name_width}}  Command"]
    for pid, name, command in rows:
        lines.append(f"{pid:<{pid_width}}  {name:<{name_width}}  {command}")
    return "\n".join(lines)


def detect_install_manager(package: str, *, executable_path: str | None = None) -> InstallDetection:
    package = normalize_package(package)
    executable_path = executable_path or sys.executable
    normalized = executable_path.replace("\\", "/").lower()
    if f"/uv/tools/{package}/" in normalized:
        return InstallDetection(
            manager="uv",
            confidence="high",
            reason="Executable path is inside a uv tools directory.",
            executable_path=executable_path,
        )
    if f"/pipx/venvs/{package}/" in normalized:
        return InstallDetection(
            manager="pipx",
            confidence="high",
            reason="Executable path is inside a pipx venv directory.",
            executable_path=executable_path,
        )
    if "/.venv/" in normalized or normalized.startswith(".venv/"):
        return InstallDetection(
            manager="unknown",
            confidence="low",
            reason="Executable path is inside a local virtual environment; choose a manager explicitly.",
            executable_path=executable_path,
        )
    return InstallDetection(
        manager="unknown",
        confidence="low",
        reason="Could not safely determine the install manager.",
        executable_path=executable_path,
    )


def build_upgrade_command(package: str, manager: str) -> list[str]:
    package = normalize_package(package)
    if manager == "uv":
        return ["uv", "tool", "upgrade", package]
    if manager == "pipx":
        return ["pipx", "upgrade", package]
    if manager == "pip":
        return [sys.executable, "-m", "pip", "install", "--upgrade", package]
    raise ValueError(f"Unsupported install manager: {manager}")


def terminate_processes(
    processes: Sequence[ManagedProcess],
    *,
    package: str,
    graceful_timeout_seconds: float = 3.0,
    force: bool = True,
    terminator: Callable[[ManagedProcess], bool] | None = None,
    remaining_processes: Callable[[], Sequence[ManagedProcess]] | None = None,
) -> ShutdownResult:
    package = normalize_package(package)
    terminator = terminator or (
        lambda process: _terminate_process(
            process,
            graceful_timeout_seconds=graceful_timeout_seconds,
            force=force,
        )
    )
    attempted: list[ManagedProcess] = []
    failed: list[ManagedProcess] = []
    current_pid = os.getpid()
    for process in processes:
        if process.package != package or process.pid == current_pid:
            failed.append(process)
            continue
        attempted.append(process)
        if not terminator(process):
            failed.append(process)
    remaining = tuple(
        remaining_processes()
        if remaining_processes is not None
        else find_managed_processes(package)
    )
    remaining_pids = {process.pid for process in remaining}
    failed_by_pid = {process.pid: process for process in failed}
    for process in attempted:
        if process.pid in remaining_pids:
            failed_by_pid.setdefault(process.pid, process)
    stopped = tuple(process for process in attempted if process.pid not in remaining_pids and process.pid not in failed_by_pid)
    failed_ordered = tuple(
        process
        for process in processes
        if process.pid in failed_by_pid
    )
    return ShutdownResult(stopped=stopped, failed=failed_ordered, remaining=remaining)


def _terminate_process(
    process: ManagedProcess,
    *,
    graceful_timeout_seconds: float,
    force: bool,
) -> bool:
    if process.pid <= 0 or process.pid == os.getpid():
        return False
    if os.name == "nt":
        return _terminate_windows_process(process.pid)
    return _terminate_posix_process(
        process.pid,
        graceful_timeout_seconds=graceful_timeout_seconds,
        force=force,
    )


def _terminate_windows_process(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _terminate_posix_process(pid: int, *, graceful_timeout_seconds: float, force: bool) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    deadline = time.monotonic() + graceful_timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(0.05)
    if not force:
        return not _pid_exists(pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return True


def _pid_exists(pid: int) -> bool:
    if os.name == "nt":
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def run_upgrade_command(command: Sequence[str]) -> int:
    try:
        result = subprocess.run(list(command))
    except FileNotFoundError:
        print(f"Upgrade command not found: {command[0]}", file=sys.stderr)
        return 127
    except OSError as exc:
        print(f"Upgrade command failed to start: {exc}", file=sys.stderr)
        return 127
    return result.returncode


def add_package_process_parsers(subparsers: argparse._SubParsersAction) -> None:
    processes_parser = subparsers.add_parser("processes", help="list active package-owned processes")
    processes_parser.add_argument("--json", action="store_true", help="emit machine-readable process data")

    shutdown_parser = subparsers.add_parser("shutdown", help="shut down package-owned processes")
    shutdown_parser.add_argument("--dry-run", action="store_true", help="list matching processes without stopping them")
    shutdown_parser.add_argument("--json", action="store_true", help="emit machine-readable shutdown data")
    shutdown_parser.add_argument("--yes", action="store_true", help="skip confirmation and stop matching processes")

    upgrade_parser = subparsers.add_parser("upgrade", help="run package-manager-aware upgrade")
    upgrade_parser.add_argument("--dry-run", action="store_true", help="show what would be stopped and upgraded")
    upgrade_parser.add_argument("--json", action="store_true", help="emit machine-readable upgrade data")
    upgrade_parser.add_argument("--yes", action="store_true", help="skip shutdown confirmation")
    upgrade_parser.add_argument("--manager", choices=["uv", "pipx", "pip"], default=None)


def run_package_process_argv(package: str, argv: Sequence[str], *, prog: str | None = None) -> int:
    parser = argparse.ArgumentParser(prog=prog or package)
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_package_process_parsers(subparsers)
    args = parser.parse_args(list(argv))
    return run_package_process_command(package, args)


def run_package_process_command(package: str, args: argparse.Namespace) -> int:
    package = normalize_package(package)
    if args.command == "processes":
        active = find_managed_processes(package)
        if args.json:
            print(json.dumps([managed_process_to_dict(process) for process in active], indent=2, ensure_ascii=False))
            return 0
        if not active:
            print(f"No active {package} processes found.")
            return 0
        print(f"Active {package} processes detected:")
        print()
        print(format_process_table(active))
        return 0

    if args.command == "shutdown":
        active = find_managed_processes(package)
        if args.dry_run:
            payload = {
                "package": package,
                "dry_run": True,
                "active_processes": [managed_process_to_dict(process) for process in active],
                "stopped": [],
                "failed": [],
                "remaining": [managed_process_to_dict(process) for process in active],
            }
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
            if not active:
                print(f"No active {package} processes found. No processes would be stopped.")
                return 0
            print(f"Would stop {len(active)} {package} {_process_word(len(active))}:")
            print()
            print(format_process_table(active))
            print()
            print("No processes were stopped.")
            return 0
        if not active:
            if args.json:
                print(
                    json.dumps(
                        {
                            "package": package,
                            "dry_run": False,
                            "active_processes": [],
                            "stopped": [],
                            "failed": [],
                            "remaining": [],
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                return 0
            print(f"No active {package} processes found.")
            return 0
        if not args.yes:
            if args.json:
                print("shutdown --json requires --yes or --dry-run for machine-readable output.", file=sys.stderr)
                return 2
            _print_active_processes(package, active)
            if not _confirm(f"Shut down these {package} processes now? [y/N]: "):
                print("Shutdown cancelled. No processes were stopped.")
                return 1
        elif not args.json:
            _print_active_processes(package, active)
        result = terminate_processes(active, package=package)
        payload = {
            "package": package,
            "dry_run": False,
            "active_processes": [managed_process_to_dict(process) for process in active],
            **shutdown_result_to_dict(result),
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0 if not result.failed and not result.remaining else 1
        if result.stopped:
            print(f"Stopped {len(result.stopped)} {package} {_process_word(len(result.stopped))}.")
        else:
            print(f"No {package} processes were stopped.")
        if result.failed or result.remaining:
            print(f"Failed to stop all {package} processes.", file=sys.stderr)
            _print_remaining_processes(result.remaining)
            return 1
        return 0

    if args.command == "upgrade":
        active = find_managed_processes(package)
        manager = args.manager
        detection = (
            InstallDetection(
                manager=manager,
                confidence="high",
                reason="Install manager supplied explicitly.",
                executable_path=sys.executable,
            )
            if manager
            else detect_install_manager(package)
        )
        command = build_upgrade_command(package, detection.manager) if detection.manager != "unknown" else None
        if args.dry_run:
            payload = {
                "package": package,
                "dry_run": True,
                "active_processes": [managed_process_to_dict(process) for process in active],
                "install_detection": install_detection_to_dict(detection),
                "upgrade_command": command,
            }
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
            if active:
                print(f"Would stop {len(active)} {package} {_process_word(len(active))}:")
                print()
                print(format_process_table(active))
                print()
            else:
                print(f"No active {package} processes found.")
            print(f"Detected install manager: {detection.manager} ({detection.confidence})")
            print(detection.reason)
            if command:
                print("Would then run:")
                print(" ".join(command))
            else:
                print("No upgrade command selected; rerun with --manager uv, pipx, or pip.")
            return 0
        if args.json:
            print("upgrade --json is supported for --dry-run previews; omit --json to execute.", file=sys.stderr)
            return 2
        if active:
            if not args.yes:
                _print_active_processes(package, active)
                if not _confirm(f"Shut down these {package} processes now? [y/N]: "):
                    print(
                        f"Upgrade cancelled because active {package} processes may block executable replacement."
                    )
                    print(f"Run: {package} shutdown")
                    print(f"Then retry: {package} upgrade")
                    return 1
            else:
                _print_active_processes(package, active)
            shutdown = terminate_processes(active, package=package)
            if shutdown.stopped:
                print(f"Stopped {len(shutdown.stopped)} {package} {_process_word(len(shutdown.stopped))}.")
            if shutdown.failed or shutdown.remaining:
                print("Upgrade cancelled because shutdown failed.", file=sys.stderr)
                _print_remaining_processes(shutdown.remaining)
                return 1
        else:
            print(f"No active {package} processes found.")
        if detection.manager == "unknown":
            if args.yes:
                _print_manager_required(package)
                return 2
            selected_manager = _choose_install_manager(package)
            if selected_manager is None:
                print("Upgrade cancelled. No install manager selected.")
                return 1
            detection = InstallDetection(
                manager=selected_manager,
                confidence="high",
                reason="Install manager selected interactively.",
                executable_path=sys.executable,
            )
        command = build_upgrade_command(package, detection.manager)
        if manager:
            print(f"Using install manager: {detection.manager}")
        else:
            print(f"Detected install manager: {detection.manager} ({detection.confidence})")
            print(detection.reason)
        print("Running:")
        print(" ".join(command))
        return run_upgrade_command(command)

    return 2


def _process_word(count: int) -> str:
    return "process" if count == 1 else "processes"


def _print_active_processes(package: str, active: Sequence[ManagedProcess]) -> None:
    print(f"Active {package} processes detected:")
    print()
    print(format_process_table(active))
    print()
    print("These processes may block executable replacement.")


def _print_remaining_processes(remaining: Sequence[ManagedProcess]) -> None:
    if not remaining:
        return
    pids = ", ".join(str(process.pid) for process in remaining)
    print(f"Remaining blocking PIDs: {pids}", file=sys.stderr)


def _confirm(prompt: str) -> bool:
    try:
        response = input(prompt)
    except EOFError:
        return False
    return response.strip().lower() in {"y", "yes"}


def _choose_install_manager(package: str) -> InstallManager | None:
    print(f"Could not safely determine how {package} was installed.")
    print()
    print("Choose one:")
    print(f"1. uv    -> uv tool upgrade {package}")
    print(f"2. pipx  -> pipx upgrade {package}")
    print(f"3. pip   -> {sys.executable} -m pip install --upgrade {package}")
    print("4. cancel")
    try:
        response = input("Upgrade with which manager? [1/2/3/4]: ").strip().lower()
    except EOFError:
        return None
    choices: dict[str, InstallManager | None] = {
        "1": "uv",
        "uv": "uv",
        "2": "pipx",
        "pipx": "pipx",
        "3": "pip",
        "pip": "pip",
        "4": None,
        "cancel": None,
        "": None,
    }
    return choices.get(response)


def _print_manager_required(package: str) -> None:
    print("Could not safely determine install manager.", file=sys.stderr)
    print("Re-run with one of:", file=sys.stderr)
    print(f"{package} upgrade --yes --manager uv", file=sys.stderr)
    print(f"{package} upgrade --yes --manager pipx", file=sys.stderr)
    print(f"{package} upgrade --yes --manager pip", file=sys.stderr)
