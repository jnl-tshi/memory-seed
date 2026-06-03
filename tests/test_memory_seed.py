import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    SEED_FILES,
    compact_sessions,
    doctor,
    generate_session_entry_id,
    get_version,
    init_project,
    resolve_runtime,
    update_project,
)


class MemorySeedTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "2.4")

    def test_version_at_least_orders_versions_numerically(self):
        from memory_seed.core import _version_at_least

        self.assertTrue(_version_at_least("2.2", "2.2"))   # equal
        self.assertTrue(_version_at_least("2.3", "2.2"))   # newer
        self.assertTrue(_version_at_least("2.10", "2.9"))  # multi-digit, not string compare
        self.assertFalse(_version_at_least("2.1", "2.2"))  # older
        self.assertFalse(_version_at_least(None, "2.2"))   # missing -> treat as older
        self.assertFalse(_version_at_least("garbage", "2.2"))  # unparseable -> older

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
        self.assertFalse((cwd / ".memory-seed").exists())

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
        self.assertFalse((cwd / ".memory-seed" / "index.md").exists())
        self.assertFalse((cwd / ".memory-seed" / "policy.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "agent-rules.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "project-bootstrap.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "skills").is_dir())
        self.assertTrue((cwd / ".memory-seed" / "sessions").is_dir())
        self.assertTrue((cwd / ".memory-seed" / "archive").is_dir())
        self.assertFalse((cwd / ".AGENTS").exists())

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
        self.assertTrue(result.backed_up[0].startswith(".memory-seed/backups/"))
        self.assertEqual((cwd / result.backed_up[0]).read_text(encoding="utf-8"), "existing")
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(".memory-seed/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_init_force_preserves_existing_gitignore_when_adding_backup_ignore(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")
        (cwd / ".gitignore").write_text("dist/\n", encoding="utf-8")

        init_project(cwd=cwd, force=True)

        gitignore = (cwd / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("dist/\n", gitignore)
        self.assertEqual(gitignore.count(".memory-seed/backups/"), 1)

    def test_doctor_reports_missing_and_version_mismatched_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        gemini = cwd / "GEMINI.md"
        gemini.write_text(
            gemini.read_text(encoding="utf-8").replace(get_version(), "1.1"),
            encoding="utf-8",
        )
        (cwd / "CLAUDE.md").unlink()

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertFalse(result.control_plane_ok)
        self.assertFalse(result.bootstrap_complete)
        self.assertEqual(result.missing, ["CLAUDE.md"])
        self.assertEqual(
            sorted(result.bootstrap_missing),
            [".memory-seed/index.md", ".memory-seed/policy.md"],
        )
        self.assertEqual(
            result.version_mismatches,
            [{"file": "GEMINI.md", "expected": get_version(), "actual": "1.1"}],
        )

    def test_doctor_distinguishes_bootstrap_completeness_from_control_plane_health(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertTrue(result.control_plane_ok)
        self.assertFalse(result.bootstrap_complete)
        self.assertEqual(result.missing, [])
        self.assertEqual(result.version_mismatches, [])
        self.assertEqual(
            sorted(result.bootstrap_missing),
            [".memory-seed/index.md", ".memory-seed/policy.md"],
        )

        (cwd / ".memory-seed" / "index.md").write_text("# Runtime Index\n", encoding="utf-8")
        (cwd / ".memory-seed" / "policy.md").write_text("# Runtime Policy\n", encoding="utf-8")

        complete = doctor(cwd=cwd)

        self.assertTrue(complete.ok)
        self.assertTrue(complete.control_plane_ok)
        self.assertTrue(complete.bootstrap_complete)
        self.assertEqual(complete.bootstrap_missing, [])

    def test_session_entry_id_is_short_and_metadata_deterministic(self):
        first = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )
        second = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )

        self.assertEqual(first, second)
        self.assertRegex(first, r"^ms-[0-9a-f]{8}$")

    def test_reusable_seed_docs_are_self_contained(self):
        checked = [
            Path("AGENTS.md"),
            Path(".memory-seed/agent-rules.md"),
            Path(".memory-seed/project-bootstrap.md"),
            Path("memory_seed/seed/AGENTS.md"),
            Path("memory_seed/seed/.memory-seed/agent-rules.md"),
            Path("memory_seed/seed/.memory-seed/project-bootstrap.md"),
        ]
        forbidden = ("v1.4", "Memory Seed v1.4", "context.md", "style.md")

        for path in checked:
            content = path.read_text(encoding="utf-8")
            for term in forbidden:
                self.assertNotIn(term, content, f"{path} should not reference {term}")
            self.assertNotIn(".memory-seed/backups/", content)

    def test_update_refreshes_control_plane_and_preserves_generated_memory(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        (cwd / "AGENTS.md").write_text("old agent entry", encoding="utf-8")
        (cwd / "CLAUDE.md").unlink()
        (cwd / ".memory-seed" / "index.md").write_text(
            "project facts",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertIn("CLAUDE.md", result.created)
        self.assertTrue(any(path.endswith("/AGENTS.md") for path in result.backed_up))
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "CLAUDE.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (cwd / ".memory-seed" / "index.md").read_text(encoding="utf-8"),
            "project facts",
        )
        self.assertIn(".memory-seed/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_update_archives_replaced_control_plane_files_by_old_version(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(get_version(), "1.4"),
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        archived = cwd / ".memory-seed" / "archive" / "1.4" / "AGENTS.md"
        self.assertIn(".memory-seed/archive/1.4/AGENTS.md", result.archived)
        self.assertTrue(archived.exists())
        self.assertIn("memory-system-version: 1.4", archived.read_text(encoding="utf-8"))

    def test_update_does_not_downgrade_newer_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        # Simulate a project on a newer control plane than this tool ships.
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                f"memory-system-version: {get_version()}",
                "memory-system-version: 9.9",
            ),
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        # The newer file must be left untouched: no overwrite, no archive.
        self.assertIn("memory-system-version: 9.9", agents.read_text(encoding="utf-8"))
        self.assertNotIn("AGENTS.md", result.created)
        self.assertFalse(any("AGENTS.md" in archived for archived in result.archived))

    def test_update_archives_unknown_version_control_plane_files_under_timestamped_folder(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text("old unversioned agent entry", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        unknown_archives = list((cwd / ".memory-seed" / "archive").glob("unknown-*/AGENTS.md"))
        self.assertEqual(len(unknown_archives), 1)
        self.assertEqual(len(result.archived), 1)
        self.assertTrue(result.archived[0].startswith(".memory-seed/archive/unknown-"))
        self.assertEqual(
            unknown_archives[0].read_text(encoding="utf-8"),
            "old unversioned agent entry",
        )

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
        self.assertFalse((cwd / ".memory-seed" / "backups").exists())

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

    def test_update_refreshes_reusable_runtime_procedure_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        rules = cwd / ".memory-seed" / "agent-rules.md"
        rules.write_text("old runtime rules", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertIn(".memory-seed/agent-rules.md", result.created)
        self.assertTrue(
            any(path.endswith("/.memory-seed/agent-rules.md") for path in result.backed_up)
        )
        self.assertIn(f"memory-system-version: {get_version()}", rules.read_text(encoding="utf-8"))

    def test_control_plane_files_report_current_version(self):
        for seed_file in SEED_FILES:
            if not seed_file.source.suffix == ".md":
                continue
            content = seed_file.source.read_text(encoding="utf-8")
            self.assertIn(f"memory-system-version: {get_version()}", content, seed_file.destination)

    def test_repo_root_control_plane_files_match_version(self):
        # Guards the recurring release trap: the frontmatter version-bump sed is
        # scoped to memory_seed/seed/ and .memory-seed/, so it silently skips
        # this self-hosting repo's own root routing files (AGENTS/CLAUDE/GEMINI.md).
        # doctor() catches the drift at runtime; this pins it in the suite so a
        # missed root file fails CI instead of shipping (happened in 2.2.3 / 2.3.0).
        repo_root = Path(__file__).resolve().parent.parent
        expected = f"memory-system-version: {get_version()}"
        for seed_file in SEED_FILES:
            if not seed_file.source.suffix == ".md":
                continue
            live = repo_root / seed_file.destination
            self.assertTrue(live.exists(), f"missing live control-plane file: {seed_file.destination}")
            self.assertIn(expected, live.read_text(encoding="utf-8"), seed_file.destination)

    def test_seed_files_use_memory_seed_runtime(self):
        destinations = sorted(seed_file.destination for seed_file in SEED_FILES)

        self.assertEqual(
            destinations,
            [
                ".memory-seed/agent-rules.md",
                ".memory-seed/archive/.gitkeep",
                ".memory-seed/hooks/memory-retrieval-check.py",
                ".memory-seed/hooks/session-log-check.py",
                ".memory-seed/project-bootstrap.md",
                ".memory-seed/sessions/.gitkeep",
                ".memory-seed/skills/code_search.md",
                ".memory-seed/skills/data_architecture.md",
                ".memory-seed/skills/index.md",
                ".memory-seed/skills/local_compilation.md",
                ".memory-seed/skills/memory_consolidation.md",
                ".memory-seed/skills/memory_doctor.md",
                ".memory-seed/skills/release_publishing.md",
                ".memory-seed/skills/security_triage.md",
                "AGENTS.md",
                "CLAUDE.md",
                "GEMINI.md",
            ],
        )

    def test_resolve_runtime_prefers_nearest_memory_seed(self):
        cwd = self.make_project()
        root_runtime = cwd / MEMORY_DIR_NAME
        subproject = cwd / "apps" / "mobile"
        sub_runtime = subproject / MEMORY_DIR_NAME
        root_runtime.mkdir(parents=True)
        sub_runtime.mkdir(parents=True)
        nested = subproject / "src"
        nested.mkdir()

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, subproject.resolve())
        self.assertEqual(resolved.memory_dir, sub_runtime.resolve())
        self.assertFalse(resolved.legacy)

    def test_resolve_runtime_falls_back_to_legacy_agents(self):
        cwd = self.make_project()
        legacy = cwd / ".AGENTS"
        legacy.mkdir()
        nested = cwd / "packages" / "core"
        nested.mkdir(parents=True)

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, cwd.resolve())
        self.assertEqual(resolved.memory_dir, legacy.resolve())
        self.assertTrue(resolved.legacy)

    # --- compact tests ---

    def _make_sessions(self, cwd, entries):
        sessions_dir = cwd / MEMORY_DIR_NAME / "sessions"
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


class HookMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-hooks-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_retrieval_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("UserPromptSubmit", claude["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            claude["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("UserPromptSubmit", codex["hooks"])

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("UserPromptSubmit", gemini["hooks"])

        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        self.assertIn("sessionStart", cursor["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            cursor["hooks"]["sessionStart"][0]["command"],
        )

    def test_retrieval_hook_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_retrieval_hook,
            _merge_cursor_retrieval_hook,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_retrieval_hook(cwd))
        self.assertFalse(_merge_claude_retrieval_hook(cwd))
        self.assertTrue(_merge_cursor_retrieval_hook(cwd))
        self.assertFalse(_merge_cursor_retrieval_hook(cwd))

    def test_grouped_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_grouped_hook

        cwd = self.make_project()
        config = cwd / ".claude" / "settings.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --old-flag"}]}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py"
        result = _merge_grouped_hook(config, "UserPromptSubmit", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [
            h["command"]
            for g in data["hooks"]["UserPromptSubmit"]
            for h in g.get("hooks", [])
        ]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate

    def test_cursor_event_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_cursor_event_hook

        cwd = self.make_project()
        config = cwd / ".cursor" / "hooks.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "version": 1,
                "hooks": {
                    "sessionStart": [
                        {"command": "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor --old-flag"}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor"
        result = _merge_cursor_event_hook(config, "sessionStart", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [e["command"] for e in data["hooks"]["sessionStart"]]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate


class SessionLogOrderingHookTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-log-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-order-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed" / "sessions").mkdir(parents=True)
        return path

    def _run(self, cwd):
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout

    def test_out_of_order_entries_trigger_warning(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        (cwd / ".memory-seed" / "sessions" / f"{today}.md").write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("ORDER WARNING", self._run(cwd))

    def test_in_order_entries_do_not_trigger_order_warning(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        (cwd / ".memory-seed" / "sessions" / f"{today}.md").write_text(
            f"## {today} 01:45 - earlier\n\ntext\n\n## {today} 02:00 - later\n\ntext\n",
            encoding="utf-8",
        )
        self.assertNotIn("ORDER WARNING", self._run(cwd))

    def test_staleness_fires_when_no_session_file(self):
        cwd = self.make_project()
        out = self._run(cwd)
        self.assertIn("SESSION LOG REMINDER", out)

    def test_staleness_fires_when_last_entry_is_old(self):
        import datetime

        cwd = self.make_project()
        # Use a timestamp 30 min in the past (> the 15 min staleness threshold)
        # relative to the actual clock, so the test is not brittle near midnight
        # where a hardcoded early-morning time would read as a future entry.
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        (cwd / ".memory-seed" / "sessions" / f"{day}.md").write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("SESSION LOG REMINDER", self._run(cwd))

    def test_staleness_silent_when_recent_entry(self):
        import datetime

        cwd = self.make_project()
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        recent_time = now.strftime("%H:%M")
        (cwd / ".memory-seed" / "sessions" / f"{today}.md").write_text(
            f"## {today} {recent_time} - recent entry\n\ntext\n",
            encoding="utf-8",
        )
        self.assertNotIn("SESSION LOG REMINDER", self._run(cwd))

    def test_staleness_not_defeated_by_file_mtime(self):
        import datetime
        import os

        cwd = self.make_project()
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        session_file = cwd / ".memory-seed" / "sessions" / f"{day}.md"
        session_file.write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )
        # Touch the file to update mtime to now — simulating what git commit does.
        os.utime(session_file, None)
        # Staleness check should still fire because the entry heading is old.
        self.assertIn("SESSION LOG REMINDER", self._run(cwd))


class McpMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-mcp-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_mcp_for_claude(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Claude Code reads project-scope MCP servers from .mcp.json, not settings.json.
        data = json.loads((cwd / ".mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

        # The dead settings.json mcpServers block must not be created.
        settings = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertNotIn("mcpServers", settings)

    def test_init_installs_mcp_for_cursor(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".cursor" / "mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

    def test_init_installs_mcp_for_gemini(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_mcp,
            _merge_cursor_mcp,
            _merge_gemini_mcp,
            _merge_codex_mcp,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_mcp(cwd))
        self.assertFalse(_merge_claude_mcp(cwd))
        self.assertTrue(_merge_cursor_mcp(cwd))
        self.assertFalse(_merge_cursor_mcp(cwd))
        self.assertTrue(_merge_gemini_mcp(cwd))
        self.assertFalse(_merge_gemini_mcp(cwd))
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertFalse(_merge_codex_mcp(cwd))

    def test_mcp_merge_updates_stale_args(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "memory-seed-mcp", "args": ["--old"]}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        result = _merge_claude_mcp(cwd)
        self.assertTrue(result)

        data = json.loads(mcp_path.read_text())
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merge_preserves_unrelated_mcp_server(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"other-server": {"command": "other-cmd", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        _merge_claude_mcp(cwd)

        data = json.loads(mcp_path.read_text())
        self.assertIn("other-server", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["other-server"]["command"], "other-cmd")
        self.assertIn("memory-seed", data["mcpServers"])

    def test_strip_removes_legacy_claude_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A project seeded by 2.2.0-2.3.0: dead mcpServers block alongside a real hook.
        settings.write_text(
            json.dumps(
                {
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]},
                    "mcpServers": {
                        "memory-seed": {
                            "command": "uvx",
                            "args": ["--from", "memory-seed", "memory-seed-mcp", "--stdio"],
                            "type": "stdio",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertTrue(_strip_claude_settings_mcp(cwd))

        data = json.loads(settings.read_text())
        self.assertNotIn("mcpServers", data)  # dead block removed, empty parent pruned
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "keep-me")  # rest preserved
        self.assertFalse(_strip_claude_settings_mcp(cwd))  # idempotent

    def test_strip_preserves_foreign_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be deleted.
        settings.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "some-other-server", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertFalse(_strip_claude_settings_mcp(cwd))
        data = json.loads(settings.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "some-other-server")

    def test_gemini_mcp_merge_preserves_existing_hooks(self):
        import json

        cwd = self.make_project()
        gemini_path = cwd / ".gemini" / "settings.json"
        gemini_path.parent.mkdir(parents=True, exist_ok=True)
        gemini_path.write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing"}]}]}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_gemini_mcp
        _merge_gemini_mcp(cwd)

        data = json.loads(gemini_path.read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        self.assertIn("Stop", data["hooks"])
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "existing")

    def test_init_installs_mcp_for_codex(self):
        import tomllib

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Codex reads project-scope MCP servers from .codex/config.toml.
        data = tomllib.loads((cwd / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("memory-seed", data["mcp_servers"])
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_updates_stale_args(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        config_path.write_text(
            '[mcp_servers.memory-seed]\n'
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_preserves_existing_config(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Unrelated setting + comment + a foreign MCP server must all survive.
        config_path.write_text(
            "# my codex config\n"
            'model = "gpt-5-codex"\n'
            "\n"
            "[mcp_servers.other]\n"
            'command = "other-cmd"\n'
            'args = []\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        text = config_path.read_text(encoding="utf-8")
        self.assertIn("# my codex config", text)  # comment preserved
        data = tomllib.loads(text)
        self.assertEqual(data["model"], "gpt-5-codex")  # unrelated setting preserved
        self.assertEqual(data["mcp_servers"]["other"]["command"], "other-cmd")  # foreign server kept
        self.assertIn("memory-seed", data["mcp_servers"])  # ours appended

    def test_codex_mcp_merge_preserves_foreign_server_on_our_key(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be overwritten.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertFalse(_merge_codex_mcp(cwd))
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp_servers"]["memory-seed"]["command"], "some-other-server")

    def test_doctor_warns_when_codex_hooks_without_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)
        # Simulate a project that has Codex hooks but no MCP registration yet.
        (cwd / ".codex" / "config.toml").unlink()

        result = doctor(cwd=cwd)
        self.assertTrue(any("Codex" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # After re-registering, the warning clears.
        _merge_codex_mcp(cwd)
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_doctor_warns_on_stale_manual_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        init_project(cwd=cwd)  # healthy control plane, so the non-fatal check is meaningful
        config_path = cwd / ".codex" / "config.toml"
        # Ours but stale, written as dotted keys -> no standard header to anchor a
        # rewrite. Update must no-op, and doctor must NOT stay silent about it.
        config_path.write_text(
            'mcp_servers.memory-seed.command = "memory-seed-mcp"\n'
            'mcp_servers.memory-seed.args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-manual")
        self.assertFalse(_merge_codex_mcp(cwd))  # safe no-op, not a corruption

        result = doctor(cwd=cwd)
        self.assertTrue(any("non-standard TOML form" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # non-fatal

    def test_doctor_warns_on_stale_fixable_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Ours but stale, standard header form -> update can migrate it.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-fixable")
        result = doctor(cwd=cwd)
        self.assertTrue(any("outdated memory-seed MCP entry" in w for w in result.warnings))

        # update migrates it; warning then clears and status is current.
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_codex_mcp_status_current_and_foreign_are_quiet(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        # current
        _merge_codex_mcp(cwd)
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

        # foreign: a different server squatting our key
        (cwd / ".codex" / "config.toml").write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )
        self.assertEqual(_codex_mcp_status(cwd), "foreign")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))


class RetrievalCheckPathTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/memory-retrieval-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed").mkdir()
        return path

    def _run(self, cwd, extra_env=None):
        import subprocess
        import sys
        import os

        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_mcp_found_message_mentions_memory_search(self):
        import os
        import stat

        cwd = self.make_project()
        # Create a dummy memory-seed-mcp binary on PATH
        bin_dir = cwd / "bin"
        bin_dir.mkdir()
        fake_bin = bin_dir / "memory-seed-mcp"
        fake_bin.write_text("#!/usr/bin/env python3\n")
        fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IEXEC)

        out = self._run(cwd, extra_env={"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")})
        self.assertIn("memory_search", out)
        self.assertNotIn("uv tool install", out)

    def test_mcp_missing_message_mentions_install(self):
        cwd = self.make_project()
        out = self._run(cwd, extra_env={"PATH": ""})
        self.assertIn("uv tool install", out)
        self.assertNotIn("memory_search MCP tool", out)


class CliHelpTests(unittest.TestCase):
    def _run(self, argv):
        import contextlib
        import io

        from memory_seed.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_help_command_lists_all_commands(self):
        code, out = self._run(["help"])
        self.assertEqual(code, 0)
        for command in ("init", "update", "compact", "doctor", "version", "help"):
            self.assertIn(command, out)
        self.assertIn("Keeping Memory Seed current", out)

    def test_no_command_prints_help(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("Keeping Memory Seed current", out)


if __name__ == "__main__":
    unittest.main()
