import contextlib
import io
import json
import sys
import unittest
from unittest import mock


class ProcessMatchingTests(unittest.TestCase):
    def test_finds_only_conservative_memory_seed_matches(self):
        from memory_seed.processes import ProcessInfo, find_managed_processes

        snapshots = [
            ProcessInfo(101, "memory-seed-mcp.exe", None, ("memory-seed-mcp.exe", "--stdio")),
            ProcessInfo(102, "uvx.exe", None, ("uvx", "--from", "memory-seed", "memory-seed-mcp", "--stdio")),
            ProcessInfo(103, "uv.exe", None, ("uv", "tool", "uvx", "--from", "memory-seed", "memory-seed-mcp")),
            ProcessInfo(104, "pipx.exe", None, ("pipx", "run", "memory-seed", "memory-seed-mcp")),
            ProcessInfo(
                105,
                "python.exe",
                r"C:\Users\j\AppData\Roaming\uv\tools\memory-seed\Scripts\python.exe",
                ("python.exe", "-m", "memory_seed.mcp_server"),
            ),
            ProcessInfo(201, "python.exe", None, ("python.exe", "unrelated_script.py")),
            ProcessInfo(202, "uvx.exe", None, ("uvx", "--from", "other-package", "other-server")),
            ProcessInfo(203, "pipx.exe", None, ("pipx", "run", "other-package", "other-server")),
            ProcessInfo(204, "claude.exe", None, ("claude.exe",)),
            ProcessInfo(205, "code.exe", None, ("code.exe",)),
            ProcessInfo(206, "memory-other-mcp.exe", None, ("memory-other-mcp.exe", "--stdio")),
            ProcessInfo(207, "memory-seedling.exe", None, ("memory-seedling.exe", "--stdio")),
        ]

        matches = find_managed_processes("memory-seed", snapshots=snapshots, current_pid=999)

        self.assertEqual([process.pid for process in matches], [101, 102, 103, 104, 105])
        self.assertTrue(all(process.package == "memory-seed" for process in matches))

    def test_finds_memory_trace_matches_with_same_rules(self):
        from memory_seed.processes import ProcessInfo, find_managed_processes

        snapshots = [
            ProcessInfo(301, "memory-trace.exe", None, ("memory-trace", "--no-open")),
            ProcessInfo(302, "uvx.exe", None, ("uvx", "--from", "memory-trace", "memory-trace")),
            ProcessInfo(
                303,
                "python.exe",
                r"C:\Users\j\.local\pipx\venvs\memory-trace\Scripts\python.exe",
                ("python.exe", "-m", "memory_trace.cli"),
            ),
            ProcessInfo(401, "uvx.exe", None, ("uvx", "--from", "memory-seed", "memory-seed-mcp")),
            ProcessInfo(402, "memory-tracer.exe", None, ("memory-tracer.exe",)),
        ]

        matches = find_managed_processes("memory-trace", snapshots=snapshots, current_pid=999)

        self.assertEqual([process.pid for process in matches], [301, 302, 303])
        self.assertTrue(all(process.package == "memory-trace" for process in matches))

    def test_skips_current_process(self):
        from memory_seed.processes import ProcessInfo, find_managed_processes

        snapshots = [
            ProcessInfo(500, "memory-seed.exe", None, ("memory-seed", "processes")),
            ProcessInfo(501, "memory-seed-mcp.exe", None, ("memory-seed-mcp", "--stdio")),
        ]

        matches = find_managed_processes("memory-seed", snapshots=snapshots, current_pid=500)

        self.assertEqual([process.pid for process in matches], [501])

    def test_skips_package_control_commands_started_through_wrappers(self):
        from memory_seed.processes import ProcessInfo, find_managed_processes

        snapshots = [
            ProcessInfo(600, "uvx.exe", None, ("uvx", "--from", "memory-seed", "memory-seed", "upgrade")),
            ProcessInfo(601, "memory-seed.exe", None, ("memory-seed", "shutdown", "--yes")),
            ProcessInfo(602, "memory-seed-mcp.exe", None, ("memory-seed-mcp", "--stdio")),
            ProcessInfo(
                603,
                "python.exe",
                r"C:\Users\j\AppData\Roaming\uv\tools\memory-seed\Scripts\python.exe",
                ("python.exe", "-m", "memory_seed.cli", "upgrade"),
            ),
        ]

        matches = find_managed_processes("memory-seed", snapshots=snapshots, current_pid=999)

        self.assertEqual([process.pid for process in matches], [602])

    def test_install_manager_detection_is_conservative(self):
        from memory_seed.processes import build_upgrade_command, detect_install_manager

        self.assertEqual(
            detect_install_manager(
                "memory-seed",
                executable_path=r"C:\Users\j\AppData\Roaming\uv\tools\memory-seed\Scripts\memory-seed.exe",
            ).manager,
            "uv",
        )
        self.assertEqual(
            detect_install_manager(
                "memory-trace",
                executable_path="/home/j/.local/pipx/venvs/memory-trace/bin/memory-trace",
            ).manager,
            "pipx",
        )
        ambiguous = detect_install_manager("memory-seed", executable_path=".venv/bin/memory-seed")
        self.assertEqual(ambiguous.manager, "unknown")
        self.assertEqual(ambiguous.confidence, "low")
        self.assertEqual(build_upgrade_command("memory-seed", "uv"), ["uv", "tool", "upgrade", "memory-seed"])
        self.assertEqual(build_upgrade_command("memory-trace", "pipx"), ["pipx", "upgrade", "memory-trace"])
        self.assertEqual(
            build_upgrade_command("memory-seed", "pip"),
            [sys.executable, "-m", "pip", "install", "--upgrade", "memory-seed"],
        )

    def test_terminate_processes_reports_failed_remaining_processes(self):
        from memory_seed.processes import ManagedProcess, terminate_processes

        stopped = ManagedProcess(700, "memory-seed-mcp.exe", None, ("memory-seed-mcp",), "memory-seed")
        failed = ManagedProcess(701, "uvx.exe", None, ("uvx", "--from", "memory-seed"), "memory-seed")
        calls = []

        def fake_terminate(process):
            calls.append(process.pid)
            return process.pid != failed.pid

        result = terminate_processes(
            [stopped, failed],
            package="memory-seed",
            terminator=fake_terminate,
            remaining_processes=lambda: [failed],
        )

        self.assertEqual(calls, [700, 701])
        self.assertEqual([process.pid for process in result.stopped], [700])
        self.assertEqual([process.pid for process in result.failed], [701])
        self.assertEqual([process.pid for process in result.remaining], [701])


