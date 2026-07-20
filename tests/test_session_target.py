import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, session_target


class SessionTargetTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _write_participants(self, cwd):
        cfg = cwd / MEMORY_DIR_NAME / "project.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "participants:",
                    "  - slug: jean",
                    "    initials: JN",
                    "    display_name: Jean",
                    "  - slug: amina",
                    "    initials: AM",
                    "    display_name: Amina",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_session_target_uses_month_grouped_path_without_configured_user(self):
        cwd = self.make_project()
        (cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)

        target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md",
        )
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

    def test_session_target_uses_environment_user_before_local_config(self):
        import os
        from unittest.mock import patch

        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: amina\n", encoding="utf-8")
        self._write_participants(cwd)

        with patch.dict(os.environ, {"MEMORY_SEED_USER": "jean"}):
            target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(target.user, "jean")
        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md",
        )
        self.assertEqual(target.layout, "month-user")

    def test_session_target_stays_flat_with_fewer_than_two_participants(self):
        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: jean\n", encoding="utf-8")

        # No participants: file at all -> flat.
        target = session_target(cwd=cwd, date_str="2026-06-21")
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

        # Exactly one participant -> still flat; a configured user alone isn't
        # enough to fragment the log, since there's no second author to
        # collide with yet.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        target = session_target(cwd=cwd, date_str="2026-06-21")
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

    def test_session_target_switches_to_per_user_with_two_participants(self):
        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: jean\n", encoding="utf-8")
        self._write_participants(cwd)

        target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(target.user, "jean")
        self.assertEqual(target.layout, "month-user")

    def test_session_target_explicit_user_bypasses_participant_gate(self):
        cwd = self.make_project()

        target = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean")

        self.assertEqual(target.user, "jean")
        self.assertEqual(target.layout, "month-user")

    def test_session_target_create_initializes_per_user_file_once(self):
        cwd = self.make_project()

        target = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True)
        first = target.path.read_text(encoding="utf-8")
        target.path.write_text(first + "\n## 2026-06-21 12:00 - Existing\n\nbody\n", encoding="utf-8")
        session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True)

        text = target.path.read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", text)
        self.assertIn("session_date: 2026-06-21", text)
        self.assertIn("hash_id: msm_", text)
        self.assertIn("user: jean", text)
        self.assertIn("## 2026-06-21 12:00 - Existing", text)
        self.assertEqual(text.count("schema_version: 2"), 1)

    def test_session_target_rejects_invalid_user_slug(self):
        cwd = self.make_project()

        with self.assertRaises(ValueError):
            session_target(cwd=cwd, date_str="2026-06-21", explicit_user="Bad_User")

    def test_session_target_rejects_invalid_session_date(self):
        cwd = self.make_project()

        with self.assertRaises(ValueError):
            session_target(cwd=cwd, date_str="2026-13-40")


if __name__ == "__main__":
    unittest.main()
