"""merge_trigger: hold a branch landing for explicit user authorization.

The switch (operating-mode-variables-proposal.md) gates the integration handoff.
It fails open to 'automatic' so unconfigured/legacy projects behave exactly as
before; a project opts into 'manual' to require --user-approved on the CLI and to
make the unattended MCP integrate decline. A dry run is never gated.
"""

import shutil
import tempfile
import unittest
import pytest
from pathlib import Path

from _git_helpers import run_git
from memory_seed.core import (
    DEFAULT_MERGE_TRIGGER,
    MEMORY_DIR_NAME,
    MERGE_TRIGGERS,
    _merge_trigger_block,
    read_merge_trigger,
    session_merge_branch,
)
from memory_seed.mcp_server import call_tool


def _write_config(root, value):
    cfg = root / MEMORY_DIR_NAME / "project.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(f"merge_trigger: {value}\n", encoding="utf-8")


def _entry(ts, eid, title, branch):
    return (
        f"## {ts} - {title}\n\n```yaml\nentry_id: {eid}\nuser_initials: JNL\nagent_type: claude\n"
        f"agent_name: null\nproject_path: .\nsubproject_path: null\nbranch: {branch}\n```\n\n"
        "### Decision\n\n- D: something\n- R: because\n\n"
    )


class ReadMergeTriggerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mseed-mt-read-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def test_default_is_automatic(self):
        self.assertEqual(DEFAULT_MERGE_TRIGGER, "automatic")
        self.assertEqual(set(MERGE_TRIGGERS), {"manual", "automatic"})

    def test_fail_open_automatic_when_absent(self):
        # No project.yaml at all -> legacy/unconfigured behaves as before.
        self.assertEqual(read_merge_trigger(self.root), "automatic")

    def test_reads_manual_and_automatic(self):
        _write_config(self.root, "manual")
        self.assertEqual(read_merge_trigger(self.root), "manual")
        _write_config(self.root, "automatic")
        self.assertEqual(read_merge_trigger(self.root), "automatic")

    def test_unrecognised_value_fails_open(self):
        _write_config(self.root, "sometimes")
        self.assertEqual(read_merge_trigger(self.root), "automatic")


class MergeTriggerBlockTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mseed-mt-block-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def test_automatic_never_blocks(self):
        _write_config(self.root, "automatic")
        self.assertIsNone(_merge_trigger_block(self.root, user_approved=False))

    def test_manual_blocks_without_approval(self):
        _write_config(self.root, "manual")
        msg = _merge_trigger_block(self.root, user_approved=False)
        self.assertIsNotNone(msg)
        self.assertIn("--user-approved", msg)

    def test_manual_passes_with_approval(self):
        _write_config(self.root, "manual")
        self.assertIsNone(_merge_trigger_block(self.root, user_approved=True))


class _RepoFixture(unittest.TestCase):
    """A minimal git repo with one trunk entry and helpers to add a fusable branch."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mseed-mt-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-06"
        self.sessions.mkdir(parents=True, exist_ok=True)
        self.log = self.sessions / "2026-06-13.md"
        run_git(self.root, "init", "-b", "main", check=False)
        run_git(self.root, "config", "user.email", "t@example.com", check=False)
        run_git(self.root, "config", "user.name", "T", check=False)
        self.log.write_text(_entry("2026-06-13 09:00", "mse_" + "a" * 16, "trunk-first", "main"), encoding="utf-8")
        run_git(self.root, "add", "-A", check=False)
        run_git(self.root, "commit", "-m", "base", check=False)

    def set_trigger(self, value):
        (self.root / MEMORY_DIR_NAME / "project.yaml").write_text(f"merge_trigger: {value}\n", encoding="utf-8")
        run_git(self.root, "add", "-A", check=False)
        run_git(self.root, "commit", "-m", f"trigger {value}", check=False)

    def branch_with_entry(self, name, ts, eid, title):
        run_git(self.root, "checkout", "-b", name, check=False)
        self.log.write_text(self.log.read_text(encoding="utf-8") + _entry(ts, eid, title, name), encoding="utf-8")
        run_git(self.root, "add", "-A", check=False)
        run_git(self.root, "commit", "-m", f"work on {name}", check=False)
        run_git(self.root, "checkout", "main", check=False)


class MergeTriggerGateTests(_RepoFixture):
    @pytest.mark.integration
    def test_manual_blocks_a_real_merge_without_approval(self):
        self.set_trigger("manual")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = session_merge_branch(self.root, branch="feature")

        self.assertTrue(result.merge_trigger_blocked)
        self.assertFalse(result.committed)
        self.assertTrue(any("--user-approved" in i for i in result.issues), result.issues)
        self.assertNotIn("branch-entry", self.log.read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_manual_dry_run_is_never_blocked(self):
        self.set_trigger("manual")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = session_merge_branch(self.root, branch="feature", dry_run=True)

        self.assertFalse(result.merge_trigger_blocked)
        self.assertFalse(result.committed)  # a dry run previews, it does not commit
        self.assertEqual(result.issues, [])

    @pytest.mark.integration
    def test_manual_lands_with_user_approval(self):
        self.set_trigger("manual")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = session_merge_branch(self.root, branch="feature", user_approved=True)

        self.assertFalse(result.merge_trigger_blocked)
        self.assertTrue(result.committed, result.issues)
        self.assertIn("branch-entry", self.log.read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_automatic_lands_without_a_flag(self):
        self.set_trigger("automatic")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = session_merge_branch(self.root, branch="feature")

        self.assertFalse(result.merge_trigger_blocked)
        self.assertTrue(result.committed, result.issues)


class MergeTriggerMcpTests(_RepoFixture):
    @pytest.mark.integration
    def test_mcp_integrate_declines_under_manual(self):
        self.set_trigger("manual")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertFalse(result["ok"])
        self.assertFalse(result["committed"])
        self.assertEqual(result["merge_trigger"], "manual")
        self.assertTrue(any("manual" in i for i in result["issues"]), result["issues"])
        self.assertIn("--user-approved", result["cli_command"])
        self.assertNotIn("branch-entry", self.log.read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_mcp_integrate_dry_run_previews_under_manual(self):
        self.set_trigger("manual")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature", "dry_run": True})

        self.assertTrue(result["ok"], result.get("issues"))
        self.assertFalse(result["committed"])

    @pytest.mark.integration
    def test_mcp_integrate_proceeds_under_automatic(self):
        self.set_trigger("automatic")
        self.branch_with_entry("feature", "2026-06-13 10:00", "mse_" + "b" * 16, "branch-entry")

        result = call_tool("memory_session_integrate", {"cwd": str(self.root), "branch": "feature"})

        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(result["committed"])


if __name__ == "__main__":
    unittest.main()
