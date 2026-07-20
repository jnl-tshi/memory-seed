import shutil
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
        self._flat_target(cwd, today).write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("ORDER WARNING", self._run(cwd))

    def test_in_order_entries_do_not_trigger_order_warning(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        self._flat_target(cwd, today).write_text(
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
        self._flat_target(cwd, day).write_text(
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
        self._flat_target(cwd, today).write_text(
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
        session_file = self._flat_target(cwd, day)
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
        self._write_two_participants(cwd)
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        self._user_target(cwd, today, "amina").write_text(
            f"## {today} {now.strftime('%H:%M')} - Amina recent\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertIn(f".memory-seed/sessions/{today[:7]}/{today}/jean.md", out)
        self.assertNotIn(f".memory-seed/sessions/{today}.md", out)

    def test_user_scoped_order_warning_checks_only_selected_file(self):
        import datetime

        cwd = self.make_project()
        self._write_two_participants(cwd)
        today = datetime.date.today().isoformat()
        self._user_target(cwd, today, "jean").write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self._user_target(cwd, today, "amina").write_text(
            f"## {today} 01:00 - amina\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("ORDER WARNING", out)
        self.assertIn(f".memory-seed/sessions/{today[:7]}/{today}/jean.md", out)

    def _write_stale_entry(self, cwd, minutes_ago=30):
        import datetime

        old = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        self._flat_target(cwd, day).write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )

    def test_first_stale_check_uses_base_wording_not_escalated(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertNotIn("repeated", out)

    def test_second_consecutive_stale_check_escalates_wording(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)
        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER (repeated - 2 checks in a row", out)
        self.assertIn("discipline failure", out)

    def test_escalation_count_keeps_climbing_across_repeated_misses(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)
        self._run(cwd)
        out = self._run(cwd)

        self.assertIn("3 checks in a row", out)

    def test_escalation_resets_once_a_new_entry_is_logged(self):
        import datetime

        cwd = self.make_project()
        self._write_stale_entry(cwd)
        self._run(cwd)
        self._run(cwd)

        # Simulate the agent complying: append a fresh entry before the next check.
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        target = self._flat_target(cwd, today)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(
            existing + f"\n## {today} {now.strftime('%H:%M')} - caught up\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run(cwd)

        self.assertEqual(out.strip(), "")

    def test_state_file_written_under_memory_seed_directory(self):
        import json

        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)

        state_path = cwd / ".memory-seed" / ".session-log-check-state"
        self.assertTrue(state_path.exists())
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["consecutive_misses"], 1)

    def test_corrupt_state_file_fails_open(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)
        (cwd / ".memory-seed" / ".session-log-check-state").write_text(
            "not valid json {{{", encoding="utf-8"
        )

        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertNotIn("repeated", out)
