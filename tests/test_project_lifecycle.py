import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from memory_seed.cli import main as cli_main
from memory_seed.core import (
    CORE_RETRIEVAL_PROFILES,
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
        self.assertEqual(get_version(), "2.24")

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

    def test_graphify_scope_is_passive_and_project_owned(self):
        cwd = self.make_project()
        fresh = self.make_project()
        init_project(cwd=fresh)
        self.assertEqual(
            (Path(__file__).resolve().parents[1] / "memory_seed" / "seed" / ".graphifyignore").read_text(encoding="utf-8"),
            (fresh / ".graphifyignore").read_text(encoding="utf-8"),
        )
        self.assertNotIn("graphify_merge_refresh: true", (fresh / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))
        custom_scope = cwd / ".graphifyignore"
        custom_scope.write_text("private-work/\n", encoding="utf-8")
        init_project(cwd=cwd)
        self.assertEqual("private-work/\n", custom_scope.read_text(encoding="utf-8"))
        self.assertNotIn("graphify_merge_refresh: true", (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))
        update_project(cwd=cwd)
        self.assertEqual("private-work/\n", custom_scope.read_text(encoding="utf-8"))
        init_project(cwd=cwd, force=True)
        self.assertEqual("private-work/\n", custom_scope.read_text(encoding="utf-8"))

    def test_core_retrieval_profiles_install_update_and_remain_immutable(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        profile_root = cwd / MEMORY_DIR_NAME / "retrieval-profiles"
        expected = {
            f"{profile_id}/v{profile_version}.yaml"
            for profile_id, profile_version in CORE_RETRIEVAL_PROFILES
        }
        installed = {
            path.relative_to(profile_root).as_posix()
            for path in profile_root.glob("*/v*.yaml")
        }
        self.assertEqual(installed, expected)

        implementation = profile_root / "implementation" / "v1.yaml"
        customized = implementation.read_text(encoding="utf-8") + "# local note\n"
        implementation.write_text(customized, encoding="utf-8")
        custom = profile_root / "team-review" / "v7.yaml"
        custom.parent.mkdir(parents=True)
        custom.write_text("project-owned\n", encoding="utf-8")
        missing = profile_root / "research" / "v1.yaml"
        missing.unlink()

        result = update_project(cwd=cwd)

        self.assertEqual(implementation.read_text(encoding="utf-8"), customized)
        self.assertEqual(custom.read_text(encoding="utf-8"), "project-owned\n")
        self.assertTrue(missing.is_file())
        self.assertIn(
            ".memory-seed/retrieval-profiles/research/v1.yaml", result.created
        )
        self.assertNotIn(
            ".memory-seed/retrieval-profiles/implementation/v1.yaml", result.created
        )

    def test_force_init_preserves_existing_core_profile_and_custom_ids(self):
        cwd = self.make_project()
        implementation = (
            cwd
            / MEMORY_DIR_NAME
            / "retrieval-profiles"
            / "implementation"
            / "v1.yaml"
        )
        implementation.parent.mkdir(parents=True)
        implementation.write_text("existing-core-version\n", encoding="utf-8")
        custom = (
            cwd / MEMORY_DIR_NAME / "retrieval-profiles" / "my-custom" / "v2.yaml"
        )
        custom.parent.mkdir(parents=True)
        custom.write_text("existing-custom-id\n", encoding="utf-8")

        init_project(cwd=cwd, force=True)

        self.assertEqual(
            implementation.read_text(encoding="utf-8"), "existing-core-version\n"
        )
        self.assertEqual(custom.read_text(encoding="utf-8"), "existing-custom-id\n")

    def test_doctor_is_unhealthy_when_managed_retrieval_profile_identity_is_wrong(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        profile = (
            cwd
            / MEMORY_DIR_NAME
            / "retrieval-profiles"
            / "implementation"
            / "v1.yaml"
        )
        profile.write_text(
            profile.read_text(encoding="utf-8").replace(
                "id: implementation", "id: wrong-profile"
            ),
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)

        warning = next(
            warning
            for warning in result.warnings
            if "Managed retrieval profile implementation:v1 is invalid" in warning
        )
        self.assertIn("identity does not match exact path", warning)
        self.assertFalse(result.control_plane_ok)
        self.assertFalse(result.ok)

    def test_doctor_and_cli_are_unhealthy_when_managed_profile_effective_spec_is_invalid(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        profile = (
            cwd
            / MEMORY_DIR_NAME
            / "retrieval-profiles"
            / "implementation"
            / "v1.yaml"
        )
        profile.write_text(
            profile.read_text(encoding="utf-8").replace(
                "max_tokens: 12000", "max_tokens: 0"
            ),
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)
        self.assertFalse(result.control_plane_ok)
        self.assertFalse(result.ok)
        self.assertTrue(any("max_tokens" in warning for warning in result.warnings))

        output = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(cwd)
            with contextlib.redirect_stdout(output):
                status = cli_main(["doctor"])
        finally:
            os.chdir(previous)
        self.assertEqual(status, 1)
        self.assertIn("control plane has issues", output.getvalue())
        self.assertIn("max_tokens", output.getvalue())

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

    def test_doctor_warns_when_constitution_is_missing_without_failing_control_plane(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        result = doctor(cwd=cwd)

        warning = next(w for w in result.warnings if "Constitution" in w)
        self.assertIn("docs/CONSTITUTION.md", warning)
        self.assertIn("Task Packets cannot be compiled", warning)
        self.assertIn("**Version:** 1.0 — **RATIFIED YYYY-MM-DD**", warning)
        self.assertTrue(result.control_plane_ok)

    def test_doctor_warns_when_constitution_is_draft_without_failing_control_plane(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        constitution = cwd / "docs" / "CONSTITUTION.md"
        constitution.parent.mkdir(parents=True)
        constitution.write_text(
            "# Constitution\n\n**Version:** 1.0 — **DRAFT**\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)

        warning = next(w for w in result.warnings if "Constitution" in w)
        self.assertIn("draft, not yet ratified", warning)
        self.assertIn("Task Packets cannot be compiled", warning)
        self.assertTrue(result.control_plane_ok)

    def test_doctor_is_silent_when_constitution_is_ratified(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        constitution = cwd / "docs" / "CONSTITUTION.md"
        constitution.parent.mkdir(parents=True)
        constitution.write_text(
            "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-10-24**\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)

        self.assertFalse(any("Constitution" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)

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
        self.assertIn("systematic_debugging.md", installed)
        self.assertIn("data_architecture.md", installed)
        self.assertIn("proposal_lifecycle.md", installed)
        self.assertIn("design_discovery.md", installed)
        self.assertTrue((cwd / "docs" / "inbox" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / "completed" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "reference" / ".gitkeep").exists())
        self.assertIn("docs/inbox/.gitkeep", result.created)
        self.assertIn("docs/reference/.gitkeep", result.created)
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("coding", project_yaml)
        self.assertIn("planning", project_yaml)

    def test_delivery_quality_skills_are_registered_with_their_profiles(self):
        cwd = self.make_project()

        init_project(cwd=cwd, skill_profiles={"coding", "planning"})

        self.assertNotIn("design_discovery.md", CORE_SKILL_NAMES)
        self.assertIn("design_discovery.md", OPTIONAL_SKILL_NAMES)
        self.assertNotIn("systematic_debugging.md", CORE_SKILL_NAMES)
        self.assertIn("systematic_debugging.md", OPTIONAL_SKILL_NAMES)
        self.assertEqual(
            SKILL_PROFILES["planning"].skills,
            ("proposal_lifecycle.md", "design_discovery.md"),
        )
        self.assertIn("systematic_debugging.md", SKILL_PROFILES["coding"].skills)
        self.assertTrue((cwd / ".memory-seed" / "skills" / "design_discovery.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "skills" / "systematic_debugging.md").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: design_discovery.md", registry)
        self.assertIn("skill: systematic_debugging.md", registry)

    def test_update_respects_ignored_optional_skills(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())

        result = update_project(cwd=cwd)

        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())
        self.assertNotIn(".memory-seed/skills/code_search.md", result.created)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_task_packet_skill_is_core_for_any_profile_set(self):
        # Gagiste (2026-10-23) chose these profiles and never received the
        # Task Packet skill that its installed rules pointed to (MSI-012).
        cwd = self.make_project()

        init_project(cwd=cwd, skill_profiles={"coding", "security", "planning", "diagramming"})

        self.assertIn("agent_collaboration.md", CORE_SKILL_NAMES)
        self.assertNotIn("agent_collaboration.md", OPTIONAL_SKILL_NAMES)
        self.assertNotIn("collaboration", SKILL_PROFILES)
        self.assertTrue((cwd / ".memory-seed" / "skills" / "agent_collaboration.md").exists())
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertNotIn("agent_collaboration.md", project_yaml)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_removed_collaboration_profile_is_explained_not_aliased(self):
        cwd = self.make_project()

        with self.assertRaisesRegex(ValueError, "agent_collaboration.md .* is now a core skill"):
            init_project(cwd=cwd, skill_profiles={"collaboration"})

        init_project(cwd=cwd)
        result = add_skill(cwd=cwd, name="collaboration")
        self.assertFalse(result["changed"])
        self.assertIn("now a core skill", result["message"])

    def test_update_migrates_legacy_collaboration_entries(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles={"coding"})
        project_yaml = cwd / ".memory-seed" / "project.yaml"
        text = project_yaml.read_text(encoding="utf-8")
        text = text.replace("  profiles:\n", "  profiles:\n    - collaboration\n", 1)
        text = text.replace("  ignored:\n", "  ignored:\n    - agent_collaboration.md\n", 1)
        project_yaml.write_text(text, encoding="utf-8")
        (cwd / ".memory-seed" / "skills" / "agent_collaboration.md").unlink()

        preview = update_project(cwd=cwd, dry_run=True)
        result = update_project(cwd=cwd)

        self.assertEqual(preview.notes, result.notes)
        self.assertEqual(len(result.notes), 2)
        self.assertTrue(any("Removed profile 'collaboration'" in note for note in result.notes))
        self.assertTrue(any("skills.ignored" in note for note in result.notes))
        migrated = project_yaml.read_text(encoding="utf-8")
        self.assertNotIn("collaboration", migrated.split("skills:", 1)[1].split("ignored:", 1)[0])
        self.assertNotIn("agent_collaboration.md", migrated)
        self.assertIn("- coding", migrated)
        self.assertTrue((cwd / ".memory-seed" / "skills" / "agent_collaboration.md").exists())
        self.assertEqual(update_project(cwd=cwd).notes, [])

    def test_update_migration_keeps_unrecognised_skill_entries(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles={"coding"})
        project_yaml = cwd / ".memory-seed" / "project.yaml"
        text = project_yaml.read_text(encoding="utf-8")
        text = text.replace(
            "  profiles:\n", "  profiles:\n    - collaboration\n    - team-local-profile\n", 1
        )
        text = text.replace("  ignored:\n", "  ignored:\n    - agent_collaboration.md\n    - house_style.md\n", 1)
        text = text.replace("skills:\n", "skills:\n  note: kept by hand\n", 1)
        project_yaml.write_text(text + "custom_key: untouched\n", encoding="utf-8")

        update_project(cwd=cwd)

        migrated = project_yaml.read_text(encoding="utf-8")
        for kept in ("team-local-profile", "house_style.md", "note: kept by hand", "custom_key: untouched"):
            self.assertIn(kept, migrated)
        self.assertNotIn("- collaboration", migrated)
        self.assertNotIn("agent_collaboration.md", migrated)

    def test_update_migration_filters_inline_skill_lists(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        project_yaml = cwd / ".memory-seed" / "project.yaml"
        project_yaml.write_text(
            "schema_version: 1\nskills:\n  profiles: [collaboration, coding]\n"
            "  selected: []\n  ignored: [agent_collaboration.md, house_style.md]\n",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        migrated = project_yaml.read_text(encoding="utf-8")
        self.assertEqual(len(result.notes), 2)
        self.assertIn("profiles: [coding]", migrated)
        self.assertIn("ignored: [house_style.md]", migrated)

    def test_bootstrap_guides_do_not_offer_the_removed_profile(self):
        for path in (
            Path(".memory-seed/project-bootstrap.md"),
            PACKAGE_ROOT / "seed" / ".memory-seed" / "project-bootstrap.md",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("`collaboration`:", text, str(path))
            self.assertIn("is a core skill and is always installed", text, str(path))

    def test_init_installs_managed_session_merge_rules(self):
        # MSI-003: projects never received the `-merge` protection that the
        # Memory Seed repository itself relies on.
        cwd = self.make_project()

        result = init_project(cwd=cwd)

        self.assertIn(".gitattributes", result.created)
        text = (cwd / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(".memory-seed/sessions/** -merge", text)
        self.assertIn(".memory-seed/reflections/active/** -merge", text)
        self.assertNotIn("merge rules for session memory", " ".join(doctor(cwd=cwd).warnings))
        self.assertNotIn(".gitattributes", update_project(cwd=cwd).created)

    def test_managed_merge_rules_preserve_foreign_bytes(self):
        cwd = self.make_project()
        foreign = b"* text=auto\r\n*.png binary\r\n# project rule\r\ndocs/** linguist-documentation"
        (cwd / ".gitattributes").write_bytes(foreign)

        init_project(cwd=cwd)

        written = (cwd / ".gitattributes").read_bytes()
        self.assertTrue(written.startswith(foreign + b"\r\n"))
        self.assertIn(b".memory-seed/sessions/** -merge\r\n", written)

    def test_update_refreshes_a_stale_managed_block_only(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        path = cwd / ".gitattributes"
        stale = path.read_text(encoding="utf-8").replace(".memory-seed/sessions/** -merge\n", "")
        path.write_text("*.sh text eol=lf\n" + stale + "*.bat text eol=crlf\n", encoding="utf-8")
        self.assertIn("stale", " ".join(doctor(cwd=cwd).warnings))

        result = update_project(cwd=cwd)

        refreshed = path.read_text(encoding="utf-8")
        self.assertIn(".gitattributes", result.created)
        self.assertTrue(refreshed.startswith("*.sh text eol=lf\n"))
        self.assertTrue(refreshed.endswith("*.bat text eol=crlf\n"))
        self.assertEqual(refreshed.count(".memory-seed/sessions/** -merge"), 1)

    def test_doctor_warns_when_session_merge_rules_are_missing(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        (cwd / ".gitattributes").unlink()

        warnings = " ".join(doctor(cwd=cwd).warnings)

        self.assertIn("merge rules for session memory are missing", warnings)
        self.assertIn("memory-seed session open-pr", warnings)

    def test_session_files_are_unmergeable_by_git_after_init(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        cwd = self.make_project()
        subprocess.run(["git", "init", "-q", str(cwd)], check=True)
        init_project(cwd=cwd)

        out = subprocess.run(
            ["git", "-C", str(cwd), "check-attr", "merge", "--", ".memory-seed/sessions/2026-10/2026-10-23.md"],
            check=True, capture_output=True, text=True,
        ).stdout

        self.assertIn("merge: unset", out)

    def test_managed_merge_rules_survive_non_utf8_foreign_bytes(self):
        cwd = self.make_project()
        foreign = b"# r\xe9gle h\xe9rit\xe9e (latin-1)\n*.png binary\n"
        (cwd / ".gitattributes").write_bytes(foreign)

        init_project(cwd=cwd)

        written = (cwd / ".gitattributes").read_bytes()
        self.assertTrue(written.startswith(foreign))
        self.assertIn(b".memory-seed/sessions/** -merge\n", written)

    def test_overridden_merge_rules_are_reported_and_moved_last(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        cwd = self.make_project()
        subprocess.run(["git", "init", "-q", str(cwd)], check=True)
        init_project(cwd=cwd)
        path = cwd / ".gitattributes"
        path.write_text(path.read_text(encoding="utf-8") + ".memory-seed/sessions/** merge\n", encoding="utf-8")

        self.assertIn("are overridden", " ".join(doctor(cwd=cwd).warnings))
        result = update_project(cwd=cwd)

        self.assertIn(".gitattributes", result.created)
        out = subprocess.run(
            ["git", "-C", str(cwd), "check-attr", "merge", "--", ".memory-seed/sessions/2026-10/x.md"],
            check=True, capture_output=True, text=True,
        ).stdout
        self.assertIn("merge: unset", out)
        self.assertTrue(path.read_text(encoding="utf-8").rstrip().endswith("memory-seed managed merge rules <<<"))
        self.assertNotIn("merge rules for session memory", " ".join(doctor(cwd=cwd).warnings))

    def test_one_update_repairs_a_stale_and_overridden_block(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        cwd = self.make_project()
        subprocess.run(["git", "init", "-q", str(cwd)], check=True)
        init_project(cwd=cwd)
        path = cwd / ".gitattributes"
        stale = path.read_text(encoding="utf-8").replace(".memory-seed/sessions/** -merge\n", "")
        path.write_text(stale + ".memory-seed/sessions/** merge\n.memory-seed/reflections/active/** merge\n",
                        encoding="utf-8")

        update_project(cwd=cwd)

        out = subprocess.run(
            ["git", "-C", str(cwd), "check-attr", "merge", "--",
             ".memory-seed/sessions/2026-10/x.md", ".memory-seed/reflections/active/x.md"],
            check=True, capture_output=True, text=True,
        ).stdout
        self.assertEqual(out.count("merge: unset"), 2, out)
        self.assertNotIn("merge rules for session memory", " ".join(doctor(cwd=cwd).warnings))

    def test_nested_override_is_reported_without_churn(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        cwd = self.make_project()
        subprocess.run(["git", "init", "-q", str(cwd)], check=True)
        init_project(cwd=cwd)
        (cwd / ".memory-seed" / "sessions").mkdir(parents=True, exist_ok=True)
        (cwd / ".memory-seed" / "sessions" / ".gitattributes").write_text("* merge\n", encoding="utf-8")

        self.assertIn("nested .gitattributes", " ".join(doctor(cwd=cwd).warnings))
        self.assertNotIn(".gitattributes", update_project(cwd=cwd).created)

    def test_doctor_reports_unresolved_skill_references(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles={"coding"})
        rules = cwd / ".memory-seed" / "agent-rules.md"
        rules.write_text(
            rules.read_text(encoding="utf-8")
            + "\nLoad `.memory-seed/skills/release_publishing.md` before a release.\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)

        self.assertTrue(result.control_plane_ok)
        matching = [w for w in result.warnings if "release_publishing.md" in w]
        self.assertEqual(len(matching), 1)
        self.assertIn(".memory-seed/agent-rules.md", matching[0])
        self.assertIn("memory-seed skills add release", matching[0])
        self.assertFalse(any("code_search.md, which is not installed" in w for w in result.warnings))

        (cwd / ".memory-seed" / "skills" / "agent_collaboration.md").unlink()
        broken = doctor(cwd=cwd)
        self.assertFalse(broken.control_plane_ok)
        self.assertIn(".memory-seed/skills/agent_collaboration.md", broken.missing)

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

    def test_worktree_reconciliation_is_a_core_safety_skill(self):
        cwd = self.make_project()

        init_project(cwd=cwd)

        self.assertIn("worktree_reconciliation.md", CORE_SKILL_NAMES)
        self.assertTrue((cwd / ".memory-seed" / "skills" / "worktree_reconciliation.md").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: worktree_reconciliation.md", registry)
        self.assertIn("worktree_reconciliation.md", skill_status(cwd=cwd)["core"])

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
                ".graphifyignore",
                ".memory-seed/agent-rules.md",
                ".memory-seed/archive/.gitkeep",
                ".memory-seed/hooks/file-touch-decisions.py",
                ".memory-seed/hooks/memory-retrieval-check.py",
                ".memory-seed/hooks/prepare-commit-msg.py",
                ".memory-seed/hooks/session-log-check.py",
                ".memory-seed/hooks/session-start-context.py",
                ".memory-seed/project-bootstrap.md",
                ".memory-seed/retrieval-profiles/adr-review/v1.yaml",
                ".memory-seed/retrieval-profiles/adr-review/v2.yaml",
                ".memory-seed/retrieval-profiles/architecture/v1.yaml",
                ".memory-seed/retrieval-profiles/architecture/v2.yaml",
                ".memory-seed/retrieval-profiles/bug-investigation/v1.yaml",
                ".memory-seed/retrieval-profiles/bug-investigation/v2.yaml",
                ".memory-seed/retrieval-profiles/design-discovery/v1.yaml",
                ".memory-seed/retrieval-profiles/design-discovery/v2.yaml",
                ".memory-seed/retrieval-profiles/implementation/v1.yaml",
                ".memory-seed/retrieval-profiles/implementation/v2.yaml",
                ".memory-seed/retrieval-profiles/refactoring/v1.yaml",
                ".memory-seed/retrieval-profiles/refactoring/v2.yaml",
                ".memory-seed/retrieval-profiles/research/v1.yaml",
                ".memory-seed/retrieval-profiles/research/v2.yaml",
                ".memory-seed/sessions/.gitkeep",
                ".memory-seed/skills/adr_sweep.md",
                ".memory-seed/skills/agent_collaboration.md",
                ".memory-seed/skills/code_search.md",
                ".memory-seed/skills/compact_mermaid_diagrams.md",
                ".memory-seed/skills/copywriter-conversion.md",
                ".memory-seed/skills/data_architecture.md",
                ".memory-seed/skills/decision_marking.md",
                ".memory-seed/skills/design_discovery.md",
                ".memory-seed/skills/developer-rendered-ui-debugging.md",
                ".memory-seed/skills/document_ingestion.md",
                ".memory-seed/skills/docx_render_windows.md",
                ".memory-seed/skills/end_of_turn.md",
                ".memory-seed/skills/graphify_analysis.md",
                ".memory-seed/skills/history_retrieval.md",
                ".memory-seed/skills/index.md",
                ".memory-seed/skills/link_swarm.md",
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
                ".memory-seed/skills/subagent_orientation.md",
                ".memory-seed/skills/subproject_runtime.md",
                ".memory-seed/skills/superpowers_integration.md",
                ".memory-seed/skills/systematic_debugging.md",
                ".memory-seed/skills/topic_swarm.md",
                ".memory-seed/skills/worktree_reconciliation.md",
                ".memory-seed/topics.yaml",
                "AGENTS.md",
                "CLAUDE.md",
                "GEMINI.md",
            ],
        )

    def test_model2vec_is_the_only_required_dependency(self):
        # This is what makes the documented lightweight install work.
        # Extras can only ADD dependencies, never subtract, so there is no way
        # to express "memory-seed without semantic" as an extra. The supported
        # lite path is `pip install --no-deps memory-seed`, and that is only
        # equivalent to "everything except semantic" while model2vec is the
        # SOLE required dependency.
        #
        # If you are adding a second required dependency, this test failing is
        # the point: --no-deps would silently start dropping it too, so the
        # lite install story has to be redesigned in the same change (README
        # "Lightweight install" section) rather than quietly breaking.
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        required = pyproject["project"]["dependencies"]
        self.assertEqual(len(required), 1, f"expected exactly one required dependency, got {required}")
        self.assertTrue(required[0].startswith("model2vec"), required[0])

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
