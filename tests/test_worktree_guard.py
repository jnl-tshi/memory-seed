import shutil
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME


class WorktreeGuardTests(unittest.TestCase):
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
    def test_worktree_guard_passes_owned_and_blocks_foreign_namespace(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  namespaces:",
                    "    codex: .CODEX/WORKTREES",
                    "    claude: .claude/worktrees",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        codex_wt = cwd / ".codex" / "worktrees" / "task with spaces"
        claude_wt = cwd / ".claude" / "worktrees" / "task"
        codex_wt.parent.mkdir(parents=True)
        claude_wt.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "codex/task", str(codex_wt)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "claude/task", str(claude_wt)],
            check=True,
            capture_output=True,
        )

        owned = worktree_guard(cwd=codex_wt, agent_type="Codex", write_intent=True)
        foreign = worktree_guard(cwd=claude_wt, agent_type="codex", write_intent=True)

        self.assertTrue(owned.ok, owned)
        self.assertEqual(owned.classification, "owned-worktree")
        self.assertTrue(owned.safe_to_write)
        self.assertEqual(owned.actual_namespace_owner, "codex")
        self.assertFalse(foreign.ok)
        self.assertEqual(foreign.classification, "foreign-worktree")
        self.assertFalse(foreign.safe_to_write)
        self.assertEqual(foreign.actual_namespace_owner, "claude")

    @pytest.mark.integration
    def test_worktree_guard_root_checkout_requires_explicit_override_for_writes(self):
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)

        read_only = worktree_guard(cwd=cwd, agent_type="codex")
        blocked = worktree_guard(cwd=cwd, agent_type="codex", write_intent=True)
        allowed = worktree_guard(cwd=cwd, agent_type="codex", write_intent=True, allow_root_write=True)

        self.assertTrue(read_only.ok)
        self.assertEqual(read_only.classification, "root-checkout")
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.severity, "block")
        self.assertTrue(allowed.ok)
        self.assertEqual(allowed.classification, "root-checkout")

    @pytest.mark.integration
    def test_worktree_guard_unmanaged_write_policy_can_block(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  unmanaged_write_policy: block",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        unmanaged = cwd / "scratch worktrees" / "task"
        unmanaged.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "scratch/task", str(unmanaged)],
            check=True,
            capture_output=True,
        )

        status = worktree_guard(cwd=unmanaged, agent_type="codex", write_intent=True)

        self.assertFalse(status.ok)
        self.assertEqual(status.classification, "unmanaged-worktree")
        self.assertEqual(status.severity, "block")

    @pytest.mark.integration
    def test_worktree_guard_uses_project_namespace_overrides(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  namespaces:",
                    "    codex: custom spaces/codex",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        custom = cwd / "custom spaces" / "codex" / "task"
        custom.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "codex/custom-task", str(custom)],
            check=True,
            capture_output=True,
        )

        status = worktree_guard(cwd=custom, agent_type="codex", write_intent=True)

        self.assertTrue(status.ok, status)
        self.assertEqual(status.classification, "owned-worktree")
        self.assertEqual(status.expected_namespace, "custom spaces/codex")


if __name__ == "__main__":
    unittest.main()
