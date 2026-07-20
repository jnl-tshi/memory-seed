"""`memory_session_integrate`: autonomous branch integration over MCP.

The merge machinery itself is `session_merge_branch`, already covered in
test_memory_seed.py. These tests cover what the MCP surface changes about it:
it applies without waiting for a human, so it must never walk away from a
half-merged tree, and it must decline the PR path outright.
"""

import shutil
import subprocess
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.mcp_server import call_tool


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def _entry(ts, eid, title, branch):
    return (
        f"## {ts} - {title}\n\n```yaml\nentry_id: {eid}\nuser_initials: JNL\nagent_type: claude\n"
        f"agent_name: null\nproject_path: .\nsubproject_path: null\nbranch: {branch}\n```\n\n"
        "### Decision\n\n- D: something\n- R: because\n\n"
    )


class MemorySessionIntegrateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mseed-mcp-integrate-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-06"
        self.sessions.mkdir(parents=True, exist_ok=True)
        self.log = self.sessions / "2026-06-13.md"

        _git(self.root, "init", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "user.name", "T")
        self.log.write_text(_entry("2026-06-13 09:00", "mse_" + "a" * 16, "trunk-first", "main"), encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", "base")

    def _branch_with_entry(self, name, ts, eid, title, extra=None):
        _git(self.root, "checkout", "-b", name)
        self.log.write_text(self.log.read_text(encoding="utf-8") + _entry(ts, eid, title, name), encoding="utf-8")
        if extra:
            (self.root / extra[0]).write_text(extra[1], encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", f"work on {name}")
        _git(self.root, "checkout", "main")

    @pytest.mark.integration
    def test_merges_and_fuses_without_a_human_gate(self):
        self._branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(result["committed"])
        self.assertFalse(result["merge_in_progress"])
        self.assertEqual(result["issues"], [])
        merged = self.log.read_text(encoding="utf-8")
        self.assertIn("trunk-first", merged)
        self.assertIn("branch-entry", merged)
        self.assertLess(merged.index("trunk-first"), merged.index("branch-entry"))

    @pytest.mark.integration
    def test_dry_run_reports_the_plan_without_merging(self):
        self._branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")
        before = _git(self.root, "rev-parse", "HEAD").stdout.strip()

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature", "dry_run": True})

        self.assertTrue(result["ok"], result["issues"])
        self.assertFalse(result["committed"])
        self.assertEqual(_git(self.root, "rev-parse", "HEAD").stdout.strip(), before)
        self.assertNotIn("branch-entry", self.log.read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_a_non_session_conflict_aborts_and_leaves_a_clean_tree(self):
        # The autonomous difference: session_merge_branch parks this for a human,
        # which would strand an agent in a half-merged repo it cannot resolve.
        (self.root / "shared.txt").write_text("trunk side\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", "add shared")

        self._branch_with_entry(
            "feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry",
            extra=("shared.txt", "branch side\n"),
        )
        (self.root / "shared.txt").write_text("trunk moved on\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", "trunk edits shared")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertFalse(result["committed"])
        self.assertTrue(result["merge_aborted"], "an autonomous caller must not leave a merge in progress")
        self.assertFalse(result["merge_in_progress"])
        self.assertIn("shared.txt", result["conflicts"])
        self.assertFalse((self.root / ".git" / "MERGE_HEAD").exists(), "tree must be restored")
        self.assertEqual(_git(self.root, "status", "--porcelain").stdout.strip(), "")

    @pytest.mark.integration
    def test_pr_mode_is_declined_with_the_cli_command(self):
        # Commit the config on main first: created after branching, it would
        # land on the branch and vanish on checkout.
        (self.root / MEMORY_DIR_NAME / "project.yaml").write_text(
            "schema_version: 1\nintegration_mode: pr\n", encoding="utf-8"
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", "declare pr integration mode")
        self._branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertFalse(result["ok"])
        self.assertFalse(result["committed"])
        self.assertEqual(result["integration_mode"], "pr")
        self.assertIn("not run unattended", " ".join(result["issues"]))
        self.assertIn("memory-seed session integrate", result["cli_command"])

    @pytest.mark.integration
    def test_a_session_problem_aborts_before_the_merge_starts(self):
        # Fail-closed: a fuse issue must leave no merge state behind at all.
        _git(self.root, "checkout", "-b", "feature")
        self.log.write_text(
            self.log.read_text(encoding="utf-8")
            + _entry("2026-06-13 10:00", "mse_" + "b" * 16, "wrong-branch-provenance", "some-other-branch"),
            encoding="utf-8",
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-m", "bad provenance")
        _git(self.root, "checkout", "main")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertFalse(result["committed"])
        self.assertTrue(result["issues"])
        self.assertFalse((self.root / ".git" / "MERGE_HEAD").exists())


if __name__ == "__main__":
    unittest.main()
