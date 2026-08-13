"""`memory-seed situate` (orientation preflight): a network-free, read-only
report of local git/version/session/worktree facts, so a session starts from
ground truth. Mirrors the esr preflight shape; the authoritative PyPI check lives
in the orientation routine/shims, never in this CLI.
"""

import shutil
import subprocess
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.situate import (
    SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS,
    format_situate_report,
    situate_report,
)

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
        for section in ("## Location", "## Git", "## Integration mode", "## Newest session entry", "## Version", "## Worktrees"):
            self.assertIn(section, text)

    def test_newest_session_resolved_across_layouts(self):
        # A legacy-flat older file plus a month-dir newer file: newest wins, and
        # the LAST entry heading in that file is reported (not the first).
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        month = self.sessions / "2026-07"
        month.mkdir()
        newest = month / "2026-07-05.md"
        newest.write_text(
            _entry("2026-07-05 09:00", B) + _entry("2026-07-05 14:30", C), encoding="utf-8"
        )

        report = situate_report(cwd=self.cwd)

        self.assertEqual(report.newest_session_date, "2026-07-05")
        self.assertIn("2026-07-05", report.newest_session_path or "")
        self.assertEqual(report.newest_entry, "2026-07-05 14:30 - entry cccc")
        self.assertEqual(report.newest_session_entries, 2)
        self.assertEqual(
            report.newest_session_characters,
            len(newest.read_bytes().decode("utf-8")),
        )
        self.assertEqual(report.context_route, "direct")
        self.assertIn("Do not rely on memory_search", format_situate_report(report))

    def test_context_route_is_pinned_at_the_character_boundary(self):
        target = self.sessions / "2026-07-05.md"
        target.write_text("x" * SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS, encoding="utf-8")
        direct = situate_report(cwd=self.cwd)
        self.assertEqual(direct.newest_session_characters, 12_000)
        self.assertEqual(direct.context_route, "direct")

        target.write_text("x" * (SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS + 1), encoding="utf-8")
        summarize = situate_report(cwd=self.cwd)
        self.assertEqual(summarize.newest_session_characters, 12_001)
        self.assertEqual(summarize.context_route, "summarize")
        self.assertEqual(
            summarize.to_dict()["newest_session"]["compression_threshold_characters"],
            12_000,
        )

    def test_invalid_utf8_reports_unavailable_context_without_guessing_a_route(self):
        (self.sessions / "2026-07-05.md").write_bytes(b"\xff\xfe")

        report = situate_report(cwd=self.cwd)

        self.assertEqual(report.newest_session_bytes, 2)
        self.assertIsNone(report.newest_session_characters)
        self.assertIsNone(report.newest_session_entries)
        self.assertIsNone(report.context_route)
        self.assertEqual(report.newest_session_read_error, "invalid UTF-8")
        self.assertIn("session context: unavailable", format_situate_report(report))

    def test_active_user_selects_applicable_latest_file_and_reports_contributors(self):
        month_day = self.sessions / "2026-07" / "2026-07-05"
        month_day.mkdir(parents=True)
        (month_day / "jean.md").write_text(_entry("2026-07-05 10:00", B), encoding="utf-8")
        (month_day / "amina.md").write_text(_entry("2026-07-05 11:00", C), encoding="utf-8")

        report = situate_report(cwd=self.cwd, explicit_user="jean")

        self.assertTrue((report.newest_session_path or "").endswith("2026-07-05/jean.md"))
        self.assertEqual(report.newest_session_user, "jean")
        self.assertEqual(len(report.session_contributors), 1)
        self.assertEqual(report.session_contributors[0].user, "amina")
        self.assertEqual(report.session_contributors[0].entries, 1)

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

    @pytest.mark.integration
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

    @pytest.mark.integration
    def test_phantom_worktree_path_still_reports_the_primary_checkout(self):
        # The regression this section exists for. An agent is told it is working in
        # `<repo>/.claude/worktrees/<session>`, but the worktree was never created -
        # the directory is an ordinary nested folder. Git then walks UP out of it, so
        # every command silently addresses the shared primary checkout. Location must
        # name the checkout that git actually resolved, not the path it was called from.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args):
            subprocess.run(["git", "-C", str(self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")

        phantom = self.cwd / ".claude" / "worktrees" / "session-x"
        phantom.mkdir(parents=True)

        report = situate_report(cwd=phantom)
        text = format_situate_report(report)

        self.assertEqual(report.checkout_classification, "root-checkout")
        self.assertEqual(Path(report.checkout_path or "").resolve(), self.cwd.resolve())
        self.assertIn("PRIMARY checkout", text)
        # The line that lets an agent falsify a harness banner rather than believe it.
        self.assertIn("Measured from this cwd, not declared", text)

    @pytest.mark.integration
    def test_real_worktree_is_not_reported_as_the_primary_checkout(self):
        # The counterpart: a genuinely created worktree must classify as something
        # other than root-checkout, so the phantom assertion above is discriminating
        # rather than merely always-true.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args):
            subprocess.run(["git", "-C", str(self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")

        real = self.cwd / ".claude" / "worktrees" / "session-y"
        git("worktree", "add", "-b", "claude/fix/topic", str(real))

        report = situate_report(cwd=real)

        self.assertNotEqual(report.checkout_classification, "root-checkout")
        self.assertEqual(Path(report.checkout_path or "").resolve(), real.resolve())
        self.assertEqual(Path(report.repo_root or "").resolve(), self.cwd.resolve())
        self.assertNotIn("PRIMARY checkout", format_situate_report(report))

    @pytest.mark.integration
    def test_location_is_classified_from_cwd_not_from_the_resolved_runtime_root(self):
        # Pins the argument passed to worktree_guard. The two inputs only diverge
        # when the runtime dir is ABSENT from the worktree checkout - then
        # resolve_runtime walks up past the worktree to the primary checkout, and
        # classifying from that root reports a correctly-isolated agent as sitting
        # in the shared checkout. Measured: guard(cwd)=owned-worktree,
        # guard(root)=root-checkout. The repo's own .memory-seed is tracked, so
        # this case does not arise here today - which is exactly why it needs a
        # test rather than a comment.
        def git(*args):
            subprocess.run(["git", "-C", str(self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        # Runtime dir stays UNTRACKED, so the worktree checkout will not contain it.
        (self.cwd / ".gitignore").write_text(f"{MEMORY_DIR_NAME}/\n.claude/worktrees/\n", encoding="utf-8")
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        (self.cwd / "f.txt").write_text("x\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "base")

        real = self.cwd / ".claude" / "worktrees" / "session-z"
        git("worktree", "add", "-b", "claude/fix/topic", str(real))
        self.assertFalse((real / MEMORY_DIR_NAME).exists(), "fixture precondition: runtime absent from worktree")

        report = situate_report(cwd=real)

        # From cwd this is the worktree. From the resolved root it would be the
        # primary checkout - the regression this assertion catches.
        self.assertNotEqual(report.checkout_classification, "root-checkout")
        self.assertEqual(Path(report.checkout_path or "").resolve(), real.resolve())

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
