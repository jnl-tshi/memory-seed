import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    check_session_links,
    migrate_session_month_layout,
    migrate_session_layout,
    session_target,
)


class SessionLayoutMigrationTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _per_user_session(self, cwd, date, user, *, fm_user=None, fm_date=None,
                          schema="2", hash_id=None, entries=("ms-aaaaaaaa",), extra_fm=""):
        d = cwd / MEMORY_DIR_NAME / "sessions" / date
        d.mkdir(parents=True, exist_ok=True)
        fm = ["---", f"schema_version: {schema}", f"session_date: {fm_date or date}"]
        if hash_id is not None:
            fm.append(f"hash_id: {hash_id}")
        fm += [f"user: {fm_user or user}", "created_at: 2026-06-13T00:00:00Z"]
        if extra_fm:
            fm.append(extra_fm)
        fm.append("---")
        body = []
        for eid in entries:
            body += ["", f"## {date} 09:00 - entry", "", "```yaml", f"entry_id: {eid}", "```", "", "- note"]
        (d / f"{user}.md").write_text("\n".join(fm + body) + "\n", encoding="utf-8")

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

    def _write_flat_session(self, cwd, date_str="2026-06-21"):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / f"{date_str}.md"
        path.write_text(
            "\n".join(
                [
                    "# 2026-06-21",
                    "",
                    "## 2026-06-21 09:00 - Jean entry",
                    "",
                    "```yaml",
                    "entry_id: ms-11111111",
                    "user_initials: JN",
                    "agent_type: codex",
                    "```",
                    "",
                    "- Jean body.",
                    "",
                    "## 2026-06-21 10:00 - Amina entry",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "user_initials: AM",
                    "agent_type: codex",
                    "```",
                    "",
                    "- Amina body.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def _write_old_diagram_sidecar(self, cwd, date_str="2026-06-21", entry_id="ms-11111111"):
        diagrams = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        path = diagrams / f"{date_str}.md"
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    f"diagram_date: {date_str}",
                    "---",
                    "",
                    f"## {date_str} 09:00 - Diagram",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
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
        return path

    def test_migrate_sessions_layout_dry_run_plans_without_writing(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, ["2026-06-21.md -> 2026-06/2026-06-21/amina.md", "2026-06-21.md -> 2026-06/2026-06-21/jean.md"])
        self.assertEqual(result.issues, [])
        self.assertTrue(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").exists())

    def test_migrate_sessions_layout_is_idempotent_after_apply(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        self._write_flat_session(cwd)

        migrate_session_layout(cwd=cwd)
        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, [])
        self.assertEqual(result.migrated, [])
        self.assertEqual(result.issues, [])

    def test_migrate_sessions_layout_blocks_unknown_initials_without_writing(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)
        text = flat.read_text(encoding="utf-8").replace("user_initials: AM", "user_initials: ZZ")
        flat.write_text(text, encoding="utf-8")

        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.migrated, [])
        self.assertTrue(result.issues)
        self.assertIn("ZZ", result.issues[0])
        self.assertTrue(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").exists())

    def test_migrate_sessions_layout_blocks_duplicate_participant_initials(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        cfg = cwd / MEMORY_DIR_NAME / "project.yaml"
        cfg.write_text(
            cfg.read_text(encoding="utf-8")
            + "  - slug: other-jean\n"
            + "    initials: JN\n",
            encoding="utf-8",
        )
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("duplicate participant initials JN", result.issues[0])
        self.assertTrue(flat.exists())

    def test_migrate_sessions_layout_appends_to_existing_user_file_when_safe(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        self._write_flat_session(cwd)
        existing = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True).path
        existing.write_text(existing.read_text(encoding="utf-8") + "## 2026-06-21 08:00 - Existing\n\n- Existing body.\n", encoding="utf-8")

        result = migrate_session_layout(cwd=cwd)

        self.assertTrue(result.changed)
        jean = existing.read_text(encoding="utf-8")
        self.assertIn("## 2026-06-21 08:00 - Existing", jean)
        self.assertIn("entry_id: ms-11111111", jean)
        self.assertEqual(jean.count("hash_id: msm_"), 1)

    def test_migrate_sessions_month_layout_dry_run_plans_without_writing(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        self._per_user_session(cwd, "2026-06-22", "jean", hash_id="msm_" + "c" * 32, entries=("ms-33333333",))
        diagram = self._write_old_diagram_sidecar(cwd)

        result = migrate_session_month_layout(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(
            result.planned,
            [
                "2026-06-21.md -> 2026-06/2026-06-21.md",
                "2026-06-22/jean.md -> 2026-06/2026-06-22/jean.md",
                "diagrams/2026-06-21.md -> diagrams/2026-06/2026-06-21.md",
            ],
        )
        self.assertEqual(result.issues, [])
        self.assertTrue(flat.exists())
        self.assertTrue(diagram.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md").exists())

    def test_migrate_sessions_month_layout_is_idempotent_after_apply(self):
        cwd = self.make_project()
        self._write_flat_session(cwd)

        migrate_session_month_layout(cwd=cwd)
        result = migrate_session_month_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, [])
        self.assertEqual(result.migrated, [])
        self.assertEqual(result.issues, [])

    def test_migrate_sessions_month_layout_appends_to_existing_target_when_safe(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "## 2026-06-21 08:00 - Existing\n\n```yaml\nentry_id: ms-existing\n```\n\n- Existing.\n",
            encoding="utf-8",
        )

        result = migrate_session_month_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertFalse(flat.exists())
        text = target.read_text(encoding="utf-8")
        self.assertIn("entry_id: ms-existing", text)
        self.assertIn("entry_id: ms-11111111", text)
        self.assertIn("entry_id: mse_0123456789abcdef", text)

    def test_migrate_sessions_month_layout_blocks_duplicate_target_entry_ids(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("## Existing\n\n```yaml\nentry_id: ms-11111111\n```\n", encoding="utf-8")

        result = migrate_session_month_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("ms-11111111", result.issues[0])
        self.assertTrue(flat.exists())

    def test_migrate_sessions_layout_apply_splits_entries_and_backs_up_source(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertFalse(flat.exists())
        self.assertEqual(result.migrated, ["2026-06/2026-06-21/amina.md", "2026-06/2026-06-21/jean.md"])
        self.assertEqual(len(result.backed_up), 1)
        backup = cwd / result.backed_up[0]
        self.assertTrue(backup.exists())
        jean = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").read_text(encoding="utf-8")
        amina = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "amina.md").read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", jean)
        self.assertIn("hash_id: msm_", jean)
        self.assertIn("user: jean", jean)
        self.assertIn("entry_id: ms-11111111", jean)
        self.assertNotIn("entry_id: mse_0123456789abcdef", jean)
        self.assertIn("entry_id: mse_0123456789abcdef", amina)
        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_migrate_sessions_month_layout_apply_moves_sources_and_backs_up(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        self._per_user_session(cwd, "2026-06-22", "jean", hash_id="msm_" + "c" * 32, entries=("ms-33333333",))
        diagram = self._write_old_diagram_sidecar(cwd)

        result = migrate_session_month_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertEqual(
            result.migrated,
            [
                "2026-06/2026-06-21.md",
                "2026-06/2026-06-22/jean.md",
                "diagrams/2026-06/2026-06-21.md",
            ],
        )
        self.assertFalse(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-22" / "jean.md").exists())
        self.assertFalse(diagram.exists())
        self.assertEqual(len(result.backed_up), 3)
        for backup in result.backed_up:
            self.assertTrue((cwd / backup).exists())
        moved_flat = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md").read_text(encoding="utf-8")
        moved_user = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-22" / "jean.md").read_text(encoding="utf-8")
        moved_diagram = (cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-06" / "2026-06-21.md").read_text(encoding="utf-8")
        self.assertIn("entry_id: ms-11111111", moved_flat)
        self.assertIn("hash_id: msm_" + "c" * 32, moved_user)
        self.assertIn("```mermaid", moved_diagram)
        self.assertTrue(check_session_links(cwd=cwd).ok)
