import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "context-derivation"
sys.path.insert(0, str(EXPERIMENT))

from judge import select_reviews, selected_repetition  # noqa: E402
from report import render_report  # noqa: E402
from score import score_experiment, score_run, wilson  # noqa: E402


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
        }

    def sample_run(self, **overrides):
        value = {
            "run_id": "r1",
            "task_id": "CTX-01",
            "arm": "adr-candidate-packet",
            "agent": "claude",
            "repetition": 1,
            "answer": {
                "schema": "context-answer.v1",
                "adr_ids": ["adr_a"],
                "authoritative_refs": ["mse_new:d1"],
                "lineage_edges": [{"source": "mse_new:d1", "target": "mse_old:d1", "type": "evolves"}],
                "citations": ["mse_new:d1"],
                "explanation": "The new decision evolves the old one.",
                "insufficient_evidence": False,
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

    def test_wilson_is_bounded(self):
        low, high = wilson(9, 10)
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(high, 1)

    def test_judge_selection_is_stable(self):
        self.assertEqual(selected_repetition("CTX-01", "search-mcp", "claude"), selected_repetition("CTX-01", "search-mcp", "claude"))
        runs = []
        for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow"):
            for agent in ("claude", "codex"):
                for repetition in (1, 2, 3):
                    runs.append({"task_id": "CTX-01", "arm": arm, "agent": agent, "repetition": repetition})
        self.assertEqual(len(select_reviews({"runs": runs})), 8)

    def test_report_keeps_agents_separate(self):
        score = {
            "production_recommendation_gate": {"passed": False, "failures": ["not run"]},
            "aggregates": {agent: {arm: {"runs": 0, "metrics": {}, "context_tokens": {}} for arm in ("search-mcp", "retrieval-v1-packet", "adr-candidate-packet", "adr-mcp-workflow")} for agent in ("claude", "codex")},
        }
        report = render_report(score)
        self.assertIn("### Claude", report)
        self.assertIn("### Codex", report)
        self.assertIn("does not authorize", report)


if __name__ == "__main__":
    unittest.main()
