import datetime
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SessionLogOrderingHookTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-log-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-order-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed" / "sessions").mkdir(parents=True)
        return path

    def make_git_project(self):
        cwd = self.make_project()
        (cwd / "tracked.txt").write_text("alpha\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=cwd, check=True)
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=cwd, check=True)
        return cwd

    def _flat_target(self, cwd, day):
        path = cwd / ".memory-seed" / "sessions" / day[:7] / f"{day}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _user_target(self, cwd, day, user):
        path = cwd / ".memory-seed" / "sessions" / day[:7] / day / f"{user}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _write_two_participants(self, cwd):
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "  - slug: amina\n"
            "    initials: AM\n",
            encoding="utf-8",
        )

    def _write_entry(self, cwd, when=None, title="entry", entry_id="mse_0123456789abcdef"):
        when = when or datetime.datetime.now()
        day = when.strftime("%Y-%m-%d")
        target = self._flat_target(cwd, day)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(
            existing
            + f"## {when.strftime('%Y-%m-%d %H:%M')} - {title}\n\n"
            + "```yaml\n"
            + f"entry_id: {entry_id}\n"
            + "user_initials: JNL\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            + "```\n\n### Summary\n\n- test\n\n### Validation\n\n- test\n",
            encoding="utf-8",
        )
        return target

    def _run_payload(self, cwd, payload=None, *args, env=None):
        completed = subprocess.run(
            [os.sys.executable, str(self.SCRIPT), *args],
            cwd=cwd,
            input=json.dumps(payload or {}),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return completed.stdout

    def _run(self, cwd, *args):
        return self._run_payload(cwd, {}, *args)

    def _establish_debt(self, cwd):
        self._write_entry(cwd)
        self._run(cwd)
        (cwd / "tracked.txt").write_text("beta\n", encoding="utf-8")

    def test_out_of_order_entries_trigger_warning_even_when_git_is_unavailable(self):
        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        self._flat_target(cwd, today).write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("ORDER WARNING", self._run(cwd))

    def test_in_order_entries_do_not_trigger_order_warning(self):
        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        self._flat_target(cwd, today).write_text(
            f"## {today} 01:45 - earlier\n\ntext\n\n## {today} 02:00 - later\n\ntext\n",
            encoding="utf-8",
        )
        self.assertNotIn("ORDER WARNING", self._run(cwd))

    def test_time_alone_does_not_create_debt_or_escalation(self):
        cwd = self.make_git_project()
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        self._write_entry(cwd, old)
        first = self._run(cwd, "--codex")
        second = self._run(cwd, "--codex")
        third = self._run(cwd, "--codex")

        self.assertIn("SELF-CHECK", first)
        self.assertEqual(second.strip(), "")
        self.assertEqual(third.strip(), "")
        self.assertNotIn("repeated", first.lower())
        self.assertNotIn("checks in a row", first.lower())

    def test_no_session_file_does_not_manufacture_debt(self):
        cwd = self.make_git_project()
        self.assertEqual(self._run(cwd).strip(), "")

    def test_stop_output_supports_claude_and_vscode_shapes(self):
        cwd = self.make_git_project()
        self._establish_debt(cwd)
        data = json.loads(
            self._run_payload(
                cwd,
                {"hook_event_name": "Stop", "session_id": "vscode-1", "stop_hook_active": False},
            )
        )
        self.assertEqual(data["decision"], "block")
        self.assertEqual(data["hookSpecificOutput"]["decision"], "block")
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "Stop")
        self.assertEqual(data["reason"], data["hookSpecificOutput"]["reason"])
        self.assertIn("SESSION RECORD CHECKPOINT", data["reason"])

    def test_stop_hook_active_suppresses_repeat_block(self):
        cwd = self.make_git_project()
        self._establish_debt(cwd)
        out = self._run_payload(
            cwd,
            {"hook_event_name": "Stop", "session_id": "vscode-1", "stop_hook_active": True},
        )
        self.assertEqual(out.strip(), "")

    def test_copilot_agent_stop_uses_top_level_decision(self):
        cwd = self.make_git_project()
        self._establish_debt(cwd)
        data = json.loads(
            self._run_payload(
                cwd,
                {"sessionId": "copilot-1", "stop_hook_active": False},
                "--copilot",
            )
        )
        self.assertEqual(data["decision"], "block")
        self.assertNotIn("hookSpecificOutput", data)

    def test_copilot_agent_stop_skips_vscode_compatible_replay(self):
        cwd = self.make_git_project()
        self._establish_debt(cwd)
        out = self._run_payload(
            cwd,
            {"hook_event_name": "Stop", "session_id": "vscode-1", "stop_hook_active": False},
            "--copilot",
        )
        self.assertEqual(out.strip(), "")

    def test_clean_advisory_uses_entry_timestamp_not_file_mtime(self):
        cwd = self.make_git_project()
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        target = self._write_entry(cwd, old)
        os.utime(target, None)
        out = self._run(cwd, "--codex")
        self.assertIn("SELF-CHECK", out)

    def test_user_scoped_order_warning_checks_only_selected_file(self):
        cwd = self.make_project()
        self._write_two_participants(cwd)
        today = datetime.date.today().isoformat()
        self._user_target(cwd, today, "jean").write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self._user_target(cwd, today, "amina").write_text(
            f"## {today} 01:00 - amina\n\ntext\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env["MEMORY_SEED_USER"] = "jean"
        out = self._run_payload(cwd, {}, env=env)
        self.assertIn("ORDER WARNING", out)
        self.assertIn(f".memory-seed/sessions/{today[:7]}/{today}/jean.md", out)

    def test_user_scoped_state_targets_only_the_selected_user(self):
        cwd = self.make_git_project()
        self._write_two_participants(cwd)
        env = os.environ.copy()
        env["MEMORY_SEED_USER"] = "jean"
        self._run_payload(cwd, {}, "--codex", env=env)
        state = json.loads(
            (cwd / ".memory-seed" / ".session-log-check-state").read_text(encoding="utf-8")
        )
        today = datetime.date.today().isoformat()
        self.assertEqual(state["target"], f".memory-seed/sessions/{today[:7]}/{today}/jean.md")

    def test_state_file_is_versioned_and_has_no_miss_counter(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        self._run(cwd)
        state = json.loads(
            (cwd / ".memory-seed" / ".session-log-check-state").read_text(encoding="utf-8")
        )
        self.assertEqual(state["schema_version"], 2)
        self.assertIn("baseline_head", state)
        self.assertIn("pending_checkpoint", state)
        self.assertIn("clean_advisory_entry", state)
        self.assertIn("last_mechanical_resolution", state)
        self.assertNotIn("consecutive_misses", state)

    def test_corrupt_state_file_fails_open(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        state = cwd / ".memory-seed" / ".session-log-check-state"
        state.write_text("not valid json {{{", encoding="utf-8")
        (cwd / "tracked.txt").write_text("beta\n", encoding="utf-8")
        self.assertEqual(self._run(cwd).strip(), "")

    def test_git_diff_trigger_fires_on_new_file_even_with_a_fresh_entry(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        self._run(cwd)
        (cwd / "RELEASE.md").write_text("checklist\n", encoding="utf-8")
        out = self._run(cwd)
        self.assertIn("SESSION RECORD CHECKPOINT", out)
        self.assertIn("worktree evidence", out)

    def test_dirty_file_predating_the_entry_is_covered_by_initial_baseline(self):
        cwd = self.make_git_project()
        (cwd / "tracked.txt").write_text("already dirty\n", encoding="utf-8")
        self._write_entry(cwd)
        self.assertEqual(self._run(cwd).strip(), "")

    def test_new_entry_clears_debt_without_retriggering_same_diff(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        self._run(cwd)
        (cwd / "RELEASE.md").write_text("checklist\n", encoding="utf-8")
        self.assertIn("SESSION RECORD CHECKPOINT", self._run(cwd))
        self._write_entry(
            cwd,
            datetime.datetime.now() + datetime.timedelta(minutes=1),
            title="logged it",
            entry_id="mse_fedcba9876543210",
        )
        self.assertEqual(self._run(cwd).strip(), "")
        self.assertEqual(self._run(cwd).strip(), "")

    def test_reediting_a_covered_dirty_file_creates_new_debt(self):
        cwd = self.make_git_project()
        (cwd / "RELEASE.md").write_text("checklist\n", encoding="utf-8")
        self._write_entry(cwd)
        self._run(cwd)
        with (cwd / "RELEASE.md").open("a", encoding="utf-8") as handle:
            handle.write("extra line\n")
        self.assertIn("SESSION RECORD CHECKPOINT", self._run(cwd))

    def test_session_log_changes_do_not_self_trigger(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        self._run(cwd)
        self._write_entry(
            cwd,
            datetime.datetime.now() + datetime.timedelta(minutes=1),
            title="later",
            entry_id="mse_fedcba9876543210",
        )
        self.assertEqual(self._run(cwd).strip(), "")

    def test_git_check_fails_open_outside_a_repository(self):
        cwd = self.make_project()
        self._write_entry(cwd)
        (cwd / "RELEASE.md").write_text("checklist\n", encoding="utf-8")
        out = self._run(cwd)
        self.assertNotIn("SESSION RECORD CHECKPOINT", out)

    def test_changed_head_creates_debt_with_a_clean_tree(self):
        cwd = self.make_git_project()
        self._write_entry(cwd)
        self._run(cwd)
        (cwd / "tracked.txt").write_text("beta\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "head change"], cwd=cwd, check=True)
        out = self._run(cwd)
        self.assertIn("SESSION RECORD CHECKPOINT", out)
        self.assertIn("head evidence", out)
if __name__ == "__main__":
    unittest.main()
