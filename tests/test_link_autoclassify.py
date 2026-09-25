"""Automatic lifecycle-link classification (JNL, 2026-09-25).

Validated swarm verdicts become live, retractable edges without a human approval step.
`replaces`/`refines` need two agreeing runs; `builds-on`/`related` need one; a human
`link verify` record raises a machine edge to full weight.
"""

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, check_session_links
from memory_seed.link_autoclassify import apply_auto_links, plan_auto_links, verify_link
from memory_seed.retrieval import (
    collect_link_swarm_run,
    entry_link_sidecars,
    materialize_link_swarm_run,
    plan_link_audit_batches,
)
from test_link_audit import _entry

A = "mse_" + "a" * 16  # older
B = "mse_" + "b" * 16  # newer
HEADER = (
    "schema: memory-seed.link-swarm-verdicts.v1\nbatch: 1\n"
    "verdicts[1]{source_entry_id,source_decision,candidate_entry_id,candidate_decision,verdict,quote,"
    "quote_entry_id,why,confidence,exclusion_reason}:\n"
)
QUOTE = "the older proposal remains useful as design rationale"


class AutoClassifyTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-autolink-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        sessions = self.cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", A, title="older proposal", decisions=["Old"]), encoding="utf-8"
        )
        (sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", B, title="newer implementation", decisions=["New"]), encoding="utf-8"
        )
        payload = {
            "semantic": {}, "criteria": {},
            "gaps": [{
                "entry_id": B, "title": "new", "session_date": "2026-06-02",
                "decisions": [{"ordinal": "d1", "name": "new", "text": "the newer decision implements the older proposal"}],
                "candidates": [{
                    "entry_id": A, "title": "old", "session_date": "2026-06-01", "score": 20.0,
                    "decisions": [{"ordinal": "d1", "name": "old", "text": QUOTE}],
                }],
            }],
        }
        self.plan = plan_link_audit_batches(payload, context_window_tokens=10_000, worker_skill_text="# skill\n")

    def _run(self, name, verdict, confidence="0.9"):
        run_dir = self.cwd / name
        materialize_link_swarm_run(self.plan, run_dir)
        if verdict == "none":
            row = f"{B},d1,{A},d1,none,null,null,\"unrelated\",null,\"no shared decision\"\n"
        else:
            row = f'{B},d1,{A},d1,{verdict},"{QUOTE}",{A},"implements it",{confidence},null\n'
        (run_dir / "findings" / "batch-0001.toon").write_text(HEADER + row, encoding="utf-8")
        self.assertEqual(collect_link_swarm_run(run_dir)["status"], "complete")
        return run_dir

    def test_refines_needs_two_agreeing_runs(self):
        one = self._run("r1", "refines")
        single = plan_auto_links(one)
        self.assertEqual([edge.verdict for edge in single.edges], ["related"], "one run may only support related")

        two = plan_auto_links(one, self._run("r2", "refines", "0.7"))
        self.assertEqual(len(two.edges), 1)
        edge = two.edges[0]
        self.assertEqual((edge.kind, edge.ref, edge.agreement), ("evolves", f"{A} (refines)", "two-run"))
        self.assertEqual(edge.confidence, 0.7, "confidence is the weaker of the two runs")

    def test_disagreeing_runs_fall_back_to_the_weaker_label(self):
        plan = plan_auto_links(self._run("r1", "replaces"), self._run("r2", "builds-on"))
        self.assertEqual([edge.verdict for edge in plan.edges], ["builds-on"])
        self.assertEqual(plan.counts["fallback"], 1)

    def test_none_from_both_runs_records_examined_not_applicable(self):
        plan = plan_auto_links(self._run("r1", "none"), self._run("r2", "none"))
        self.assertEqual(plan.edges, [])
        self.assertIn(B, plan.not_applicable)

    def test_apply_writes_live_derived_edge_that_links_check_accepts(self):
        result = apply_auto_links(
            self.cwd, self._run("r1", "replaces"), self._run("r2", "replaces", "0.6"),
            now=datetime(2026, 9, 25, 21, 0),
        )
        self.assertTrue(result["written"])
        sidecar = self.cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06" / "2026-06-02.md"
        text = sidecar.read_text(encoding="utf-8")
        self.assertIn("source: derived", text)
        self.assertIn(f"replaces:\n  - {A}", text)
        self.assertIn("confidence: 0.60", text)
        self.assertIn(QUOTE, text)
        errors = [i for i in check_session_links(self.cwd).issues if i.severity == "error"]
        self.assertEqual(errors, [])
        links = entry_link_sidecars(self.cwd)[B]
        self.assertIn(A, links["replaces"])
        self.assertEqual(list(links["edge_confidence"].values()), [0.6])

    def test_dry_run_writes_nothing(self):
        result = apply_auto_links(self.cwd, self._run("r1", "related"), dry_run=True)
        self.assertFalse(result["written"])
        self.assertFalse((self.cwd / MEMORY_DIR_NAME / "sessions" / "links").exists())

    def test_verify_raises_a_machine_edge_to_full_weight(self):
        apply_auto_links(
            self.cwd, self._run("r1", "replaces"), self._run("r2", "replaces", "0.6"),
            now=datetime(2026, 9, 25, 21, 0),
        )
        verify_link(self.cwd, B, A, verified_by="JNL", now=datetime(2026, 9, 25, 21, 5))
        self.assertEqual(list(entry_link_sidecars(self.cwd)[B]["edge_confidence"].values()), [1.0])
        errors = [i for i in check_session_links(self.cwd).issues if i.severity == "error"]
        self.assertEqual(errors, [])

    def test_verify_refuses_an_edge_that_does_not_exist(self):
        with self.assertRaises(LookupError):
            verify_link(self.cwd, B, A, verified_by="JNL")


class ConfidenceScaledDampingTests(AutoClassifyTests):
    """A machine `replaces` demotes by its confidence; verification restores full damping."""

    def _scores(self, damping=True):
        # search_memory augments the corpus with link sidecars, so sidecar edges count.
        from memory_seed.retrieval import search_memory

        payload = search_memory(
            "older proposal decision", self.cwd, top_k=5, recency_enabled=False,
            semantic_enabled=False, granularity="entry", supersession_damping=damping,
            replacing_successor_boost=False,
        )
        return {item["chunk_id"].split(":")[0]: item["score"] for item in payload["results"]}

    def test_machine_replacement_demotes_less_until_verified(self):
        from memory_seed.semantic_cache import REPLACED_RANK_DAMPING

        undamped = self._scores(damping=False)[A]
        apply_auto_links(
            self.cwd, self._run("r1", "replaces"), self._run("r2", "replaces", "0.5"),
            now=datetime(2026, 9, 25, 21, 0),
        )
        self.assertAlmostEqual(self._scores()[A], undamped * (1.0 - 0.5 * (1.0 - REPLACED_RANK_DAMPING)), places=4)

        verify_link(self.cwd, B, A, verified_by="JNL", now=datetime(2026, 9, 25, 21, 5))
        self.assertAlmostEqual(self._scores()[A], undamped * REPLACED_RANK_DAMPING, places=4)

    # The parent's tests are not re-run here.
    test_refines_needs_two_agreeing_runs = None
    test_disagreeing_runs_fall_back_to_the_weaker_label = None
    test_none_from_both_runs_records_examined_not_applicable = None
    test_apply_writes_live_derived_edge_that_links_check_accepts = None
    test_dry_run_writes_nothing = None
    test_verify_raises_a_machine_edge_to_full_weight = None
    test_verify_refuses_an_edge_that_does_not_exist = None


if __name__ == "__main__":
    unittest.main()
