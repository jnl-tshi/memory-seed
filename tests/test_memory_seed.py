import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import SEED_FILES, doctor, get_version, init_project


class MemorySeedTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "1.2")

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
            "memory-system-version: 1.2",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )

    def test_doctor_reports_missing_and_version_mismatched_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        gemini = cwd / "GEMINI.md"
        gemini.write_text(
            gemini.read_text(encoding="utf-8").replace("1.2", "1.1"),
            encoding="utf-8",
        )
        (cwd / "CLAUDE.md").unlink()

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertEqual(result.missing, ["CLAUDE.md"])
        self.assertEqual(
            result.version_mismatches,
            [{"file": "GEMINI.md", "expected": "1.2", "actual": "1.1"}],
        )


if __name__ == "__main__":
    unittest.main()
