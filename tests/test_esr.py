"""`memory-seed esr` (P4): one read-only pass over the deterministic
end-of-turn checks. Every section reports even when clean, so a skipped step
is visible; only hard integrity failures affect the exit path (the report is
a preflight, not a gate).
"""

import shutil
import subprocess
import tempfile
import unittest
import pytest
from pathlib import Path
from unittest.mock import patch

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.esr import esr_report, format_esr_report

A = "mse_" + "a" * 16
B = "mse_" + "b" * 16


def test_reflection_close_pending_uses_shared_projection(tmp_path):
    from memory_seed.reflection_operations import run_reflection_operation
    from test_reflection_workstream_ledger import _planned_transaction
    root, _, context = _planned_transaction(tmp_path, "close")
    locator = {key: value for key, value in context["receipt_locator"].items() if key != "chain_id"}
    result = run_reflection_operation("ledger_close", dict(cwd=str(root),
        workstream_id=context["close_kwargs"]["workstream_id"], chain_id=context["chain"], receipts=[locator], apply=True))
    assert result["ok"], result
    expected = run_reflection_operation("board_view", {"cwd": str(root)})
    report = esr_report(cwd=root, session_date="2026-09-06")
    assert report.reflection == expected
    text = format_esr_report(report)
    assert "closed_receipts_pending" in text
    assert "Missing member receipt:" in text and "Missing closure receipt:" in text


def _entry(dt, eid, *, topics=(), files=(), replaces=()):
    lines = [f"## {dt} - entry {eid[-4:]}", "", "```yaml", f"entry_id: {eid}"]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {t}" for t in topics)
    if replaces:
        lines.append("replaces:")
        lines.extend(f"  - {s}" for s in replaces)
    lines += ["```", ""]
    lines += [f"- F: `{f}`" for f in files]
    lines += ["", "Body.", ""]
    return "\n".join(lines)


class EsrReportTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-esr-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def test_clean_corpus_reports_every_section_ok(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertTrue(report.integrity_ok)
        self.assertTrue(report.topics_ok)
        self.assertEqual(report.link_gaps, [])
        self.assertFalse(report.seed_twins_checked)
        # Sections print even when clean - a skipped step cannot hide.
        for section in ("Integrity", "Topics", "Lifecycle link gaps", "Integration mode", "Worktrees", "Seed twins", "Docs lifecycle"):
            self.assertIn(section, text)

    def test_docs_lifecycle_section_skips_without_docs_and_reports_errors_with(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # No docs/ at all -> skipped, honestly.
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertFalse(report.docs_checked)
        self.assertIn("No docs/ directory", format_esr_report(report))

        # A docs tree with a broken link -> surfaced in the section, but the
        # integrity contract holds: only links check fails the esr exit code.
        docs = self.cwd / "docs" / "2_Todo"
        docs.mkdir(parents=True)
        (docs / "a.md").write_text(
            "---\npriority: P1\nnext_action: x\n---\n\n[gone](../5_Completed/missing.md)\n",
            encoding="utf-8",
        )
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertTrue(report.docs_checked)
        self.assertFalse(report.docs_ok)
        self.assertTrue(any("broken-link" in e for e in report.docs_errors))
        self.assertTrue(report.integrity_ok)  # docs errors do not fail integrity
        self.assertIn("broken-link", format_esr_report(report))
        self.assertEqual(report.to_dict()["docs"]["ok"], False)

    def test_integration_mode_surfaced_defaulting_to_local_merge(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        # No project.yaml -> default local-merge.
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertEqual(report.integration_mode, "local-merge")
        self.assertIn("local-merge", format_esr_report(report))
        self.assertEqual(report.to_dict()["integration_mode"], "local-merge")

        # Declared pr surfaces in the report and the formatted output.
        (self.cwd / MEMORY_DIR_NAME / "project.yaml").write_text("integration_mode: pr\n", encoding="utf-8")
        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        self.assertEqual(report.integration_mode, "pr")
        self.assertIn("pr — integrate via push", format_esr_report(report))

    def test_integrity_failure_is_reported(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, replaces=["mse_" + "9" * 16]), encoding="utf-8"
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertFalse(report.integrity_ok)
        self.assertTrue(any("dangling-replaces" in issue for issue in report.integrity_issues))

    def test_link_gaps_scoped_to_the_session_date(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-02")

        self.assertEqual([gap["entry_id"] for gap in report.link_gaps], [B])
        self.assertEqual(report.link_gaps[0]["candidates"][0]["entry_id"], A)
        # The other direction: nothing new on 06-01, so no gaps under that scope.
        self.assertEqual(esr_report(cwd=self.cwd, session_date="2026-06-01").link_gaps, [])

    def test_open_link_stubs_are_counted_in_lifecycle_section(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A), encoding="utf-8"
        )
        sidecar = self.sessions / "links" / "2026-06" / "2026-06-01.md"
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-links",
                    "link_date: 2026-06-01",
                    "---",
                    "",
                    "## 2026-06-01 09:00 - pending classification",
                    "",
                    "```yaml",
                    f"entry_id: {A}",
                    "classify_pending: true",
                    "# candidates (evidence):",
                    "#   - mse_bbbbbbbbbbbbbbbb  # topics: retrieval",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertTrue(report.integrity_ok)
        self.assertEqual(report.open_link_stubs, 1)
        self.assertEqual(report.to_dict()["open_link_stubs"], 1)
        self.assertIn("Open classification stubs: 1.", text)

    def test_stub_backlog_reports_its_age_not_just_its_size(self):
        # A raw count reads as steady state; the oldest date is what shows a
        # backlog rotting. The link backlog cleared on 2026-08-07 had been
        # accumulating since 2026-07-21 and no report said so.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        (self.sessions / "2026-06-09.md").write_text(_entry("2026-06-09 09:00", B), encoding="utf-8")
        stub_dir = self.sessions / "links" / "2026-06"
        stub_dir.mkdir(parents=True)
        for day, entry_id in (("2026-06-09", B), ("2026-06-01", A)):
            (stub_dir / f"{day}.md").write_text(
                "\n".join(
                    [
                        "---",
                        "tags:",
                        "  - session-log-links",
                        f"link_date: {day}",
                        "---",
                        "",
                        f"## {day} 09:00 - pending classification",
                        "",
                        "```yaml",
                        f"entry_id: {entry_id}",
                        "classify_pending: true",
                        "```",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

        report = esr_report(cwd=self.cwd, session_date="2026-06-09")
        text = format_esr_report(report)

        self.assertEqual(report.open_link_stubs, 2)
        self.assertEqual(report.oldest_open_link_stub, "2026-06-01")
        self.assertEqual(report.to_dict()["oldest_open_link_stub"], "2026-06-01")
        self.assertIn("Corpus-wide, not just today, oldest 2026-06-01", text)

    def test_diagram_drift_is_counted_in_entries_not_just_dated(self):
        # A date alone reads as recent at a glance. The lapse this surfaces is a
        # RUN of entries with no diagram, which no single day's view shows - and
        # counting entries needs no judgement about which of them owed one.
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        (self.sessions / "2026-06-09.md").write_text(
            "\n".join([_entry("2026-06-09 09:00", B), _entry("2026-06-09 10:00", "mse_" + "c" * 16)]),
            encoding="utf-8",
        )
        diagram = self.sessions / "diagrams" / "2026-06" / "2026-06-01.md"
        diagram.parent.mkdir(parents=True)
        diagram.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    "diagram_date: 2026-06-01",
                    "---",
                    "",
                    "## 2026-06-01 09:00 - flow",
                    "",
                    "```yaml",
                    f"entry_id: {A}",
                    "```",
                    "",
                    "```mermaid",
                    "flowchart TD",
                    "  A --> B",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-09")
        text = format_esr_report(report)

        self.assertEqual(report.last_diagram_date, "2026-06-01")
        self.assertEqual(report.entries_since_last_diagram, 2)
        self.assertEqual(report.to_dict()["diagrams"]["entries_since_last_sidecar"], 2)
        self.assertIn("last sidecar anywhere: 2026-06-01 (2 entries logged since)", text)

    def test_no_stub_backlog_prints_no_age_line(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(report.open_link_stubs, 0)
        self.assertIsNone(report.oldest_open_link_stub)
        self.assertNotIn("Corpus-wide, not just today", format_esr_report(report))

    def test_non_git_directory_reports_worktrees_unavailable(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertFalse(report.worktrees_available)
        self.assertIn("Not a git repository", format_esr_report(report))

    def test_seed_twin_drift_detected_in_dev_repo_shape(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")
        live = self.cwd / MEMORY_DIR_NAME / "skills"
        seed = self.cwd / "memory_seed" / "seed" / MEMORY_DIR_NAME / "skills"
        live.mkdir(parents=True)
        seed.mkdir(parents=True)
        (live / "end_of_turn.md").write_text("live version", encoding="utf-8")
        (seed / "end_of_turn.md").write_text("seed version", encoding="utf-8")
        # The registry may legitimately diverge (project-local persona skills).
        (live / "index.md").write_text("live registry + persona skills", encoding="utf-8")
        (seed / "index.md").write_text("seed registry", encoding="utf-8")

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertTrue(report.seed_twins_checked)
        self.assertEqual(report.seed_twin_drift, ["end_of_turn.md: live and seed twin differ"])

    @pytest.mark.integration
    def test_git_worktree_posture_marks_merged_clean_as_stale_candidate(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args, cwd=None):
            subprocess.run(["git", "-C", str(cwd or self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")
        wt = self.cwd / ".claude" / "worktrees" / "wt-merged"
        git("worktree", "add", "-b", "feature-merged", str(wt))

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertTrue(report.worktrees_available)
        secondary = [w for w in report.worktrees if not w.is_primary]
        self.assertEqual(len(secondary), 1)
        self.assertEqual(secondary[0].branch, "feature-merged")
        self.assertEqual(secondary[0].ahead, 0)
        self.assertEqual(secondary[0].dirty, 0)
        self.assertTrue(secondary[0].stale_candidate)
        self.assertIn("STALE CANDIDATE", format_esr_report(report))

    @pytest.mark.integration
    def test_git_worktree_posture_surfaces_unregistered_physical_residue(self):
        (self.sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

        def git(*args, cwd=None):
            subprocess.run(["git", "-C", str(cwd or self.cwd), *args], check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "T")
        git("add", "-A")
        git("commit", "-m", "base")
        registered = self.cwd / ".codex" / "worktrees" / "registered"
        git("worktree", "add", "-b", "feature-registered", str(registered))
        residue = self.cwd / ".codex" / "worktrees" / "deregistered-residue"
        residue.mkdir(parents=True)
        (residue / ".git").write_text("gitdir: missing-admin-entry\n", encoding="utf-8")

        # Run from the secondary checkout: ESR must still inspect the primary
        # checkout's physical agent-worktree namespaces.
        report = esr_report(cwd=registered, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertEqual([item.path for item in report.worktree_residues], [str(residue.resolve())])
        self.assertTrue(report.worktree_residues[0].git_file_present)
        self.assertEqual(report.to_dict()["worktrees"]["residues"][0]["namespace"], ".codex/worktrees")
        self.assertIn("ORPHAN RESIDUE CANDIDATE", text)
        self.assertNotIn(f"{registered}  [.codex/worktrees]  ORPHAN", text)


class AdrHeadReviewQueueTests(unittest.TestCase):
    """ESR flags an ADR whose authoritative head has a `refines` successor.

    A mechanical fact only: the concern's current form moved and the ADR did
    not. Nothing in the report moves a head - the flag is answered by an
    authored revision or a recorded reviewed-no-change, which is why the line
    says exactly that.
    """

    HEAD = "mse_" + "1" * 16       # ADR head, refined twice
    MID = "mse_" + "2" * 16        # the intermediate hop - must never be reported
    TERMINUS = "mse_" + "3" * 16   # the chain's current form
    STABLE = "mse_" + "4" * 16     # a head nothing refines
    MEMBER = "mse_" + "5" * 16     # attached predecessor, refined
    MEMBER_NEW = "mse_" + "6" * 16  # that predecessor's current form

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-esr-adr-head-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        for index, entry_id in enumerate(
            (self.HEAD, self.MID, self.TERMINUS, self.STABLE, self.MEMBER, self.MEMBER_NEW)
        ):
            self._entry(entry_id, f"2026-06-01 0{index}:00")

    def _entry(self, entry_id, timestamp):
        path = self.sessions / "2026-06-01.md"
        block = (
            f"## {timestamp} - entry {entry_id[-4:]}\n\n```yaml\nentry_id: {entry_id}\n"
            "user_initials: JNL\nagent_type: codex\n```\n\n"
            "### Decision\n\n- D: Something.\n- R: Because.\n\n"
        )
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + block, encoding="utf-8"
        )

    def _refines(self, source, target):
        """Author a typed `refines` edge in a link sidecar, the way the corpus does."""
        directory = self.sessions / "links"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "2026-06-01.md"
        block = (
            f"## 2026-06-01 12:00 - typed edge {source[-4:]}\n\n```yaml\n"
            f"entry_id: {source}\nsource: derived\nevolves:\n  - {target} (refines)\n```\n\n"
        )
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + block, encoding="utf-8"
        )

    def _accepted_adr(self, adr_id, entry_id, *, predecessors=()):
        from memory_seed.adr import promote_decision, transition_adr

        promoted = promote_decision(
            self.cwd, adr_id=adr_id, source_entry_id=entry_id, source_decision="d1",
            title=f"Concern {adr_id}", topics=(), user_initials="JNL", agent_type="codex",
            source="write-time", direct_predecessors=predecessors,
            timestamp="2026-06-01T13:00:00",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        accepted = transition_adr(
            self.cwd, adr_id=adr_id, status="accepted", decision_ref=f"{entry_id}:d1",
            update_entry_id=entry_id, expected_previous_status="proposed",
            source="write-time", timestamp="2026-06-01T14:00:00",
        )
        self.assertTrue(accepted.ok, accepted.issues)

    def test_head_with_a_refines_successor_is_flagged_at_the_chain_terminus(self):
        # Two hops: a one-hop implementation would name MID, which is itself
        # already superseded - an ADR two refinements behind is further behind.
        self._refines(self.MID, self.HEAD)
        self._refines(self.TERMINUS, self.MID)
        self._accepted_adr("adr_moved", self.HEAD)

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        self.assertEqual(report.adr_head_reviews, [
            f"ADR adr_moved: head {self.HEAD}:d1 has current form {self.TERMINUS}:d1 "
            "- propose a revision or record reviewed-no-change"
        ])
        self.assertIn("## ADR review queue", text)
        self.assertIn(f"has current form {self.TERMINUS}:d1", text)
        self.assertNotIn(f"has current form {self.MID}:d1", text)
        # Flag only, and the wording has to keep saying so.
        self.assertIn("propose a revision or record reviewed-no-change", text)
        # The preamble now names both answer paths concretely: the revision
        # pair of CLI commands, and the MCP no-change review gate the CLI has
        # no equivalent for.
        self.assertIn("adr revise", text)
        self.assertIn("adr transition", text)
        self.assertIn('"no-change"', text)

    def test_to_dict_carries_all_adr_sweep_outputs_as_lists(self):
        self._refines(self.MID, self.HEAD)
        self._refines(self.TERMINUS, self.MID)
        self._accepted_adr("adr_moved", self.HEAD)

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        payload = report.to_dict()

        self.assertIn("adr_attachment_candidates", payload)
        self.assertIn("adr_head_reviews", payload)
        self.assertIn("adr_sweep_candidates", payload)
        self.assertIsInstance(payload["adr_attachment_candidates"], list)
        self.assertIsInstance(payload["adr_head_reviews"], list)
        self.assertIsInstance(payload["adr_sweep_candidates"], list)
        # This scenario populates the review queue - prove the populated
        # value, not just an empty list, reaches to_dict().
        self.assertEqual(payload["adr_head_reviews"], report.adr_head_reviews)
        self.assertTrue(payload["adr_head_reviews"])

    def test_head_without_a_successor_produces_nothing(self):
        # The edge exists in the corpus but touches a decision this ADR does
        # not hold: a review queue that fires on unrelated lineage is noise.
        self._refines(self.MID, self.HEAD)
        self._accepted_adr("adr_stable", self.STABLE)

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(report.adr_head_reviews, [])
        self.assertNotIn("## ADR review queue", format_esr_report(report))

    def test_non_head_attached_member_is_flagged_as_secondary(self):
        from memory_seed.adr import AdrPredecessor

        self._refines(self.MEMBER_NEW, self.MEMBER)
        self._accepted_adr(
            "adr_member", self.STABLE,
            predecessors=(AdrPredecessor(
                f"{self.MEMBER}:d1",
                f"link:{self.STABLE}:d1:evolves:{self.MEMBER}:d1",
            ),),
        )

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(report.adr_head_reviews, [
            f"ADR adr_member: member {self.MEMBER}:d1 has current form "
            f"{self.MEMBER_NEW}:d1 (secondary - the authoritative head is unchanged)"
        ])
        self.assertIn("secondary", format_esr_report(report))

    def test_section_fails_open_leaving_the_rest_of_the_report_usable(self):
        # The section rides in a preflight. It may report nothing; it may never
        # take the preflight down with it.
        self._refines(self.MID, self.HEAD)
        self._accepted_adr("adr_moved", self.HEAD)

        # Break the spine for THIS section only. `build_refines_spine` has one
        # module-global name and three callers now (`_adr_head_reviews` here,
        # `audit_link_gaps` in retrieval, `check_session_links` in core); a
        # blanket side_effect fails the other two as well and would prove
        # nothing about which one failed open. The section's own frame is the
        # discriminator - each caller imports the symbol inside its own function.
        import inspect

        from memory_seed.semantic_cache import build_refines_spine as real_spine

        raised_for_the_section = []

        def raise_for_the_adr_section_only(*args, **kwargs):
            if any(frame.function == "_adr_head_reviews" for frame in inspect.stack()):
                raised_for_the_section.append(True)
                raise RuntimeError("spine unavailable")
            return real_spine(*args, **kwargs)

        with patch(
            "memory_seed.semantic_cache.build_refines_spine",
            side_effect=raise_for_the_adr_section_only,
        ):
            report = esr_report(cwd=self.cwd, session_date="2026-06-01")
        text = format_esr_report(report)

        # The raising path was actually taken - an empty section that never
        # reached the spine would prove nothing about failing open.
        self.assertTrue(raised_for_the_section)
        self.assertEqual(report.adr_head_reviews, [])
        self.assertNotIn("## ADR review queue", text)
        self.assertIn("## Integrity (links check)", text)
        self.assertIn("## Topics", text)


class AdrSweepCandidateTests(unittest.TestCase):
    """ESR performs inverse ADR coverage and attaches advice to every item."""

    OLD = "mse_" + "a" * 16
    MID = "mse_" + "b" * 16
    NEW = "mse_" + "c" * 16

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-esr-adr-sweep-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        for index, entry_id in enumerate((self.OLD, self.MID, self.NEW)):
            self._entry(entry_id, f"2026-06-01 0{index}:00")

    def _entry(self, entry_id, timestamp):
        path = self.sessions / "2026-06-01.md"
        block = (
            f"## {timestamp} - entry {entry_id[-4:]}\n\n```yaml\nentry_id: {entry_id}\n"
            "user_initials: JNL\nagent_type: codex\n```\n\n"
            "### Decision\n\n- D: Something.\n- R: Because.\n\n"
        )
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + block,
            encoding="utf-8",
        )

    def _refines(self, source, target, minute):
        directory = self.sessions / "links"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "2026-06-01.md"
        block = (
            f"## 2026-06-01 12:{minute:02d} - typed edge {source[-4:]}\n\n```yaml\n"
            f"entry_id: {source}\nsource: derived\nevolves:\n  - {target} (refines)\n```\n\n"
        )
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + block,
            encoding="utf-8",
        )

    def _area(self, *entry_ids):
        directory = self.sessions / "topics"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "2026-06-01.md"
        blocks = []
        for minute, entry_id in enumerate(entry_ids):
            blocks.append(
                f"## 2026-06-01 13:{minute:02d} - area {entry_id[-4:]}\n\n```yaml\n"
                f"entry_id: {entry_id}\nsource: derived\ntopics:\n  area:\n"
                "    - seed-core:d1\n  activity:\n    - feature-build:d1\n```\n"
            )
        path.write_text("\n".join(blocks) + "\n", encoding="utf-8")

    def _claim_old(self):
        from memory_seed.adr import promote_decision

        result = promote_decision(
            self.cwd,
            adr_id="adr_existing_concern",
            source_entry_id=self.OLD,
            source_decision="d1",
            title="Existing concern",
            topics=(),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            timestamp="2026-06-01T14:00:00",
        )
        self.assertTrue(result.ok, result.issues)

    def test_unclaimed_chain_is_a_potential_adr_with_attached_recommendation(self):
        self._refines(self.MID, self.OLD, 0)
        self._refines(self.NEW, self.MID, 1)
        self._area(self.OLD, self.MID, self.NEW)

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(len(report.adr_sweep_candidates), 1)
        candidate = report.adr_sweep_candidates[0]
        self.assertEqual(candidate["kind"], "unclaimed-chain")
        self.assertEqual(candidate["head"], f"{self.NEW}:d1")
        self.assertEqual(candidate["recommendation"]["action"], "review-for-adr-promotion")
        self.assertTrue(candidate["recommendation"]["advisory"])
        text = format_esr_report(report)
        self.assertIn("## ADR sweep candidates", text)
        self.assertIn("Recommendation: review-for-adr-promotion", text)

    def test_claimed_chain_growth_gets_attach_or_split_recommendation(self):
        self._refines(self.MID, self.OLD, 0)
        self._refines(self.NEW, self.MID, 1)
        self._area(self.OLD, self.MID, self.NEW)
        self._claim_old()

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(len(report.adr_sweep_candidates), 1)
        candidate = report.adr_sweep_candidates[0]
        self.assertEqual(candidate["kind"], "grown-chain")
        self.assertEqual(candidate["claimed_by"], ["adr_existing_concern"])
        self.assertEqual(
            candidate["recommendation"]["action"], "review-membership-or-split"
        )

    def test_unclaimed_pair_is_exposed_with_weaker_recommendation(self):
        self._refines(self.MID, self.OLD, 0)
        self._area(self.OLD, self.MID)

        report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(len(report.adr_sweep_candidates), 1)
        candidate = report.adr_sweep_candidates[0]
        self.assertEqual(candidate["kind"], "unclaimed-pair")
        self.assertEqual(
            candidate["recommendation"]["action"],
            "architectural-review-before-promotion",
        )

    def test_candidate_discovery_fails_open(self):
        self._refines(self.MID, self.OLD, 0)
        self._area(self.OLD, self.MID)
        import inspect

        from memory_seed.semantic_cache import build_refines_spine as real_spine

        def raise_for_sweep_only(*args, **kwargs):
            if any(frame.function == "_adr_sweep_candidates" for frame in inspect.stack()):
                raise RuntimeError("spine unavailable")
            return real_spine(*args, **kwargs)

        with patch(
            "memory_seed.semantic_cache.build_refines_spine",
            side_effect=raise_for_sweep_only,
        ):
            report = esr_report(cwd=self.cwd, session_date="2026-06-01")

        self.assertEqual(report.adr_sweep_candidates, [])
        self.assertIn("None — no unclaimed pair/chain", format_esr_report(report))


_MISSING = object()


class ToDictCompletenessTests(unittest.TestCase):
    """Every `EsrReport` dataclass field must be reachable in `to_dict()`.

    Two fields (`adr_attachment_candidates`, `adr_head_reviews`) were added to
    the dataclass without ever being added to `to_dict()` - `esr --json`
    silently dropped both ADR queues. A field-by-field walk pins today's
    shape (including its existing renames/nesting quirks) so the next
    omission fails here instead of downstream in an automation consumer.
    """

    # field name -> path of keys into to_dict()'s output where that field's
    # data lives. Most fields keep their own name at the top level; the
    # entries below are the known exceptions (renames, or grouped under a
    # nested bucket like "diagrams" / "worktrees" / "docs" / "semantic" /
    # "integrity" / "topics" / "seed_twins").
    FIELD_PATHS = {
        "session_date": ("session_date",),
        "integration_mode": ("integration_mode",),
        "merge_trigger": ("merge_trigger",),
        "integrity_ok": ("integrity", "ok"),
        "integrity_issues": ("integrity", "issues"),
        "topics_ok": ("topics", "ok"),
        "topics_issues": ("topics", "issues"),
        "link_gaps": ("link_gaps",),
        "open_link_stubs": ("open_link_stubs",),
        "oldest_open_link_stub": ("oldest_open_link_stub",),
        "topic_attribution_gaps": ("topic_attribution_gaps",),
        "oldest_topic_attribution_gap": ("oldest_topic_attribution_gap",),
        "proposed_topics": ("proposed_topics",),
        "worktrees": ("worktrees", "entries"),
        "worktree_residues": ("worktrees", "residues"),
        "worktrees_available": ("worktrees", "available"),
        "seed_twins_checked": ("seed_twins", "checked"),
        "seed_twin_drift": ("seed_twins", "drift"),
        "docs_checked": ("docs", "checked"),
        "docs_ok": ("docs", "ok"),
        "docs_errors": ("docs", "errors"),
        "docs_warning_count": ("docs", "warning_count"),
        "semantic_available": ("semantic", "available"),
        "semantic_provider": ("semantic", "provider"),
        "semantic_unavailable_reason": ("semantic", "unavailable_reason"),
        "diagrams_today": ("diagrams", "today"),
        "entries_today": ("diagrams", "entries_today"),
        "last_diagram_date": ("diagrams", "last_sidecar_date"),
        "entries_since_last_diagram": ("diagrams", "entries_since_last_sidecar"),
        "adrs_total": ("diagrams", "adrs_total"),
        "adrs_without_diagram_answer": ("diagrams", "adrs_without_diagram_answer"),
        "adrs_needing_diagram_rereview": ("diagrams", "adrs_needing_diagram_rereview"),
        "skills_without_governing_adr": ("diagrams", "skills_without_governing_adr"),
        "skills_with_dangling_governing_adr": ("diagrams", "skills_with_dangling_governing_adr"),
        "adr_attachment_candidates": ("adr_attachment_candidates",),
        "adr_head_reviews": ("adr_head_reviews",),
        "adr_sweep_candidates": ("adr_sweep_candidates",),
        "corpus_cache": ("corpus_cache",),
        "provenance": ("provenance",),
        "temporal_lineage": ("temporal_lineage",),
        "reflection": ("reflection",),
    }

    # Fields whose to_dict() representation is a transform of the raw
    # dataclass objects (list[WorktreePosture] / list[WorktreeResidue] become
    # list[dict]), so equality is checked structurally rather than by
    # identity/equality of the raw field value.
    TRANSFORMED = {"worktrees", "worktree_residues"}

    @staticmethod
    def _get_by_path(payload, path):
        node = payload
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return _MISSING
            node = node[key]
        return node

    def test_field_paths_cover_every_dataclass_field(self):
        import dataclasses

        from memory_seed.esr import EsrReport

        field_names = {f.name for f in dataclasses.fields(EsrReport)}
        self.assertEqual(
            field_names,
            set(self.FIELD_PATHS),
            "EsrReport gained or lost a field - update FIELD_PATHS (and, if "
            "gained, to_dict()) to match",
        )

    def test_every_field_is_reachable_in_to_dict(self):
        from memory_seed.esr import EsrReport, WorktreePosture, WorktreeResidue

        report = EsrReport(
            session_date="2026-08-10",
            integration_mode="pr",
            merge_trigger="manual",
            integrity_ok=False,
            integrity_issues=["bad-link"],
            topics_ok=False,
            topics_issues=["bad-topic"],
            link_gaps=[{"entry_id": "mse_x", "kind": "gap"}],
            open_link_stubs=3,
            oldest_open_link_stub="2026-01-01",
            topic_attribution_gaps=2,
            oldest_topic_attribution_gap="2026-01-02",
            proposed_topics=["new-topic"],
            worktrees=[WorktreePosture(
                path="/wt/one", branch="claude/x", ahead=2, dirty=1, is_primary=False,
            )],
            worktree_residues=[WorktreeResidue(
                path="/wt/orphan", namespace="ns", git_file_present=False,
            )],
            worktrees_available=True,
            seed_twins_checked=True,
            seed_twin_drift=["skill-x drifted"],
            docs_checked=True,
            docs_ok=False,
            docs_errors=["broken-link: a.md"],
            docs_warning_count=4,
            semantic_available=False,
            semantic_provider="local",
            semantic_unavailable_reason="dependency missing",
            diagrams_today=1,
            entries_today=5,
            last_diagram_date="2026-01-03",
            entries_since_last_diagram=6,
            adrs_total=7,
            adrs_without_diagram_answer=8,
            adrs_needing_diagram_rereview=9,
            skills_without_governing_adr=["skill-a"],
            skills_with_dangling_governing_adr=["skill-b"],
            adr_attachment_candidates=["ADR adr_a: candidate ..."],
            adr_head_reviews=["ADR adr_b: head ..."],
            adr_sweep_candidates=[{
                "kind": "unclaimed-chain",
                "recommendation": {"action": "review-for-adr-promotion"},
            }],
            corpus_cache={"health": "current"},
            provenance={"ok": True},
            temporal_lineage={"cache_status": "available"},
            reflection={"ok": True, "items": []},
        )

        payload = report.to_dict()

        import dataclasses

        for f in dataclasses.fields(EsrReport):
            path = self.FIELD_PATHS[f.name]
            found = self._get_by_path(payload, path)
            self.assertIsNot(
                found, _MISSING,
                f"field {f.name!r} not reachable at {path!r} in to_dict() output",
            )
            raw = getattr(report, f.name)
            if f.name == "worktrees":
                self.assertEqual(len(found), len(raw))
                self.assertEqual(found[0]["path"], raw[0].path)
                self.assertEqual(found[0]["branch"], raw[0].branch)
            elif f.name == "worktree_residues":
                self.assertEqual(len(found), len(raw))
                self.assertEqual(found[0]["path"], raw[0].path)
                self.assertEqual(found[0]["namespace"], raw[0].namespace)
            else:
                self.assertEqual(found, raw, f"field {f.name!r} value mismatch at {path!r}")


class EsrJsonCliTests(unittest.TestCase):
    """First CLI-level `esr --json` coverage: the flag must actually work,
    end to end, not just via `EsrReport.to_dict()` called directly."""

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-esr-json-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(_entry("2026-06-01 09:00", A), encoding="utf-8")

    def test_esr_json_flag_emits_parseable_json_with_both_adr_queue_keys(self):
        import contextlib
        import io
        import json
        import os

        from memory_seed.cli import main as cli_main

        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(["esr", "--date", "2026-06-01", "--json"])
        finally:
            os.chdir(previous)

        self.assertEqual(exit_code, 0, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertIn("adr_attachment_candidates", payload)
        self.assertIn("adr_head_reviews", payload)
        self.assertIsInstance(payload["adr_attachment_candidates"], list)
        self.assertIsInstance(payload["adr_head_reviews"], list)
        self.assertEqual(payload["session_date"], "2026-06-01")


if __name__ == "__main__":
    unittest.main()
