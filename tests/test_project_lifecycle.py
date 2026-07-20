import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    PACKAGE_ROOT,
    SEED_FILES,
    CORE_SKILL_NAMES,
    OPTIONAL_SKILL_NAMES,
    SKILL_PROFILES,
    add_skill,
    doctor,
    get_version,
    init_project,
    resolve_runtime,
    remove_skill,
    skill_status,
    update_project,
)


class ProjectLifecycleTests(unittest.TestCase):
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

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "2.19")

    def test_doctor_summarizes_session_integrity_issues(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        self._per_user_session(cwd, "2026-06-13", "jean", fm_user="bob", hash_id="msm_" + "a" * 32, entries=("ms-12121212",))

        result = doctor(cwd=cwd)

        self.assertTrue(any("integrity issue" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # non-fatal

    def test_doctor_summarizes_encoding_and_static_text_io_issues(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        (cwd / "bad.md").write_bytes(b"alpha\r\n")
        package = cwd / "package"
        package.mkdir()
        (package / "bad.py").write_bytes(b"open('notes.md')\n")

        result = doctor(cwd=cwd)

        warning = next(w for w in result.warnings if "encoding issue" in w)
        self.assertIn("2 encoding issue(s)", warning)
        self.assertIn("memory-seed encoding check", warning)
        self.assertTrue(result.control_plane_ok)

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
        expected = [
            seed_file.destination
            for seed_file in SEED_FILES
            if not seed_file.destination.startswith(".memory-seed/skills/")
            or Path(seed_file.destination).name in set(CORE_SKILL_NAMES) | {"index.md"}
        ]
        self.assertEqual(
            sorted(result.planned),
            sorted(expected),
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
            if (
                seed_file.destination.startswith(".memory-seed/skills/")
                and Path(seed_file.destination).name in OPTIONAL_SKILL_NAMES
            ):
                continue
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

    def test_update_dry_run_reports_seed_files_without_writing(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("old agent entry", encoding="utf-8")

        result = update_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(result.backed_up, [])
        expected = [
            seed_file.destination
            for seed_file in SEED_FILES
            if not seed_file.destination.startswith(".memory-seed/skills/")
            or Path(seed_file.destination).name in set(CORE_SKILL_NAMES) | {"index.md"}
        ]
        self.assertEqual(
            sorted(result.planned),
            sorted(expected),
        )
        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "old agent entry")

    def test_init_installs_minimal_core_skills_and_records_ignored_optionals(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd)

        installed = {p.name for p in (cwd / ".memory-seed" / "skills").glob("*.md")}
        self.assertIn("session_logging.md", installed)
        self.assertIn("history_retrieval.md", installed)
        self.assertIn("memory_doctor.md", installed)
        self.assertNotIn("code_search.md", installed)
        self.assertNotIn("proposal_lifecycle.md", installed)
        self.assertNotIn("docs/inbox/.gitkeep", result.created)
        self.assertNotIn("docs/reference/.gitkeep", result.created)
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("skills:", project_yaml)
        self.assertIn("selected:", project_yaml)
        self.assertIn("ignored:", project_yaml)
        self.assertIn("code_search.md", project_yaml)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_init_profile_installs_profile_skills_and_docs_lifecycle(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd, skill_profiles={"coding", "planning"})

        installed = {p.name for p in (cwd / ".memory-seed" / "skills").glob("*.md")}
        self.assertIn("code_search.md", installed)
        self.assertIn("local_compilation.md", installed)
        self.assertIn("data_architecture.md", installed)
        self.assertIn("proposal_lifecycle.md", installed)
        self.assertTrue((cwd / "docs" / "inbox" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / "completed" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "reference" / ".gitkeep").exists())
        self.assertIn("docs/inbox/.gitkeep", result.created)
        self.assertIn("docs/reference/.gitkeep", result.created)
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("coding", project_yaml)
        self.assertIn("planning", project_yaml)

    def test_update_respects_ignored_optional_skills(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())

        result = update_project(cwd=cwd)

        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())
        self.assertNotIn(".memory-seed/skills/code_search.md", result.created)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_legacy_project_without_skills_block_preserves_installed_optionals(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles=set(SKILL_PROFILES))
        project_yaml = cwd / ".memory-seed" / "project.yaml"
        project_yaml.write_text("agents:\n  - codex\n", encoding="utf-8")
        self.assertTrue((cwd / ".memory-seed" / "skills" / "code_search.md").exists())

        result = update_project(cwd=cwd)

        self.assertTrue((cwd / ".memory-seed" / "skills" / "code_search.md").exists())
        self.assertNotIn(".memory-seed/skills/code_search.md", result.created)

    def test_skill_add_and_remove_update_files_registry_and_state(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        added = add_skill(cwd=cwd, name="planning")

        self.assertTrue(added["changed"])
        self.assertTrue((cwd / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
        self.assertTrue((cwd / "docs" / "inbox" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "reference" / ".gitkeep").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: proposal_lifecycle.md", registry)
        self.assertIn("planning", (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

        removed = remove_skill(cwd=cwd, skill="proposal_lifecycle.md")

        self.assertTrue(removed["changed"])
        self.assertFalse((cwd / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
        self.assertFalse((cwd / "docs" / "reference" / ".gitkeep").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertNotIn("skill: proposal_lifecycle.md", registry)
        self.assertTrue(any(path.endswith("proposal_lifecycle.md") for path in removed["backed_up"]))
        self.assertFalse(any("proposal_lifecycle.md" in w for w in doctor(cwd=cwd).warnings))

    def test_skill_status_reports_profiles_installed_and_ignored(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles={"coding"})

        status = skill_status(cwd=cwd)

        self.assertIn("session_logging.md", status["core"])
        self.assertIn("code_search.md", status["installed_optional"])
        self.assertIn("proposal_lifecycle.md", status["ignored"])
        self.assertEqual(status["profiles"]["coding"], list(SKILL_PROFILES["coding"].skills))
        self.assertEqual(set(status["available_optional"]), set(OPTIONAL_SKILL_NAMES))

    def test_skill_architecture_is_optional_governance_profile_skill(self):
        cwd = self.make_project()

        init_project(cwd=cwd, skill_profiles={"governance"})

        self.assertNotIn("skill_architecture.md", CORE_SKILL_NAMES)
        self.assertIn("skill_architecture.md", OPTIONAL_SKILL_NAMES)
        self.assertEqual(SKILL_PROFILES["governance"].skills, ("skill_architecture.md",))
        self.assertTrue((cwd / ".memory-seed" / "skills" / "skill_architecture.md").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: skill_architecture.md", registry)
        self.assertIn("governance", (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

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
                ".claude/commands/situate.md",
                ".gemini/commands/esr.toml",
                ".gemini/commands/situate.toml",
                ".github/copilot-instructions.md",
                ".memory-seed/agent-rules.md",
                ".memory-seed/archive/.gitkeep",
                ".memory-seed/hooks/memory-retrieval-check.py",
                ".memory-seed/hooks/prepare-commit-msg.py",
                ".memory-seed/hooks/session-log-check.py",
                ".memory-seed/hooks/session-start-context.py",
                ".memory-seed/project-bootstrap.md",
                ".memory-seed/sessions/.gitkeep",
                ".memory-seed/skills/agent_collaboration.md",
                ".memory-seed/skills/code_search.md",
                ".memory-seed/skills/compact_mermaid_diagrams.md",
                ".memory-seed/skills/copywriter-conversion.md",
                ".memory-seed/skills/data_architecture.md",
                ".memory-seed/skills/developer-rendered-ui-debugging.md",
                ".memory-seed/skills/document_ingestion.md",
                ".memory-seed/skills/docx_render_windows.md",
                ".memory-seed/skills/end_of_turn.md",
                ".memory-seed/skills/history_retrieval.md",
                ".memory-seed/skills/index.md",
                ".memory-seed/skills/local_compilation.md",
                ".memory-seed/skills/memory_consolidation.md",
                ".memory-seed/skills/memory_doctor.md",
                ".memory-seed/skills/memory_hygiene.md",
                ".memory-seed/skills/office_document_editing.md",
                ".memory-seed/skills/orientation.md",
                ".memory-seed/skills/proposal_lifecycle.md",
                ".memory-seed/skills/release_publishing.md",
                ".memory-seed/skills/risk_signaling.md",
                ".memory-seed/skills/security_triage.md",
                ".memory-seed/skills/session_logging.md",
                ".memory-seed/skills/skill_architecture.md",
                ".memory-seed/skills/subproject_runtime.md",
                ".memory-seed/topics.yaml",
                "AGENTS.md",
                "CLAUDE.md",
                "GEMINI.md",
            ],
        )

    def test_package_data_includes_all_seed_files(self):
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        package_data = set(pyproject["tool"]["setuptools"]["package-data"]["memory_seed"])
        expected = {
            seed_file.source.relative_to(PACKAGE_ROOT).as_posix()
            for seed_file in SEED_FILES
        }

        self.assertEqual(expected - package_data, set())

    def test_seed_toml_files_parse_without_bom(self):
        for seed_file in SEED_FILES:
            if seed_file.source.suffix != ".toml":
                continue
            data = seed_file.source.read_bytes()
            self.assertFalse(
                data.startswith(b"\xef\xbb\xbf"),
                f"{seed_file.destination} must be UTF-8 without BOM",
            )
            parsed = tomllib.loads(data.decode("utf-8"))
            self.assertIsInstance(parsed, dict)

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
