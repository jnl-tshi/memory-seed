"""`memory-seed esr` (P4): one read-only pass over the deterministic
end-of-turn checks. Every section reports even when clean, so a skipped step
is visible; only hard integrity failures affect the exit path (the report is
a preflight, not a gate).
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.esr import esr_report, format_esr_report

A = "mse_" + "a" * 16
B = "mse_" + "b" * 16


def _entry(dt, eid, *, topics=(), files=(), supersedes=()):
    lines = [f"## {dt} - entry {eid[-4:]}", "", "```yaml", f"entry_id: {eid}"]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {t}" for t in topics)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {s}" for s in supersedes)
    lines += ["```", ""]
    lines += [f"- F: `{f}`" for f in files]
    lines += ["", "Body.", ""]
    return "\n".join(lines)


class EsrReportTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-esr-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def test_clean_corpus_reports_every_section_ok(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertTrue(report.integrity_ok)
        self.assertTrue(report.topics_ok)
        self.assertEqual(report.link_gaps, [])
        self.assertFalse(report.seed_twins_checked)
        # Sections print even when clean - a skipped step cannot hide.
        for section in ("Integrity", "Topics", "Lifecycle link gaps", "Worktrees", "Seed twins"):
            self.assertIn(section, text)

    def test_integrity_failure_is_reported(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, supersedes=["mse_" + "9" * 16]), encoding="utf-8"
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertFalse(report.integrity_ok)
        self.assertTrue(any("dangling-supersedes" in issue for issue in report.integrity_issues))

    def test_link_gaps_scoped_to_the_session_date(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-02")

        self.assertEqual([gap["entry_id"] for gap in report.link_gaps], [B])
        self.assertEqual(report.link_gaps[0]["candidates"][0]["entry_id"], A)
        # The other direction: nothing new on 06-01, so no gaps under that scope.
        self.assertEqual(esr_report(cwd=self.cwd, session_date="2026-06-01").link_gaps, [])

    def test_non_git_directory_reports_worktrees_unavailable(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertFalse(report.worktrees_available)
        self.assertIn("Not a git repository", format_esr_report(report))

    def test_seed_twin_drift_detected_in_dev_repo_shape(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        live = self.cwd / MEMORY_DIR_NAME / "skills"
        seed = self.cwd / "memory_seed" / "seed" / MEMORY_DIR_NAME / "skills"
        live.mkdir(parents=True)
        seed.mkdir(parents=True)
        (live / "end_of_turn.md").write_text("live version", encoding="utf-8")
        (seed / "end_of_turn.md").write_text("seed version", encoding="utf-8")
        # The registry may legitimately diverge (project-local persona skills).
        (live / "index.md").write_text("live registry + persona skills", encoding="utf-8")
        (seed / "index.md").write_text("seed registry", encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertTrue(report.seed_twins_checked)
        self.assertEqual(report.seed_twin_drift, ["end_of_turn.md: live and seed twin differ"])

    def test_git_worktree_posture_marks_merged_clean_as_stale_candidate(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args, cwd=None):
            subprocess.run(["git", "-C", str(cwd or self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")
        wt = self.cwd / ".claude" / "worktrees" / "wt-merged"
        git("worktree", "add", "-b", "feature-merged", str(wt))

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertTrue(report.worktrees_available)
        secondary = [w for w in report.worktrees if not w.is_primary]
        self.assertEqual(len(secondary), 1)
        self.assertEqual(secondary[0].branch, "feature-merged")
        self.assertEqual(secondary[0].ahead, 0)
        self.assertEqual(secondary[0].dirty, 0)
        self.assertTrue(secondary[0].stale_candidate)
        self.assertIn("STALE CANDIDATE", format_esr_report(report))


if __name__ == "__main__":
    unittest.main()
