import shutil
import tempfile
import unittest
from pathlib import Path

from _git_helpers import run_git
from memory_seed.core import (
    MEMORY_DIR_NAME,
    init_project,
    update_project,
)


class IntegrationModeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _git(self, cwd, *args):
        return run_git(cwd, *args, check=True)

    def _init_git_project(self, cwd):
        self._git(cwd, "init", "-q")
        self._git(cwd, "config", "user.name", "Test User")
        self._git(cwd, "config", "user.email", "test@example.com")
        self._git(cwd, "config", "commit.gpgsign", "false")
        self._git(cwd, "branch", "-M", "main")

    def test_read_integration_mode_defaults_parses_and_fails_open(self):
        from memory_seed.core import DEFAULT_INTEGRATION_MODE, read_integration_mode

        cwd = self.make_project()
        mseed = cwd / MEMORY_DIR_NAME
        mseed.mkdir(parents=True, exist_ok=True)

        # Absent file -> default (legacy/unconfigured behaves as before).
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Present file without the key -> default.
        (mseed / "project.yaml").write_text(
            "participants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Declared pr (alongside other keys).
        (mseed / "project.yaml").write_text(
            "integration_mode: pr\nparticipants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        self.assertEqual(read_integration_mode(cwd), "pr")
        # Explicit local-merge.
        (mseed / "project.yaml").write_text("integration_mode: local-merge\n", encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Unrecognised value fails open to the default, not the garbage.
        (mseed / "project.yaml").write_text("integration_mode: octopus\n", encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), DEFAULT_INTEGRATION_MODE)
        # Quoted value is accepted.
        (mseed / "project.yaml").write_text('integration_mode: "pr"\n', encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), "pr")

    def test_suggest_integration_mode_uses_collaborator_signal(self):
        import json
        import unittest.mock

        from memory_seed.core import suggest_integration_mode

        cwd = self.make_project()
        self._init_git_project(cwd)
        self._git(cwd, "remote", "add", "origin", "https://example.com/org/repo.git")

        with unittest.mock.patch(
            "memory_seed.core._gh_text",
            side_effect=[
                (0, "gh version 2.0.0", ""),
                (0, "", ""),
                (
                    0,
                    json.dumps(
                        {
                            "nameWithOwner": "org/repo",
                            "defaultBranchRef": {"name": "main"},
                            "branchProtectionRules": [],
                        }
                    ),
                    "",
                ),
                (0, "[]", ""),
                (0, json.dumps([{"login": "alice"}, {"login": "bob"}]), ""),
            ],
        ):
            mode, reason = suggest_integration_mode(cwd)

        self.assertEqual(mode, "pr")
        self.assertIn("more than one collaborator", reason)

    def test_suggest_integration_mode_fails_open_on_bad_gh_responses(self):
        import json
        import unittest.mock

        from memory_seed.core import suggest_integration_mode

        cwd = self.make_project()
        self._init_git_project(cwd)
        self._git(cwd, "remote", "add", "origin", "https://example.com/org/repo.git")

        with self.subTest("malformed json"):
            with unittest.mock.patch(
                "memory_seed.core._gh_text",
                side_effect=[
                    (0, "gh version 2.0.0", ""),
                    (0, "", ""),
                    (
                        0,
                        json.dumps(
                            {
                                "nameWithOwner": "org/repo",
                                "defaultBranchRef": {"name": "main"},
                                "branchProtectionRules": [],
                            }
                        ),
                        "",
                    ),
                    (0, "{not-json", ""),
                    (0, "{still-not-json", ""),
                ],
            ):
                mode, reason = suggest_integration_mode(cwd)
            self.assertEqual(mode, "local-merge")
            self.assertIn("no team PR signals", reason)

        with self.subTest("failing collaborator query"):
            with unittest.mock.patch(
                "memory_seed.core._gh_text",
                side_effect=[
                    (0, "gh version 2.0.0", ""),
                    (0, "", ""),
                    (
                        0,
                        json.dumps(
                            {
                                "nameWithOwner": "org/repo",
                                "defaultBranchRef": {"name": "main"},
                                "branchProtectionRules": [],
                            }
                        ),
                        "",
                    ),
                    (0, "[]", ""),
                    (1, "", "boom"),
                ],
            ):
                mode, reason = suggest_integration_mode(cwd)
            self.assertEqual(mode, "local-merge")
            self.assertIn("no team PR signals", reason)

    def test_integration_mode_contract_has_live_seed_parity(self):
        pairs = (
            (
                Path(".memory-seed/agent-rules.md"),
                Path("memory_seed/seed/.memory-seed/agent-rules.md"),
            ),
            (
                Path(".memory-seed/project-bootstrap.md"),
                Path("memory_seed/seed/.memory-seed/project-bootstrap.md"),
            ),
            (
                Path(".memory-seed/skills/agent_collaboration.md"),
                Path("memory_seed/seed/.memory-seed/skills/agent_collaboration.md"),
            ),
            (
                Path(".memory-seed/skills/session_logging.md"),
                Path("memory_seed/seed/.memory-seed/skills/session_logging.md"),
            ),
        )
        for live, seed in pairs:
            self.assertEqual(live.read_text(encoding="utf-8"), seed.read_text(encoding="utf-8"))

        rules = pairs[0][0].read_text(encoding="utf-8")
        collaboration = pairs[2][0].read_text(encoding="utf-8")
        bootstrap = pairs[1][0].read_text(encoding="utf-8")
        self.assertIn("integration_mode", rules)
        self.assertIn("local-merge", rules)
        self.assertIn("normal non-force push and PR", rules)
        self.assertIn("integration_artifact", collaboration)
        self.assertIn("from the task branch", collaboration)
        self.assertIn("human confirms", bootstrap)
        self.assertIn("never silently changed", bootstrap)

    def test_write_integration_mode_refuses_unreadable_existing_config(self):
        import unittest.mock

        from memory_seed.core import write_integration_mode

        cwd = self.make_project()
        config = cwd / MEMORY_DIR_NAME / "project.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = b"participants:\n  - slug: jean\n"
        config.write_bytes(original_bytes)
        original_read_text = Path.read_text

        def fail_config_read(path, *args, **kwargs):
            if path == config:
                raise OSError("simulated read failure")
            return original_read_text(path, *args, **kwargs)

        with unittest.mock.patch.object(Path, "read_text", new=fail_config_read):
            with self.assertRaisesRegex(ValueError, "cannot read existing"):
                write_integration_mode(cwd, "pr")

        self.assertEqual(config.read_bytes(), original_bytes)

    def test_update_preserves_declared_integration_mode(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        project_config = cwd / MEMORY_DIR_NAME / "project.yaml"
        project_config.write_text("integration_mode: pr\n", encoding="utf-8")

        update_project(cwd=cwd)

        self.assertEqual(project_config.read_text(encoding="utf-8"), "integration_mode: pr\n")


if __name__ == "__main__":
    unittest.main()
