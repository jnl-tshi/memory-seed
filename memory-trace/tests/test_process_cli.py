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


if __name__ == "__main__":
    unittest.main()
