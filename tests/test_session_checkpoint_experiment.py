import unittest

from experiments.session_checkpoint.scenario_matrix import run_matrix


class SessionCheckpointScenarioMatrixTests(unittest.TestCase):
    def test_candidate_passes_promotion_gate_against_legacy_oracle(self):
        result = run_matrix()

        self.assertTrue(result["gate_passed"], result)
        self.assertTrue(result["comparison"]["legacy_clean_stale_false_positive"])
        self.assertTrue(result["comparison"]["legacy_head_change_miss"])
        self.assertTrue(result["checks"]["candidate_captures_all_implementation_evidence"])
        self.assertTrue(result["checks"]["candidate_never_creates_clean_time_debt"])


if __name__ == "__main__":
    unittest.main()
