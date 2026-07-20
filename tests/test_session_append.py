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

    def test_dry_run_rendered_is_byte_identical_to_the_real_append(self):
        # The dummy write's whole value is fidelity: on a fresh file the block
        # IS the file, so the preview must match the real write byte for byte.
        preview = self._append(dry_run=True)

        self.assertTrue(preview.ok, preview.issues)
        self.assertFalse(preview.written)
        self.assertIsNotNone(preview.rendered)
        self.assertFalse(preview.path.exists(), "a dry run must not create the file")

        real = self._append()
        self.assertEqual(real.path.read_text(encoding="utf-8"), preview.rendered)
        self.assertEqual(real.entry_id, preview.entry_id)

    def test_rendered_is_absent_outside_a_passing_dry_run(self):
        written = self._append()
        self.assertIsNone(written.rendered, "a real write confirms with id/path, not an echo of the body")

        refused = self._append(title="Out of order", timestamp="2026-06-13 08:00", dry_run=True)
        self.assertFalse(refused.ok)
        self.assertIsNone(refused.rendered, "a refused write has no final output to preview")

    def test_decision_density_never_blocks_session_append(self):
        from memory_seed.core import entry_body_advisories, entry_body_format_issues

        body = (
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n\n"
            "#### D3 - three\n\n- D: c\n- R: r\n"
        )

        # The write-time gate must stay silent; only the advisory path speaks.
        # session append calls entry_body_format_issues and refuses on any hit.
        self.assertEqual(entry_body_format_issues(body), [])
        self.assertEqual(len(entry_body_advisories(body)), 1)

    def test_future_timestamp_advisory_grace_window_and_past_are_quiet(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)

        def text_at(stamp):
            return (
                f"## {stamp:%Y-%m-%d %H:%M} - Entry\n\n"
                "```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\n```\n\n"
                "### Summary\n\n- a note\n"
            )

        # Past and present stamps are the normal case.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now - timedelta(hours=2)), now=now), [])
        self.assertEqual(check_entry_timestamp_advisories(text_at(now), now=now), [])
        # Inside (and exactly at) the clock-skew grace window: quiet.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now + timedelta(minutes=10)), now=now), [])
        # Beyond the grace window: flagged, attributed to the entry id.
        flagged = check_entry_timestamp_advisories(text_at(now + timedelta(minutes=11)), now=now)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0][0], "mse_aaaaaaaaaaaaaaaa")
        self.assertIn("in the future", flagged[0][1])

    def test_future_timestamp_advisory_flags_only_the_drifted_entry(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)
        future = now + timedelta(hours=2)
        text = (
            "## 2026-07-18 09:00 - Fine\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Summary\n\n- ok\n\n"
            f"## {future:%Y-%m-%d %H:%M} - Drifted\n\n```yaml\nentry_id: ms-bbbbbbbb\n```\n\n"
            "### Summary\n\n- stamped ahead\n"
        )

        flagged = check_entry_timestamp_advisories(text, now=now)

        self.assertEqual([entry_id for entry_id, _ in flagged], ["ms-bbbbbbbb"])


if __name__ == "__main__":
    unittest.main()
