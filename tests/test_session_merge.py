"""Integration previews carry the same cadence warning contract as branches."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, session_merge_branch


def _session(date: str, entry_id: str, branch: str) -> str:
    return "\n".join(
        [
            "---",
            "tags:",
            "  - session-log",
            f"session_date: {date}",
            "---",
            "",
            f"## {date} 09:00 - checkpoint",
            "",
            "```yaml",
            f"entry_id: {entry_id}",
            "user_initials: JN",
            "agent_type: codex",
            f"branch: {branch}",
            "```",
            "",
            "- work",
            "",
        ]
    )


class SessionMergeCadenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="mseed-session-merge-cadence-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Merge Test")
        self.git("config", "user.email", "merge@example.com")
        self.write_session("2026-09-04", "mse_0000000000000001", "main")
        self.git("add", "-A")
        self.git("commit", "-m", "base")
        self.git("switch", "-c", "codex/merge-cadence")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, text=True, capture_output=True
        )

    def write_session(self, date: str, entry_id: str, branch: str) -> None:
        target = self.root / MEMORY_DIR_NAME / "sessions" / date[:7] / f"{date}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_session(date, entry_id, branch), encoding="utf-8")

    def test_dry_run_exposes_high_file_cadence_before_integration(self) -> None:
        self.write_session("2026-09-05", "mse_0000000000000002", "codex/merge-cadence")
        for index in range(16):
            (self.root / f"change-{index}.txt").write_text("branch work\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "feature work")
        self.git("switch", "main")

        preview = session_merge_branch(
            cwd=self.root, branch="codex/merge-cadence", dry_run=True
        )

        self.assertEqual(preview.issues, [])
        self.assertIsNotNone(preview.cadence)
        self.assertIn("files=16 (high threshold 16)", preview.cadence.high_signals)
        self.assertTrue(preview.cadence_warnings)
        contract = preview.integration_preview_contract()
        self.assertEqual(contract["cadence"], preview.cadence.to_dict())
        self.assertEqual(contract["cadence_warnings"], preview.cadence_warnings)


if __name__ == "__main__":
    unittest.main()
