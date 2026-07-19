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


class SessionWriterOrderingTests(unittest.TestCase):
    """The tie-break contract the fuse writers depend on.

    Callers hand the writer [existing-file-order..., incoming...]. A stable sort
    on the timestamp alone must therefore leave existing entries exactly where
    they were and append incoming ones after any same-minute neighbours. This is
    what stops a fuse from re-positioning history it never touched.
    """

    def _records(self, pairs):
        from memory_seed.core import _SessionEntryRecord

        return [
            _SessionEntryRecord(
                entry_id=eid, timestamp=ts, session_date=ts[:10], user=None,
                branch=None, source_path="x.md", target_path="x.md", text=f"## {ts} - {eid}\n",
            )
            for ts, eid in pairs
        ]

    def test_existing_ties_keep_their_order_regardless_of_entry_id(self):
        from memory_seed.core import _session_record_sort_key

        # ids descending against file order: an entry_id tie-break would swap
        # these two, silently rewriting the position of untouched history.
        existing = self._records([("2026-06-13 10:00", C), ("2026-06-13 10:00", B)])
        ordered = sorted(existing, key=_session_record_sort_key)
        self.assertEqual([r.entry_id for r in ordered], [C, B])

    def test_incoming_entries_land_after_existing_ones_at_the_same_minute(self):
        from memory_seed.core import _session_record_sort_key

        existing = self._records([("2026-06-13 10:00", C)])
        incoming = self._records([("2026-06-13 10:00", A)])
        ordered = sorted(existing + incoming, key=_session_record_sort_key)
        self.assertEqual([r.entry_id for r in ordered], [C, A], "append means after, even for a lower id")

    def test_ordering_is_a_fixed_point(self):
        from memory_seed.core import _session_record_sort_key

        records = self._records([("2026-06-13 11:00", A), ("2026-06-13 10:00", C), ("2026-06-13 10:00", B)])
        once = sorted(records, key=_session_record_sort_key)
        twice = sorted(once, key=_session_record_sort_key)
        self.assertEqual([r.entry_id for r in once], [r.entry_id for r in twice])
        self.assertEqual([r.entry_id for r in once], [C, B, A])

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

    def test_equal_timestamps_ignore_entry_id_when_breaking_ties(self):
        # The discriminating case: ids run OPPOSITE to file order. Sorting ties
        # on entry_id would swap these; append order must win, because an id is
        # a metadata hash and carries no information about what happened first,
        # while the order the entries were written in does.
        text = (
            _entry("2026-06-13 10:00", C, "logged-first-higher-id")
            + _entry("2026-06-13 10:00", B, "logged-second-lower-id")
        )
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13")

        titles = [item.split(" - ", 1)[1] for item in result.order_after]
        self.assertEqual(titles, ["logged-first-higher-id", "logged-second-lower-id"])
        self.assertFalse(result.changed, "already in order; nothing to permute")

    def test_tied_entries_without_ids_keep_their_original_order(self):
        # Nothing to break the tie with, so the final key (original index)
        # preserves the file's order rather than shuffling on an empty string.
        text = (
            "## 2026-06-13 10:00 - no-id-first\n\n- note\n\n"
            "## 2026-06-13 10:00 - no-id-second\n\n- note\n\n"
            "## 2026-06-13 09:00 - earlier\n\n- note\n\n"
        )
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13")

        titles = [item.split(" - ", 1)[1] for item in result.order_after]
        self.assertEqual(titles, ["earlier", "no-id-first", "no-id-second"])

    def test_reordered_output_is_stable_under_a_second_pass(self):
        # Ordering must be a fixed point: reorder twice, no further change.
        text = (
            _entry("2026-06-13 10:00", C, "tie-first")
            + _entry("2026-06-13 10:00", B, "tie-second")
            + _entry("2026-06-13 09:00", A, "earlier")
        )
        self.path.write_text(text, encoding="utf-8")

        first = session_reorder(self.cwd, date_str="2026-06-13", apply=True)
        self.assertTrue(first.applied)
        settled = self.path.read_text(encoding="utf-8")

        second = session_reorder(self.cwd, date_str="2026-06-13", apply=True)
        self.assertFalse(second.changed, "canonical order should be a fixed point")
        self.assertEqual(self.path.read_text(encoding="utf-8"), settled)

    def test_non_timestamped_heading_is_body_content_not_a_boundary(self):
        # Under the unified entry grammar a plain `##` heading inside an entry
        # is body content. Reorder no longer refuses the file (the old refusal
        # guarded the broad `^##` grammar that could not tell body from
        # boundary) - it succeeds and leaves the heading attached to its entry.
        text = _entry("2026-06-13 10:00", B, "fine") + "## A stray heading\n\ncontent\n"
        self.path.write_text(text, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13", apply=True)

        self.assertTrue(result.ok)
        self.assertFalse(result.changed)  # one entry: already in order
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_stray_heading_travels_with_its_entry_through_reorder(self):
        # Two out-of-order entries; the LATER-written, earlier-timestamped one
        # carries a stray `##` heading in its body. After reorder the stray
        # heading must still sit inside that entry's block, not become its own.
        late = _entry("2026-06-13 11:00", B, "late entry")
        early = _entry("2026-06-13 10:00", A, "early entry") + "## Stray note\n\nbody content\n"
        self.path.write_text(late + early, encoding="utf-8")

        result = session_reorder(self.cwd, date_str="2026-06-13", apply=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.changed)
        reordered = self.path.read_text(encoding="utf-8")
        # The early entry now comes first and still owns its stray heading.
        self.assertLess(reordered.index("10:00"), reordered.index("11:00"))
        self.assertLess(reordered.index("## Stray note"), reordered.index("11:00"))

    def test_missing_file_reports_cleanly(self):
        result = session_reorder(self.cwd, date_str="2026-06-14")
        self.assertFalse(result.ok)
        self.assertIn("no session file", result.issues[0])


if __name__ == "__main__":
    unittest.main()
