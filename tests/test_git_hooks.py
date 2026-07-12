"""Memory-Entry trailer auto-stamping (P3): the prepare-commit-msg hook makes
the entry->commit join true by construction on ordinary commits, not just
tool-mediated merges. The hook is standalone (no memory_seed import) and never
blocks a commit; the shim installer is idempotent and refuses to clobber a
hook it did not write.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, PACKAGE_ROOT, install_git_hooks

HOOK_SCRIPT = PACKAGE_ROOT / "seed" / MEMORY_DIR_NAME / "hooks" / "prepare-commit-msg.py"

EID = "mse_" + "a" * 16
EID2 = "mse_37fpcovvuniqzlxk"  # non-Crockford letters: the wider id shape


def _entry(dt, eid):
    return f"## {dt} - entry\n\n```yaml\nentry_id: {eid}\n```\n\n- note\n"


class GitHookTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-hook-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions" / "2026-06"
        self.sessions.mkdir(parents=True, exist_ok=True)
        self._git("init", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "T")
        # Repo-tracked hook script, exactly as init would seed it.
        hooks_dir = self.cwd / MEMORY_DIR_NAME / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HOOK_SCRIPT, hooks_dir / "prepare-commit-msg.py")

    def _git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.cwd), *args], check=True, capture_output=True, text=True
        )

    def _last_message(self) -> str:
        return self._git("log", "-1", "--format=%B").stdout

    def test_installer_writes_shim_and_is_idempotent(self):
        first = install_git_hooks(self.cwd)
        second = install_git_hooks(self.cwd)

        self.assertTrue(any("installed" in action for action in first))
        self.assertTrue(any("already installed" in action for action in second))
        hook = self.cwd / ".git" / "hooks" / "prepare-commit-msg"
        self.assertIn("Installed by memory-seed", hook.read_text(encoding="utf-8"))

    def test_installer_refuses_to_clobber_a_foreign_hook(self):
        hook = self.cwd / ".git" / "hooks" / "prepare-commit-msg"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")

        actions = install_git_hooks(self.cwd)

        self.assertTrue(any("NOT installed" in action for action in actions))
        self.assertIn("echo custom", hook.read_text(encoding="utf-8"))

    def test_commit_carrying_an_entry_gets_the_trailer_end_to_end(self):
        install_git_hooks(self.cwd)
        (self.sessions / "2026-06-13.md").write_text(_entry("2026-06-13 09:00", EID), encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "docs: session entry")

        message = self._last_message()

        self.assertIn(f"Memory-Entry: {EID}", message)

    def test_existing_trailer_is_not_duplicated(self):
        install_git_hooks(self.cwd)
        (self.sessions / "2026-06-13.md").write_text(_entry("2026-06-13 09:00", EID), encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", f"docs: session entry\n\nMemory-Entry: {EID}")

        message = self._last_message()

        self.assertEqual(message.count(f"Memory-Entry: {EID}"), 1)

    def test_wider_id_shape_is_stamped(self):
        install_git_hooks(self.cwd)
        (self.sessions / "2026-06-13.md").write_text(_entry("2026-06-13 09:00", EID2), encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "docs: codex-shaped id")

        self.assertIn(f"Memory-Entry: {EID2}", self._last_message())

    def test_commit_without_session_changes_is_untouched(self):
        install_git_hooks(self.cwd)
        (self.cwd / "README.md").write_text("hello\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "docs: readme")

        self.assertNotIn("Memory-Entry:", self._last_message())

    def test_fixture_like_entry_ids_outside_session_tree_are_not_stamped(self):
        install_git_hooks(self.cwd)
        tests_dir = self.cwd / "tests"
        tests_dir.mkdir()
        (tests_dir / "fixture.md").write_text(_entry("2026-06-13 09:00", EID), encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "test: fixture with an entry_id line")

        self.assertNotIn("Memory-Entry:", self._last_message())


if __name__ == "__main__":
    unittest.main()
