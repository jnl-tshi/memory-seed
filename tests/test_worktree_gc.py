import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.worktree_gc import classify_worktrees, format_worktree_gc_report


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

    def test_clean_merged_owned_worktree_is_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        # Merge the branch so it is genuinely reachable from main.
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        # Classify from the repo root, so `wt` is not the active worktree.
        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "removable")
        self.assertEqual([i.path for i in report.removable], [str(wt.resolve())])

    def test_dirty_worktree_is_never_removable_even_when_merged(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/dirty", "claude/feature/dirty")
        _git(repo, "merge", "--no-ff", "claude/feature/dirty", "-m", "merge")
        (wt / "SCRATCH.txt").write_text("uncommitted\n", encoding="utf-8")

        report = classify_worktrees(repo, agent_type="claude")

        # The load-bearing rule: merged says nothing about the working tree.
        self.assertEqual(self.state_of(report, wt), "dirty")
        self.assertEqual(report.removable, ())

    def test_unmerged_worktree_is_not_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/wip", "claude/feature/wip")
        (wt / "work.txt").write_text("work\n", encoding="utf-8")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-m", "unmerged work")

        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "unmerged")
        self.assertEqual(report.removable, ())

    def test_other_agents_worktree_is_foreign(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".codex/worktrees/theirs", "codex/feature/theirs")
        _git(repo, "merge", "--no-ff", "codex/feature/theirs", "-m", "merge")

        report = classify_worktrees(repo, agent_type="claude")

        # Clean and merged, but not ours to remove.
        self.assertEqual(self.state_of(report, wt), "foreign")
        self.assertEqual(report.removable, ())

    def test_worktree_outside_any_namespace_is_foreign(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, "stray", "claude/feature/stray")
        _git(repo, "merge", "--no-ff", "claude/feature/stray", "-m", "merge")

        report = classify_worktrees(repo, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "foreign")

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

    def test_active_worktree_is_not_removable(self):
        repo = self.make_repo()
        wt = self.add_worktree(repo, ".claude/worktrees/here", "claude/feature/here")
        _git(repo, "merge", "--no-ff", "claude/feature/here", "-m", "merge")

        # Classify from *inside* wt: it is clean and merged, but it is where we
        # are running, so removing it would pull the floor out.
        report = classify_worktrees(wt, agent_type="claude")

        self.assertEqual(self.state_of(report, wt), "active")
        self.assertEqual(report.removable, ())

    def test_classification_is_deterministic(self):
        repo = self.make_repo()
        self.add_worktree(repo, ".claude/worktrees/done", "claude/feature/done")
        _git(repo, "merge", "--no-ff", "claude/feature/done", "-m", "merge")

        self.assertEqual(
            classify_worktrees(repo, agent_type="claude").to_dict(),
            classify_worktrees(repo, agent_type="claude").to_dict(),
        )

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


if __name__ == "__main__":
    unittest.main()
