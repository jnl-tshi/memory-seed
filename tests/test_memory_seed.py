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
    iter_session_documents,
    resolve_runtime,
    session_target,
    update_project,
)


class MemorySeedTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "2.11")

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
        # .AGENTS is the legacy directory. On case-insensitive filesystems (Windows),
        # it resolves to the same path as our new .agents/ folder. Verify via resolve_runtime
        # that the active runtime is .memory-seed/, not the legacy .AGENTS/ fallback.
        from memory_seed.core import resolve_runtime
        runtime = resolve_runtime(cwd)
        self.assertFalse(runtime.legacy)
        # .agents/ persona templates are seeded; registry is bootstrap-generated (absent after bare init)
        self.assertTrue((cwd / ".agents" / "README.md").exists())
        self.assertTrue((cwd / ".agents" / "developer.md").exists())
        self.assertTrue((cwd / ".agents" / "solo-founder.md").exists())
        self.assertFalse((cwd / ".agents" / "_registry.yaml").exists())

    def test_init_merges_into_foreign_routing_file_without_force(self):
        # A pre-existing foreign entry-point file (no frontmatter, e.g. a host's
        # own AGENTS.md) no longer blocks init: we inject our routing block and
        # leave the host's content intact, never overwrite.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost content\n", encoding="utf-8")

        result = init_project(cwd=cwd)

        self.assertTrue(result.changed)
        text = (cwd / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("host content", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertIn("AGENTS.md", result.created)
        # No backup/overwrite of a foreign file.
        self.assertEqual(result.backed_up, [])

    def test_init_force_does_not_clobber_foreign_routing_file(self):
        # --force does not license destroying host content: a foreign routing
        # file is still merged, not backed up + overwritten.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost content\n", encoding="utf-8")

        result = init_project(cwd=cwd, force=True)

        text = (cwd / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("host content", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertEqual(result.backed_up, [])

    def test_init_force_backs_up_existing_owned_files_before_replacement(self):
        # An owned routing file (carries our frontmatter) is the case --force
        # backs up + replaces wholesale.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold owned entry\n", encoding="utf-8"
        )

        result = init_project(cwd=cwd, force=True)

        self.assertTrue(result.changed)
        self.assertEqual(len(result.backed_up), 1)
        self.assertTrue(result.backed_up[0].startswith(".memory-seed/backups/"))
        self.assertIn("old owned entry", (cwd / result.backed_up[0]).read_text(encoding="utf-8"))
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(".memory-seed/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_init_force_preserves_existing_gitignore_when_adding_backup_ignore(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold owned entry\n", encoding="utf-8"
        )
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
        # Owned (frontmatter) but old: the case update backs up + replaces wholesale.
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold agent entry\n", encoding="utf-8"
        )
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

    def test_update_merges_into_foreign_routing_file_without_clobbering(self):
        # Replaces the retired "versionless -> archive + overwrite" behavior:
        # a foreign (host-owned, no-frontmatter) entry-point file is now merged,
        # never destroyed. This is the fail-safe direction when ownership is
        # unprovable.
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text("# HyperFrames Project\n\nhost rules here\n", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        text = agents.read_text(encoding="utf-8")
        self.assertIn("host rules here", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertIn("AGENTS.md", result.created)
        # Foreign file is not archived/overwritten.
        self.assertEqual(result.archived, [])
        self.assertFalse(list((cwd / ".memory-seed" / "archive").glob("unknown-*/AGENTS.md")))

    def test_update_resyncs_existing_routing_block_in_place(self):
        # The "second merge": a foreign file already carrying an old routing block
        # has only that block replaced in place; host content is untouched and
        # there is exactly one block.
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            "# HyperFrames Project\n\nhost rules here\n\n"
            "<!-- BEGIN memory-seed v=2.7 (managed block) -->\n"
            "stale routing text\n"
            "<!-- END memory-seed -->\n",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        text = agents.read_text(encoding="utf-8")
        self.assertIn("host rules here", text)
        self.assertNotIn("stale routing text", text)
        self.assertIn("agent-rules.md", text)  # current block body
        self.assertEqual(text.count("<!-- BEGIN memory-seed"), 1)
        self.assertEqual(text.count("<!-- END memory-seed -->"), 1)
        self.assertIn("AGENTS.md", result.created)

    def test_update_foreign_routing_merge_is_idempotent(self):
        # Once the current block is present, a second update reports no change
        # for that file (content-equality gate, like the JSON merges).
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text("# HyperFrames Project\n\nhost rules here\n", encoding="utf-8")

        update_project(cwd=cwd)
        before = agents.read_text(encoding="utf-8")
        result = update_project(cwd=cwd)

        self.assertEqual(agents.read_text(encoding="utf-8"), before)
        self.assertNotIn("AGENTS.md", result.created)

    def test_merge_routing_stanza_resyncs_on_body_change_only(self):
        # The no-churn guarantee: the block is rewritten only when its body
        # differs, not on a bare version bump (the block carries no version).
        from memory_seed.core import _merge_routing_stanza

        cwd = self.make_project()
        f = cwd / "HOST.md"
        f.write_text("# Host\n\nhost content\n", encoding="utf-8")

        self.assertTrue(_merge_routing_stanza(f))            # injected
        self.assertFalse(_merge_routing_stanza(f))           # identical -> no write
        # A different stanza body forces an in-place re-sync.
        changed = "<!-- BEGIN memory-seed -->\nnew body\n<!-- END memory-seed -->"
        self.assertTrue(_merge_routing_stanza(f, changed))
        self.assertFalse(_merge_routing_stanza(f, changed))
        self.assertIn("host content", f.read_text(encoding="utf-8"))

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
            if seed_file.destination.startswith(".agents/"):
                continue  # agent personas are project-local, not version-tracked control plane
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
            if seed_file.destination.startswith(".agents/"):
                continue  # agent personas are project-local, not version-tracked control plane
            live = repo_root / seed_file.destination
            self.assertTrue(live.exists(), f"missing live control-plane file: {seed_file.destination}")
            self.assertIn(expected, live.read_text(encoding="utf-8"), seed_file.destination)

    def test_seed_files_use_memory_seed_runtime(self):
        destinations = sorted(seed_file.destination for seed_file in SEED_FILES)

        self.assertEqual(
            destinations,
            [
                ".agents/README.md",
                ".agents/content-creator.md",
                ".agents/copywriter.md",
                ".agents/developer.md",
                ".agents/researcher.md",
                ".agents/sales-rep.md",
                ".agents/solo-founder.md",
                ".claude/commands/esr.md",
                ".gemini/commands/esr.toml",
                ".github/copilot-instructions.md",
                ".memory-seed/agent-rules.md",
                ".memory-seed/archive/.gitkeep",
                ".memory-seed/hooks/memory-retrieval-check.py",
                ".memory-seed/hooks/session-log-check.py",
                ".memory-seed/hooks/session-start-context.py",
                ".memory-seed/project-bootstrap.md",
                ".memory-seed/sessions/.gitkeep",
                ".memory-seed/skills/code_search.md",
                ".memory-seed/skills/copywriter-conversion.md",
                ".memory-seed/skills/data_architecture.md",
                ".memory-seed/skills/document_ingestion.md",
                ".memory-seed/skills/index.md",
                ".memory-seed/skills/local_compilation.md",
                ".memory-seed/skills/memory_consolidation.md",
                ".memory-seed/skills/memory_doctor.md",
                ".memory-seed/skills/office_document_editing.md",
                ".memory-seed/skills/release_publishing.md",
                ".memory-seed/skills/security_triage.md",
                "AGENTS.md",
                "CLAUDE.md",
                "GEMINI.md",
            ],
        )

    def test_update_does_not_overwrite_customized_agent_persona(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        persona = cwd / ".agents" / "developer.md"
        persona.write_text(persona.read_text(encoding="utf-8") + "\n## Custom Section\nProject-specific rule.\n", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertNotIn(".agents/developer.md", result.created)
        self.assertIn("Custom Section", persona.read_text(encoding="utf-8"))

    def test_init_installs_esr_command_for_claude_and_gemini_only(self):
        # The /esr end-of-session command ships only for agents with a verified
        # repo-level command mechanism; Codex/Cursor invoke the routine via
        # agent-rules.md instead.
        for agents, claude_cmd, gemini_cmd in (
            ({"claude"}, True, False),
            ({"gemini"}, False, True),
            ({"claude", "gemini"}, True, True),
            ({"codex"}, False, False),
        ):
            cwd = self.make_project()
            init_project(cwd=cwd, agents=agents)
            self.assertEqual((cwd / ".claude" / "commands" / "esr.md").exists(), claude_cmd, agents)
            self.assertEqual((cwd / ".gemini" / "commands" / "esr.toml").exists(), gemini_cmd, agents)

    def test_update_keeps_gemini_command_deploy_once_but_refreshes_claude_command(self):
        # The Gemini TOML command cannot carry a version marker, so it is
        # deploy-once (never overwritten); the Claude .md command is version-
        # tracked and refreshes on update.
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "gemini"})
        gem = cwd / ".gemini" / "commands" / "esr.toml"
        claude = cwd / ".claude" / "commands" / "esr.md"
        gem.write_text(gem.read_text(encoding="utf-8") + "\n# local tweak\n", encoding="utf-8")
        claude.write_text("stale claude command", encoding="utf-8")

        result = update_project(cwd=cwd)

        # Gemini command preserved (deploy-once); Claude command refreshed.
        self.assertIn("# local tweak", gem.read_text(encoding="utf-8"))
        self.assertNotIn(".gemini/commands/esr.toml", result.created)
        self.assertIn(".claude/commands/esr.md", result.created)
        self.assertIn(f"memory-system-version: {get_version()}", claude.read_text(encoding="utf-8"))

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
            path = sessions_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_iter_session_documents_discovers_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy\n",
            "2026-06-21/jean.md": "## Jean\n",
            "2026-06-21/amina.md": "## Amina\n",
            "2026-06-21/README.md": "## Not a user\n",
            "2026-06-21/Bad_User.md": "## Invalid slug\n",
            "not-a-date/theo.md": "## Invalid date\n",
            "2026-06-22.md/readme.md": "## Invalid layout\n",
        })

        docs = list(iter_session_documents(cwd / MEMORY_DIR_NAME / "sessions"))

        self.assertEqual(
            [(doc.session_date, doc.user, doc.layout, doc.path.name) for doc in docs],
            [
                ("2026-06-20", None, "legacy-flat", "2026-06-20.md"),
                ("2026-06-21", "amina", "per-user-day", "amina.md"),
                ("2026-06-21", "jean", "per-user-day", "jean.md"),
            ],
        )

    def test_session_target_uses_legacy_path_without_configured_user(self):
        cwd = self.make_project()
        (cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)

        target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-21.md",
        )
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "legacy-flat")

    def test_session_target_uses_environment_user_before_local_config(self):
        import os
        from unittest.mock import patch

        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: amina\n", encoding="utf-8")

        with patch.dict(os.environ, {"MEMORY_SEED_USER": "jean"}):
            target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(target.user, "jean")
        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-21" / "jean.md",
        )
        self.assertEqual(target.layout, "per-user-day")

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

    def test_compact_all_includes_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy entry\n\nLegacy text.\n",
            "2026-06-21/jean.md": "## Jean entry\n\nJean text.\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(result.sessions_scanned, ["2026-06-20.md", "2026-06-21/jean.md"])
        self.assertEqual(result.headings["2026-06-20"], ["Legacy entry"])
        self.assertEqual(result.headings["2026-06-21/jean.md"], ["Jean entry"])
        self.assertIn("Legacy text.", result.full_text)
        self.assertIn("Jean text.", result.full_text)
        self.assertEqual(result.date_range, ("2026-06-20", "2026-06-21"))

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

        # Gemini's prompt-submit event is BeforeAgent; it has no UserPromptSubmit.
        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("BeforeAgent", gemini["hooks"])
        self.assertNotIn("UserPromptSubmit", gemini["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            gemini["hooks"]["BeforeAgent"][0]["hooks"][0]["command"],
        )

        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        self.assertIn("sessionStart", cursor["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            cursor["hooks"]["sessionStart"][0]["command"],
        )

    def test_gemini_session_log_hook_uses_afteragent_not_stop(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("AfterAgent", gemini["hooks"])
        self.assertNotIn("Stop", gemini["hooks"])
        self.assertIn(
            "session-log-check.py",
            gemini["hooks"]["AfterAgent"][0]["hooks"][0]["command"],
        )

    def test_strip_gemini_dead_hooks_removes_ours_preserves_foreign(self):
        import json
        from memory_seed.core import _strip_gemini_dead_hooks

        cwd = self.make_project()
        settings = cwd / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/session-log-check.py --gemini"}]},
                        {"hooks": [{"type": "command", "command": "some-foreign-tool"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --gemini"}]},
                    ],
                }
            }),
            encoding="utf-8",
        )

        self.assertTrue(_strip_gemini_dead_hooks(cwd))
        data = json.loads(settings.read_text())
        # Our UserPromptSubmit entry was the only one -> event removed entirely.
        self.assertNotIn("UserPromptSubmit", data["hooks"])
        # Foreign Stop entry preserved; our Stop entry removed.
        stop_cmds = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_cmds, ["some-foreign-tool"])
        # Idempotent: nothing of ours left to strip.
        self.assertFalse(_strip_gemini_dead_hooks(cwd))

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

    def test_init_installs_session_start_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("SessionStart", claude["hooks"])
        self.assertIn(
            "session-start-context.py",
            claude["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("SessionStart", codex["hooks"])
        self.assertIn(
            "--codex",
            codex["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("SessionStart", gemini["hooks"])

        # Cursor fires both reminders at sessionStart; both scripts must be present.
        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        cursor_cmds = [e["command"] for e in cursor["hooks"]["sessionStart"]]
        self.assertTrue(any("session-start-context.py" in c for c in cursor_cmds))
        self.assertTrue(any("memory-retrieval-check.py" in c for c in cursor_cmds))

    def test_init_installs_copilot_mcp_and_prompt_hook(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".github" / "mcp.json").read_text())
        server = mcp["mcpServers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        self.assertEqual(server["tools"], ["*"])

        hook = json.loads((cwd / ".github" / "hooks" / "memory-seed.json").read_text())
        self.assertEqual(hook["version"], 1)
        entry = hook["hooks"]["sessionStart"][0]
        self.assertEqual(entry["type"], "prompt")
        self.assertIn("Do NOT use memory_search", entry["prompt"])
        self.assertIn(".memory-seed/sessions/", entry["prompt"])

    def test_copilot_merges_are_idempotent(self):
        from memory_seed.core import _merge_copilot_mcp, _merge_copilot_startup_hook

        cwd = self.make_project()
        self.assertTrue(_merge_copilot_mcp(cwd))
        self.assertFalse(_merge_copilot_mcp(cwd))
        self.assertTrue(_merge_copilot_startup_hook(cwd))
        self.assertFalse(_merge_copilot_startup_hook(cwd))

    def test_copilot_mcp_preserves_foreign_server(self):
        import json
        from memory_seed.core import _merge_copilot_mcp

        cwd = self.make_project()
        mcp_path = cwd / ".github" / "mcp.json"
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "other-tool"}}}),
            encoding="utf-8",
        )

        self.assertFalse(_merge_copilot_mcp(cwd))  # foreign entry left untouched
        data = json.loads(mcp_path.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "other-tool")

    def test_init_installs_vscode_mcp_under_servers_key(self):
        import json
        from memory_seed.core import _merge_vscode_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".vscode" / "mcp.json").read_text())
        # VS Code uses the "servers" key, not "mcpServers".
        self.assertIn("servers", mcp)
        self.assertNotIn("mcpServers", mcp)
        server = mcp["servers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        # Idempotent.
        self.assertFalse(_merge_vscode_mcp(cwd))

    def test_init_installs_copilot_instructions_router(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        router = cwd / ".github" / "copilot-instructions.md"
        self.assertTrue(router.exists())
        text = router.read_text(encoding="utf-8")
        self.assertIn("GitHub Copilot Instructions", text)
        self.assertIn("AGENTS.md", text)


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

    def _run_with_env(self, cwd, extra_env):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
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

    def test_user_scoped_staleness_ignores_other_users_recent_entry(self):
        import datetime

        cwd = self.make_project()
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        user_dir = cwd / ".memory-seed" / "sessions" / today
        user_dir.mkdir(parents=True)
        (user_dir / "amina.md").write_text(
            f"## {today} {now.strftime('%H:%M')} - Amina recent\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertIn(f".memory-seed/sessions/{today}/jean.md", out)
        self.assertNotIn(f".memory-seed/sessions/{today}.md", out)

    def test_user_scoped_order_warning_checks_only_selected_file(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        user_dir = cwd / ".memory-seed" / "sessions" / today
        user_dir.mkdir(parents=True)
        (user_dir / "jean.md").write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        (user_dir / "amina.md").write_text(
            f"## {today} 01:00 - amina\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("ORDER WARNING", out)
        self.assertIn(f".memory-seed/sessions/{today}/jean.md", out)


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

    def test_doctor_warns_on_orphan_skill_not_in_registry(self):
        from memory_seed.core import doctor

        cwd = self.make_project()
        init_project(cwd=cwd)

        # A freshly seeded project's skills are all registered: no orphan warning.
        self.assertFalse(
            any("orphan skill" in w for w in doctor(cwd=cwd).warnings)
        )

        # Drop a skill runbook that is not referenced by skills/index.md.
        orphan = cwd / ".memory-seed" / "skills" / "ghost_skill.md"
        orphan.write_text(
            "---\nmemory-system-version: 2.7\n---\n\n# Ghost Skill\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)
        self.assertTrue(
            any("ghost_skill.md" in w and "orphan skill" in w for w in result.warnings)
        )
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # Registering it in the trigger registry clears the warning.
        registry = cwd / ".memory-seed" / "skills" / "index.md"
        registry.write_text(
            registry.read_text(encoding="utf-8")
            + "\n  - skill: ghost_skill.md\n    required: false\n",
            encoding="utf-8",
        )
        self.assertFalse(
            any("ghost_skill.md" in w for w in doctor(cwd=cwd).warnings)
        )

    def test_doctor_warns_when_runtime_exists_but_routing_file_is_foreign(self):
        from memory_seed.core import doctor, _merge_routing_stanza

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Fresh project: our AGENTS.md routes into the runtime, no route warning.
        self.assertFalse(any("route into" in w for w in doctor(cwd=cwd).warnings))

        # Replace it with a foreign file: neither our frontmatter nor our block.
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost only\n", encoding="utf-8")
        result = doctor(cwd=cwd)
        self.assertTrue(
            any("AGENTS.md" in w and "route into" in w for w in result.warnings)
        )
        # Non-fatal, and not counted as a version mismatch (host owns the file).
        self.assertTrue(result.control_plane_ok)
        self.assertFalse(any(m["file"] == "AGENTS.md" for m in result.version_mismatches))

        # Injecting our managed block clears the warning.
        _merge_routing_stanza(cwd / "AGENTS.md")
        self.assertFalse(
            any("AGENTS.md" in w and "route into" in w for w in doctor(cwd=cwd).warnings)
        )


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

    def test_user_set_show_clear_and_session_target(self):
        import contextlib

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-user-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)

        try:
            import os

            os.chdir(project)
            self.assertEqual(self._run(["user", "set", "jean"])[0], 0)
            local = project / ".memory-seed" / "local.yaml"
            self.assertIn("user: jean", local.read_text(encoding="utf-8"))
            self.assertIn(".memory-seed/local.yaml", (project / ".gitignore").read_text(encoding="utf-8"))

            code, out = self._run(["user", "show"])
            self.assertEqual(code, 0)
            self.assertIn("jean", out)

            code, out = self._run(["session", "target"])
            self.assertEqual(code, 0)
            self.assertRegex(out.strip(), r"\.memory-seed/sessions/\d{4}-\d{2}-\d{2}/jean\.md$")

            code, out = self._run(["session", "target", "--create"])
            self.assertEqual(code, 0)
            target = project / out.strip()
            self.assertTrue(target.exists())
            created = target.read_text(encoding="utf-8")
            self.assertIn("schema_version: 2", created)
            self.assertIn("user: jean", created)
            self.assertIn("hash_id: msm_", created)

            self.assertEqual(self._run(["user", "clear"])[0], 0)
            self.assertFalse(local.exists())
        finally:
            os.chdir(cwd)


class SessionStartContextHookTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-start-context.py").resolve()

    def make_project(self, sessions=None):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-startup-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        sdir = path / ".memory-seed" / "sessions"
        sdir.mkdir(parents=True)
        for name, body in (sessions or {}).items():
            target = sdir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return path

    def _run(self, cwd, *args):
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout

    def _run_with_env(self, cwd, extra_env, *args):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_injects_newest_file_headings_and_latest_entry(self):
        import json

        cwd = self.make_project({
            "2026-01-01.md": "## 2026-01-01 09:00 - Older work\n\nbody one\n",
            "2026-02-02.md": (
                "## 2026-02-02 10:00 - First entry\n\nbody A\n\n"
                "## 2026-02-02 14:30 - Latest entry title\n\nthe newest body\n"
            ),
        })

        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        # Newest file by date is selected, not the older one.
        self.assertIn("Newest session file: .memory-seed/sessions/2026-02-02.md", context)
        self.assertIn("Prior session file: .memory-seed/sessions/2026-01-01.md", context)
        # All headings of the newest file are listed.
        self.assertIn("2026-02-02 10:00 - First entry", context)
        self.assertIn("2026-02-02 14:30 - Latest entry title", context)
        # The most recent entry's body is injected verbatim (self-sufficient).
        self.assertIn("the newest body", context)
        # The recency-vs-search rule is present.
        self.assertIn("do NOT use memory_search", context)

    def test_cursor_uses_additional_context_field(self):
        import json

        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})
        out = self._run(cwd, "--cursor")
        data = json.loads(out)
        self.assertIn("additional_context", data)
        self.assertNotIn("hookSpecificOutput", data)

    def test_caps_long_latest_entry(self):
        import json

        big = "## 2026-02-02 10:00 - Huge\n\n" + ("x" * 5000) + "\n"
        cwd = self.make_project({"2026-02-02.md": big})
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("truncated", context)

    def test_empty_sessions_dir_emits_nothing(self):
        cwd = self.make_project({})
        self.assertEqual(self._run(cwd).strip(), "")

    def test_missing_sessions_dir_emits_nothing(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-startup-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        self.assertEqual(self._run(path).strip(), "")

    def test_ignores_non_date_filenames(self):
        import json

        cwd = self.make_project({
            "2026-02-02.md": "## 2026-02-02 10:00 - Real\n\nb\n",
            "notes.md": "## Should be ignored\n\nignored\n",
        })
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("2026-02-02.md", context)
        self.assertNotIn("Should be ignored", context)

    def test_user_context_injects_active_user_and_lists_contributors(self):
        import json

        cwd = self.make_project({
            "2026-02-02/jean.md": (
                "## 2026-02-02 10:00 - Jean first\n\nbody A\n\n"
                "## 2026-02-02 14:30 - Jean latest\n\njean newest body\n"
            ),
            "2026-02-02/amina.md": "## 2026-02-02 11:00 - Amina work\n\namina body\n",
            "2026-02-01/jean.md": "## 2026-02-01 09:00 - Jean older\n\nold body\n",
        })

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        self.assertIn("Newest session file: .memory-seed/sessions/2026-02-02/jean.md", context)
        self.assertIn("jean newest body", context)
        self.assertIn("Co-contributor session files for 2026-02-02:", context)
        self.assertIn(".memory-seed/sessions/2026-02-02/amina.md (1 entry)", context)
        self.assertNotIn("amina body", context)

    def test_markdown_heading_in_body_is_not_an_entry_boundary(self):
        import json

        # A "## " line inside an entry body (e.g. a quoted heading) must not be
        # parsed as an entry boundary, or the latest-entry extraction would start
        # from it and drop the real entry's content above it.
        cwd = self.make_project({
            "2026-02-02.md": (
                "## 2026-02-02 10:00 - Real entry\n\n"
                "Here is an example heading we quote:\n\n"
                "## Not A Real Entry Heading\n\n"
                "real entry trailing content\n"
            ),
        })
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        # Exactly one real entry heading is listed.
        self.assertIn("- 2026-02-02 10:00 - Real entry", context)
        self.assertNotIn("- Not A Real Entry Heading", context)
        # The latest entry includes content from above the stray "## " line.
        self.assertIn("Here is an example heading we quote", context)
        self.assertIn("real entry trailing content", context)

    def test_seed_and_live_hook_match(self):
        live = Path(".memory-seed/hooks/session-start-context.py")
        seed = Path("memory_seed/seed/.memory-seed/hooks/session-start-context.py")
        self.assertEqual(
            live.read_text(encoding="utf-8"),
            seed.read_text(encoding="utf-8"),
        )


class AgentSelectionTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-agents-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    # --- resolve_agents ---
    def test_resolve_agents_flag_parsing_and_validation(self):
        from memory_seed.core import resolve_agents, KNOWN_AGENTS

        self.assertEqual(resolve_agents("claude,codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("claude codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("all", isatty=False), set(KNOWN_AGENTS))
        # No flag, non-TTY -> all (backward-compatible default).
        self.assertEqual(resolve_agents(None, isatty=False), set(KNOWN_AGENTS))
        # Interactive empty response -> all.
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response=""), set(KNOWN_AGENTS))
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response="gemini"), {"gemini"})
        with self.assertRaises(ValueError):
            resolve_agents("claude,bogus", isatty=False)

    # --- selective init ---
    def test_init_with_subset_installs_only_selected(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})

        self.assertTrue((cwd / "AGENTS.md").exists())
        self.assertTrue((cwd / "CLAUDE.md").exists())
        self.assertTrue((cwd / ".claude" / "settings.json").exists())
        self.assertTrue((cwd / ".codex" / "hooks.json").exists())
        self.assertTrue((cwd / ".mcp.json").exists())
        # Deselected agents leave no trace.
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())
        self.assertFalse((cwd / ".cursor").exists())
        # Agent-agnostic core always present.
        self.assertTrue((cwd / ".memory-seed" / "agent-rules.md").exists())
        self.assertTrue((cwd / ".agents" / "developer.md").exists())
        # Selection persisted.
        from memory_seed.core import selected_agents
        self.assertEqual(selected_agents(cwd), {"claude", "codex"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())

    def test_init_all_agents_writes_no_project_yaml(self):
        # Default (all) must stay byte-identical to legacy: no project.yaml written.
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertFalse((cwd / ".memory-seed" / "project.yaml").exists())
        from memory_seed.core import read_project_agents, KNOWN_AGENTS, selected_agents
        self.assertIsNone(read_project_agents(cwd))
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS))

    def test_doctor_ignores_deselected_agent_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        result = doctor(cwd=cwd)
        # GEMINI.md is intentionally absent; doctor must not flag it.
        self.assertNotIn("GEMINI.md", result.missing)
        self.assertEqual(result.missing, [])
        self.assertFalse(any("Codex" in w for w in result.warnings))

    def test_update_does_not_readd_deselected_agents(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        update_project(cwd=cwd)
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())

    # --- add / remove ---
    def test_add_agent_installs_and_persists(self):
        from memory_seed.core import add_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = add_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertTrue((cwd / "GEMINI.md").exists())
        self.assertTrue((cwd / ".gemini" / "settings.json").exists())
        self.assertEqual(selected_agents(cwd), {"claude", "gemini"})
        # Adding an already-installed agent is a no-op.
        self.assertFalse(add_agent(cwd=cwd, agent="gemini")["changed"])

    def test_remove_agent_strips_ours_preserves_foreign_and_backs_up(self):
        import json
        from memory_seed.core import remove_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        # Inject foreign content into Claude's settings.
        settings = cwd / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["permissions"] = {"allow": ["Bash"]}
        settings.write_text(json.dumps(data))

        res = remove_agent(cwd=cwd, agent="claude")
        self.assertTrue(res["changed"])
        self.assertTrue(res["backed_up"])  # something was backed up
        # Routing file + ours-only .mcp.json gone.
        self.assertFalse((cwd / "CLAUDE.md").exists())
        self.assertFalse((cwd / ".mcp.json").exists())
        # Foreign content preserved; file NOT deleted.
        self.assertTrue(settings.exists())
        self.assertEqual(list(json.loads(settings.read_text()).keys()), ["permissions"])
        self.assertEqual(selected_agents(cwd), {"codex"})

    def test_remove_not_installed_is_noop(self):
        from memory_seed.core import remove_agent
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertFalse(res["changed"])

    def test_remove_last_agent_warns_and_is_zero_state(self):
        from memory_seed.core import remove_agent, selected_agents, read_project_agents
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        res = remove_agent(cwd=cwd, agent="codex")
        self.assertTrue(res["warning"])
        # Zero-agents is a real state (empty set), distinct from unconfigured (None).
        self.assertEqual(read_project_agents(cwd), set())
        self.assertEqual(selected_agents(cwd), set())
        # doctor expects no agent files and is clean.
        self.assertEqual(doctor(cwd=cwd).missing, [])

    def test_remove_codex_preserves_foreign_toml(self):
        import tomllib
        from memory_seed.core import remove_agent

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        cfg = cwd / ".codex" / "config.toml"
        # Surround our block with foreign TOML: a top-level key before, a foreign
        # MCP table after. Exercises the line-based stripper's "delete to next [".
        cfg.write_text(
            'model = "gpt-x"\n\n'
            + cfg.read_text(encoding="utf-8")
            + '\n[mcp_servers.other]\ncommand = "foo"\nargs = []\n',
            encoding="utf-8",
        )

        remove_agent(cwd=cwd, agent="codex")

        self.assertTrue(cfg.exists())
        text = cfg.read_text(encoding="utf-8")
        self.assertNotIn("[mcp_servers.memory-seed]", text)
        self.assertIn('model = "gpt-x"', text)
        self.assertIn("[mcp_servers.other]", text)
        parsed = tomllib.loads(text)  # still valid TOML
        self.assertNotIn("memory-seed", parsed.get("mcp_servers", {}))
        self.assertIn("other", parsed.get("mcp_servers", {}))

    def test_remove_from_unconfigured_project_writes_remaining(self):
        from memory_seed.core import remove_agent, selected_agents, KNOWN_AGENTS

        cwd = self.make_project()
        init_project(cwd=cwd)  # all agents, no project.yaml
        self.assertFalse((cwd / ".memory-seed" / "project.yaml").exists())

        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS) - {"gemini"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())
        self.assertFalse((cwd / "GEMINI.md").exists())

    def test_project_yaml_parser_fails_open(self):
        from memory_seed.core import read_project_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        cfg = cwd / ".memory-seed" / "project.yaml"
        # Malformed / unrelated content with no agents: key -> None (treated as all).
        cfg.write_text("schema_version: 1\nusers:\n  - jean\n", encoding="utf-8")
        self.assertIsNone(read_project_agents(cwd))
        # Inline list form is parsed; unknown slugs ignored.
        cfg.write_text("agents: [claude, bogus, codex]\n", encoding="utf-8")
        self.assertEqual(read_project_agents(cwd), {"claude", "codex"})


if __name__ == "__main__":
    unittest.main()
