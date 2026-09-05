"""Task Packet commit-hook provenance and ordinary-entry cadence contracts."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, PACKAGE_ROOT, install_git_hooks


HOOK_SCRIPT = PACKAGE_ROOT / "seed" / MEMORY_DIR_NAME / "hooks" / "prepare-commit-msg.py"


def _entry(index: int) -> str:
    entry_id = f"mse_{index:016x}"
    return (
        f"## 2026-09-05 {index % 24:02d}:00 - entry {index}\n\n"
        f"```yaml\nentry_id: {entry_id}\n```\n\n- authored now\n\n"
    )


class CommitHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="mseed-provenance-hook-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Hook Test")
        self.git("config", "user.email", "hook@example.com")
        hook_dir = self.root / MEMORY_DIR_NAME / "hooks"
        hook_dir.mkdir(parents=True)
        shutil.copyfile(HOOK_SCRIPT, hook_dir / "prepare-commit-msg.py")
        install_git_hooks(self.root)

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=check,
            text=True,
            capture_output=True,
        )

    def last_message(self) -> str:
        return self.git("log", "-1", "--format=%B").stdout

    def test_active_packet_implements_is_stamped_without_history_lookup(self) -> None:
        key = "branch.main.memory-seed-task-packet-implements"
        self.git("config", "--local", "--add", key, "mse_aaaaaaaaaaaaaaaa:d2")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet implementation")

        message = self.last_message()
        self.assertIn("Memory-Implements: mse_aaaaaaaaaaaaaaaa:d2", message)
        self.assertNotIn("Memory-Entry:", message)

    def test_eleventh_new_entry_refuses_without_a_durable_bulk_reason(self) -> None:
        sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09"
        sessions.mkdir(parents=True)
        (sessions / "2026-09-05.md").write_text(
            "".join(_entry(index) for index in range(11)), encoding="utf-8"
        )
        self.git("add", "-A")

        rejected = self.git("commit", "-m", "docs: bulk entries", check=False)

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("more than 10 newly authored", rejected.stderr)
        self.git(
            "commit",
            "-m",
            "docs: approved bulk entries\n\nMemory-Bulk-Reason: User approved migration checkpoint.",
        )
        message = self.last_message()
        self.assertEqual(message.count("Memory-Entry:"), 11)
        self.assertIn("Memory-Bulk-Reason: User approved migration checkpoint.", message)


if __name__ == "__main__":
    unittest.main()
