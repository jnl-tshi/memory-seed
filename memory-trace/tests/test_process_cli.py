import contextlib
import io
import json
import unittest
from unittest import mock

from memory_trace.cli import main


class MemoryTraceProcessCliTests(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_processes_command_delegates_to_shared_process_logic(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=77,
                name="memory-trace.exe",
                exe=None,
                cmdline=("memory-trace", "--no-open"),
                package="memory-trace",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["processes", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload[0]["package"], "memory-trace")
        self.assertEqual(payload[0]["pid"], 77)

    def test_shutdown_dry_run_uses_memory_trace_package_name(self):
        from memory_seed.processes import ManagedProcess

        managed = [
            ManagedProcess(
                pid=78,
                name="memory-trace.exe",
                exe=None,
                cmdline=("memory-trace", "--no-open"),
                package="memory-trace",
            )
        ]
        with mock.patch("memory_seed.processes.find_managed_processes", return_value=managed):
            code, out, err = self.run_cli(["shutdown", "--dry-run"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Would stop 1 memory-trace process", out)

    def test_upgrade_command_targets_memory_seed_owner_package(self):
        from memory_seed.processes import InstallDetection

        with (
            mock.patch("memory_seed.processes.find_managed_processes", return_value=[]),
            mock.patch(
                "memory_seed.processes.detect_install_manager",
                return_value=InstallDetection("uv", "high", "test", "/tmp/memory-trace"),
            ),
            mock.patch("memory_seed.processes.run_upgrade_command", return_value=0) as run_upgrade,
        ):
            code, out, err = self.run_cli(["upgrade", "--yes"])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("No active memory-trace processes found.", out)
        run_upgrade.assert_called_once_with(["uv", "tool", "upgrade", "memory-seed"])


if __name__ == "__main__":
    unittest.main()
