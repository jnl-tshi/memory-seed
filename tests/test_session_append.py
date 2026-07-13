"""`session append` (P1): entry authoring with structure enforced.

The tool owns structure (target, timestamp, canonical id, YAML shape,
ref/topic validation, chronological append); the agent owns voice (title,
classification, body prose - passed through verbatim). Nothing is written
when any guard fails, and all failures report together.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    check_session_links,
    generate_session_entry_id,
    session_append_entry,
)

BODY = "### Decision\n\n- D: Something durable.\n- R: Because."


class SessionAppendTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-append-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)

    def _append(self, **overrides):
        kwargs = dict(
            cwd=self.cwd,
            title="First decision",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-06-13 09:00",
            auto_branch=False,
        )
        kwargs.update(overrides)
        return session_append_entry(**kwargs)

    def test_appends_a_valid_entry_with_canonical_id(self):
        result = self._append()

        self.assertTrue(result.ok, result.issues)
        self.assertTrue(result.written)
        expected_id = generate_session_entry_id(
            timestamp="2026-06-13 09:00",
            title="First decision",
            user_initials="JN",
            agent_type="claude",
            project_path=".",
            subproject_path=None,
        )
        self.assertEqual(result.entry_id, expected_id)
        text = result.path.read_text(encoding="utf-8")
        self.assertIn("## 2026-06-13 09:00 - First decision", text)
        self.assertIn(f"entry_id: {expected_id}", text)
        self.assertIn("- D: Something durable.", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_second_append_separates_blocks_and_stays_clean(self):
        self._append()
        result = self._append(title="Second decision", timestamp="2026-06-13 10:00")

        self.assertTrue(result.ok, result.issues)
        text = result.path.read_text(encoding="utf-8")
        self.assertIn("\n\n## 2026-06-13 10:00 - Second decision", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_out_of_order_timestamp_is_refused_loudly(self):
        self._append(timestamp="2026-06-13 11:00")

        result = self._append(title="Late-clock entry", timestamp="2026-06-13 10:30")

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertTrue(any("chronology conflict" in issue for issue in result.issues))
        # Nothing was appended.
        self.assertNotIn("Late-clock entry", result.path.read_text(encoding="utf-8"))

    def test_malformed_body_is_refused(self):
        # The tool owns structure: a DRAFT body with bare labels and no section
        # heading is rejected before anything is written, with a fix message.
        result = self._append(body="D: bare, unbulleted label\nR: no heading either")

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertTrue(any("body format" in issue for issue in result.issues), result.issues)
        self.assertNotIn("bare, unbulleted", result.path.read_text(encoding="utf-8") if result.path.exists() else "")

    def test_fabricated_ref_is_refused(self):
        result = self._append(related_entries=("mse_" + "9" * 16,))

        self.assertFalse(result.ok)
        self.assertTrue(any("no such entry_id" in issue for issue in result.issues))

    def test_forward_pointing_lifecycle_ref_is_refused(self):
        first = self._append(timestamp="2026-06-13 09:00")
        # A later entry exists...
        later = self._append(title="Later", timestamp="2026-06-13 12:00")
        # ...and a new 10:00 entry may not supersede it.
        result = self._append(
            title="Middle", timestamp="2026-06-13 10:00", supersedes=(later.entry_id,)
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("newer" in issue for issue in result.issues), result.issues)
        # But superseding the older first entry from a NEW newest entry works.
        ok = self._append(
            title="Replacement", timestamp="2026-06-13 13:00", supersedes=(first.entry_id,)
        )
        self.assertTrue(ok.ok, ok.issues)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_unknown_topic_is_refused_and_alias_resolves_to_canonical(self):
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            "schema_version: 1\ntopics:\n  - slug: memory-trace\n    label: Memory Trace\n    status: active\n    aliases: [trace-ui]\n",
            encoding="utf-8",
        )

        bad = self._append(topics=("nonexistent-topic",))
        self.assertFalse(bad.ok)
        self.assertTrue(any("unknown topic" in issue for issue in bad.issues))

        good = self._append(title="Aliased", topics=("trace-ui",))
        self.assertTrue(good.ok, good.issues)
        self.assertIn("- memory-trace", good.path.read_text(encoding="utf-8"))

    def test_identical_metadata_double_append_is_refused(self):
        self._append()
        result = self._append()

        self.assertFalse(result.ok)
        self.assertTrue(any("double-append" in issue for issue in result.issues))

    def test_all_failures_report_together(self):
        self._append(timestamp="2026-06-13 11:00")
        result = self._append(
            title="Everything wrong",
            timestamp="2026-06-13 09:30",
            related_entries=("mse_" + "9" * 16,),
        )

        self.assertFalse(result.ok)
        kinds = " ".join(result.issues)
        self.assertIn("chronology conflict", kinds)
        self.assertIn("no such entry_id", kinds)

    def test_explicit_branch_is_recorded_verbatim(self):
        result = self._append(branch="feature-x")
        self.assertIn("branch: feature-x", result.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
