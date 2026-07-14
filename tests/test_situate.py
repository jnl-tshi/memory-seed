"""`memory-seed situate` (orientation preflight): a network-free, read-only
report of local git/version/session/worktree facts, so a session starts from
ground truth. Mirrors the esr preflight shape; the authoritative PyPI check lives
in the orientation routine/shims, never in this CLI.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.situate import format_situate_report, situate_report

A = "mse_" + "a" * 16
B = "mse_" + "b" * 16
C = "mse_" + "c" * 16


def _entry(dt, eid):
    return "\n".join([f"## {dt} - entry {eid[-4:]}", "", "```yaml", f"entry_id: {eid}", "```", "", "Body.", ""])


class SituateReportTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-situate-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def test_non_git_directory_fails_open(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = situate_report(cwd=self.cwd)
        text = format_situate_report(report)

        self.assertFalse(report.git_available)
        self.assertFalse(report.worktrees_available)
        self.assertIn("Not a git repository", text)
        # Every section prints even without git - a skipped step cannot hide.
        for section in ("## Git", "## Integration mode", "## Newest session entry", "## Version", "## Worktrees"):
            self.assertIn(section, text)

    def test_newest_session_resolved_across_layouts(self):
        # A legacy-flat older file plus a month-dir newer file: newest wins, and
        # the LAST entry heading in that file is reported (not the first).
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        month = self.sessions / "2026-07"
        month.mkdir()
        (month / "2026-07-05.md").write_text(
            _entry("2026-07-05 09:00", B) + _entry("2026-07-05 14:30", C), encoding="utf-8"
        )

        report = situate_report(cwd=self.cwd)

        self.assertEqual(report.newest_session_date, "2026-07-05")
        self.assertIn("2026-07-05", report.newest_session_path or "")
        self.assertEqual(report.newest_entry, "2026-07-05 14:30 - entry cccc")
        self.assertIn("do not rely on memory_search", format_situate_report(report))

    def test_no_sessions_reports_none(self):
        report = situate_report(cwd=self.cwd)
        self.assertIsNone(report.newest_session_path)
        self.assertIn("No session logs found", format_situate_report(report))

    def test_local_version_and_memory_seed_repo_detection(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # Generic project: version parsed, not flagged as the memory-seed repo.
        (self.cwd / "pyproject.toml").write_text(
            '[project]\nname = "widget"\nversion = "3.1.4"\n', encoding="utf-8"
        )
        report = situate_report(cwd=self.cwd)
        self.assertEqual(report.local_version, "3.1.4")
        self.assertFalse(report.is_memory_seed_repo)

        # The memory-seed source repo itself: flagged, with the unreleased-tranche note.
        (self.cwd / "pyproject.toml").write_text(
            '[project]\nname = "memory-seed"\nversion = "2.18.0"\n', encoding="utf-8"
        )
        report = situate_report(cwd=self.cwd)
        self.assertEqual(report.local_version, "2.18.0")
        self.assertTrue(report.is_memory_seed_repo)
        self.assertIn("memory-seed source repo", format_situate_report(report))

    def test_changelog_unreleased_detection(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # No CHANGELOG -> None (unknown).
        self.assertIsNone(situate_report(cwd=self.cwd).changelog_unreleased)

        # Non-empty Unreleased section -> True.
        (self.cwd / "CHANGELOG.md").write_text(
            "# Changelog\n\n## Unreleased\n\n- a new thing\n\n## 1.0.0 - 2026-01-01\n- old\n", encoding="utf-8"
        )
        self.assertTrue(situate_report(cwd=self.cwd).changelog_unreleased)

        # Unreleased header immediately followed by the next release -> False.
        (self.cwd / "CHANGELOG.md").write_text(
            "# Changelog\n\n## Unreleased\n\n## 1.0.0 - 2026-01-01\n- old\n", encoding="utf-8"
        )
        self.assertFalse(situate_report(cwd=self.cwd).changelog_unreleased)

    def test_git_state_branch_dirty_ahead(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args):
            subprocess.run(["git", "-C", str(self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")
        git("checkout", "-b", "feature-x")
        (self.cwd / "new.txt").write_text("x\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "work")
        (self.cwd / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

        report = situate_report(cwd=self.cwd)

        self.assertTrue(report.git_available)
        self.assertEqual(report.branch, "feature-x")
        self.assertEqual(report.dirty, 1)
        self.assertEqual(report.ahead, 1)
        self.assertEqual(report.ahead_ref, "main")  # no origin remote -> compares to local main
        self.assertIn("1 commit(s) ahead of main", format_situate_report(report))

    def test_module_stays_network_free(self):
        # Design invariant (advisor): the CLI never touches the network - the
        # authoritative PyPI check lives in the orientation routine/shims. Guard
        # it statically so a regression that adds a fetch is caught.
        import memory_seed.situate as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        for banned in ("urllib", "requests", "http.client", "urlopen", "socket"):
            self.assertNotIn(banned, src, f"situate must stay network-free; found reference to {banned}")


if __name__ == "__main__":
    unittest.main()
