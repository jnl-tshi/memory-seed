from pathlib import Path
import tempfile
import unittest

from memory_seed.core import (
    OPTIONAL_SKILL_NAMES,
    SEED_FILES,
    SKILL_PROFILES,
    add_skill,
    init_project,
    update_project,
)


class SuperpowersIntegrationTests(unittest.TestCase):
    def test_adapter_is_optional_coding_profile_skill_with_seed_parity(self):
        name = "superpowers_integration.md"
        live = Path(".memory-seed/skills") / name
        seed = Path("memory_seed/seed/.memory-seed/skills") / name

        self.assertIn(name, OPTIONAL_SKILL_NAMES)
        self.assertIn(name, SKILL_PROFILES["coding"].skills)
        self.assertTrue(live.exists())
        self.assertTrue(seed.exists())
        self.assertEqual(live.read_text(encoding="utf-8"), seed.read_text(encoding="utf-8"))
        self.assertIn(
            ".memory-seed/skills/superpowers_integration.md",
            {seed_file.destination for seed_file in SEED_FILES},
        )

    def test_adapter_is_registered_and_preserves_memory_seed_boundaries(self):
        adapter = Path(".memory-seed/skills/superpowers_integration.md").read_text(encoding="utf-8")
        registry = Path(".memory-seed/skills/index.md").read_text(encoding="utf-8")
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn("skill: superpowers_integration.md", registry)
        self.assertIn("Worker Context Contract", adapter)
        self.assertIn("worktree guard", adapter)
        self.assertIn("finishing-a-development-branch", adapter)
        self.assertIn("must never become required", adapter)
        self.assertIn(".superpowers/sdd/", adapter)
        self.assertIn(".superpowers/sdd/", gitignore)

    def test_selecting_adapter_ignores_disposable_sdd_scratch_in_new_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            result = init_project(cwd=project, skill_profiles={"coding"})

            self.assertIn(".gitignore", result.created)
            self.assertIn(
                ".superpowers/sdd/",
                (project / ".gitignore").read_text(encoding="utf-8"),
            )

    def test_adding_adapter_ignores_disposable_sdd_scratch_in_existing_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            init_project(cwd=project)
            result = add_skill(cwd=project, name="superpowers_integration")

            self.assertIn(".gitignore", result["created"])
            self.assertIn(
                ".superpowers/sdd/",
                (project / ".gitignore").read_text(encoding="utf-8"),
            )

    def test_updating_selected_adapter_repairs_missing_sdd_ignore_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            init_project(cwd=project, skill_profiles={"coding"})
            (project / ".gitignore").write_text("dist/\n", encoding="utf-8")

            result = update_project(cwd=project)

            self.assertIn(".gitignore", result.created)
            self.assertIn(
                ".superpowers/sdd/",
                (project / ".gitignore").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
