"""`memory-seed link audit` (Phase 3): find entries that share files/topics but
carry no recorded edge, without an all-pairs semantic scan.

Candidate generation: for each target, only OLDER entries sharing >=1 F: file
OR >=1 topic. File overlap qualifies a pair even with no shared topic (files
override topics); topic-only overlap is suppressed by any existing edge, while
file overlap surfaces even a merely-"related" pair as a lifecycle upgrade
candidate. A recorded replaces/evolves edge (YAML or sidecar) removes the pair.
"""

import contextlib
import json
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


def _entry(dt, eid, *, topics=(), files=(), related=(), replaces=(), evolves=(), title=None, decisions=None):
    # Titles must share NO word by default. Candidate scoring now counts shared
    # distinctive title terms, so a fixture title like "entry aaaa" would make
    # every pair a title match and quietly defeat the tests that assert a pair
    # is NOT surfaced. Pass `title=` explicitly to exercise title overlap.
    # `decisions=[name, ...]` writes a `#### Dn - name` subsection per name, so a
    # fixture can carry addressable decisions; omitted keeps the plain body.
    lines = [f"## {dt} - {title or eid[-4:]}", "", "```yaml", f"entry_id: {eid}"]
    for key, vals in (
        ("topics", topics),
        ("related_entries", related),
        ("replaces", replaces),
        ("evolves", evolves),
    ):
        if vals:
            lines.append(f"{key}:")
            lines.extend(f"  - {v}" for v in vals)
    lines += ["```", ""]
    lines += [f"- F: `{f}`" for f in files]
    lines += [""]
    if decisions:
        lines.append("### Decisions")
        for i, name in enumerate(decisions, 1):
            lines += ["", f"#### D{i} - {name}", "", f"- D: decision {i} body", f"- R: reason {i}"]
    else:
        lines.append("Body text.")
    lines += [""]
    return "\n".join(lines)


class LinkAuditTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-linkaudit-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def _write(self, *entries):
        (self.sessions / "2026-06-01.md").write_text("\n".join(entries), encoding="utf-8")

    def _sidecar(self, source, *, replaces=(), evolves=()):
        d = self.sessions / "links" / "2026-06"
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"## 2026-06-01 12:00 - edge", "", "```yaml", f"entry_id: {source}"]
        for key, refs in (("replaces", replaces), ("evolves", evolves)):
            if refs:
                lines.append(f"{key}:")
                lines += [f"  - {ref}" for ref in refs]
        lines += ["```", ""]
        (d / "2026-06-01.md").write_text("\n".join(lines), encoding="utf-8")

    def _gap(self, entry_id):
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=entry_id)
        return gaps[0] if gaps else None

    def _run_cli(self, *args, cwd=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(cwd or self.cwd)
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

    def test_shared_title_terms_surface_a_candidate_without_file_overlap(self):
        # The signal that catches a predecessor sharing no files: measured
        # against the corpus's author-declared lifecycle edges, adding
        # idf-weighted title-term overlap moved recall@5 from 45% to 59%.
        self._write(
            _entry("2026-06-01 09:00", A, title="hide evolves connectors until selected"),
            _entry("2026-06-01 10:00", B, title="promote selected-only evolves routes to main"),
        )
        gap = self._gap(B)
        self.assertEqual([c.entry_id for c in gap.candidates], [A])
        self.assertEqual(gap.candidates[0].shared_files, ())
        self.assertEqual(gap.candidates[0].shared_title_terms, ("evolves", "selected"))

    def test_title_stamp_is_not_a_shared_term(self):
        # A chunk title carries its `YYYY-MM-DD HH:MM - ` stamp. Left in, the
        # year would be a term shared by essentially every pair in the corpus,
        # turning the discriminating signal into a universal one.
        self._write(
            _entry("2026-06-01 09:00", A, title="alpha"),
            _entry("2026-06-01 10:00", B, title="beta"),
        )
        self.assertIsNone(self._gap(B))

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
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], replaces=[A]),
        )
        self.assertIsNone(self._gap(B))

    def test_entry_yaml_decision_ref_suppresses_the_pair_and_populates_chunk(self):
        # Write-time grammar (2026-07-24): a `:dN` item in the entry's OWN
        # evolves list peels into chunk.decision_edges (never the entry-level
        # list) and suppresses the pair as a gap, exactly like a sidecar ref.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"], decisions=["Alpha", "Beta"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], evolves=[f"{A}:d1"]),
        )
        chunk = next(
            c for c in extract_memory_chunks(self.cwd, granularity="entry") if c.entry_id == B
        )
        self.assertEqual(chunk.decision_edges, (("evolves", "", A, "d1"),))
        self.assertEqual(chunk.evolves, ())  # no projection to entry level
        self.assertIsNone(self._gap(B))

    def test_arrow_and_comma_forms_populate_chunk_decision_edges(self):
        # Grammar v2 (2026-07-24): `d2 -> mse_x:d1,d2` carries the authoring
        # decision and one edge per target ordinal; an arrow-prefixed BARE ref
        # keeps its entry-level edge (arrow stripped) AND records the source
        # attribution with no target ordinal.
        self._write(
            _entry("2026-06-01 08:00", A, files=["pkg/foo.py"], decisions=["Alpha", "Beta"]),
            _entry("2026-06-01 09:00", B, files=["pkg/bar.py"], decisions=["Gamma"]),
            _entry(
                "2026-06-01 10:00", C, files=["pkg/foo.py"],
                decisions=["One", "Two"],
                evolves=[f"d2 -> {A}:d1,d2", f"d1 -> {B}"],
            ),
        )
        chunk = next(
            c for c in extract_memory_chunks(self.cwd, granularity="entry") if c.entry_id == C
        )
        self.assertEqual(
            chunk.decision_edges,
            (
                ("evolves", "d2", A, "d1"),
                ("evolves", "d2", A, "d2"),
                ("evolves", "d1", B, ""),
            ),
        )
        self.assertEqual(chunk.evolves, (B,))  # arrow-bare stays entry-level
        self.assertIsNone(self._gap(C))  # both pairs suppressed as gaps

    def test_target_and_candidate_carry_decision_structure(self):
        # Decision awareness is SURFACED, not scored: both ends' decisions ride
        # on the gap so a human or a judgment agent can narrow an edge to :dN.
        # The scoring is unchanged - the pair still surfaces on file overlap.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"], decisions=["Alpha", "Beta"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], decisions=["Gamma", "Delta", "Epsilon"]),
        )
        gap = self._gap(B)
        self.assertEqual([d.ordinal for d in gap.decisions], ["d1", "d2", "d3"])
        self.assertEqual(gap.decisions[0].name, "Gamma")
        cand = gap.candidates[0]
        self.assertEqual([d.ordinal for d in cand.decisions], ["d1", "d2"])
        self.assertEqual(cand.decisions[1].name, "Beta")
        self.assertIn("reason 1", cand.decisions[0].text)

    def test_json_emits_judgment_ready_candidates_with_both_ends_decisions(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"], decisions=["Alpha", "Beta"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], decisions=["Gamma"]),
        )
        code, out, err = self._run_cli("link", "audit", "--for", B, "--json")
        self.assertEqual(code, 0, err)
        payload = json.loads(out[out.index("{"):])
        self.assertIn("narrowing", payload["criteria"])
        gap = payload["gaps"][0]
        self.assertEqual(gap["entry_id"], B)
        self.assertEqual([d["ordinal"] for d in gap["decisions"]], ["d1"])
        cand = gap["candidates"][0]
        self.assertEqual(cand["entry_id"], A)
        self.assertEqual([d["ordinal"] for d in cand["decisions"]], ["d1", "d2"])
        self.assertIn("decision 1 body", cand["decisions"][0]["text"])

    def test_json_and_apply_are_mutually_exclusive(self):
        self._write(_entry("2026-06-01 09:00", A, files=["pkg/foo.py"]))
        code, _out, err = self._run_cli("link", "audit", "--json", "--apply", "--date", "2026-06-01")
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined", err)

    def test_decision_level_sidecar_edge_suppresses_the_pair(self):
        # A `<id>:dN` ref records the pair at finer granularity. It never
        # projects into entry-level edge sets, but the audit must treat the
        # pair as linked - else every decision-narrowed edge re-surfaces as a
        # "gap" forever. Found live: the first swarm-validated :d1 edge was
        # written and the same pair immediately re-surfaced.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"], decisions=["Alpha", "Beta"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        self._sidecar(B, evolves=[f"{A}:d1"])
        self.assertIsNone(self._gap(B))

    def test_sidecar_lifecycle_edge_suppresses_the_pair(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        self._sidecar(B, replaces=[A])
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
        self.assertNotIn("\nreplaces:", text)
        self.assertNotIn("\nevolves:", text)
        for path, before in entry_bytes.items():
            self.assertEqual(path.read_bytes(), before)

        chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(self.cwd, granularity="entry"), cwd=self.cwd
        )
        by_id = {chunk.entry_id: chunk for chunk in chunks}
        self.assertEqual(by_id[B].replaces, ())
        self.assertEqual(by_id[B].evolves, ())
        self.assertEqual(by_id[C].replaces, ())
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

    def test_examined_but_empty_resolves_a_stub_without_inventing_an_edge(self):
        # The other way a stub resolves. Before `edge_status`, "I looked and
        # there is no relationship" had no spelling: you either invented an edge
        # or deleted the block, and deleting it destroys the evidence that
        # anyone looked. Every examined-but-empty entry was then
        # indistinguishable from an un-examined one.
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)
        text = applied.path.read_text(encoding="utf-8")
        applied.path.write_text(
            text.replace(
                "classify_pending: true",
                "edge_status: not_applicable\nnote: shared file only; no lifecycle relationship",
            ),
            encoding="utf-8",
        )

        result = check_session_links(cwd=self.cwd)

        self.assertTrue(result.ok, result.issues)
        self.assertNotIn("sidecar-unclassified-stub", {issue.kind for issue in result.issues})
        # It records a judgement, not a relationship, so it must create no edge.
        chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(self.cwd, granularity="entry"), cwd=self.cwd
        )
        by_id = {chunk.entry_id: chunk for chunk in chunks}
        self.assertEqual(by_id[B].evolves, ())
        self.assertEqual(by_id[B].related_entries, ())

    def test_edge_status_unavailable_is_the_explicit_spelling_of_pending(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)
        text = applied.path.read_text(encoding="utf-8")
        applied.path.write_text(
            text.replace("classify_pending: true", "edge_status: unavailable"), encoding="utf-8"
        )

        result = check_session_links(cwd=self.cwd)

        self.assertTrue(result.ok)
        self.assertIn("sidecar-unclassified-stub", {issue.kind for issue in result.issues})

    def test_unknown_edge_status_is_a_hard_error(self):
        # A typo must not silently read as "examined". The whole value of the
        # state is that it is trustworthy, so an unrecognised value fails.
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)
        text = applied.path.read_text(encoding="utf-8")
        applied.path.write_text(
            text.replace("classify_pending: true", "edge_status: not-applicable"), encoding="utf-8"
        )

        result = check_session_links(cwd=self.cwd)

        self.assertFalse(result.ok)
        self.assertIn("malformed-link-sidecar", {issue.kind for issue in result.issues})

    def test_edge_status_governs_when_a_stale_pending_flag_remains(self):
        # Both keys present: `edge_status` is the later, more specific
        # statement, so it wins rather than the block staying flagged forever.
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)
        text = applied.path.read_text(encoding="utf-8")
        applied.path.write_text(
            text.replace(
                "classify_pending: true",
                "classify_pending: true\nedge_status: not_applicable",
            ),
            encoding="utf-8",
        )

        result = check_session_links(cwd=self.cwd)

        self.assertNotIn("sidecar-unclassified-stub", {issue.kind for issue in result.issues})

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

    def test_cli_apply_from_nested_directory_reports_workspace_relative_path(self):
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        nested = self.cwd / "nested" / "directory"
        nested.mkdir(parents=True)

        exit_code, stdout, stderr = self._run_cli(
            "link", "audit", "--date", "2026-06-02", "--apply", cwd=nested
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Applied 1 inert stub(s) to .memory-seed/sessions/links/2026-06/2026-06-02.md.", stdout)

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