class ProcessCliTests(unittest.TestCase):
    def run_cli(self, argv):
        from memory_seed.cli import main

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_processes_json_outputs_machine_readable_matches(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=42,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["processes", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out), [
            {
                "pid": 42,
                "name": "memory-seed-mcp.exe",
                "exe": None,
                "cmdline": ["memory-seed-mcp", "--stdio"],
                "package": "memory-seed",
            }
        ])

    def test_shutdown_dry_run_reports_without_terminating(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=43,
                name="uvx.exe",
                exe=None,
                cmdline=("uvx", "--from", "memory-seed", "memory-seed-mcp"),
                package="memory-seed",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["shutdown", "--dry-run"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Would stop 1 memory-seed process", out)
        self.assertIn("43", out)

    def test_shutdown_dry_run_json_reports_no_action(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=44,
                name="uv.exe",
                exe=None,
                cmdline=("uv", "tool", "uvx", "--from", "memory-seed", "memory-seed-mcp"),
                package="memory-seed",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["shutdown", "--dry-run", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["package"], "memory-seed")
        self.assertEqual(payload["active_processes"][0]["pid"], 44)
        self.assertEqual(payload["stopped"], [])

    def test_shutdown_default_decline_does_not_stop_processes(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=45,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=managed),
            mock.patch("builtins.input", return_value=""),
            mock.patch("memory_seed.processes.terminate_processes") as terminate,
        ):
            code, out, err = self.run_cli(["shutdown"])

        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        self.assertIn("Shutdown cancelled", out)
        terminate.assert_not_called()

    def test_shutdown_yes_stops_matching_processes(self):
        from memory_seed.processes import ManagedProcess, ShutdownResult

        managed = [
            ManagedProcess(
                pid=45,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        result = ShutdownResult(stopped=tuple(managed), failed=(), remaining=())
        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=managed),
            mock.patch("memory_seed.processes.terminate_processes", return_value=result) as terminate,
        ):
            code, out, err = self.run_cli(["shutdown", "--yes"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Stopped 1 memory-seed process", out)
        terminate.assert_called_once()

    def test_upgrade_dry_run_json_includes_detection_and_command(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=46,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["upgrade", "--dry-run", "--manager", "uv", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["upgrade_command"], ["uv", "tool", "upgrade", "memory-seed"])
        self.assertEqual(payload["active_processes"][0]["pid"], 46)

    def test_upgrade_yes_manager_stops_processes_then_runs_command(self):
        from memory_seed.processes import ManagedProcess, ShutdownResult

        managed = [
            ManagedProcess(
                pid=47,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        shutdown = ShutdownResult(stopped=tuple(managed), failed=(), remaining=())
        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=managed),
            mock.patch("memory_seed.processes.terminate_processes", return_value=shutdown),
            mock.patch("memory_seed.processes.run_upgrade_command", return_value=0) as run_upgrade,
        ):
            code, out, err = self.run_cli(["upgrade", "--yes", "--manager", "uv"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Running:", out)
        run_upgrade.assert_called_once_with(["uv", "tool", "upgrade", "memory-seed"])

    def test_upgrade_failed_shutdown_prevents_upgrade_command(self):
        from memory_seed.processes import ManagedProcess, ShutdownResult

        managed = [
            ManagedProcess(
                pid=48,
                name="memory-seed-mcp.exe",
                exe=None,
                cmdline=("memory-seed-mcp", "--stdio"),
                package="memory-seed",
            )
        ]
        shutdown = ShutdownResult(stopped=(), failed=tuple(managed), remaining=tuple(managed))
        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=managed),
            mock.patch("memory_seed.processes.terminate_processes", return_value=shutdown),
            mock.patch("memory_seed.processes.run_upgrade_command") as run_upgrade,
        ):
            code, out, err = self.run_cli(["upgrade", "--yes", "--manager", "uv"])

        self.assertEqual(code, 1)
        self.assertIn("Upgrade cancelled because shutdown failed", err)
        run_upgrade.assert_not_called()

    def test_upgrade_yes_requires_manager_when_detection_unknown(self):
        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=[]),
            mock.patch(
                "memory_seed.processes.detect_install_manager",
                return_value=__import__("memory_seed.processes").processes.InstallDetection(
                    manager="unknown",
                    confidence="low",
                    reason="Could not safely determine the install manager.",
                    executable_path=None,
                ),
            ),
            mock.patch("memory_seed.processes.run_upgrade_command") as run_upgrade,
        ):
            code, out, err = self.run_cli(["upgrade", "--yes"])

        self.assertEqual(code, 2)
        self.assertIn("No active memory-seed processes found.", out)
        self.assertIn("--manager uv", err)
        run_upgrade.assert_not_called()

    def test_upgrade_interactive_manager_selection_runs_selected_command(self):
        from memory_seed.processes import InstallDetection

        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=[]),
            mock.patch(
                "memory_seed.processes.detect_install_manager",
                return_value=InstallDetection("unknown", "low", "Could not safely determine.", None),
            ),
            mock.patch("builtins.input", return_value="2"),
            mock.patch("memory_seed.processes.run_upgrade_command", return_value=0) as run_upgrade,
        ):
            code, out, err = self.run_cli(["upgrade"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        run_upgrade.assert_called_once_with(["pipx", "upgrade", "memory-seed"])


if __name__ == "__main__":
    unittest.main()
