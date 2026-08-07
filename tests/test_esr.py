"""`memory-seed esr` (P4): one read-only pass over the deterministic
end-of-turn checks. Every section reports even when clean, so a skipped step
is visible; only hard integrity failures affect the exit path (the report is
a preflight, not a gate).
"""

import shutil
import subprocess
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.esr import esr_report, format_esr_report

A = "mse_" + "a" * 16
B = "mse_" + "b" * 16


def _entry(dt, eid, *, topics=(), files=(), replaces=()):
    lines = [f"## {dt} - entry {eid[-4:]}", "", "```yaml", f"entry_id: {eid}"]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {t}" for t in topics)
    if replaces:
        lines.append("replaces:")
        lines.extend(f"  - {s}" for s in replaces)
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
        for section in ("Integrity", "Topics", "Lifecycle link gaps", "Integration mode", "Worktrees", "Seed twins", "Docs lifecycle"):
            self.assertIn(section, text)

    def test_docs_lifecycle_section_skips_without_docs_and_reports_errors_with(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # No docs/ at all -> skipped, honestly.
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertFalse(report.docs_checked)
        self.assertIn("No docs/ directory", format_esr_report(report))

        # A docs tree with a broken link -> surfaced in the section, but the
        # integrity contract holds: only links check fails the esr exit code.
        docs = self.cwd / "docs" / "2_Todo"
        docs.mkdir(parents=True)
        (docs / "a.md").write_text(
            "---\npriority: P1\nnext_action: x\n---\n\n[gone](../5_Completed/missing.md)\n",
            encoding="utf-8",
        )
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertTrue(report.docs_checked)
        self.assertFalse(report.docs_ok)
        self.assertTrue(any("broken-link" in e for e in report.docs_errors))
        self.assertTrue(report.integrity_ok)  # docs errors do not fail integrity
        self.assertIn("broken-link", format_esr_report(report))
        self.assertEqual(report.to_dict()["docs"]["ok"], False)

    def test_integration_mode_surfaced_defaulting_to_local_merge(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # No project.yaml -> default local-merge.
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertEqual(report.integration_mode, "local-merge")
        self.assertIn("local-merge", format_esr_report(report))
        self.assertEqual(report.to_dict()["integration_mode"], "local-merge")

        # Declared pr surfaces in the report and the formatted output.
        (self.cwd / MEMORY_DIR_NAME / "project.yaml").write_text("integration_mode: pr\n", encoding="utf-8")
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertEqual(report.integration_mode, "pr")
        self.assertIn("pr — integrate via push", format_esr_report(report))

    def test_integrity_failure_is_reported(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, replaces=["mse_" + "9" * 16]), encoding="utf-8"
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertFalse(report.integrity_ok)
        self.assertTrue(any("dangling-replaces" in issue for issue in report.integrity_issues))

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

    def test_open_link_stubs_are_counted_in_lifecycle_section(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A), encoding="utf-8"
        )
        sidecar = self.sessions / "links" / "2026-06" / "2026-06-01.md"
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-links",
                    "link_date: 2026-06-01",
                    "---",
                    "",
                    "## 2026-06-01 09:00 - pending classification",
                    "",
                    "```yaml",
                    f"entry_id: {A}",
                    "classify_pending: true",
                    "# candidates (evidence):",
                    "#   - mse_bbbbbbbbbbbbbbbb  # topics: retrieval",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertTrue(report.integrity_ok)
        self.assertEqual(report.open_link_stubs, 1)
        self.assertEqual(report.to_dict()["open_link_stubs"], 1)
        self.assertIn("Open classification stubs: 1.", text)

    def test_stub_backlog_reports_its_age_not_just_its_size(self):
        # A raw count reads as steady state; the oldest date is what shows a
        # backlog rotting. The link backlog cleared on 2026-08-07 had been
        # accumulating since 2026-07-21 and no report said so.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        (self.sessions / "2026-06-09.md").write_text(_entry("2026-06-09 09:00", B), encoding="utf-8")
        stub_dir = self.sessions / "links" / "2026-06"
        stub_dir.mkdir(parents=True)
        for day, entry_id in (("2026-06-09", B), ("2026-06-01", A)):
            (stub_dir / f"{day}.md").write_text(
                "\n".join(
                    [
                        "---",
                        "tags:",
                        "  - session-log-links",
                        f"link_date: {day}",
                        "---",
                        "",
                        f"## {day} 09:00 - pending classification",
                        "",
                        "```yaml",
                        f"entry_id: {entry_id}",
                        "classify_pending: true",
                        "```",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

        report = esr_report(cwd=self.cwd, session_date="2026-06-09")
        text = format_esr_report(report)

        self.assertEqual(report.open_link_stubs, 2)
        self.assertEqual(report.oldest_open_link_stub, "2026-06-01")
        self.assertEqual(report.to_dict()["oldest_open_link_stub"], "2026-06-01")
        self.assertIn("Corpus-wide, not just today, oldest 2026-06-01", text)

    def test_diagram_drift_is_counted_in_entries_not_just_dated(self):
        # A date alone reads as recent at a glance. The lapse this surfaces is a
        # RUN of entries with no diagram, which no single day's view shows - and
        # counting entries needs no judgement about which of them owed one.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        (self.sessions / "2026-06-09.md").write_text(
            "\n".join([_entry("2026-06-09 09:00", B), _entry("2026-06-09 10:00", "mse_" + "c" * 16)]),
            encoding="utf-8",
        )
        diagram = self.sessions / "diagrams" / "2026-06" / "2026-06-01.md"
        diagram.parent.mkdir(parents=True)
        diagram.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    "diagram_date: 2026-06-01",
                    "---",
                    "",
                    "## 2026-06-01 09:00 - flow",
                    "",
                    "```yaml",
                    f"entry_id: {A}",
                    "```",
                    "",
                    "```mermaid",
                    "flowchart TD",
                    "  A --> B",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-09")
        text = format_esr_report(report)

        self.assertEqual(report.last_diagram_date, "2026-06-01")
        self.assertEqual(report.entries_since_last_diagram, 2)
        self.assertEqual(report.to_dict()["diagrams"]["entries_since_last_sidecar"], 2)
        self.assertIn("last sidecar anywhere: 2026-06-01 (2 entries logged since)", text)

    def test_no_stub_backlog_prints_no_age_line(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(report.open_link_stubs, 0)
        self.assertIsNone(report.oldest_open_link_stub)
        self.assertNotIn("Corpus-wide, not just today", format_esr_report(report))

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

    @pytest.mark.integration
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

    @pytest.mark.integration
    def test_git_worktree_posture_surfaces_unregistered_physical_residue(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args, cwd=None):
            subprocess.run(["git", "-C", str(cwd or self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")
        registered = self.cwd / ".codex" / "worktrees" / "registered"
        git("worktree", "add", "-b", "feature-registered", str(registered))
        residue = self.cwd / ".codex" / "worktrees" / "deregistered-residue"
        residue.mkdir(parents=True)
        (residue / ".git").write_text("gitdir: missing-admin-entry\n", encoding="utf-8")

        # Run from the secondary checkout: ESR must still inspect the primary
        # checkout's physical agent-worktree namespaces.
        report = esr_report(cwd=registered, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertEqual([item.path for item in report.worktree_residues], [str(residue.resolve())])
        self.assertTrue(report.worktree_residues[0].git_file_present)
        self.assertEqual(report.to_dict()["worktrees"]["residues"][0]["namespace"], ".codex/worktrees")
        self.assertIn("ORPHAN RESIDUE CANDIDATE", text)
        self.assertNotIn(f"{registered}  [.codex/worktrees]  ORPHAN", text)


if __name__ == "__main__":
    unittest.main()
