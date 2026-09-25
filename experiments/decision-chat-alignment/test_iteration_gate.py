from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("iteration_gate", BASE / "iteration_gate.py")
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


class IterationGateTests(unittest.TestCase):
    @staticmethod
    def row(iteration: int, recovered: int, envelope: int, tokens: int, seconds: float = 100.0) -> dict:
        return {
            "iteration": iteration, "verified_source_recovered": recovered,
            "verified_all_evidence_in_20": envelope,
            "retrieval_payload_tokens": tokens, "runtime_seconds": seconds,
            "development_ids_sha256": "frozen",
        }

    def test_recall_regression_is_rejected_even_when_cheaper(self) -> None:
        prior = self.row(0, 20, 20, 1000)
        current = self.row(1, 19, 19, 100)
        result = gate.assess(prior, current)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "verified_recall_regression")

    def test_five_percent_token_gain_at_constant_recall_counts(self) -> None:
        result = gate.assess(self.row(0, 20, 20, 1000), self.row(1, 20, 20, 950))
        self.assertTrue(result["accepted"])
        self.assertTrue(result["material_improvement"])

    def test_two_consecutive_plateaus_stop(self) -> None:
        history = [self.row(0, 20, 20, 1000), self.row(1, 20, 20, 990), self.row(2, 20, 20, 985)]
        self.assertTrue(gate.should_stop(history))

    def test_new_source_resets_plateau(self) -> None:
        history = [self.row(0, 20, 20, 1000), self.row(1, 20, 20, 990), self.row(2, 21, 20, 990)]
        self.assertFalse(gate.should_stop(history))

    def test_new_evidence_inside_safety_envelope_resets_plateau(self) -> None:
        history = [self.row(0, 20, 18, 1000), self.row(1, 20, 18, 990), self.row(2, 20, 19, 990)]
        self.assertFalse(gate.should_stop(history))

    def test_cohort_drift_is_rejected(self) -> None:
        current = self.row(1, 20, 20, 900)
        current["development_ids_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "cohort drift"):
            gate.assess(self.row(0, 20, 20, 1000), current)

    def test_unmeasured_runtime_does_not_invent_a_gain(self) -> None:
        baseline = self.row(0, 20, 20, 1000, None)
        trial = self.row(1, 20, 20, 990, None)
        result = gate.assess(baseline, trial)
        self.assertIsNone(result["runtime_reduction"])
        self.assertFalse(result["material_improvement"])

    def test_trials_compare_with_last_accepted_champion(self) -> None:
        history = [self.row(0, 20, 20, 1000), self.row(1, 21, 20, 1200),
                   self.row(2, 20, 20, 900), self.row(3, 20, 20, 800)]
        assessments = gate.assess_history(history)
        self.assertEqual([row["champion_iteration"] for row in assessments], [0, 1, 1])
        self.assertFalse(assessments[2]["accepted"])
        self.assertTrue(gate.should_stop(history))


if __name__ == "__main__":
    unittest.main()
