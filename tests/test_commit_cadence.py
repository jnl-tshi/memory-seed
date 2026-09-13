"""Calibrated branch-health checkpoint signals."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, commit_cadence, worktree_guard


def _session_entry(index: int, decisions: int) -> str:
    headings = "\n".join(
        f"#### D{ordinal} - decision {index}-{ordinal}\n\n- D: choice\n- R: reason"
        for ordinal in range(1, decisions + 1)
    )
    return (
        f"## 2026-09-05 {index + 9:02d}:00 - entry {index}\n\n"
        f"```yaml\nentry_id: mse_{index + 1:016x}\n```\n\n"
        f"### Decisions\n\n{headings}\n\n"
    )


class CommitCadenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="mseed-cadence-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Cadence Test")
        self.git("config", "user.email", "cadence@example.com")
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "base")
        self.git("switch", "-c", "codex/cadence")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, text=True, capture_output=True
        )

    def test_two_moderate_signals_warn_and_worktree_guard_exposes_them(self) -> None:
        session = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09" / "2026-09-05.md"
        session.parent.mkdir(parents=True)
        session.write_text(
            "".join((_session_entry(0, 2), _session_entry(1, 2), _session_entry(2, 1))),
            encoding="utf-8",
        )
        for index in range(7):
            (self.root / f"file-{index}.txt").write_text("changed\n", encoding="utf-8")

        cadence = commit_cadence(self.root)
        guard = worktree_guard(self.root, agent_type="codex", write_intent=True)

        # Memory/control-plane files still contribute authored-entry and
        # decision pressure, but must not inflate product-file or churn
        # pressure. Seven ordinary files plus this session is therefore seven.
        self.assertEqual((cadence.entries, cadence.decisions, cadence.files), (3, 5, 7))
        self.assertEqual(cadence.churn, 7)
        self.assertGreaterEqual(len(cadence.moderate_signals), 2)
        self.assertTrue(cadence.warnings)
        self.assertEqual(guard.cadence, cadence)
        self.assertTrue(any("Checkpoint cadence warning" in warning for warning in guard.warnings))

    def test_one_high_signal_warns(self) -> None:
        (self.root / "large.txt").write_text("x\n" * 750, encoding="utf-8")

        cadence = commit_cadence(self.root)

        self.assertIn("churn=750 (high threshold 750)", cadence.high_signals)
        self.assertTrue(cadence.warnings)


if __name__ == "__main__":
    unittest.main()
