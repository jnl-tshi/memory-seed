"""file-touch-decisions.py hook tests (file-touch-decision-surfacing-proposal.md).

The hook is exercised the way agents exercise it: as a subprocess fed PostToolUse
JSON on stdin, cwd = a workspace with a real-ish session store. Contract under
test: match fires with decision text + the duty line; a superseded match surfaces
its successor prominently; unmatched paths and non-edit tools emit nothing; the
stamp suppresses repeat fires per session; malformed input exits 0 silently; and
surfaced ids land in the retrieval log as weight-zero "file_touch" events.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "memory_seed" / "seed" / ".memory-seed" / "hooks" / "file-touch-decisions.py"

sys.path.insert(0, str(REPO_ROOT))
from memory_seed.attention import load_attention  # noqa: E402


class FileTouchHookTests(unittest.TestCase):
    def make_workspace(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-file-touch-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        sessions = root / ".memory-seed" / "sessions" / "2026-06"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-10.md").write_text(
            "## 2026-06-10 09:30 - Slugify separator policy\n\n"
            "```yaml\n"
            "entry_id: mse_seedhyphens0\n"
            "user_initials: JN\n"
            "agent_type: claude\n"
            "```\n\n"
            "### Decision\n\n"
            "- D: slugify collapses ALL non-alphanumerics to hyphens.\n"
            "- R: one separator, one canonical URL.\n"
            "- F: `strutil/text.py`.\n",
            encoding="utf-8",
        )
        return root

    def run_hook(self, cwd, payload, extra_args=()):
        proc = subprocess.run(
            [sys.executable, str(HOOK), *extra_args],
            cwd=cwd,
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def edit_payload(self, root, rel="strutil/text.py", session="sess-1", tool="Edit"):
        return {
            "session_id": session,
            "tool_name": tool,
            "tool_input": {"file_path": str(root / rel)},
        }

    def vscode_edit_payload(self, root, session="sess-vscode"):
        return {
            "hook_event_name": "PostToolUse",
            "session_id": session,
            "tool_name": "editFiles",
            "tool_input": {
                "files": [
                    str(root / "strutil" / "unrelated.py"),
                    str(root / "strutil" / "text.py"),
                ]
            },
        }

    def test_match_fires_with_decision_and_duty_line(self):
        root = self.make_workspace()
        out = self.run_hook(root, self.edit_payload(root))
        self.assertTrue(out, "expected an injection")
        message = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Slugify separator policy", message)
        self.assertIn("mse_seedhyphens0", message)
        self.assertIn("- R: one separator", message)
        self.assertIn("`replaces` or `evolves` edge", message)

    def test_superseded_match_surfaces_successor(self):
        root = self.make_workspace()
        sessions = root / ".memory-seed" / "sessions" / "2026-06"
        (sessions / "2026-06-20.md").write_text(
            "## 2026-06-20 14:00 - Underscores preserved after all\n\n"
            "```yaml\n"
            "entry_id: mse_seedunderscore1\n"
            "replaces:\n"
            "  - mse_seedhyphens0\n"
            "```\n\n"
            "- D: preserve underscores.\n"
            "- R: config keys round-trip.\n"
            "- F: `strutil/text.py`.\n",
            encoding="utf-8",
        )
        message = json.loads(self.run_hook(root, self.edit_payload(root)))[
            "hookSpecificOutput"
        ]["additionalContext"]
        self.assertIn("SUPERSEDED by mse_seedunderscore1", message)

    def test_unmatched_path_and_non_edit_tool_emit_nothing(self):
        root = self.make_workspace()
        self.assertEqual(
            self.run_hook(root, self.edit_payload(root, rel="strutil/config.py")), ""
        )
        payload = self.edit_payload(root)
        payload["tool_name"] = "Read"
        self.assertEqual(self.run_hook(root, payload), "")

    def test_vscode_edit_files_payload_surfaces_matching_file(self):
        root = self.make_workspace()
        out = self.run_hook(root, self.vscode_edit_payload(root))
        message = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("strutil/text.py", message)
        self.assertIn("Slugify separator policy", message)

    def test_vscode_camel_case_file_path_is_supported(self):
        root = self.make_workspace()
        payload = {
            "hook_event_name": "PostToolUse",
            "session_id": "sess-vscode-path",
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": str(root / "strutil" / "text.py")},
        }
        out = self.run_hook(root, payload)
        self.assertIn("Slugify separator policy", out)

    def test_copilot_camel_case_payload_uses_additional_context(self):
        root = self.make_workspace()
        payload = {
            "sessionId": "sess-copilot",
            "toolName": "edit",
            "toolArgs": {"filePath": str(root / "strutil" / "text.py")},
        }
        data = json.loads(self.run_hook(root, payload, ("--copilot",)))
        self.assertIn("Slugify separator policy", data["additionalContext"])

    def test_copilot_hook_skips_vscode_compatible_replay(self):
        root = self.make_workspace()
        out = self.run_hook(root, self.vscode_edit_payload(root), ("--copilot",))
        self.assertEqual(out, "")

    def test_stamp_suppresses_second_fire_per_session(self):
        root = self.make_workspace()
        first = self.run_hook(root, self.edit_payload(root, session="sess-A"))
        self.assertTrue(first)
        second = self.run_hook(root, self.edit_payload(root, session="sess-A"))
        self.assertEqual(second, "")
        other_session = self.run_hook(root, self.edit_payload(root, session="sess-B"))
        self.assertTrue(other_session, "a new session gets its own injection")

    def test_malformed_input_and_missing_store_exit_silently(self):
        root = self.make_workspace()
        self.assertEqual(self.run_hook(root, "not json {"), "")
        bare = Path(tempfile.mkdtemp(prefix="memory-seed-file-touch-bare-"))
        self.addCleanup(lambda: shutil.rmtree(bare, ignore_errors=True))
        self.assertEqual(self.run_hook(bare, self.edit_payload(bare)), "")

    def test_surfaced_ids_logged_at_weight_zero(self):
        root = self.make_workspace()
        self.run_hook(root, self.edit_payload(root))
        log = root / ".memory-seed" / ".retrieval-log.jsonl"
        self.assertTrue(log.exists())
        events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events[0]["tool"], "file_touch")
        self.assertEqual(events[0]["entry_id"], "mse_seedhyphens0")
        # Weight zero: a file_touch event never scores in the attention fold.
        self.assertEqual(load_attention(root / ".memory-seed"), {})

    def test_live_and_seed_copies_identical(self):
        live = REPO_ROOT / ".memory-seed" / "hooks" / "file-touch-decisions.py"
        self.assertEqual(live.read_bytes(), HOOK.read_bytes())


if __name__ == "__main__":
    unittest.main()
