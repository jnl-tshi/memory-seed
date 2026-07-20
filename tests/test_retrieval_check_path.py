import shutil
import tempfile
import unittest
from pathlib import Path



class RetrievalCheckPathTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/memory-retrieval-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed").mkdir()
        return path

    def _run(self, cwd, extra_env=None):
        import subprocess
        import sys
        import os

        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_mcp_found_message_mentions_memory_search(self):
        import os
        import stat

        cwd = self.make_project()
        # Create a dummy memory-seed-mcp binary on PATH
        bin_dir = cwd / "bin"
        bin_dir.mkdir()
        fake_bin = bin_dir / "memory-seed-mcp"
        fake_bin.write_text("#!/usr/bin/env python3\n")
        fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IEXEC)

        out = self._run(cwd, extra_env={"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")})
        self.assertIn("memory_search", out)
        self.assertNotIn("uv tool install", out)

    def test_mcp_missing_message_mentions_install(self):
        cwd = self.make_project()
        out = self._run(cwd, extra_env={"PATH": ""})
        self.assertIn("uv tool install", out)
        self.assertNotIn("memory_search MCP tool", out)
