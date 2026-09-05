"""Task Packet commit-hook provenance and ordinary-entry cadence contracts."""

import shutil
import subprocess
import tempfile
import unittest
import hashlib
import json
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
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        self.git("add", "base.txt")
        self.git("commit", "-m", "base")

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=check,
            text=True,
            capture_output=True,
        )

    def last_message(self) -> str:
        return self.git("log", "-1", "--format=%B").stdout

    def activate_packet_artifact(self, *, allowed_files: list[str], implements: list[str]) -> None:
        base = self.git("rev-parse", "HEAD").stdout.strip()
        packet = {
            "packet_schema": "memory-seed/task-packet",
            "packet_version": 1,
            "dispatch": {"execution": {"write_intent": "writing", "implements": implements, "allowed_files": allowed_files}},
            "runtime_binding": {"working_branch": "main", "worktree": str(self.root), "base_sha": base},
            "materialized_evidence": [{"id": reference, "kind": "decision"} for reference in implements],
        }
        identity = dict(packet)
        packet["fingerprint"] = "sha256:" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        payload = {"schema": "memory-seed/task-packet-activation", "version": 1, "packet": packet}
        token = hashlib.sha256(b"main").hexdigest()
        target = self.root / ".git" / "memory-seed" / "task-packets" / f"{token}.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    def test_config_alone_cannot_masquerade_as_packet_activation(self) -> None:
        key = "branch.main.memory-seed-task-packet-implements"
        self.git("config", "--local", "--add", key, "mse_aaaaaaaaaaaaaaaa:d2")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet implementation")

        message = self.last_message()
        self.assertNotIn("Memory-Implements:", message)
        self.assertNotIn("Memory-Entry:", message)

    def test_verified_packet_artifact_stamps_exact_implements_without_history_lookup(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d2"
        self.activate_packet_artifact(allowed_files=["change.txt"], implements=[reference])
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet implementation")

        self.assertIn(f"Memory-Implements: {reference}", self.last_message())

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

    def test_duplicate_new_entry_records_still_count_toward_the_cap(self) -> None:
        sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09"
        sessions.mkdir(parents=True)
        (sessions / "2026-09-05.md").write_text(_entry(0) * 11, encoding="utf-8")
        self.git("add", "-A")

        rejected = self.git("commit", "-m", "docs: duplicate bulk entries", check=False)

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("more than 10 newly authored", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
