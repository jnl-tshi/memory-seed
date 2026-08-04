import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "context-derivation"
sys.path.insert(0, str(EXPERIMENT))

from judge import (  # noqa: E402
    collect_results,
    execute_manifest,
    expected_review_cells,
    select_reviews,
    selected_repetition,
    validate_review_cells,
)
from report import render_report  # noqa: E402
from score import score_experiment, score_run, wilson, write_score_shards  # noqa: E402


class ContextDerivationScoringTests(unittest.TestCase):
    def gold(self):
        return {
            "task_id": "CTX-01",
            "required_adr_ids": ["adr_a"],
            "authoritative_refs": ["mse_new:d1"],
            "required_lineage_edges": [{"source": "mse_new:d1", "target": "mse_old:d1", "type": "evolves"}],
            "relevant_refs": ["mse_new:d1", "mse_old:d1"],
            "distractor_refs": ["mse_rejected:d1"],
            "expected_status": "accepted",
            "insufficient_evidence": False,
            "allowed_citations": ["mse_new:d1", "mse_old:d1"],
            "required_missing_refs": [],
        }

    def sample_run(self, **overrides):
        value = {
            "run_id": "r1",
            "task_id": "CTX-01",
            "arm": "adr-candidate-packet",
            "agent": "claude",
            "repetition": 1,
            "model": "model-a",
            "cli_version": "cli-a",
            "answer": {
                "schema": "context-answer.v1",
                "adr_ids": ["adr_a"],
                "authoritative_refs": ["mse_new:d1"],
                "adr_statuses": {"adr_a": "accepted"},
                "lineage_edges": [{"source": "mse_new:d1", "target": "mse_old:d1", "type": "evolves"}],
                "related_edges": [],
                "citations": ["mse_new:d1"],
                "explanation": "The new decision evolves the old one.",
                "insufficient_evidence": False,
                "missing_refs": [],
            },
            "included_refs": ["mse_new:d1", "mse_old:d1"],
            "context_token_proxy": 1000,
            "duration_ms": 10,
            "input_tokens": 20,
            "output_tokens": 10,
            "cost_usd": 0.01,
            "tool_calls": [],
            "protocol_failure": False,
            "harness_failure": False,
            "exclusion_reason": None,
        }
        value.update(overrides)
        return value

    def test_exact_mechanical_success(self):
        result = score_run(self.sample_run(), self.gold())
        self.assertTrue(result["complete_correct"])
        self.assertTrue(result["head_correct"])
        self.assertTrue(result["status_correct"])

    def test_extra_authoritative_ref_fails_head(self):
        run = self.sample_run()
        run["answer"] = dict(run["answer"], authoritative_refs=["mse_new:d1", "mse_old:d1"])
        self.assertFalse(score_run(run, self.gold())["head_correct"])

    def test_unresolvable_citation_fails(self):
        run = self.sample_run()
        run["answer"] = dict(run["answer"], citations=["mse_missing:d1"])
        result = score_run(run, self.gold())
        self.assertFalse(result["citation_resolves"])
        self.assertFalse(result["complete_correct"])

    def test_status_and_related_are_scored_separately(self):
        gold = dict(self.gold(), required_related_edges=[{"source": "mse_new:d1", "target": "mse_note:d1", "type": "related"}])
        run = self.sample_run()
        run["answer"] = dict(run["answer"], adr_statuses={"adr_a": "proposed"}, related_edges=[])
        result = score_run(run, gold)
        self.assertFalse(result["status_correct"])
        self.assertFalse(result["related_exact"])
        self.assertFalse(result["complete_correct"])

    def test_related_cannot_be_reported_as_lineage(self):
        run = self.sample_run()
        run["answer"] = dict(run["answer"], lineage_edges=[{"source": "mse_new:d1", "target": "mse_old:d1", "type": "related"}])
        result = score_run(run, self.gold())
        self.assertFalse(result["relation_types_correct"])

    def test_missing_evidence_requires_exact_missing_refs(self):
        gold = dict(self.gold(), insufficient_evidence=True, required_missing_refs=["mse_absent:d1"])
        run = self.sample_run()
        run["answer"] = dict(run["answer"], insufficient_evidence=True, missing_refs=[])
        result = score_run(run, gold)
        self.assertFalse(result["missing_refs_correct"])
        self.assertFalse(result["complete_correct"])

    def test_wilson_is_bounded(self):
        low, high = wilson(9, 10)
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(high, 1)

    def test_parallel_score_shards_are_unique_and_complete(self):
        rows = [score_run(self.sample_run(run_id=f"r{index}"), self.gold()) for index in range(3)]
        with tempfile.TemporaryDirectory() as temp:
            paths = write_score_shards(rows, temp)
            self.assertEqual(3, len(paths))
            with self.assertRaises(ValueError):
                write_score_shards(rows, temp)

    def test_protocol_failure_in_any_arm_fails_production_gate(self):
        run = self.sample_run(arm="search-mcp", protocol_failure="undeclared_tool_call")
        result = score_experiment({"runs": [run]}, {"tasks": [self.gold()]}, require_complete=False)
        self.assertFalse(result["production_recommendation_gate"]["passed"])
        self.assertTrue(any("integrity failure" in item for item in result["production_recommendation_gate"]["failures"]))

    def test_judge_selection_is_stable(self):
        self.assertEqual(selected_repetition("CTX-01", "search-mcp", "claude"), selected_repetition("CTX-01", "search-mcp", "claude"))
        runs = []
        for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow"):
            for agent in ("claude", "codex"):
                for repetition in (1, 2, 3):
                    runs.append({"task_id": "CTX-01", "arm": arm, "agent": agent, "repetition": repetition})
        self.assertEqual(len(select_reviews({"runs": runs})), 8)

    def test_judge_concurrency_is_bounded(self):
        with self.assertRaises(ValueError):
            execute_manifest([], Path("unused"), jobs_per_agent=4)

    def test_judge_requires_exact_cells_and_unique_run_ids(self):
        tasks = {"tasks": [{"task_id": "CTX-01"}, {"task_id": "CTX-02"}]}
        expected = expected_review_cells(tasks)
        selected = [
            {"task_id": task, "arm": arm, "agent": agent, "repetition": repetition,
             "run_id": f"r-{index}"}
            for index, (task, arm, agent, repetition) in enumerate(sorted(expected))
        ]
        validate_review_cells(selected, expected)
        malformed = [*selected[:-1], dict(selected[0], run_id="r-replaced")]
        with self.assertRaisesRegex(ValueError, "selected review cells mismatch"):
            validate_review_cells(malformed, expected)
        duplicate_ids = [dict(row) for row in selected]
        duplicate_ids[-1]["run_id"] = duplicate_ids[0]["run_id"]
        with self.assertRaisesRegex(ValueError, "duplicate run_id"):
            validate_review_cells(duplicate_ids, expected)

    def test_returned_judgements_require_exact_manifest_cells(self):
        expected = {("CTX-01", "search-mcp", "claude", 1)}
        with self.assertRaisesRegex(ValueError, "exact frozen review cells"):
            collect_results([], Path("unused"), expected_cells=expected)

    def test_report_keeps_agents_separate(self):
        score = {
            "production_recommendation_gate": {"passed": False, "failures": ["not run"]},
            "aggregates": {agent: {arm: {"runs": 0, "metrics": {}, "context_tokens": {}} for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow")} for agent in ("claude", "codex")},
        }
        report = render_report(score)
        self.assertIn("### Claude", report)
        self.assertIn("### Codex", report)
        self.assertIn("does not authorize", report)

    def test_report_cannot_pass_without_offline_judges_and_recommendations(self):
        score = {
            "production_recommendation_gate": {"passed": True, "failures": []},
            "aggregates": {agent: {arm: {"runs": 0, "metrics": {}, "context_tokens": {}} for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow")} for agent in ("claude", "codex")},
        }
        report = render_report(score, {"complete": True, "selected_strategy_fingerprint": "sha256:x", "strategies": [], "pareto_frontier": []}, [], {})
        self.assertIn("FAIL / INCOMPLETE", report)
        self.assertIn("exactly 96", report)

    def test_complete_matrix_rejects_out_of_range_repetition(self):
        runs = []
        for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow"):
            for agent in ("claude", "codex"):
                for repetition in (1, 2, 3):
                    run = self.sample_run(arm=arm, agent=agent, repetition=repetition)
                    runs.append(run)
        # Repeat the one-task matrix to the nominal 288 count, but inject an
        # invalid unique cell that the old count-only check accepted.
        runs = [dict(run, run_id=f"r-{index}", task_id=f"CTX-{index // 24 + 1:02d}") for index, run in enumerate(runs * 12)]
        runs[-1]["repetition"] = 4
        gold_rows = []
        for number in range(1, 13):
            row = dict(self.gold(), task_id=f"CTX-{number:02d}")
            gold_rows.append(row)
        with self.assertRaisesRegex(ValueError, "live matrix mismatch"):
            score_experiment({"runs": runs}, {"tasks": gold_rows})


if __name__ == "__main__":
    unittest.main()
