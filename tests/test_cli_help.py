import shutil
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
)


class CliHelpTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-cli-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _run(self, argv):
        import contextlib
        import io

        from memory_seed.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def _git_repo_with_commit(self, cwd):
        import subprocess

        subprocess.run(["git", "-C", str(cwd), "init", "-q"], check=True, capture_output=True)
        (cwd / "README.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-C", str(cwd),
                "-c", "user.name=test", "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "-m", "initial",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(cwd), "branch", "-M", "main"], check=True, capture_output=True)

    def test_help_command_lists_all_commands(self):
        code, out = self._run(["help"])
        self.assertEqual(code, 0)
        for command in ("init", "update", "compact", "doctor", "version", "migrate", "help"):
            self.assertIn(command, out)
        self.assertIn("Keeping Memory Seed current", out)

    def test_no_command_prints_help(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("Keeping Memory Seed current", out)

    def test_lense_command_is_a_deprecation_shim_to_memory_trace(self):
        # The review UI moved behind the optional `trace` extra and the
        # `memory-trace` command. When the extra is not installed (as in the
        # core-only test env), `memory-seed lense` points the user there and
        # exits non-zero - core ships no web stack.
        import contextlib
        import io
        import sys
        from unittest import mock

        from memory_seed.cli import main

        # Simulate the core-only environment deterministically: memory_trace
        # ships in the wheel (only fastapi is the extra), so on a dev machine
        # with the extra installed this test would otherwise take the
        # with-trace path and even start a real server. None in sys.modules
        # makes the service import raise ImportError in every environment.
        stderr = io.StringIO()
        with mock.patch.dict(
            sys.modules, {"memory_trace": None, "memory_trace.service": None}
        ):
            with contextlib.redirect_stderr(stderr):
                code = main(["lense", "--no-open"])
        self.assertEqual(code, 1)
        self.assertIn("memory-trace", stderr.getvalue())
        self.assertIn("moved", stderr.getvalue())

    def test_lense_open_both_is_forwarded_to_trace_service(self):
        import sys
        import types
        from unittest import mock

        from memory_seed.cli import main

        run_server = mock.Mock(return_value=0)
        trace_module = types.ModuleType("memory_trace")
        service_module = types.ModuleType("memory_trace.service")
        service_module.run_server = run_server

        with mock.patch.dict(
            sys.modules,
            {"memory_trace": trace_module, "memory_trace.service": service_module},
        ):
            code = main(["lense", "--open-both"])

        self.assertEqual(code, 0)
        self.assertTrue(run_server.call_args.args[0].open_both)

    def test_skills_list_shows_profiles_and_current_state(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--profile", "coding"])[0], 0)
            code, out = self._run(["skills", "list"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Core skills:", out)
        self.assertIn("Installed optional skills:", out)
        self.assertIn("Ignored optional skills:", out)
        self.assertIn("Profiles:", out)
        self.assertIn("coding:", out)
        self.assertIn("code_search.md", out)
        self.assertIn("proposal_lifecycle.md", out)

    def test_skills_add_remove_and_ignored_cli(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--no-skill-prompt"])[0], 0)
            self.assertEqual(self._run(["skills", "add", "proposal_lifecycle.md"])[0], 0)
            self.assertTrue((project / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
            self.assertEqual(self._run(["skills", "remove", "proposal_lifecycle.md"])[0], 0)
            self.assertFalse((project / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
            code, out = self._run(["skills", "ignored"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("proposal_lifecycle.md", out)

    def test_skills_add_rejects_unknown_name(self):
        import contextlib
        import io
        import os

        from memory_seed.cli import main

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--no-skill-prompt"])[0], 0)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(["skills", "add", "not-a-skill"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("Unknown skill or profile", stderr.getvalue())

    def test_init_reports_selected_and_ignored_agents(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--agents", "codex", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents: codex", out)
        self.assertIn("Ignored agents:", out)
        self.assertIn("claude", out)
        self.assertIn("gemini", out)
        self.assertNotIn("Ignored agents: (none)", out)

    def test_init_accepts_no_agent_prompt_flag(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents:", out)
        self.assertIn("Ignored agents: (none)", out)

    def test_init_can_opt_out_of_all_agents(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--agents", "none", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents: (none)", out)
        self.assertIn("Ignored agents:", out)
        self.assertFalse((project / "CLAUDE.md").exists())
        self.assertFalse((project / "GEMINI.md").exists())
        self.assertFalse((project / ".codex").exists())
        self.assertTrue((project / "AGENTS.md").exists())
        self.assertTrue((project / ".memory-seed" / "agent-rules.md").exists())
        self.assertIn("agents:\n", (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_branch_status_cli_warns_on_dirty_main(self):
        import os
        import subprocess

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            (project / "README.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "-m", "initial",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            (project / "README.txt").write_text("changed", encoding="utf-8")
            code, out = self._run(["branch", "status"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Branch: main", out)
        self.assertIn("Dirty: yes", out)
        self.assertIn("task branch", out)
        self.assertIn("--no-ff", out)

    @pytest.mark.integration
    def test_branch_status_cli_json_reports_feature_branch(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            (project / "README.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "-m", "initial",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-topic"], check=True, capture_output=True)
            code, out = self._run(["branch", "status", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["branch"], "feature-topic")
        self.assertFalse(data["is_integration_branch"])
        self.assertIn("merge --no-ff", data["recommendation"])

    @pytest.mark.integration
    def test_worktree_guard_cli_blocks_root_write_intent_without_override(self):
        import os

        project = self.make_project()
        self._git_repo_with_commit(project)
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["worktree", "guard", "--agent", "codex", "--write-intent"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("Classification: root-checkout", out)
        self.assertIn("Safe to write: no", out)
        self.assertIn("--allow-root-write", out)

    @pytest.mark.integration
    def test_worktree_guard_cli_json_reports_owned_worktree(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        self._git_repo_with_commit(project)
        worktree = project / ".codex" / "worktrees" / "cli-task"
        worktree.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(project), "worktree", "add", "-q", "-b", "codex/cli-task", str(worktree)],
            check=True,
            capture_output=True,
        )
        cwd = Path.cwd()
        try:
            os.chdir(worktree)
            code, out = self._run(["worktree", "guard", "--agent", "codex", "--write-intent", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["classification"], "owned-worktree")
        self.assertTrue(data["safe_to_write"])

    @pytest.mark.integration
    def test_worktree_status_cli_without_agent_is_read_only_observation(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        self._git_repo_with_commit(project)
        worktree = project / ".codex" / "worktrees" / "status-task"
        worktree.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(project), "worktree", "add", "-q", "-b", "codex/status-task", str(worktree)],
            check=True,
            capture_output=True,
        )
        cwd = Path.cwd()
        try:
            os.chdir(worktree)
            code, out = self._run(["worktree", "status", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["classification"], "owned-worktree")
        self.assertEqual(data["actual_namespace_owner"], "codex")
        self.assertFalse(data["write_intent"])

    def test_interactive_init_prompts_for_agent_opt_out(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("none\nnone\n")
            ):
                code = main(["init"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Which agent integrations should be installed?", out)
        self.assertIn("Recommended default: all", out)
        self.assertIn("Installed agents: (none)", out)
        self.assertIn("Selected optional skills: (none)", out)

    def test_init_refuses_unreadable_existing_integration_config_without_overwrite(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        project = self.make_project()
        config = project / MEMORY_DIR_NAME / "project.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = b"participants:\n  - slug: jean\n"
        config.write_bytes(original_bytes)
        original_read_text = Path.read_text

        def fail_config_read(path, *args, **kwargs):
            if path == config:
                raise OSError("simulated read failure")
            return original_read_text(path, *args, **kwargs)

        cwd = Path.cwd()
        stderr = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stderr(stderr), unittest.mock.patch.object(
                Path, "read_text", new=fail_config_read
            ):
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("cannot read existing", stderr.getvalue())
        self.assertEqual(config.read_bytes(), original_bytes)

    def test_init_noninteractive_writes_default_integration_mode(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, _out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: local-merge", config)

    def test_init_honors_explicit_integration_mode_flag(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, _out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt", "--integration-mode", "pr"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_interactive_init_prompts_for_integration_mode_suggestion(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("\n")
            ), unittest.mock.patch(
                "memory_seed.cli.suggest_integration_mode",
                return_value=("pr", "GitHub reports more than one collaborator"),
            ):
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("How should branch work be integrated?", out)
        self.assertIn("Suggested: pr (GitHub reports more than one collaborator)", out)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_init_preserves_declared_integration_mode_without_reprompt(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        memory_dir = project / ".memory-seed"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "project.yaml").write_text(
            "integration_mode: pr\nparticipants:\n  - slug: jean\n    initials: JN\n",
            encoding="utf-8",
        )
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("")
            ), unittest.mock.patch("memory_seed.cli.suggest_integration_mode") as suggest_mode:
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        suggest_mode.assert_not_called()
        self.assertNotIn("How should branch work be integrated?", out)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_session_integrate_cli_dispatches_pr_mode(self):
        import os
        import unittest.mock

        from memory_seed.core import SessionOpenPrResult

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            with unittest.mock.patch("memory_seed.cli.read_integration_mode", return_value="pr"), unittest.mock.patch(
                "memory_seed.cli.session_open_pr",
                return_value=SessionOpenPrResult(
                    opened=False,
                    dry_run=True,
                    base_branch="main",
                    source_branch="feature-pr",
                    pr_title="Integrate feature-pr into main",
                    pr_body="planned body",
                    planned_entries=["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
                ),
            ):
                code, out = self._run(["session", "integrate", "--branch", "feature-pr", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Integration mode: pr", out)
        self.assertIn("Prepared entry:", out)
        self.assertIn("PR title: Integrate feature-pr into main", out)
        self.assertIn("Dry run - no push or PR performed.", out)

    def test_session_integrate_cli_dispatches_local_merge_mode(self):
        import os
        import unittest.mock

        from memory_seed.core import SessionMergeBranchResult

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            with unittest.mock.patch("memory_seed.cli.read_integration_mode", return_value="local-merge"), unittest.mock.patch(
                "memory_seed.cli.session_merge_branch",
                return_value=SessionMergeBranchResult(
                    committed=False,
                    planned_entries=["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
                ),
            ):
                code, out = self._run(["session", "integrate", "--branch", "feature-merge", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Integration mode: local-merge", out)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn("Dry run - no merge performed.", out)

    def test_user_set_show_clear_and_session_target(self):
        import contextlib

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-user-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        # Per-user session targeting only activates with 2+ participants
        # registered; a lone configured user stays on the flat layout.
        (project / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "  - slug: amina\n"
            "    initials: AM\n",
            encoding="utf-8",
        )

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
            self.assertRegex(out.strip(), r"\.memory-seed/sessions/\d{4}-\d{2}/\d{4}-\d{2}-\d{2}/jean\.md$")

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

    def test_migrate_sessions_layout_cli_dry_run(self):
        import os

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-migrate-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        (project / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n",
            encoding="utf-8",
        )
        (project / ".memory-seed" / "sessions" / "2026-06-21.md").write_text(
            "## 2026-06-21 09:00 - Entry\n\n"
            "```yaml\n"
            "entry_id: ms-11111111\n"
            "user_initials: JN\n"
            "```\n\n"
            "- Body.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            code, out = self._run(["migrate", "sessions-layout", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would migrate: 2026-06-21.md -> 2026-06/2026-06-21/jean.md", out)
        self.assertIn("No files changed.", out)

    def test_migrate_sessions_month_layout_cli_dry_run(self):
        import os

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-month-migrate-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        (project / ".memory-seed" / "sessions" / "2026-06-21.md").write_text(
            "## 2026-06-21 09:00 - Entry\n\n"
            "```yaml\n"
            "entry_id: ms-11111111\n"
            "user_initials: JN\n"
            "```\n\n"
            "- Body.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            code, out = self._run(["migrate", "sessions-month-layout", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would migrate: 2026-06-21.md -> 2026-06/2026-06-21.md", out)
        self.assertIn("No files changed.", out)

    @pytest.mark.integration
    def test_session_fuse_cli_dry_run_reports_imports(self):
        import os
        import subprocess

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-fuse-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        grouped = sessions / "2026-07"
        grouped.mkdir(parents=True, exist_ok=True)
        (grouped / "2026-07-10.md").write_text(
            "---\n"
            "tags:\n"
            "  - session-log\n"
            "  - memory-seed\n"
            "session_date: 2026-07-10\n"
            "---\n\n"
            "## 2026-07-10 09:00 - Base\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "branch: main\n"
            "```\n\n"
            "- Base.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-fuse"], check=True, capture_output=True)
            (sessions / "2026-07-11.md").write_text(
                "---\n"
                "tags:\n"
                "  - session-log\n"
                "  - memory-seed\n"
                "session_date: 2026-07-11\n"
                "---\n\n"
                "## 2026-07-11 09:00 - Feature\n\n"
                "```yaml\n"
                "entry_id: mse_1111111111111111\n"
                "user_initials: JN\n"
                "agent_type: codex\n"
                "branch: feature-fuse\n"
                "```\n\n"
                "- Feature.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "feature"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "main"], check=True, capture_output=True)
            code, out = self._run(["session", "fuse", "--branch", "feature-fuse"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn(".memory-seed/sessions/2026-07/2026-07-11.md", out)

    @pytest.mark.integration
    def test_session_fuse_cli_dry_run_reports_link_sidecar_import(self):
        # Coverage gap closed: every planned_link_sidecars CLI print line (added
        # 2026-07-20 for the P1 sidecar-loss fix) previously executed its `for`
        # header but never its body in any test, since no fixture produced a
        # non-empty list - so the actual "Would import link sidecar:" text was
        # unverified. This drives a real branch-side link sidecar through the CLI.
        import os
        import subprocess

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-fuse-link-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        grouped = sessions / "2026-07"
        grouped.mkdir(parents=True, exist_ok=True)
        (grouped / "2026-07-10.md").write_text(
            "---\n"
            "tags:\n"
            "  - session-log\n"
            "  - memory-seed\n"
            "session_date: 2026-07-10\n"
            "---\n\n"
            "## 2026-07-10 09:00 - Base\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "branch: main\n"
            "```\n\n"
            "- Base.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-fuse"], check=True, capture_output=True)
            link_target = sessions / "links" / "2026-07" / "2026-07-10.md"
            link_target.parent.mkdir(parents=True, exist_ok=True)
            link_target.write_text(
                "---\n"
                "tags:\n"
                "  - session-log-links\n"
                "link_date: 2026-07-10\n"
                "---\n\n"
                "## 2026-07-10 09:15 - Note\n\n"
                "```yaml\n"
                "entry_id: mse_0123456789abcdef\n"
                "related_entries:\n"
                "  - mse_zzzzzzzzzzzzzzzz\n"
                "```\n\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "branch link sidecar"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "main"], check=True, capture_output=True)
            code, out = self._run(["session", "fuse", "--branch", "feature-fuse"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would import link sidecar: mse_0123456789abcdef", out)
        self.assertIn(".memory-seed/sessions/links/2026-07/2026-07-10.md", out)

    @pytest.mark.integration
    def test_session_merge_branch_cli_dry_run_reports_plan(self):
        import os
        import subprocess

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-merge-branch-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        grouped = sessions / "2026-07"
        grouped.mkdir(parents=True, exist_ok=True)
        (grouped / "2026-07-10.md").write_text(
            "---\n"
            "tags:\n"
            "  - session-log\n"
            "  - memory-seed\n"
            "session_date: 2026-07-10\n"
            "---\n\n"
            "## 2026-07-10 09:00 - Base\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "branch: main\n"
            "```\n\n"
            "- Base.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-merge"], check=True, capture_output=True)
            (grouped / "2026-07-11.md").write_text(
                "---\n"
                "tags:\n"
                "  - session-log\n"
                "  - memory-seed\n"
                "session_date: 2026-07-11\n"
                "---\n\n"
                "## 2026-07-11 09:00 - Feature\n\n"
                "```yaml\n"
                "entry_id: mse_1111111111111111\n"
                "user_initials: JN\n"
                "agent_type: codex\n"
                "branch: feature-merge\n"
                "```\n\n"
                "- Feature.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "feature"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "main"], check=True, capture_output=True)
            code, out = self._run(["session", "merge-branch", "--branch", "feature-merge", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn("Dry run - no merge performed.", out)
