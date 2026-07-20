import shutil
import tempfile
import unittest
from pathlib import Path



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

    def test_injects_five_newest_entries_and_startup_directive(self):
        import json

        cwd = self.make_project({
            "2026-01-01.md": (
                "## 2026-01-01 08:00 - Excluded old work\n\ndrop me\n\n"
                "## 2026-01-01 09:00 - Prior context\n\nkeep prior\n"
            ),
            "2026-02-02.md": (
                "## 2026-02-02 10:00 - First entry\n\nbody A\n\n"
                "## 2026-02-02 11:00 - Second entry\n\nbody B\n\n"
                "## 2026-02-02 12:00 - Third entry\n\nbody C\n\n"
                "## 2026-02-02 14:30 - Latest entry title\n\nthe newest body\n"
            ),
        })

        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        self.assertIn("`AGENTS.md`", context)
        self.assertIn("Read the five newest applicable entries", context)
        self.assertIn("Newest 5 session entries", context)
        # The window spans files when the newest file has fewer than five entries.
        self.assertIn(".memory-seed/sessions/2026-02-02.md", context)
        self.assertIn(".memory-seed/sessions/2026-01-01.md", context)
        self.assertIn("2026-01-01 09:00 - Prior context", context)
        self.assertNotIn("Excluded old work", context)
        self.assertNotIn("drop me", context)
        self.assertIn("2026-02-02 10:00 - First entry", context)
        self.assertIn("2026-02-02 14:30 - Latest entry title", context)
        self.assertIn("the newest body", context)
        self.assertIn("Use memory_search only for topical questions", context)

    def test_cursor_uses_additional_context_field(self):
        import json

        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})
        out = self._run(cwd, "--cursor")
        data = json.loads(out)
        self.assertIn("additional_context", data)
        self.assertNotIn("hookSpecificOutput", data)
        self.assertIn("`AGENTS.md`", data["additional_context"])

    def test_all_dynamic_agent_outputs_include_startup_directive(self):
        import json

        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})
        cases = (
            ((), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--codex",), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--gemini",), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--cursor",), lambda data: data["additional_context"]),
        )
        for args, context_from in cases:
            with self.subTest(agent=args or ("claude",)):
                context = context_from(json.loads(self._run(cwd, *args)))
                self.assertIn("`AGENTS.md`", context)
                self.assertIn("five newest applicable entries", context)

    def test_caps_long_latest_entry(self):
        import json

        big = "## 2026-02-02 10:00 - Huge\n\n" + ("x" * 5000) + "\n"
        cwd = self.make_project({"2026-02-02.md": big})
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("truncated", context)

    def test_empty_sessions_dir_still_emits_startup_directive(self):
        import json

        cwd = self.make_project({})
        (cwd / ".memory-seed" / "local.yaml").write_text("user: jean\n", encoding="utf-8")
        context = json.loads(self._run(cwd))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("`AGENTS.md`", context)
        self.assertIn("No applicable session entries were found yet.", context)

    def test_missing_sessions_dir_still_emits_startup_directive(self):
        import json

        path = Path(tempfile.mkdtemp(prefix="memory-seed-startup-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        context = json.loads(self._run(path))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("`AGENTS.md`", context)
        self.assertIn("No applicable session entries were found yet.", context)

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

    def _write_participants(self, cwd, count=2):
        slugs = [("jean", "JN"), ("amina", "AM"), ("theo", "TH")][:count]
        lines = ["participants:"]
        for slug, initials in slugs:
            lines.append(f"  - slug: {slug}")
            lines.append(f"    initials: {initials}")
        (cwd / ".memory-seed" / "project.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

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
        self._write_participants(cwd)

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        self.assertIn("Source: .memory-seed/sessions/2026-02-02/jean.md", context)
        self.assertIn("jean newest body", context)
        self.assertIn("Co-contributor session files for 2026-02-02:", context)
        self.assertIn(".memory-seed/sessions/2026-02-02/amina.md (1 entry)", context)
        self.assertNotIn("amina body", context)

    def test_configured_user_ignored_with_fewer_than_two_participants(self):
        import json

        # A per-user file exists, but with no participants: registered the
        # env-var user should be gated back to flat lookup - and since there's
        # no flat file either, the hook reports no applicable entries.
        cwd = self.make_project({
            "2026-02-02/jean.md": "## 2026-02-02 10:00 - Jean entry\n\nbody\n",
        })
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No applicable session entries were found yet.", context)
        self.assertNotIn("jean body", context)

        # With exactly one participant registered, still gated to flat.
        self._write_participants(cwd, count=1)
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No applicable session entries were found yet.", context)

        # A flat file is found once gated back, even though a per-user file
        # for the same date also exists.
        flat = cwd / ".memory-seed" / "sessions" / "2026-02-02.md"
        flat.write_text("## 2026-02-02 09:00 - Flat entry\n\nflat body\n", encoding="utf-8")
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Source: .memory-seed/sessions/2026-02-02.md", context)
        self.assertIn("flat body", context)

    def test_explicit_user_arg_bypasses_participant_gate(self):
        import json

        cwd = self.make_project({
            "2026-02-02/jean.md": "## 2026-02-02 10:00 - Jean entry\n\njean body\n",
        })
        out = self._run(cwd, "--user=jean")
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("jean body", context)

    def test_identity_offer_fires_once_then_never_again(self):
        cwd = self.make_project({})

        first = self._run(cwd).strip()
        self.assertIn("No local Memory Seed identity is configured", first)
        self.assertIn("AGENTS.md", first)
        self.assertTrue((cwd / ".memory-seed" / ".identity-offer-stamp").exists())

        second = self._run(cwd).strip()
        self.assertIn("AGENTS.md", second)
        self.assertNotIn("No local Memory Seed identity is configured", second)

    def test_identity_offer_skipped_when_user_already_configured(self):
        cwd = self.make_project({})
        (cwd / ".memory-seed" / "local.yaml").write_text("user: jean\n", encoding="utf-8")

        self.assertIn("AGENTS.md", self._run(cwd))
        self.assertFalse((cwd / ".memory-seed" / ".identity-offer-stamp").exists())

    def test_identity_offer_appended_alongside_project_state(self):
        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})

        out = self._run(cwd)
        self.assertIn("No local Memory Seed identity is configured", out)
        self.assertIn("Newest 1 session entry", out)

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

        # The quoted heading stays inside the one real entry rather than
        # becoming a second context entry.
        self.assertIn("Newest 1 session entry", context)
        self.assertEqual(context.count("## 2026-02-02 10:00 - Real entry"), 1)
        self.assertIn("Here is an example heading we quote", context)
        self.assertIn("real entry trailing content", context)

    def test_seed_and_live_hook_match(self):
        live = Path(".memory-seed/hooks/session-start-context.py")
        seed = Path("memory_seed/seed/.memory-seed/hooks/session-start-context.py")
        self.assertEqual(
            live.read_text(encoding="utf-8"),
            seed.read_text(encoding="utf-8"),
        )

    def test_seed_and_live_agent_rules_match(self):
        live = Path(".memory-seed/agent-rules.md")
        seed = Path("memory_seed/seed/.memory-seed/agent-rules.md")
        self.assertEqual(
            live.read_text(encoding="utf-8"),
            seed.read_text(encoding="utf-8"),
        )
