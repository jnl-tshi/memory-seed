import shutil
import subprocess
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.worktree_gc import (
    apply_worktree_gc,
    classify_worktrees,
    format_worktree_gc_apply,
    format_worktree_gc_report,
)


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


class WorktreeClassifyTests(unittest.TestCase):
    """Real git repos in a temp dir - the classifier is git-integration code, so
    fixtures that stub git would prove nothing about it."""

    def make_repo(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-wtgc-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        _git(path, "init", "-b", "main")
        _git(path, "config", "user.email", "t@example.com")
        _git(path, "config", "user.name", "T")
        (path / "README.md").write_text("seed\n", encoding="utf-8")
        _git(path, "add", "-A")
        _git(path, "commit", "-m", "init")
        return path

    def add_worktree(self, repo, relpath, branch):
        target = repo / relpath
        result = _git(repo, "worktree", "add", str(target), "-b", branch)
        self.assertEqual(result.returncode, 0, result.stderr)
        return target

    def state_of(self, report, path):
        resolved = str(Path(path).resolve())
        return next(i.state for i in report.classifications if i.path == resolved)

    def test_primary_worktree_is_root_and_never_removable(self):
        repo = self.make_repo()

        report = classify_worktrees(repo, agent_type="claude")

        root = report.classifications[0]
        self.assertEqual(root.state, "root")
        self.assertFalse(root.removable)

    @pytest.mark.integration
    def test_clean_merged_owned_worktree_is_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        # Merge the branch so it is genuinely reachable from main.
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        # Classify from the repo root, so `wt` is not the active worktree.
        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "removable")
        self.assertEqual([i.path for i in report.removable], [str(wt.resolve())])

    @pytest.mark.integration
    def test_dirty_worktree_is_never_removable_even_when_merged(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/dirty", "claude/feature/dirty")
        _git(repo, "merge", "--no-ff", "claude/feature/dirty", "-m", "merge")
        (wt / "SCRATCH.txt").write_text("uncommitted\n", encoding="utf-8")

        report = classify_worktrees(repo, agent_type="claude")

        # The load-bearing rule: merged says nothing about the working tree.
        self.assertEqual(self.state_of(report, wt), "dirty")
        self.assertEqual(report.removable, ())

    @pytest.mark.integration
    def test_unmerged_worktree_is_not_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/wip", "claude/feature/wip")
        (wt / "work.txt").write_text("work\n", encoding="utf-8")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-m", "unmerged work")

        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "unmerged")
        self.assertEqual(report.removable, ())

    @pytest.mark.integration
    def test_other_agents_worktree_is_foreign(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".codex/worktrees/theirs", "codex/feature/theirs")
        _git(repo, "merge", "--no-ff", "codex/feature/theirs", "-m", "merge")

        report = classify_worktrees(repo, agent_type="claude")

        # Clean and merged, but not ours to remove.
        self.assertEqual(self.state_of(report, wt), "foreign")
        self.assertEqual(report.removable, ())

    @pytest.mark.integration
    def test_worktree_outside_any_namespace_is_foreign(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, "stray", "claude/feature/stray")
        _git(repo, "merge", "--no-ff", "claude/feature/stray", "-m", "merge")

        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "foreign")

    @pytest.mark.integration
    def test_detached_head_fails_closed_to_unknown(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/detached", "claude/feature/detached")
        _git(repo, "merge", "--no-ff", "claude/feature/detached", "-m", "merge")
        head = _git(repo, "rev-parse", "HEAD").stdout.strip()
        _git(wt, "checkout", "--detach", head)

        report = classify_worktrees(repo, agent_type="claude")

        # No branch means merge status is unanswerable -> refuse, don't permit.
        self.assertEqual(self.state_of(report, wt), "unknown")
        self.assertEqual(report.removable, ())

    @pytest.mark.integration
    def test_active_worktree_is_not_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/here", "claude/feature/here")
        _git(repo, "merge", "--no-ff", "claude/feature/here", "-m", "merge")

        # Classify from *inside* wt: it is clean and merged, but it is where we
        # are running, so removing it would pull the floor out.
        report = classify_worktrees(wt, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "active")
        self.assertEqual(report.removable, ())

    @pytest.mark.integration
    def test_classification_is_deterministic(self):
        repo = self.make_repo()
        self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        self.assertEqual(
            classify_worktrees(repo, agent_type="claude").to_dict(),
            classify_worktrees(repo, agent_type="claude").to_dict(),
        )

    @pytest.mark.integration
    def test_report_removes_nothing(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        report = classify_worktrees(repo, agent_type="claude")
        text = format_worktree_gc_report(report)

        # It classified this removable - and left it entirely alone.
        self.assertEqual(self.state_of(report, wt), "removable")
        self.assertTrue(wt.exists())
        # git prints posix separators even on Windows; compare in that form.
        self.assertIn(wt.resolve().as_posix(), _git(repo, "worktree", "list").stdout)
        self.assertIn("nothing has been removed", text)

    @pytest.mark.integration
    def test_no_agent_scope_still_reports_owner_without_foreign_verdict(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".codex/worktrees/theirs", "codex/feature/theirs")
        _git(repo, "merge", "--no-ff", "codex/feature/theirs", "-m", "merge")

        report = classify_worktrees(repo, agent_type=None)

        # Without a scope, a namespaced worktree is not foreign, but its owner
        # is still reported so a caller can decide.
        item = next(i for i in report.classifications if i.path == str(wt.resolve()))
        self.assertEqual(item.namespace_owner, "codex")
        self.assertEqual(item.state, "removable")

    def test_non_git_directory_yields_empty_report(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-wtgc-nogit-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))

        report = classify_worktrees(path)

        self.assertEqual(report.classifications, ())
        self.assertIn("No worktrees found", format_worktree_gc_report(report))

    # --- apply / removal ---------------------------------------------------

    @pytest.mark.integration
    def test_apply_removes_a_removable_worktree_and_leaves_its_branch(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        result = apply_worktree_gc(repo, agent_type="claude")

        self.assertEqual([r.path for r in result.removed], [str(wt.resolve())])
        self.assertEqual(result.refused, ())
        self.assertFalse(wt.exists())
        self.assertNotIn(wt.resolve().as_posix(), _git(repo, "worktree", "list").stdout)
        # The branch is a separate object and must survive.
        self.assertIn("claude/feature/done", _git(repo, "branch").stdout)

    @pytest.mark.integration
    def test_apply_reclassifies_and_never_removes_a_dirty_worktree(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/dirty", "claude/feature/dirty")
        _git(repo, "merge", "--no-ff", "claude/feature/dirty", "-m", "merge")
        (wt / "SCRATCH.txt").write_text("uncommitted\n", encoding="utf-8")

        result = apply_worktree_gc(repo, agent_type="claude")

        # A stale "removable" verdict must never be trusted; apply reclassifies.
        self.assertEqual(result.removed, ())
        self.assertTrue(wt.exists())

    @pytest.mark.integration
    def test_apply_never_touches_another_agents_worktree(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".codex/worktrees/theirs", "codex/feature/theirs")
        _git(repo, "merge", "--no-ff", "codex/feature/theirs", "-m", "merge")

        result = apply_worktree_gc(repo, agent_type="claude")

        self.assertEqual(result.removed, ())
        self.assertTrue(wt.exists())

    @pytest.mark.integration
    def test_apply_retries_a_locked_worktree_then_refuses_without_raw_deletion(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/locked", "claude/feature/locked")
        _git(repo, "merge", "--no-ff", "claude/feature/locked", "-m", "merge")

        # Simulate the OneDrive lock the remover exists for -- it cannot be
        # summoned on demand, so inject a remover that always reports it locked.
        calls = {"n": 0}

        def always_locked(root, target):
            calls["n"] += 1
            return 1, "fatal: ... : Permission denied (locked)"

        result = apply_worktree_gc(
            repo, agent_type="claude", max_attempts=3, remover=always_locked
        )

        # Bounded retry: exactly max_attempts, then refuse.
        self.assertEqual(calls["n"], 3)
        self.assertEqual(result.removed, ())
        self.assertEqual(len(result.refused), 1)
        self.assertEqual(result.refused[0].attempts, 3)
        self.assertIn("denied", result.refused[0].detail.lower())
        # The guarantee: a refused removal leaves the worktree entirely intact.
        # There is no raw-filesystem fallback, so the directory still exists.
        self.assertTrue(wt.exists())
        self.assertIn("left intact", format_worktree_gc_apply(result))

    @pytest.mark.integration
    def test_apply_does_not_retry_a_non_lock_failure(self):
        repo = self.make_repo()
        self.add_worktree(repo, ".claude/worktrees/x", "claude/feature/x")
        _git(repo, "merge", "--no-ff", "claude/feature/x", "-m", "merge")

        calls = {"n": 0}

        def hard_fail(root, target):
            calls["n"] += 1
            return 1, "fatal: some other git error"

        result = apply_worktree_gc(
            repo, agent_type="claude", max_attempts=5, remover=hard_fail
        )

        # A non-lock failure is not retryable -- fail fast, don't spin 5 times.
        self.assertEqual(calls["n"], 1)
        self.assertEqual(len(result.refused), 1)

    def test_apply_on_nothing_removable_is_a_clean_noop(self):
        repo = self.make_repo()  # only the primary worktree exists

        result = apply_worktree_gc(repo, agent_type="claude")

        self.assertEqual(result.removed, ())
        self.assertEqual(result.refused, ())
        self.assertIn("No removable worktree", format_worktree_gc_apply(result))


if __name__ == "__main__":
    unittest.main()
