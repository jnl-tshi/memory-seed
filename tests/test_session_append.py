"""`session append` (P1): entry authoring with structure enforced.

The tool owns structure (target, timestamp, canonical id, YAML shape,
ref/topic validation, chronological append); the agent owns voice (title,
classification, body prose - passed through verbatim). Nothing is written
when any guard fails, and all failures report together.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from _git_helpers import run_git

from memory_seed.core import (
    MEMORY_DIR_NAME,
    _git_capture,
    check_session_links,
    generate_session_entry_id,
    resolve_runtime,
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

    def test_decision_envelope_writes_topics_and_links_only_to_sidecars(self):
        # The entry owns its narrative.  Decision-scoped semantic assertions
        # are published in the existing append-only sidecar formats, where the
        # checker and branch fuse already know how to validate them.
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )
        older = self._append(title="Earlier decision", timestamp="2026-06-13 08:00")
        result = self._append(
            title="Sidecar decision",
            timestamp="2026-06-13 09:00",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build", "source": "write-time"},
                    "links": {"evolves": [older.entry_id]},
                }
            ],
        )

        self.assertTrue(result.ok, result.issues)
        entry = result.path.read_text(encoding="utf-8")
        self.assertNotIn("topics:", entry)
        self.assertNotIn("evolves:", entry)
        self.assertEqual(len(result.sidecar_paths), 2)
        self.assertIsNotNone(result.journal_path)
        journal = json.loads(result.journal_path.read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "complete")
        self.assertFalse(journal["recovered"])
        self.assertEqual(journal["receipt"]["sidecar_paths"], [str(path) for path in result.sidecar_paths])
        topic_path = self.cwd / MEMORY_DIR_NAME / "sessions" / "topics" / "2026-06" / "2026-06-13.md"
        link_path = self.cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06" / "2026-06-13.md"
        self.assertIn(f"entry_id: {result.entry_id}", topic_path.read_text(encoding="utf-8"))
        self.assertIn("- schema:d1", topic_path.read_text(encoding="utf-8"))
        self.assertIn("- feature-build:d1", topic_path.read_text(encoding="utf-8"))
        self.assertIn(f"- d1 -> {older.entry_id}", link_path.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_decision_envelope_refuses_legacy_semantic_fields_and_bad_ordinals(self):
        result = self._append(
            topics=["schema"],
            decisions=[{"decision": "d9", "topics": {"area": "schema"}}],
        )

        self.assertFalse(result.ok)
        joined = " ".join(result.issues)
        self.assertIn("one sidecar authority", joined)
        self.assertIn("not recorded in the body", joined)
        self.assertEqual(list((self.cwd / MEMORY_DIR_NAME / "sessions").rglob("*.md")), [])

    def test_pending_journal_recovers_after_sidecar_write_interrupt(self):
        """An interrupted sidecar write keeps the already-published parent valid."""
        from unittest.mock import patch

        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )
        older = self._append(title="Earlier decision", timestamp="2026-06-13 08:00")
        payload = {
            "title": "Interrupted sidecar decision",
            "timestamp": "2026-06-13 09:00",
            "decisions": [{
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build"},
                "links": {"evolves": [older.entry_id]},
            }],
        }
        from memory_seed.core import _write_chronological_topic_sidecar_file as real_write_topic_sidecar

        def interrupt_topic_write(path, topic_date, records):
            real_write_topic_sidecar(path, topic_date, records)
            raise OSError("simulated interruption after topic sidecar write")

        with patch("memory_seed.core._write_chronological_topic_sidecar_file", side_effect=interrupt_topic_write):
            with self.assertRaisesRegex(OSError, "simulated interruption after topic sidecar write"):
                self._append(**payload)

        journals = list((self.cwd / MEMORY_DIR_NAME / "transactions" / "decision-sidecar").glob("*.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "pending")
        self.assertTrue(check_session_links(cwd=self.cwd).ok)
        altered = self._append(
            **payload,
            body="### Decision\n\n- D: Alter the retry.\n- R: It must be refused.\n",
        )
        self.assertFalse(altered.ok)
        self.assertTrue(any("conflicts with this write" in issue for issue in altered.issues), altered.issues)
        recovered = self._append(**payload)
        self.assertTrue(recovered.ok, recovered.issues)
        self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "complete")
        self.assertTrue(json.loads(journals[0].read_text(encoding="utf-8"))["recovered"])
        written = recovered.path.read_text(encoding="utf-8")
        self.assertEqual(written.count("Interrupted sidecar decision"), 1)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def _append_multi_decision_older(self):
        body = (
            "### Decisions\n\n"
            "#### D1 - First call\n\n- D: alpha\n- R: because\n\n"
            "#### D2 - Second call\n\n- D: beta\n- R: reasons\n"
        )
        result = self._append(title="Older with decisions", body=body, timestamp="2026-06-13 08:00")
        self.assertTrue(result.ok, result.issues)
        return result.entry_id

    def test_append_accepts_decision_ref_in_evolves(self):
        # Write-time grammar (2026-07-24): `:dN` on an existing ordinal of an
        # older entry passes the guards and is written verbatim.
        older = self._append_multi_decision_older()
        result = self._append(evolves=[f"{older}:d2"])
        self.assertTrue(result.ok, result.issues)
        text = result.path.read_text(encoding="utf-8")
        self.assertIn(f"- {older}:d2", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_rejects_decision_ref_to_missing_ordinal(self):
        older = self._append_multi_decision_older()
        result = self._append(evolves=[f"{older}:d9"])
        self.assertFalse(result.ok)
        self.assertTrue(any("has no d9" in issue for issue in result.issues))

    def test_append_accepts_decision_ref_in_related_entries(self):
        # Decision-level related (2026-07-25): related_entries may carry :dN,
        # allowed but never mandated. A valid ordinal on a 2-decision target
        # passes; a nonexistent one is still dangling.
        older = self._append_multi_decision_older()  # has d1, d2
        ok = self._append(related_entries=[f"{older}:d2"])
        self.assertTrue(ok.ok, ok.issues)
        self.assertIn(f"- {older}:d2", ok.path.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        bad = self._append(title="Bad ord", timestamp="2026-06-13 10:00", related_entries=[f"{older}:d9"])
        self.assertFalse(bad.ok)
        self.assertTrue(any("has no d9" in issue for issue in bad.issues), bad.issues)

    def test_append_does_not_mandate_decision_ref_in_related_entries(self):
        # Unlike replaces/evolves, related is NOT required to name the decision
        # on a multi-decision target - it stays casual for hand-authoring.
        older = self._append_multi_decision_older()  # 2 decisions
        ok = self._append(related_entries=[older])  # bare, no :dN
        self.assertTrue(ok.ok, ok.issues)

    # --- Grammar v2 (2026-07-24): granularity is mandated at write time ---

    def test_append_mandates_target_ordinal_when_target_has_multiple_decisions(self):
        older = self._append_multi_decision_older()
        result = self._append(evolves=[older])
        self.assertFalse(result.ok)
        self.assertTrue(any("has 2 decisions (d1,d2)" in issue for issue in result.issues), result.issues)

    def test_append_accepts_bare_ref_to_a_decisionless_target(self):
        summary_only = self._append(
            title="Note only", body="### Summary\n\n- a plain note.", timestamp="2026-06-13 08:00"
        )
        self.assertTrue(summary_only.ok, summary_only.issues)
        result = self._append(replaces=[summary_only.entry_id])
        self.assertTrue(result.ok, result.issues)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_takes_a_single_decision_target_bare_and_rejects_its_d1(self):
        # 2026-07-24 reconciliation: a single-decision target's :d1 and its bare
        # id denote the same edge, so bare is canonical and :d1 is rejected -
        # name a decision only when there is a choice to make.
        single = self._append(title="One call", timestamp="2026-06-13 08:00")  # BODY is singular
        self.assertTrue(single.ok, single.issues)

        bare = self._append(title="Refines it", timestamp="2026-06-13 10:00", evolves=[single.entry_id])
        self.assertTrue(bare.ok, bare.issues)
        self.assertIn(f"- {single.entry_id}", bare.path.read_text(encoding="utf-8"))

        redundant = self._append(
            title="Over-specified", timestamp="2026-06-13 11:00", evolves=[f"{single.entry_id}:d1"]
        )
        self.assertFalse(redundant.ok)
        self.assertTrue(any("single decision" in issue and "bare id" in issue for issue in redundant.issues), redundant.issues)

    def test_append_accepts_comma_multi_ordinal_and_validates_each(self):
        older = self._append_multi_decision_older()
        ok = self._append(evolves=[f"{older}:d1,d2"])
        self.assertTrue(ok.ok, ok.issues)
        self.assertIn(f"- {older}:d1,d2", ok.path.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        bad = self._append(title="Bad ordinal", timestamp="2026-06-13 10:00", evolves=[f"{older}:d1,d9"])
        self.assertFalse(bad.ok)
        self.assertTrue(any("has no d9" in issue for issue in bad.issues))

    def test_append_mandates_arrow_source_prefix_for_multi_decision_body(self):
        older = self._append_multi_decision_older()
        multi_body = (
            "### Decisions\n\n"
            "#### D1 - keep\n\n- D: a\n- R: because\n\n"
            "#### D2 - change\n\n- D: b\n- R: reasons\n"
        )
        # Without the arrow nobody knows which decision authors the edge.
        result = self._append(body=multi_body, evolves=[f"{older}:d1"])
        self.assertFalse(result.ok)
        self.assertTrue(any("prefix which one authors the edge" in issue for issue in result.issues), result.issues)

        # With it, the ref is written verbatim and the corpus stays clean.
        ok = self._append(body=multi_body, evolves=[f"d2 -> {older}:d1"])
        self.assertTrue(ok.ok, ok.issues)
        self.assertIn(f"- d2 -> {older}:d1", ok.path.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_rejects_arrow_ordinal_absent_from_own_body(self):
        older = self._append_multi_decision_older()
        # The default BODY is single-decision: it has d1 and nothing else.
        result = self._append(evolves=[f"d9 -> {older}:d1"])
        self.assertFalse(result.ok)
        self.assertTrue(any("this entry has no d9" in issue for issue in result.issues), result.issues)

    def test_cli_ref_flags_are_repeatable_and_survive_intra_ref_commas(self):
        # The flag's comma has always separated ITEMS, but grammar v2 puts a
        # comma INSIDE a ref (`mse_x:d1,d4`). Splitting naively turns that one
        # ref into a valid ref plus the garbage token `d4`. Found by
        # dogfooding: three --evolves flags collapsed to one before the fix.
        import contextlib
        import io
        import os

        from memory_seed.cli import main as cli_main

        older = self._append_multi_decision_older()
        body_file = self.cwd / "body.md"
        body_file.write_text(BODY, encoding="utf-8")

        previous = Path.cwd()
        out = io.StringIO()
        try:
            os.chdir(self.cwd)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = cli_main([
                    "session", "append",
                    "--title", "Repeated refs",
                    "--user-initials", "JN",
                    "--agent-type", "claude",
                    "--timestamp", "2026-06-13 09:30",
                    "--no-branch",
                    "--body-file", str(body_file),
                    "--evolves", f"{older}:d1,d2",
                    "--evolves", f"{older}:d2",
                    "--dry-run",
                ])
        finally:
            os.chdir(previous)

        self.assertEqual(code, 0, out.getvalue())
        rendered = out.getvalue()
        self.assertIn(f"- {older}:d1,d2", rendered)  # comma kept inside the ref
        self.assertIn(f"- {older}:d2", rendered)  # the second flag is not lost
        self.assertNotIn("- d2\n", rendered)  # never split into a bare ordinal

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
        # ...and a new 10:00 entry may not replace it.
        result = self._append(
            title="Middle", timestamp="2026-06-13 10:00", replaces=(later.entry_id,)
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("newer" in issue for issue in result.issues), result.issues)
        # But replacing the older first entry from a NEW newest entry works.
        # `first` is single-decision, so the ref stays BARE - :d1 there is
        # redundant and rejected (2026-07-24: name a decision only on a
        # choice).
        ok = self._append(
            title="Replacement", timestamp="2026-06-13 13:00", replaces=(first.entry_id,)
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


class BranchProvenanceTests(unittest.TestCase):
    """What `branch:` actually records, per repository layout.

    `branch:` is the ONLY git-derived field on an entry (core.py, the single
    `_git_capture` call in `session_append_entry`); every other YAML key is
    caller-supplied, `read_local_user` is a file read, and the entry id hashes
    timestamp/title/initials/agent/paths. Diagram, topic and link sidecars carry
    no branch at all.

    What it records is the HEAD of the working tree containing
    `runtime.workspace_root`, read at write time. That is a property of a
    *checkout*, not of an agent's session, which is the whole of the
    cross-session contamination question. These tests pin the empirical matrix
    behind docs/2_Todo/branch-field-provenance.md so a future change to
    `resolve_runtime` cannot silently move it.
    """

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="mseed-branch-"))
        self.addCleanup(self._cleanup)
        self._repos = []
        self.primary, self.worktree, self.plain = self._build_repo("tracked", tracked=True)

    def _build_repo(self, name, *, tracked):
        """A primary checkout, a real nested worktree, and a plain nested dir.

        ``tracked`` decides whether `.memory-seed` is committed. That single bit
        is what makes worktree isolation work: a worktree only gets its own
        memory dir if the memory dir is in the tree. `.memory-seed/sessions`
        alone is not enough - git does not track empty directories.
        """
        primary = self.base / name
        (primary / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)
        run_git(primary, "init", "-b", "main", check=True)
        run_git(primary, "config", "user.email", "probe@example.com", check=True)
        run_git(primary, "config", "user.name", "Probe", check=True)
        (primary / MEMORY_DIR_NAME / "agent-rules.md").write_text("# rules\n", encoding="utf-8")
        (primary / MEMORY_DIR_NAME / "sessions" / ".gitkeep").write_text("", encoding="utf-8")
        ignored = ".claude/worktrees/\n" + ("" if tracked else f"{MEMORY_DIR_NAME}/\n")
        (primary / ".gitignore").write_text(ignored, encoding="utf-8")
        run_git(primary, "add", "-A", check=True)
        run_git(primary, "commit", "-m", "init", check=True)
        self._repos.append(primary)

        # A real, nested, gitignored worktree on its own branch - the layout
        # this repo's parallel agents actually run in.
        worktree = primary / ".claude" / "worktrees" / "real-wt"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        run_git(primary, "worktree", "add", "-b", f"feat/{name}", str(worktree), check=True)

        # A plain nested directory: no .git, no .memory-seed of its own.
        plain = primary / ".claude" / "worktrees" / "plain-dir"
        plain.mkdir(parents=True)

        # The primary then moves onto a feature branch, standing in for another
        # agent (or the user) checking one out mid-session.
        run_git(primary, "checkout", "-b", "claude/feature/someone-else", check=True)
        return primary, worktree, plain

    def _cleanup(self):
        for repo in self._repos:
            run_git(repo, "worktree", "prune")
        shutil.rmtree(self.base, ignore_errors=True)

    def _stamped_branch(self, cwd):
        result = session_append_entry(
            cwd,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            dry_run=True,
        )
        self.assertTrue(result.ok, result.issues)
        for line in (result.rendered or "").splitlines():
            if line.startswith("branch:"):
                return line.split(":", 1)[1].strip()
        return None

    def test_tracked_memory_seed_makes_a_worktree_record_its_own_branch(self):
        # THE headline result. When `.memory-seed` is committed - as it is in
        # this repository - a worktree gets its own copy, resolve_runtime stops
        # there, and git reads that worktree's HEAD. A worktree-isolated agent
        # is therefore NOT contaminated by whatever the primary has checked out.
        self.assertEqual(self._stamped_branch(self.worktree), "feat/tracked")
        self.assertEqual(self._stamped_branch(self.primary), "claude/feature/someone-else")

    def test_untracked_memory_seed_worktree_omits_the_branch_rather_than_lying(self):
        # The same worktree layout would silently stamp the PRIMARY's branch
        # when `.memory-seed` is not tracked: nothing stops the walk-up, so the
        # agent writes into the primary's memory dir. Neither HEAD is right -
        # the session is on the worktree's branch, the file lands on the
        # primary's - so the field is omitted, on the same principle as the
        # pre-existing detached-HEAD case. Omission, not refusal: the append
        # still succeeds and reports no issues.
        _, worktree, _ = self._build_repo("untracked", tracked=False)
        result = session_append_entry(
            worktree,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            dry_run=True,
        )
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.issues, ())
        self.assertNotIn("branch:", result.rendered)
        self.assertIsNone(self._stamped_branch(worktree))

    def test_shared_checkout_concurrency_is_still_invisible(self):
        # The half that code cannot fix, pinned so nobody mistakes the omission
        # rule above for a complete answer. A plain nested dir and the primary
        # itself are the same working tree with the same HEAD, so an agent
        # working out of either records whatever branch is checked out at write
        # time - including one another's. Undecidable from git; needs a design
        # decision, not a heuristic.
        self.assertEqual(
            self._stamped_branch(self.plain), self._stamped_branch(self.primary)
        )
        self.assertEqual(self._stamped_branch(self.plain), "claude/feature/someone-else")

    def test_toplevels_agree_when_the_memory_dir_is_in_the_callers_own_tree(self):
        # The obvious fix - "resolve git relative to cwd rather than the
        # walked-up workspace_root" - is a NO-OP in every layout that behaves
        # correctly: git's own discovery walks up exactly as resolve_runtime
        # does, so both toplevels name the same working tree. In particular it
        # cannot tell a plain nested dir apart from a legitimate append made
        # from the primary checkout, which is the case that must keep working.
        for cwd in (self.primary, self.worktree, self.plain):
            with self.subTest(cwd=cwd.name):
                runtime = resolve_runtime(cwd)
                self.assertEqual(
                    _git_capture(cwd, "rev-parse", "--show-toplevel"),
                    _git_capture(runtime.workspace_root, "rev-parse", "--show-toplevel"),
                )

    def test_toplevels_disagree_exactly_when_the_stamped_branch_is_foreign(self):
        # ...but they DO disagree in the one layout that produces a wrong value
        # without any concurrency at all: cwd sits in working tree A while the
        # memory dir - and therefore the HEAD that gets stamped - belongs to
        # working tree B. This is the detectable subset, and the only part of
        # item 5 that code could act on. See docs/2_Todo/branch-field-provenance.md.
        _, worktree, _ = self._build_repo("untracked", tracked=False)
        runtime = resolve_runtime(worktree)
        self.assertNotEqual(
            _git_capture(worktree, "rev-parse", "--show-toplevel"),
            _git_capture(runtime.workspace_root, "rev-parse", "--show-toplevel"),
        )

    def test_explicit_branch_overrides_the_checkouts_head(self):
        # The documented mitigation: the caller is the only party that knows
        # which branch its session is really on, so it can say so.
        result = session_append_entry(
            self.plain,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            branch="claude/fix/my-own-task",
            dry_run=True,
        )
        self.assertIn("branch: claude/fix/my-own-task", result.rendered)

    def test_auto_branch_false_omits_the_field_inside_a_repository(self):
        # The other mitigation: record nothing rather than something wrong.
        result = session_append_entry(
            self.plain,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            auto_branch=False,
            dry_run=True,
        )
        self.assertNotIn("branch:", result.rendered)


if __name__ == "__main__":
    unittest.main()
