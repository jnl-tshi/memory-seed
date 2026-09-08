"""`memory-seed link audit` (Phase 3): find entries that share files/topics but
carry no recorded edge.

Candidate MEMBERSHIP is decided lexically and never by semantic similarity. An
all-pairs cosine IS computed (since 2026-07-22) and does reorder the surviving
candidates; what the lexical gate rules out is cosine deciding *whether* a pair
is a candidate at all. So the semantic term can change rank but structurally
cannot change reach - see LinkAuditSemanticExposureTests.

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
    plan_link_audit_batches,
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

    def _gated(self, entry_id):
        """Only the candidates the LEXICAL GATE admitted.

        A gap can now hold two kinds of candidate, so "did a gap appear" stopped
        being the same question as "did the gate admit anything". A test about
        gate behaviour has to ask the second one explicitly or it silently
        starts measuring the semantic pass instead.
        """
        gap = self._gap(entry_id)
        return [c for c in gap.candidates if not c.ungated] if gap else []

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
        # Asserted against the GATED set: the semantic pass may still offer this
        # pair, which is its job, but no shared TERM may put it there.
        self.assertEqual(self._gated(B), [])

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
        self.assertEqual(chunk.decision_edges, (("evolves", "", A, "d1", ""),))
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
                ("evolves", "d2", A, "d1", ""),
                ("evolves", "d2", A, "d2", ""),
                ("evolves", "d1", B, "", ""),
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

    def test_batch_plan_packs_complete_pairs_and_reports_oversize_pairs(self):
        payload = {
            "semantic": {}, "criteria": {},
            "gaps": [{
                "entry_id": B, "title": "new", "session_date": "2026-06-01",
                "decisions": [{"ordinal": "d1", "name": "new", "text": "new body"}],
                "candidates": [
                    {"entry_id": A, "title": "old", "session_date": "2026-06-01", "decisions": [{"ordinal": "d1", "name": "old", "text": "old body"}]},
                    {"entry_id": C, "title": "older", "session_date": "2026-06-01", "decisions": [{"ordinal": "d1", "name": "older", "text": "older body"}]},
                ],
            }],
        }
        roomy = plan_link_audit_batches(payload, context_window_tokens=10_000)
        self.assertEqual(roomy["pair_count"], 2)
        self.assertEqual(roomy["batch_count"], 1)
        self.assertEqual(len(roomy["batches"][0]["pairs"]), 2)
        self.assertEqual(roomy["oversize_pair_count"], 0)
        self.assertEqual(roomy["measurement"]["evidence_budget_tokens"], 2000)

        tight = plan_link_audit_batches(payload, context_window_tokens=10)
        self.assertEqual(tight["batch_count"], 0)
        self.assertEqual(tight["oversize_pair_count"], 2)

    def test_cli_batch_plan_is_read_only_json(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"], decisions=["Alpha"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"], decisions=["Beta"]),
        )
        code, out, err = self._run_cli(
            "link", "batch-plan", "--for", B, "--context-window", "400000", "--no-semantic"
        )
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        self.assertEqual(plan["measurement"]["evidence_budget_tokens"], 80000)
        self.assertEqual(plan["pair_count"], 1)
        self.assertEqual(plan["batch_count"], 1)
        self.assertFalse((self.sessions / "links").exists())

    def test_batch_plan_excludes_linked_and_decisionless_candidates(self):
        payload = {
            "semantic": {}, "criteria": {},
            "gaps": [{
                "entry_id": B, "title": "new", "session_date": "2026-06-01",
                "decisions": [{"ordinal": "d1", "name": "new", "text": "new body"}],
                "candidates": [
                    {"entry_id": A, "title": "linked", "session_date": "2026-06-01",
                     "already_related": True,
                     "decisions": [{"ordinal": "d1", "name": "old", "text": "old body"}]},
                    {"entry_id": C, "title": "decisionless", "session_date": "2026-06-01",
                     "decisions": []},
                ],
            }],
        }
        plan = plan_link_audit_batches(payload, context_window_tokens=10_000)
        self.assertEqual(plan["pair_count"], 0)
        self.assertEqual(plan["batch_count"], 0)
        self.assertEqual(plan["excluded_pair_count"], 2)
        self.assertEqual(
            [item["reason"] for item in plan["excluded_pairs"]],
            ["already_related", "missing_decision"],
        )

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
        # Only B gapped ON THE GATE (C shares nothing); B's candidate A is from
        # the PRIOR session. Filtered to gated candidates because the semantic
        # pass is corpus-wide by design and would otherwise mask the scoping.
        gated = {g.entry_id: [c for c in g.candidates if not c.ungated] for g in gaps}
        self.assertEqual([eid for eid, cands in gated.items() if cands], [B])
        self.assertEqual([c.entry_id for c in gated[B]], [A])
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

    def test_apply_sorts_a_wall_clock_stamped_sidecar_instead_of_refusing(self):
        # A sidecar is filed under its SOURCE entry's date, but a later
        # enrichment pass stamps its blocks with the AUTHORING wall clock (block
        # identity is (entry_id, heading timestamp), so a second block for one
        # entry needs a distinct stamp). Those two rules together make a
        # re-visited file legitimately non-chronological. `apply` used to refuse
        # such a file outright, which permanently closed the date to further
        # scaffolding - four dates in this repo's own corpus were stuck that way.
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
        links_dir = self.sessions / "links" / "2026-06"
        links_dir.mkdir(parents=True, exist_ok=True)
        sidecar = links_dir / "2026-06-02.md"
        # Two passes over C, appended newest-first: out of chronological order.
        second_pass = f"## 2026-07-25 20:02 - second pass\n\n```yaml\nentry_id: {C}\nevolves:\n  - {A} (builds-on)\n```"
        first_pass = f"## 2026-07-25 17:58 - first pass\n\n```yaml\nentry_id: {C}\nrelated_entries:\n  - {B}\n```"
        sidecar.write_text(
            f"---\ntags:\n  - session-log-links\nlink_date: 2026-06-02\n---\n\n{second_pass}\n\n{first_pass}\n",
            encoding="utf-8",
        )

        gaps = audit_link_gaps(cwd=self.cwd, session_date="2026-06-02")
        result = apply_link_gap_stubs(gaps, session_date="2026-06-02", cwd=self.cwd)

        # C already carries blocks, so only B is scaffolded.
        self.assertEqual(result.added_entry_ids, (B,))
        self.assertEqual(result.skipped_entry_ids, (C,))
        text = sidecar.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\ntags:\n  - session-log-links\nlink_date: 2026-06-02\n---\n"))
        # Sorted on write: B's stub (the entry's own stamp) precedes both
        # wall-clock blocks, and those two are now in order.
        self.assertLess(text.index("## 2026-06-02 09:00"), text.index("## 2026-07-25 17:58"))
        self.assertLess(text.index("## 2026-07-25 17:58"), text.index("## 2026-07-25 20:02"))
        # Reordering is a pure permutation - both published blocks survive verbatim.
        self.assertIn(second_pass, text)
        self.assertIn(first_pass, text)
        self.assertEqual(text.count("classify_pending: true"), 1)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_apply_appends_to_a_frontmatter_only_sidecar_without_duplicating_it(self):
        # The rewrite computes the preamble from the first block; a file with
        # valid frontmatter and NO blocks has none, so this path takes the whole
        # existing text as preamble. It must not duplicate or mangle it.
        (self.sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]), encoding="utf-8"
        )
        (self.sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, files=["pkg/foo.py"]), encoding="utf-8"
        )
        links_dir = self.sessions / "links" / "2026-06"
        links_dir.mkdir(parents=True, exist_ok=True)
        sidecar = links_dir / "2026-06-02.md"
        sidecar.write_text("---\ntags:\n  - session-log-links\nlink_date: 2026-06-02\n---\n", encoding="utf-8")

        result = apply_link_gap_stubs(
            audit_link_gaps(cwd=self.cwd, session_date="2026-06-02"),
            session_date="2026-06-02",
            cwd=self.cwd,
        )

        self.assertEqual(result.added_entry_ids, (B,))
        text = sidecar.read_text(encoding="utf-8")
        self.assertEqual(text.count("link_date: 2026-06-02"), 1)
        self.assertEqual(text.count("- session-log-links"), 1)
        self.assertTrue(
            text.startswith("---\ntags:\n  - session-log-links\nlink_date: 2026-06-02\n---\n\n## 2026-06-02 09:00"),
            text[:160],
        )
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

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
            text.replace("classify_pending: true", f"evolves:\n  - {A} (builds-on)"),
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


D = "mse_" + "d" * 16  # filler, so idf of a shared file is not log(1) == 0


class _StubProvider:
    """Deterministic embeddings, keyed on which entry_ids are declared "near".

    Real model2vec is a hard dependency, but loading it here would make these
    assertions depend on a model's opinion of fixture prose. Keying on entry_id
    rather than a marker word in the text matters: a marker word would also
    become a shared TITLE term and contaminate the lexical half of the score,
    which is exactly what these tests need to hold still.
    """

    name = "stub:test"

    def __init__(self, near=()):
        self.near = tuple(near)
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        # Unit basis vectors: "near" entries are identical (cosine 1), everything
        # else is orthogonal to them (cosine 0). No floating-point slack.
        return [[1.0, 0.0] if any(eid in text for eid in self.near) else [0.0, 1.0] for text in texts]


class LinkAuditSemanticExposureTests(unittest.TestCase):
    """The semantic term must be inspectable and its absence must be reported.

    Semantic ranking shipped 2026-07-22 defaulted ON, but the cosine was folded
    into `file_overlap_score` and a missing provider degraded to lexical
    silently. Measured on the 637-entry corpus the term changes the top-5 for
    610/629 sources, so a silent fallback is a materially different answer.

    Own setUp rather than subclassing LinkAuditTests: inheriting would re-run
    that whole class's tests a second time for no added coverage.
    """

    setUp = LinkAuditTests.setUp
    _write = LinkAuditTests._write
    _run_cli = LinkAuditTests._run_cli

    def _patch_provider(self, provider, fallback=None):
        import memory_seed.retrieval as retrieval

        original = retrieval.resolve_semantic_provider
        name = getattr(provider, "name", "stub:test")
        self.addCleanup(lambda: setattr(retrieval, "resolve_semantic_provider", original))
        retrieval.resolve_semantic_provider = lambda *a, **k: (provider, name, fallback)
        return provider

    def _pair(self):
        """A and B share a file (the lexical gate) and are semantically identical.

        The unrelated filler entry is load-bearing: with only the pair in the
        corpus, idf(shared file) is log(2/2) == 0 and the lexical half of the
        score would be zero for reasons unrelated to what is under test.
        """
        self._write(
            _entry("2026-06-01 08:00", D, files=["pkg/other.py"]),
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B, files=["pkg/foo.py"]),
        )
        return _StubProvider(near=(A, B))

    def test_no_semantic_skips_the_provider_entirely(self):
        """--no-semantic must load no model - the offline/lightweight path."""
        import memory_seed.retrieval as retrieval

        self._pair()
        calls = []
        original = retrieval.resolve_semantic_provider
        self.addCleanup(lambda: setattr(retrieval, "resolve_semantic_provider", original))

        def _tripwire(*args, **kwargs):
            calls.append(1)
            return None, None, None

        retrieval.resolve_semantic_provider = _tripwire

        status = {}
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=B, semantic_enabled=False, semantic_status=status)

        self.assertEqual(calls, [], "semantic_enabled=False must not resolve a provider")
        self.assertEqual(status["requested"], False)
        self.assertEqual(status["active"], False)
        self.assertIsNone(gaps[0].candidates[0].semantic_score)

    def test_empty_corpus_still_reports_that_semantic_was_requested(self):
        """The status dict is seeded before the empty-corpus early return.

        Left unset, `requested` reads False and the CLI would label a default
        (semantic) run as if `--no-semantic` had been passed.
        """
        status = {}
        gaps = audit_link_gaps(cwd=self.cwd, semantic_status=status)

        self.assertEqual(gaps, [])
        self.assertEqual(status["requested"], True)
        self.assertEqual(status["active"], False)
        self.assertIsNone(status["fallback_reason"])

        code, stdout, _ = self._run_cli("link", "audit")
        self.assertEqual(code, 0)
        self.assertIn("no entries to embed", stdout)
        self.assertNotIn("--no-semantic", stdout)

    def test_unavailable_provider_is_reported_not_swallowed(self):
        self._pair()
        self._patch_provider(None, fallback="No module named 'model2vec'")

        status = {}
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=B, semantic_status=status)

        self.assertEqual(status["requested"], True)
        self.assertEqual(status["active"], False)
        self.assertEqual(status["fallback_reason"], "No module named 'model2vec'")
        # Ranking silently degraded to lexical before this change.
        self.assertIsNone(gaps[0].candidates[0].semantic_score)

    def test_score_decomposes_into_lexical_plus_weighted_cosine(self):
        from memory_seed.retrieval import SEMANTIC_OVERLAP_BOOST

        self._patch_provider(self._pair())

        gap = audit_link_gaps(cwd=self.cwd, entry_id=B)[0]
        cand = gap.candidates[0]

        self.assertEqual(cand.entry_id, A)
        # A and B are both "near" -> identical unit vectors -> cosine exactly 1.
        self.assertAlmostEqual(cand.semantic_score, 1.0, places=5)
        self.assertAlmostEqual(
            cand.file_overlap_score,
            cand.lexical_score + SEMANTIC_OVERLAP_BOOST * cand.semantic_score,
            places=4,
        )
        self.assertGreater(cand.lexical_score, 0.0)

    def test_semantic_term_reorders_without_changing_membership(self):
        """The exposed term must be the thing actually driving the order.

        This is the measured shape of the signal: on the real corpus the semantic
        term changed the top-5 for 610/629 sources while candidate MEMBERSHIP
        stayed lexical, because cosine only ever adds to the score of a pair the
        lexical gate already admitted.
        """
        self._write(
            # A wins lexically: it shares the distinctive title term with C.
            _entry("2026-06-01 08:00", A, files=["pkg/foo.py"], title="alpha shibboleth"),
            # B wins semantically: no shared title term, but near C.
            _entry("2026-06-01 09:00", B, files=["pkg/foo.py"], title="beta"),
            _entry("2026-06-01 10:00", C, files=["pkg/foo.py"], title="gamma shibboleth"),
            _entry("2026-06-01 07:00", D, files=["pkg/other.py"]),
        )
        self._patch_provider(_StubProvider(near=(B, C)))

        with_semantic = [c.entry_id for c in audit_link_gaps(cwd=self.cwd, entry_id=C)[0].candidates]
        lexical_only = [
            c.entry_id for c in audit_link_gaps(cwd=self.cwd, entry_id=C, semantic_enabled=False)[0].candidates
        ]

        self.assertEqual(lexical_only[0], A, "lexically the shared title term should lead")
        self.assertEqual(with_semantic[0], B, "semantically the near neighbour should lead")
        self.assertEqual(set(with_semantic), set(lexical_only), "membership stays lexical")
        self.assertNotEqual(with_semantic, lexical_only, "ranking differs, membership does not")

    def test_ungated_pass_surfaces_a_pair_the_gate_cannot_see(self):
        """The blind spot the second source exists to cover.

        D shares no file, no topic and no title term with C, so the lexical gate
        can never admit it however related the two are. Semantic rank can.
        """
        self._write(
            _entry("2026-06-01 08:00", A, files=["pkg/foo.py"], title="alpha"),
            _entry("2026-06-01 09:00", D, files=["pkg/other.py"], title="delta"),
            _entry("2026-06-01 10:00", C, files=["pkg/foo.py"], title="gamma"),
        )
        self._patch_provider(_StubProvider(near=(D, C)))

        gap = audit_link_gaps(cwd=self.cwd, entry_id=C)[0]
        by_id = {c.entry_id: c for c in gap.candidates}

        self.assertIn(D, by_id, "the semantic pass must reach past the gate")
        self.assertTrue(by_id[D].ungated)
        self.assertEqual(by_id[D].shared_files, ())
        self.assertEqual(by_id[D].shared_title_terms, ())
        self.assertEqual(by_id[D].lexical_score, 0.0)
        # A is still here on file overlap, and is NOT mislabelled.
        self.assertIn(A, by_id)
        self.assertFalse(by_id[A].ungated)

    def test_ungated_candidates_never_displace_gated_ones(self):
        """A separate cap, so recall widening cannot cost checkable evidence."""
        self._write(
            _entry("2026-06-01 07:00", A, files=["pkg/foo.py"], title="alpha"),
            _entry("2026-06-01 08:00", B, files=["pkg/foo.py"], title="beta"),
            _entry("2026-06-01 09:00", D, files=["pkg/other.py"], title="delta"),
            _entry("2026-06-01 10:00", C, files=["pkg/foo.py"], title="gamma"),
        )
        self._patch_provider(_StubProvider(near=(D, C)))

        gap = audit_link_gaps(cwd=self.cwd, entry_id=C, top_k=2)[0]
        gated = [c.entry_id for c in gap.candidates if not c.ungated]
        ungated = [c.entry_id for c in gap.candidates if c.ungated]

        self.assertEqual(sorted(gated), sorted([A, B]), "top_k gated survivors are untouched")
        self.assertEqual(ungated, [D])
        self.assertEqual([c.ungated for c in gap.candidates], [False, False, True],
                         "ungated candidates are appended after the gated slice")

    def test_no_ungated_candidates_when_semantic_is_off(self):
        """A top-N over all-zero cosines is an arbitrary set wearing a ranking's
        authority, so the pass is skipped rather than degraded."""
        self._write(
            _entry("2026-06-01 08:00", A, files=["pkg/foo.py"], title="alpha"),
            _entry("2026-06-01 09:00", D, files=["pkg/other.py"], title="delta"),
            _entry("2026-06-01 10:00", C, files=["pkg/foo.py"], title="gamma"),
        )
        self._patch_provider(_StubProvider(near=(D, C)))

        gap = audit_link_gaps(cwd=self.cwd, entry_id=C, semantic_enabled=False)[0]

        self.assertEqual([c.ungated for c in gap.candidates], [False])
        self.assertNotIn(D, [c.entry_id for c in gap.candidates])

    def test_ungated_candidate_is_labelled_in_the_written_stub(self):
        """A reader of the sidecar must see that this line has no checkable
        overlap behind it."""
        self._write(
            _entry("2026-06-01 08:00", A, files=["pkg/foo.py"], title="alpha"),
            _entry("2026-06-01 09:00", D, files=["pkg/other.py"], title="delta"),
            _entry("2026-06-01 10:00", C, files=["pkg/foo.py"], title="gamma"),
        )
        self._patch_provider(_StubProvider(near=(D, C)))

        gaps = [g for g in audit_link_gaps(cwd=self.cwd, session_date="2026-06-01") if g.entry_id == C]
        result = apply_link_gap_stubs(gaps, session_date="2026-06-01", cwd=self.cwd)
        text = result.path.read_text(encoding="utf-8")

        self.assertIn(f"#   - {D}  # UNGATED - semantic rank only", text)
        self.assertIn(f"#   - {A}  # files: pkg/foo.py", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_ungated_pass_never_resurfaces_an_already_related_pair(self):
        """It carries strictly weaker evidence than a topic-only candidate, so
        it cannot justify a laxer rule than the one that suppresses those."""
        self._write(
            _entry("2026-06-01 09:00", D, title="delta"),
            _entry("2026-06-01 10:00", C, title="gamma", related=[D]),
        )
        self._patch_provider(_StubProvider(near=(D, C)))

        self.assertEqual(audit_link_gaps(cwd=self.cwd, entry_id=C), [])

    def test_cli_reports_ranking_provenance_and_cosine(self):
        self._patch_provider(self._pair())

        code, stdout, _ = self._run_cli("link", "audit", "--for", B)

        self.assertEqual(code, 0)
        self.assertIn("Ranking: lexical + semantic (stub:test)", stdout)
        self.assertIn("cosine: 1.00", stdout)

    def test_cli_reports_unavailable_semantic_loudly(self):
        self._pair()
        self._patch_provider(None, fallback="boom")

        code, stdout, _ = self._run_cli("link", "audit", "--for", B)

        self.assertEqual(code, 0)
        self.assertIn("UNAVAILABLE", stdout)
        self.assertIn("boom", stdout)
        self.assertNotIn("cosine:", stdout)

    def test_cli_no_semantic_flag_labels_lexical_ranking(self):
        self._patch_provider(self._pair())

        code, stdout, _ = self._run_cli("link", "audit", "--for", B, "--no-semantic")

        self.assertEqual(code, 0)
        self.assertIn("lexical only (--no-semantic)", stdout)
        self.assertNotIn("cosine:", stdout)

    def test_json_carries_semantic_block_and_decomposed_scores(self):
        self._patch_provider(self._pair())

        code, stdout, _ = self._run_cli("link", "audit", "--for", B, "--json")
        payload = json.loads(stdout)

        self.assertEqual(code, 0)
        self.assertEqual(payload["semantic"]["active"], True)
        self.assertEqual(payload["semantic"]["provider"], "stub:test")
        cand = payload["gaps"][0]["candidates"][0]
        self.assertAlmostEqual(cand["semantic_score"], 1.0, places=5)
        self.assertIn("lexical_score", cand)
        self.assertAlmostEqual(cand["score"], cand["lexical_score"] + 160.0 * cand["semantic_score"], places=4)


if __name__ == "__main__":
    unittest.main()


class ChainPositionCandidateTests(unittest.TestCase):
    """Candidates are annotated from the decision-keyed refines spine: interior
    members are related-only, replaced ones are never offered (their terminal
    replacement substitutes). The invalid option leaves the menu at
    candidate-generation time - the closed-list lesson applied to verdicts."""

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-chainpos-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)

    def _write(self, *entries):
        (self.sessions / "2026-06-01.md").write_text("\n".join(entries), encoding="utf-8")

    def _sidecar_lines(self, *lines):
        d = self.sessions / "links" / "2026-06"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "2026-06-01.md"
        # Frontmatter on first write: apply_link_gap_stubs refuses an existing
        # sidecar file without it.
        head = (
            path.read_text(encoding="utf-8")
            if path.exists()
            else "---\ntags:\n  - session-log-links\nlink_date: 2026-06-01\n---\n\n"
        )
        path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")

    def _candidates(self, entry_id):
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=entry_id, semantic_enabled=False)
        return {c.entry_id: c for c in (gaps[0].candidates if gaps else ())}

    def test_interior_chain_member_is_annotated_related_only(self):
        # B refines A, so A's slot is taken: A is interior, the chain lives at B.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B),
            _entry("2026-06-01 11:00", C, files=["pkg/foo.py"]),
        )
        self._sidecar_lines(
            "## 2026-06-01 12:00 - typed", "", "```yaml", f"entry_id: {B}",
            "evolves:", f"  - {A} (refines)", "```", "",
        )
        cands = self._candidates(C)
        self.assertIn(A, cands)
        self.assertEqual(cands[A].chain_position, "interior")
        self.assertEqual(cands[A].refines_taken_by, f"{B}:d1")
        self.assertEqual(cands[A].current_form, f"{B}:d1")

    def test_open_head_keeps_default_position(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 11:00", C, files=["pkg/foo.py"]),
        )
        cands = self._candidates(C)
        self.assertEqual(cands[A].chain_position, "head")
        self.assertIsNone(cands[A].refines_taken_by)

    def test_replaced_candidate_is_dropped_and_its_replacement_substitutes(self):
        # A is replaced by B. B shares nothing with the target, so only the
        # substitution can surface it - and A itself must never appear.
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B),
            _entry("2026-06-01 11:00", C, files=["pkg/foo.py"]),
        )
        self._sidecar_lines(
            "## 2026-06-01 12:00 - replacement", "", "```yaml", f"entry_id: {B}",
            "replaces:", f"  - {A}", "```", "",
        )
        cands = self._candidates(C)
        self.assertNotIn(A, cands, "a replaced decision is not a lifecycle target")
        self.assertIn(B, cands)
        self.assertEqual(cands[B].substitute_for, A)
        self.assertEqual(cands[B].chain_position, "head")

    def test_stub_renderer_carries_the_position_flags(self):
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 10:00", B),
            _entry("2026-06-01 11:00", C, files=["pkg/foo.py"]),
        )
        self._sidecar_lines(
            "## 2026-06-01 12:00 - typed", "", "```yaml", f"entry_id: {B}",
            "evolves:", f"  - {A} (refines)", "```", "",
        )
        gaps = audit_link_gaps(cwd=self.cwd, entry_id=C, semantic_enabled=False)
        applied = apply_link_gap_stubs(gaps, session_date="2026-06-01", cwd=self.cwd)
        text = applied.path.read_text(encoding="utf-8")
        self.assertIn("INTERIOR chain member - related-only", text)
        self.assertIn(f"refines taken by {B}:d1", text)

    def test_spine_failure_degrades_to_unannotated_candidates(self):
        # Fail-open like the sibling spine call sites: annotation is advisory
        # context, so a spine failure must not take down the audit (or the ESR
        # preflight that calls it).
        from unittest import mock
        self._write(
            _entry("2026-06-01 09:00", A, files=["pkg/foo.py"]),
            _entry("2026-06-01 11:00", C, files=["pkg/foo.py"]),
        )
        with mock.patch(
            "memory_seed.semantic_cache.build_refines_spine",
            side_effect=RuntimeError("boom"),
        ):
            gaps = audit_link_gaps(cwd=self.cwd, entry_id=C, semantic_enabled=False)
        cands = {c.entry_id: c for c in gaps[0].candidates}
        self.assertIn(A, cands)
        self.assertEqual(cands[A].chain_position, "head")
