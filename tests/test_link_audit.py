"""`memory-seed link audit` (Phase 3): find entries that share files/topics but
carry no recorded edge, without an all-pairs semantic scan.

Candidate generation: for each target, only OLDER entries sharing >=1 F: file
OR >=1 topic. File overlap qualifies a pair even with no shared topic (files
override topics); topic-only overlap is suppressed by any existing edge, while
file overlap surfaces even a merely-"related" pair as a lifecycle upgrade
candidate. A recorded supersedes/evolves edge (YAML or sidecar) removes the pair.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.retrieval import audit_link_gaps

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


if __name__ == "__main__":
    unittest.main()
