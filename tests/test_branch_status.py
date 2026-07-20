import shutil
import tempfile
import unittest
import pytest
from pathlib import Path


class BranchStatusTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _git_repo_with_commit(self, cwd, message="initial"):
        import subprocess

        subprocess.run(["git", "-C", str(cwd), "init", "-q"], check=True, capture_output=True)
        (cwd / "README.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-C", str(cwd),
                "-c", "user.name=test", "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "-m", message,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(cwd), "branch", "-M", "main"], check=True, capture_output=True)
        head = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        return head

    @pytest.mark.integration
    def test_branch_status_warns_on_dirty_main(self):
        from memory_seed.core import branch_status

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        (cwd / "README.txt").write_text("changed", encoding="utf-8")

        status = branch_status(cwd=cwd)

        self.assertTrue(status.is_git_repo)
        self.assertEqual(status.branch, "main")
        self.assertTrue(status.is_integration_branch)
        self.assertTrue(status.dirty)
        self.assertTrue(any("task branch" in warning for warning in status.warnings))
        self.assertIn("--no-ff", status.recommendation)

    @pytest.mark.integration
    def test_branch_status_recognizes_feature_branch(self):
        import subprocess
        from memory_seed.core import branch_status

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        subprocess.run(
            ["git", "-C", str(cwd), "switch", "-c", "feature-topic"],
            check=True,
            capture_output=True,
        )

        status = branch_status(cwd=cwd)

        self.assertTrue(status.is_git_repo)
        self.assertEqual(status.branch, "feature-topic")
        self.assertFalse(status.is_integration_branch)
        self.assertFalse(status.dirty)
        self.assertIn("merge --no-ff", status.recommendation)

    def test_branch_status_handles_non_git_directory(self):
        from memory_seed.core import branch_status

        cwd = self.make_project()

        status = branch_status(cwd=cwd)

        self.assertFalse(status.is_git_repo)
        self.assertIn("Not a Git repository", status.recommendation)


if __name__ == "__main__":
    unittest.main()
