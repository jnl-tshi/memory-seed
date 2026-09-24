from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "evaluate_staged_retrieval", BASE / "evaluate_staged_retrieval.py"
)
assert SPEC and SPEC.loader
staged = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = staged
SPEC.loader.exec_module(staged)


class StagedRetrievalTests(unittest.TestCase):
    def test_uses_ranked_spans_inside_twenty_turn_envelope(self) -> None:
        evidence = {("r", 2)}
        top = {("r", 1)}
        envelope = {("r", 1), ("r", 2)}
        scope = envelope | {("p", 1)}
        result = staged.classify_stages(evidence, top, envelope, scope)
        self.assertEqual(result["first_complete_stage"], "lineage_backward_20")
        self.assertFalse(result["top_3_all_evidence"])
        self.assertTrue(result["envelope_all_evidence"])

    def test_beyond_twenty_is_a_fallback_not_a_negative(self) -> None:
        result = staged.classify_stages(
            {("p", 1)}, {("r", 2)}, {("r", 1), ("r", 2)},
            {("p", 1), ("r", 1), ("r", 2)},
        )
        self.assertEqual(result["first_complete_stage"], "source_scope_plus_envelope")

    def test_no_gold_evidence_is_unresolved_not_success(self) -> None:
        result = staged.classify_stages(set(), {("r", 1)}, {("r", 1)}, {("r", 1)})
        self.assertIsNone(result["first_complete_stage"])
        self.assertEqual(result["evidence_status"], "unresolved")

    def test_top_ranked_coordinates_must_be_inside_envelope(self) -> None:
        with self.assertRaisesRegex(ValueError, "within the envelope"):
            staged.classify_stages({("r", 1)}, {("p", 1)}, {("r", 1)}, {("r", 1)})

    def test_strict_decision_metrics_exclude_documentation_control(self) -> None:
        gold = [
            {"decision": {"id": decision_id}, "adjudication": {
                "label": "verified_source", "evidence_refs": [{"rollout_id": "r", "turn": turn}],
            }}
            for decision_id, turn in (("decision", 1), ("documentation", 2))
        ]
        windows = {"rows": [{
            "decision_id": decision_id,
            "source_scope_coordinates": [["r", 1], ["r", 2]],
            "strategies": {"lineage_backward_20": {"coordinates": [["r", 1], ["r", 2]]}},
        } for decision_id in ("decision", "documentation")]}
        ranks = {"rows": [{
            "decision_id": decision_id,
            "strategies": {"lexical_top_3": {"coordinates": [["r", 1]]}},
        } for decision_id in ("decision", "documentation")]}
        result = staged.evaluate(gold, windows, ranks, documentation_ids={"documentation"})
        self.assertEqual(result["summary"]["strict_verified_rows"], 1)
        self.assertEqual(result["summary"]["strict_verified_complete_at_top_3"], 1)
        self.assertEqual(result["summary"]["verified_complete_at_top_3"], 1)


if __name__ == "__main__":
    unittest.main()
