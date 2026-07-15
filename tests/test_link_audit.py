"""`memory-seed link audit` (Phase 3): find entries that share files/topics but
carry no recorded edge, without an all-pairs semantic scan.

Candidate generation: for each target, only OLDER entries sharing >=1 F: file
OR >=1 topic. File overlap qualifies a pair even with no shared topic (files
override topics); topic-only overlap is suppressed by any existing edge, while
file overlap surfaces even a merely-"related" pair as a lifecycle upgrade
candidate. A recorded supersedes/evolves edge (YAML or sidecar) removes the pair.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, check_session_links
from memory_seed.cli import main as cli_main
from memory_seed.retrieval import (
    apply_link_gap_stubs,
    audit_link_gaps,
    augment_chunks_with_link_sidecars,
)
from memory_seed.semantic_cache import extract_memory_chunks

A = "mse_" + "a" * 16  # oldest
B = "mse_" + "b" * 16
C = "mse_" + "c" * 16  # newest


def _entry(dt, eid, *, topics=(), files=(), related=(), supersedes=(), evolves=()):
    lines = [f"## {dt} - entry {eid[-4:]}", "", "```yaml", f"entry_id: {eid}"]
    for key, vals in (
        ("topics", topics),
        ("related_entries", related),
        ("supersedes", supersedes),
        ("evolves", evolves),
    ):
        if vals:
            lines.append(f"{key}:")
            lines.extend(f"  - {v}" for v in vals)
    lines += ["```", ""]
    lines += [f"- F: `{f}`" for f in files]
    lines += ["", "Body text.", ""]
    return "\n".join(lines)


class LinkAuditTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-linkaudit-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def _write(self, *entries):
        (self.sessions / "2026-06-01.md").write_text("\n".join(entries), encoding="utf-8")

    def _sidecar(self, source, *, supersedes=()):
        d = self.sessions / "links" / "2026-06"
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"## 2026-06-01 12:00 - edge", "", "```yaml", f"entry_id: {source}", "supersedes:"]
        lines += [f"  - {ref}" for ref in supersedes]
        lines += ["```", ""]
        (d / "2026-06-01.md").write_text("\n".join(lines), encoding="utf-8")

    def _gap(self, entry_id):
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=entry_id)
        return gaps[0] if gaps else None

    def _run_cli(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(list(args))
        finally:
            os.chdir(previous)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_file_overlap_no_edge_is_flagged(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        gap = self._gap(B)
        self.assertEqual([c.entry_id for c in gap.candidates], [A])
        self.assertEqual(gap.candidates[0].shared_files, ("pkg/foo.py",))
        self.assertFalse(gap.candidates[0].already_related)

    def test_file_overlap_surfaces_without_a_shared_topic(self):
        # Files override the absence of a topic link.
        self._write(
            _entry("2026-06-01 09:00", A, topics=["alpha"], files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, topics=["beta"], files=["pkg/foo.py"]),
        )
        gap = self._gap(B)
        self.assertEqual([c.entry_id for c in gap.candidates], [A])
        self.assertEqual(gap.candidates[0].shared_topics, ())

    def test_topic_only_gap_is_flagged_when_unlinked(self):
        self._write(
            _entry("2026-06-01 09:00", A, topics=["alpha"]),
            _entry("2026-06-01 10:00", B, topics=["alpha"]),
        )
        gap = self._gap(B)
        self.assertEqual([c.entry_id for c in gap.candidates], [A])
        self.assertEqual(gap.candidates[0].shared_topics, ("alpha",))

    def test_topic_only_is_suppressed_when_already_related(self):
        self._write(
            _entry("2026-06-01 09:00", A, topics=["alpha"]),
            _entry("2026-06-01 10:00", B, topics=["alpha"], related=[A]),
        )
        self.assertIsNone(self._gap(B))

    def test_file_overlap_flags_related_pair_as_upgrade_candidate(self):
        # A related link does NOT hide a lifecycle gap when files overlap.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], related=[A]),
        )
        gap = self._gap(B)
        self.assertEqual([c.entry_id for c in gap.candidates], [A])
        self.assertTrue(gap.candidates[0].already_related)

    def test_recorded_lifecycle_edge_suppresses_the_pair(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], supersedes=[A]),
        )
        self.assertIsNone(self._gap(B))

    def test_sidecar_lifecycle_edge_suppresses_the_pair(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        self._sidecar(B, supersedes=[A])
        self.assertIsNone(self._gap(B))

    def test_only_older_entries_are_candidates(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        # A is older than B, so auditing A must not offer B (forward-only).
        self.assertIsNone(self._gap(A))

    def test_unknown_entry_id_raises(self):
        self._write(_entry("2026-06-01 09:00", A, files=["pkg/foo.py"]))
        with self.assertRaises(LookupError):
            audit_link_gaps(cwd=self.cwd, entry_id="mse_dddddddddddddddd")

    def test_session_date_scopes_targets_not_candidates(self):
        # The end-of-session sweep audits only today's entries as targets, but
        # candidates still come from the whole corpus (older sessions).
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            "\n".join(
                [
                    _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]),
                    _entry("2026-06-02 10:00", C, files=["pkg/bar.py"]),
                ]
            ),
            encoding="utf-8",
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        # Only B gapped (C shares nothing); B's candidate A is from the PRIOR session.
        self.assertEqual([g.entry_id for g in gaps], [B])
        self.assertEqual([c.entry_id for c in gaps[0].candidates], [A])
        # And the earlier session's entry is never a target under the scope.
        self.assertEqual(audit_link_gaps(cwd=self.cwd, session_date="2026-06-01"), [])

    def test_apply_writes_chronological_inert_stubs_without_editing_entries(self):
        older = self.sessions / "2026-06-01.md"
        audited = self.sessions / "2026-06-02.md"
        older.write_text(_entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8")
        audited.write_text(
            "\n".join(
                [
                    _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]),
                    _entry("2026-06-02 10:00", C, files=["pkg/foo.py"]),
                ]
            ),
            encoding="utf-8",
        )
        entry_bytes = {path: path.read_bytes() for path in (older, audited)}
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")

        result = apply_link_gap_stubs(reversed(gaps), session_date="2026-06-02", cwd=self.cwd)

        self.assertTrue(result.changed)
        self.assertEqual(result.added_entry_ids, (B, C))
        text = result.path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\ntags:\n  - session-log-links\nlink_date: 2026-06-02\n---\n"))
        self.assertLess(text.index(f"entry_id: {B}"), text.index(f"entry_id: {C}"))
        self.assertEqual(text.count("classify_pending: true"), 2)
        self.assertIn(f"#   - {A}  # files: pkg/foo.py", text)
        self.assertNotIn("\nsupersedes:", text)
        self.assertNotIn("\nevolves:", text)
        for path, before in entry_bytes.items():
            self.assertEqual(path.read_bytes(), before)

        chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(self.cwd, granularity="entry"), cwd=self.cwd
        )
        by_id = {chunk.entry_id: chunk for chunk in chunks}
        self.assertEqual(by_id[B].supersedes, ())
        self.assertEqual(by_id[B].evolves, ())
        self.assertEqual(by_id[C].supersedes, ())
        self.assertEqual(by_id[C].evolves, ())

        before = result.path.read_bytes()
        reapplied = apply_link_gap_stubs(
            audit_link_gaps(cwd=self.cwd, session_date="2026-06-02"),
            session_date="2026-06-02",
            cwd=self.cwd,
        )
        self.assertFalse(reapplied.changed)
        self.assertEqual(reapplied.skipped_entry_ids, (B, C))
        self.assertEqual(result.path.read_bytes(), before)

    def test_apply_stub_classify_check_round_trip(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)

        pending_check = check_session_links(cwd=self.cwd)
        pending = [issue for issue in pending_check.issues if issue.kind == "sidecar-unclassified-stub"]
        self.assertTrue(pending_check.ok)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].severity, "warning")

        text = applied.path.read_text(encoding="utf-8")
        applied.path.write_text(
            text.replace("classify_pending: true", f"evolves:\n  - {A}"),
            encoding="utf-8",
        )

        classified_check = check_session_links(cwd=self.cwd)
        self.assertTrue(classified_check.ok, classified_check.issues)
        self.assertNotIn("sidecar-unclassified-stub", {issue.kind for issue in classified_check.issues})
        chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(self.cwd, granularity="entry"), cwd=self.cwd
        )
        by_id = {chunk.entry_id: chunk for chunk in chunks}
        self.assertEqual(by_id[B].evolves, (A,))
        self.assertEqual(audit_link_gaps(cwd=self.cwd, session_date="2026-06-02"), [])

    def test_apply_updates_existing_sidecar_without_changing_classified_block(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            "\n".join(
                [
                    _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]),
                    _entry("2026-06-02 10:00", C, files=["pkg/foo.py"]),
                ]
            ),
            encoding="utf-8",
        )
        sidecar = self.sessions / "links" / "2026-06" / "2026-06-02.md"
        sidecar.parent.mkdir(parents=True)
        classified_block = "\n".join(
            [
                "## 2026-06-02 10:00 - classified entry cccc",
                "",
                "```yaml",
                f"entry_id: {C}",
                "evolves:",
                f"  - {A}",
                "```",
            ]
        )
        sidecar.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-links",
                    "link_date: 2026-06-02",
                    "---",
                    "",
                    classified_block,
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = apply_link_gap_stubs(
            audit_link_gaps(cwd=self.cwd, session_date="2026-06-02"),
            session_date="2026-06-02",
            cwd=self.cwd,
        )

        text = sidecar.read_text(encoding="utf-8")
        self.assertEqual(result.added_entry_ids, (B,))
        self.assertEqual(result.skipped_entry_ids, (C,))
        self.assertLess(text.index(f"entry_id: {B}"), text.index(f"entry_id: {C}"))
        self.assertIn(classified_block, text)
        self.assertEqual(text.count(f"entry_id: {C}"), 1)

    def test_cli_apply_creates_stub_and_reapply_is_idempotent(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )

        first_code, first_stdout, first_stderr = self._run_cli(
            "link", "audit", "--date", "2026-06-02", "--apply"
        )

        sidecar = self.sessions / "links" / "2026-06" / "2026-06-02.md"
        self.assertEqual(first_code, 0)
        self.assertEqual(first_stderr, "")
        self.assertIn("Applied 1 inert stub(s)", first_stdout)
        self.assertTrue(sidecar.exists())
        before = sidecar.read_bytes()

        second_code, second_stdout, second_stderr = self._run_cli(
            "link", "audit", "--date", "2026-06-02", "--apply"
        )

        self.assertEqual(second_code, 0)
        self.assertEqual(second_stderr, "")
        self.assertIn("No stubs added", second_stdout)
        self.assertEqual(sidecar.read_bytes(), before)

    def test_cli_apply_refuses_missing_date_and_for_scope(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )

        no_date_code, _no_date_stdout, no_date_stderr = self._run_cli(
            "link", "audit", "--apply"
        )
        for_code, _for_stdout, for_stderr = self._run_cli(
            "link", "audit", "--date", "2026-06-01", "--for", B, "--apply"
        )

        self.assertEqual(no_date_code, 2)
        self.assertIn("requires --date", no_date_stderr)
        self.assertEqual(for_code, 2)
        self.assertIn("cannot be combined with --for", for_stderr)
        self.assertFalse((self.sessions / "links").exists())


if __name__ == "__main__":
    unittest.main()
