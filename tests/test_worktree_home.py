import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from _git_helpers import run_git
from memory_seed.worktree_home import (
    LEASE_FILE,
    home_admin_dir,
    home_worktree_path,
    is_home_worktree,
    read_lease,
    touch_lease,
    worktree_home,
)


def _git(cwd, *args):
    return run_git(cwd, *args, timeout=60)


class _HomeRepoMixin:
    def make_repo(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-home-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        _git(path, "init", "-b", "main")
        _git(path, "config", "user.email", "t@example.com")
        _git(path, "config", "user.name", "T")
        (path / ".gitignore").write_text(".claude/worktrees/\n.codex/worktrees/\n", encoding="utf-8")
        (path / "README.md").write_text("seed\n", encoding="utf-8")
        _git(path, "add", "-A")
        _git(path, "commit", "-m", "init")
        return path

    def commit_in(self, worktree, name="work.txt"):
        (worktree / name).write_text("change\n", encoding="utf-8")
        _git(worktree, "add", "-A")
        result = _git(worktree, "commit", "-m", f"add {name}")
        self.assertEqual(result.returncode, 0, result.stderr)


class WorktreeHomeTests(_HomeRepoMixin, unittest.TestCase):
    """Real git repositories: the home lifecycle is git plumbing, so stubs would prove nothing."""

    # --- paths -----------------------------------------------------------------

    def test_home_path_uses_agent_namespace(self):
        repo = self.make_repo()
        self.assertEqual(home_worktree_path(repo, "claude"), repo.resolve() / ".claude" / "worktrees" / "home")
        self.assertEqual(home_worktree_path(repo, "codex"), repo.resolve() / ".codex" / "worktrees" / "home")

    def test_is_home_worktree_matches_only_home_folders(self):
        repo = self.make_repo()
        self.assertEqual(is_home_worktree(repo, repo / ".claude" / "worktrees" / "home"), "claude")
        self.assertEqual(is_home_worktree(repo, repo / ".codex" / "worktrees" / "jean" / "home"), "codex")
        self.assertIsNone(is_home_worktree(repo, repo / ".claude" / "worktrees" / "overflow-1234"))
        self.assertIsNone(is_home_worktree(repo, repo))

    # --- status / create -------------------------------------------------------

    def test_status_reports_missing_without_creating(self):
        repo = self.make_repo()
        result = worktree_home(repo, agent="claude", action="status")
        self.assertEqual(result.state, "missing")
        self.assertFalse(home_worktree_path(repo, "claude").exists())
        self.assertEqual(result.exit_code, 0)

    def test_park_creates_a_missing_home_detached_at_main(self):
        repo = self.make_repo()
        result = worktree_home(repo, agent="claude", action="park")
        home = home_worktree_path(repo, "claude")
        self.assertEqual(result.state, "parked", result.issues)
        self.assertTrue(home.exists())
        self.assertEqual(_git(home, "branch", "--show-current").stdout.strip(), "")
        self.assertEqual(
            _git(home, "rev-parse", "HEAD").stdout.strip(), _git(repo, "rev-parse", "main").stdout.strip()
        )

    # --- claim -----------------------------------------------------------------

    def test_claim_creates_home_writes_lease_and_checks_out_task_branch(self):
        repo = self.make_repo()
        result = worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        self.assertEqual(result.state, "claimed", result.issues)
        self.assertEqual(result.path, str(home))
        self.assertEqual(_git(home, "branch", "--show-current").stdout.strip(), "claude/fix/one")
        lease = read_lease(home)
        self.assertEqual(lease["session_id"], "s-1")
        self.assertEqual(lease["branch"], "claude/fix/one")

    def test_creating_a_home_keeps_the_primary_clean_without_touching_gitignore(self):
        repo = self.make_repo()
        (repo / ".gitignore").write_text("", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "no ignores")

        worktree_home(repo, agent="claude", action="park")

        self.assertEqual(_git(repo, "status", "--porcelain").stdout.strip(), "")

    def test_claim_rejects_branch_outside_agent_namespace(self):
        repo = self.make_repo()
        result = worktree_home(repo, agent="claude", action="claim", branch="feature-x", session="s-1")
        self.assertEqual(result.exit_code, 2)
        self.assertTrue(result.issues)

    def test_same_session_reclaim_is_a_no_op(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        again = worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        self.assertEqual(again.state, "claimed")
        self.assertEqual(again.exit_code, 0)

    @pytest.mark.integration
    def test_second_live_session_gets_an_overflow_worktree(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        second = worktree_home(repo, agent="claude", action="claim", branch="claude/fix/two", session="s-2")
        self.assertEqual(second.state, "busy")
        self.assertEqual(second.exit_code, 0)
        self.assertIsNotNone(second.overflow_path)
        overflow = Path(second.overflow_path)
        self.assertTrue(overflow.name.startswith("overflow-"))
        self.assertEqual(_git(overflow, "branch", "--show-current").stdout.strip(), "claude/fix/two")
        self.assertIsNone(is_home_worktree(repo, overflow))

    def _age_lease(self, home, minutes):
        admin = home_admin_dir(home)
        lease_path = admin / LEASE_FILE
        lease = json.loads(lease_path.read_text(encoding="utf-8"))
        old = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        lease["last_active"] = old
        lease_path.write_text(json.dumps(lease), encoding="utf-8")

    def test_stale_clean_unmerged_home_offers_resume(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        self.commit_in(home)
        self._age_lease(home, 600)

        offered = worktree_home(repo, agent="claude", action="claim", branch="claude/fix/two", session="s-2")
        self.assertEqual(offered.state, "stale-resumable")
        self.assertEqual(offered.exit_code, 2)

        resumed = worktree_home(repo, agent="claude", action="claim", session="s-2", resume=True)
        self.assertEqual(resumed.state, "claimed", resumed.issues)
        self.assertEqual(read_lease(home)["session_id"], "s-2")
        self.assertEqual(_git(home, "branch", "--show-current").stdout.strip(), "claude/fix/one")

    def test_stale_dirty_home_stops_for_the_user(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        (home / "uncommitted.txt").write_text("wip\n", encoding="utf-8")
        self._age_lease(home, 600)

        result = worktree_home(repo, agent="claude", action="claim", branch="claude/fix/two", session="s-2")
        self.assertEqual(result.state, "stale-dirty")
        self.assertEqual(result.exit_code, 3)
        self.assertTrue((home / "uncommitted.txt").exists(), "leftover work must never be discarded")

    # --- park / release ----------------------------------------------------------

    def test_park_refuses_an_unmerged_branch(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        self.commit_in(home_worktree_path(repo, "claude"))
        result = worktree_home(repo, agent="claude", action="park")
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.state, "claimed")

    @pytest.mark.integration
    def test_park_after_merge_detaches_and_releases_lease(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        self.commit_in(home)
        _git(repo, "merge", "--no-ff", "claude/fix/one", "-m", "merge")

        result = worktree_home(repo, agent="claude", action="park")
        self.assertEqual(result.state, "parked", result.issues)
        self.assertEqual(_git(home, "branch", "--show-current").stdout.strip(), "")
        self.assertIsNone(read_lease(home))

    def test_release_only_drops_the_lease(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        worktree_home(repo, agent="claude", action="release")
        self.assertIsNone(read_lease(home))
        self.assertEqual(_git(home, "branch", "--show-current").stdout.strip(), "claude/fix/one")

    def test_heartbeat_refreshes_the_lease_of_the_home_it_runs_in(self):
        from memory_seed.worktree_home import heartbeat

        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        self._age_lease(home, 600)
        import os
        import time

        lease_path = home_admin_dir(home) / LEASE_FILE
        os.utime(lease_path, (time.time() - 3600, time.time() - 3600))
        self.assertTrue(heartbeat(home))
        self.assertEqual(worktree_home(repo, agent="claude", action="status").state, "claimed")
        self.assertFalse(heartbeat(repo), "the primary checkout has no lease")

    def test_touch_lease_refreshes_only_the_owning_session(self):
        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/one", session="s-1")
        home = home_worktree_path(repo, "claude")
        self._age_lease(home, 600)
        self.assertFalse(touch_lease(home, "someone-else"))
        self.assertTrue(touch_lease(home, "s-1", min_interval_seconds=0))
        state = worktree_home(repo, agent="claude", action="status")
        self.assertEqual(state.state, "claimed")


class WorktreeHomeSurfaceTests(_HomeRepoMixin, unittest.TestCase):
    """CLI, MCP and guard surfaces drive and report the same lifecycle."""

    def test_guard_blocks_writes_in_a_parked_home_and_allows_a_claimed_one(self):
        from memory_seed.core import worktree_guard

        repo = self.make_repo()
        worktree_home(repo, agent="claude", action="park")
        home = home_worktree_path(repo, "claude")
        parked = worktree_guard(home, agent_type="claude", write_intent=True)
        self.assertEqual(parked.classification, "parked-home")
        self.assertTrue(parked.is_home)
        self.assertFalse(parked.safe_to_write)

        worktree_home(repo, agent="claude", action="claim", branch="claude/fix/g", session="s-1")
        claimed = worktree_guard(home, agent_type="claude", write_intent=True)
        self.assertEqual(claimed.classification, "owned-worktree")
        self.assertTrue(claimed.safe_to_write)

    def test_cli_claim_reports_claimed_json(self):
        import os
        import subprocess
        import sys

        repo = self.make_repo()
        claim = subprocess.run(
            [sys.executable, "-m", "memory_seed.cli", "worktree", "home", "--agent", "claude",
             "--claim", "--branch", "claude/fix/cli", "--session", "s-cli", "--json"],
            cwd=repo, capture_output=True, text=True, timeout=120,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        )
        self.assertEqual(claim.returncode, 0, claim.stderr)
        self.assertEqual(json.loads(claim.stdout)["state"], "claimed")

    def test_mcp_tool_reports_status(self):
        from memory_seed.mcp_server import call_tool

        repo = self.make_repo()
        payload = call_tool("memory_worktree_home", {"agent_type": "claude", "cwd": str(repo)})
        self.assertEqual(payload["state"], "missing")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
