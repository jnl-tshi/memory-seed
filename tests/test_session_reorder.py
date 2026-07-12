"""`session reorder` (P2): restore chronological order in one day's session
file as a PURE block permutation - entry bytes are never altered, only block
order. Dry-run by default; refuses rather than guesses on anything that would
make the permutation ambiguous.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, check_session_links, session_reorder

A = "mse_" + "a" * 16
B = "mse_" + "b" * 16
C = "mse_" + "c" * 16


def _entry(dt, eid, title, body="- note"):
    return f"## {dt} - {title}\n\n```yaml\nentry_id: {eid}\n```\n\n{body}\n\n"


class SessionReorderTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-reorder-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.month = self.sessions / "2026-06"
        self.month.mkdir(parents=True, exist_ok=True)
        self.path = self.month / "2026-06-13.md"

    def test_dry_run_plans_swap_without_writing(self):
        text = (
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-13 09:00", A, "first")
            + _entry("2026-06-13 11:00", C, "third-out-of-order")
            + _entry("2026-06-13 10:00", B, "second")
        )
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13")

        self.assertTrue(result.ok)
        self.assertTrue(result.changed)
        self.assertFalse(result.applied)
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)  # untouched
        self.assertEqual(
            [item.split(" - ", 1)[1] for item in result.order_after],
            ["first", "second", "third-out-of-order"],
        )

    def test_apply_is_a_byte_pure_permutation(self):
        before = (
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-13 11:00", C, "later-logged-first", body="- unique C body")
            + _entry("2026-06-13 09:00", A, "earlier", body="- unique A body")
        )
        self.path.write_text(before, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13", apply=True)
        after = self.path.read_text(encoding="utf-8")

        self.assertTrue(result.ok)
        self.assertTrue(result.applied)
        self.assertNotEqual(after, before)
        # Same bytes, different order: nothing added, edited, or lost.
        self.assertEqual(sorted(after), sorted(before))
        self.assertLess(after.index("earlier"), after.index("later-logged-first"))
        self.assertIn("- unique A body", after)
        self.assertIn("- unique C body", after)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_already_chronological_is_a_no_op(self):
        text = (
            _entry("2026-06-13 09:00", A, "first")
            + _entry("2026-06-13 10:00", B, "second")
        )
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13", apply=True)

        self.assertTrue(result.ok)
        self.assertFalse(result.changed)
        self.assertFalse(result.applied)
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_equal_timestamps_keep_original_relative_order(self):
        text = (
            _entry("2026-06-13 10:00", B, "tie-logged-first")
            + _entry("2026-06-13 10:00", C, "tie-logged-second")
            + _entry("2026-06-13 09:00", A, "earlier")
        )
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13")

        titles = [item.split(" - ", 1)[1] for item in result.order_after]
        self.assertEqual(titles, ["earlier", "tie-logged-first", "tie-logged-second"])

    def test_refuses_non_timestamped_heading(self):
        text = _entry("2026-06-13 10:00", B, "fine") + "## A stray heading\n\ncontent\n"
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13", apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(any("not a timestamped entry" in issue for issue in result.issues))
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_missing_file_reports_cleanly(self):
        result = session_reorder(self.cwd, date_str="2026-06-14")
        self.assertFalse(result.ok)
        self.assertIn("no session file", result.issues[0])


if __name__ == "__main__":
    unittest.main()
