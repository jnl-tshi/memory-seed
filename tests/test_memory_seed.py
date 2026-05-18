import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    SEED_FILES,
    compact_sessions,
    doctor,
    get_version,
    init_project,
    update_project,
)


class MemorySeedTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "1.4")

    def test_init_dry_run_reports_seed_files_without_writing(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(
            sorted(result.planned),
            sorted(seed_file.destination for seed_file in SEED_FILES),
        )
        self.assertFalse((cwd / "AGENTS.md").exists())
        self.assertFalse((cwd / ".AGENTS").exists())

    def test_init_dry_run_does_not_require_force_when_files_exist(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")

        result = init_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "existing")

    def test_init_writes_only_reusable_seed_files(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd)

        self.assertTrue(result.changed)
        for seed_file in SEED_FILES:
            self.assertTrue(
                (cwd / seed_file.destination).exists(),
                f"{seed_file.destination} should exist",
            )
        self.assertFalse((cwd / ".AGENTS" / "context.md").exists())
        self.assertFalse((cwd / ".AGENTS" / "index.md").exists())
        self.assertFalse((cwd / ".AGENTS" / "style.md").exists())
        self.assertFalse((cwd / ".AGENTS" / "sessions").exists())

    def test_init_refuses_to_overwrite_existing_files_without_force(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")

        with self.assertRaisesRegex(
            FileExistsError, r"Refusing to overwrite existing files: AGENTS\.md"
        ):
            init_project(cwd=cwd)

        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "existing")

    def test_init_force_backs_up_existing_files_before_replacement(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")

        result = init_project(cwd=cwd, force=True)

        self.assertTrue(result.changed)
        self.assertEqual(len(result.backed_up), 1)
        self.assertTrue(result.backed_up[0].startswith(".AGENTS/backups/"))
        self.assertEqual((cwd / result.backed_up[0]).read_text(encoding="utf-8"), "existing")
        self.assertIn(
            "memory-system-version: 1.4",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(".AGENTS/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_init_force_preserves_existing_gitignore_when_adding_backup_ignore(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")
        (cwd / ".gitignore").write_text("dist/\n", encoding="utf-8")

        init_project(cwd=cwd, force=True)

        gitignore = (cwd / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("dist/\n", gitignore)
        self.assertEqual(gitignore.count(".AGENTS/backups/"), 1)

    def test_doctor_reports_missing_and_version_mismatched_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        gemini = cwd / "GEMINI.md"
        gemini.write_text(
            gemini.read_text(encoding="utf-8").replace("1.4", "1.1"),
            encoding="utf-8",
        )
        (cwd / "CLAUDE.md").unlink()

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertEqual(result.missing, ["CLAUDE.md"])
        self.assertEqual(
            result.version_mismatches,
            [{"file": "GEMINI.md", "expected": "1.4", "actual": "1.1"}],
        )

    def test_update_refreshes_control_plane_and_preserves_generated_memory(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        (cwd / "AGENTS.md").write_text("old agent entry", encoding="utf-8")
        (cwd / "CLAUDE.md").unlink()
        (cwd / ".AGENTS" / "context.md").write_text("project facts", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertIn("CLAUDE.md", result.created)
        self.assertTrue(any(path.endswith("/AGENTS.md") for path in result.backed_up))
        self.assertIn(
            "memory-system-version: 1.4",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "memory-system-version: 1.4",
            (cwd / "CLAUDE.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (cwd / ".AGENTS" / "context.md").read_text(encoding="utf-8"),
            "project facts",
        )
        self.assertIn(".AGENTS/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_update_dry_run_reports_seed_files_without_writing(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("old agent entry", encoding="utf-8")

        result = update_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(result.backed_up, [])
        self.assertEqual(
            sorted(result.planned),
            sorted(seed_file.destination for seed_file in SEED_FILES),
        )
        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "old agent entry")

    def test_update_does_nothing_when_control_plane_is_current(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        result = update_project(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(result.backed_up, [])
        self.assertFalse((cwd / ".AGENTS" / "backups").exists())

    def test_update_uses_yaml_version_instead_of_full_file_comparison(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8") + "\nLocal same-version note.\n",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.backed_up, [])
        self.assertIn("Local same-version note.", agents.read_text(encoding="utf-8"))

    def test_control_plane_files_report_current_version(self):
        for seed_file in SEED_FILES:
            content = seed_file.source.read_text(encoding="utf-8")
            self.assertIn("memory-system-version: 1.4", content, seed_file.destination)

    # --- compact tests ---

    def _make_sessions(self, cwd, entries):
        sessions_dir = cwd / ".AGENTS" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in entries.items():
            (sessions_dir / filename).write_text(content, encoding="utf-8")

    def test_compact_returns_headings_from_recent_sessions(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## First heading\n\nSome text.\n\n## Second heading\n\nMore text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertEqual(result.headings[today], ["First heading", "Second heading"])
        self.assertIn("Some text.", result.full_text)
        self.assertEqual(result.date_range, (today, today))

    def test_compact_respects_day_filter(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n\nOld text.\n",
            "2099-12-31.md": "## Future entry\n\nFuture text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, ["2099-12-31.md"])
        self.assertNotIn("Old text.", result.full_text)

    def test_compact_all_includes_every_session(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n",
            "2099-12-31.md": "## Future entry\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(len(result.sessions_scanned), 2)
        self.assertIn("2020-01-01.md", result.sessions_scanned)
        self.assertIn("2099-12-31.md", result.sessions_scanned)

    def test_compact_empty_sessions_returns_empty_result(self):
        cwd = self.make_project()

        result = compact_sessions(cwd=cwd)

        self.assertEqual(result.sessions_scanned, [])
        self.assertEqual(result.headings, {})
        self.assertEqual(result.full_text, "")
        self.assertIsNone(result.date_range)

    def test_compact_ignores_non_date_filenames(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## Valid\n",
            "notes.md": "## Should be ignored\n",
            "readme.txt": "not a session",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertNotIn("Should be ignored", result.full_text)


if __name__ == "__main__":
    unittest.main()
