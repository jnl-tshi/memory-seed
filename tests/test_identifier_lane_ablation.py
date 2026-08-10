import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PATH = Path(__file__).parents[1] / "experiments" / "semantic-compression" / "identifier_lane_ablation.py"
SPEC = importlib.util.spec_from_file_location("identifier_lane_ablation", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class IdentifierLaneAblationTests(unittest.TestCase):
    def test_holdout_is_disjoint_stratified_and_has_exact_identifiers(self):
        decisions, identity = MODULE.BENCHMARK.frozen_corpus()
        sample = MODULE.BENCHMARK.choose_sample(decisions)
        prior_entries = {chunk.entry_id for chunk in MODULE.LEAN.choose_pilot(sample)}
        selected = MODULE.choose_holdout(sample)

        self.assertEqual(identity["source_revision"], MODULE.EXPECTED_SOURCE_REVISION)
        self.assertEqual(len(selected), 30)
        self.assertFalse(prior_entries & {chunk.entry_id for chunk in selected})
        self.assertTrue(all(MODULE.current_authored_identifiers(chunk) for chunk in selected))

    def test_normalization_uses_the_production_rule_and_reaches_bm25f(self):
        self.assertEqual(MODULE.normalized_terms(("rare_symbol.py",)), ("rare symbol py",))
        decisions, _ = MODULE.BENCHMARK.frozen_corpus()
        sample = MODULE.BENCHMARK.choose_sample(decisions)
        result = MODULE.sensitivity_control(sample)

        self.assertTrue(result["passes"])
        self.assertEqual(result["current_representation"]["target_lexical_score"], 0.0)
        self.assertGreater(result["normalized_representation"]["target_lexical_score"], 0.0)
        self.assertIn("lexical_terms", result["normalized_representation"]["target_matched_fields"])

    def test_query_validator_requires_disjoint_query_types_and_exact_identifier(self):
        class Chunk:
            def __init__(self, index):
                self.chunk_id = f"mse_identifierfixture{index}:d1"
                self.text = (
                    f"- D: Keep canonical evidence in `rare_symbol_{index}.py`.\n"
                    "- R: Derived views remain replaceable and source linked.\n"
                    f"- F: `rare_symbol_{index}.py`\n"
                )
                self.lexical_terms = (f"rare_symbol_{index}.py",)

        selected = [Chunk(index) for index in range(3)]
        payload = {
            "schema": "identifier-lane-queries.v1",
            "authoring": {
                "passes": 3,
                "authors": [
                    {"author_id": f"a{index}", "model": "fixture-model"} for index in range(3)
                ],
                "input_access": "canonical-source-and-identifiers-only",
                "ranking_results_seen": False,
                "arm_definitions_seen": False,
                "prior_results_seen": False,
            },
            "queries": [
                {
                    "packet_id": MODULE.packet_id(chunk.chunk_id),
                    "author_id": f"a{index}",
                    "semantic_query": f"Which design keeps evidence authoritative for derived view case {index}?",
                    "identifier_query": f"Why does `rare_symbol_{index}.py` remain the selected source evidence location?",
                    "identifier": f"rare_symbol_{index}.py",
                }
                for index, chunk in enumerate(selected)
            ],
        }
        self.assertEqual(len(MODULE.validate_queries(payload, selected)), 3)
        payload["queries"][0]["semantic_query"] = "Why does rare_symbol_0.py remain authoritative for this decision?"
        with self.assertRaisesRegex(ValueError, "semantic query contains an identifier"):
            MODULE.validate_queries(payload, selected)

    def test_review_validator_requires_every_query_accepted(self):
        class Chunk:
            chunk_id = "mse_identifierfixture:d1"

        selected = [Chunk()]
        packet = MODULE.packet_id(Chunk.chunk_id)
        review = {
            "schema": "identifier-lane-query-review.v1",
            "query_sha256": "sha256:query",
            "reviewer_model": "fixture-reviewer",
            "input_access": "canonical-source-and-queries-only",
            "ranking_results_seen": False,
            "arm_definitions_seen": False,
            "reviews": [
                {"packet_id": packet, "kind": "semantic", "accepted": True},
                {"packet_id": packet, "kind": "identifier", "accepted": True},
            ],
        }
        for item in review["reviews"]:
            item.update({
                "target_specific": True,
                "natural": True,
                "source_copying_absent": True,
                "reason": "The query is specific, natural, and not copied from the source.",
            })
        self.assertEqual(len(MODULE.validate_query_review(review, "sha256:query", selected)), 2)
        review["reviews"][1]["accepted"] = False
        with self.assertRaisesRegex(ValueError, "rejected or did not accept"):
            MODULE.validate_query_review(review, "sha256:query", selected)

    def test_scoring_writes_nothing_while_query_pin_is_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "score"
            with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", MODULE.selector_sha256()), \
                 mock.patch.object(
                     MODULE,
                     "EXPECTED_SELECTION_FINGERPRINT",
                     MODULE.freeze_info()["selection_fingerprint"],
                 ):
                with self.assertRaisesRegex(RuntimeError, "query pin is PENDING"):
                    MODULE.run(output)
            self.assertFalse(output.exists())

    def test_query_packets_are_source_only_and_batch_disjoint(self):
        pins = MODULE.freeze_info()
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", pins["selector_sha256"]), \
             mock.patch.object(MODULE, "EXPECTED_SELECTION_FINGERPRINT", pins["selection_fingerprint"]):
            all_packets = MODULE.query_packets()
            batches = [MODULE.query_packets(index, 3) for index in range(3)]
        self.assertEqual(len(all_packets), 30)
        self.assertEqual(sum(len(batch) for batch in batches), 30)
        self.assertEqual(
            {item["packet_id"] for item in all_packets},
            {item["packet_id"] for batch in batches for item in batch},
        )
        self.assertEqual(set(all_packets[0]), {"packet_id", "source", "allowed_identifiers"})

    def test_query_packets_fail_until_selector_and_targets_are_frozen(self):
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", "PENDING"), \
             mock.patch.object(MODULE, "EXPECTED_SELECTION_FINGERPRINT", "PENDING"):
            with self.assertRaisesRegex(RuntimeError, "must be frozen before authoring"):
                MODULE.query_packets()

    def test_sensitivity_failure_is_fail_closed_before_measurement_or_output(self):
        with tempfile.TemporaryDirectory() as temporary, \
             mock.patch.object(MODULE, "load_frozen_inputs", return_value=([], [], {}, {"reviews": []}, {})), \
             mock.patch.object(MODULE, "sensitivity_control", return_value={"passes": False}), \
             mock.patch.object(MODULE, "retrieval_measurement") as measurement:
            with self.assertRaisesRegex(RuntimeError, "sensitivity control failed"):
                MODULE.run(Path(temporary) / "score")
            measurement.assert_not_called()
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_real_corpus_exposure_failure_writes_nothing(self):
        per_query = [{
            "packet_id": "il_fixture",
            "kind": "identifier",
            "arms": {
                arm: {"target_lexical_field_match": False} for arm in MODULE.ARMS
            },
        }]
        with tempfile.TemporaryDirectory() as temporary, \
             mock.patch.object(MODULE, "load_frozen_inputs", return_value=([], [], {}, {"reviews": []}, {})), \
             mock.patch.object(MODULE, "sensitivity_control", return_value={"passes": True}), \
             mock.patch.object(MODULE, "retrieval_measurement", return_value=({}, per_query)):
            with self.assertRaisesRegex(RuntimeError, "real-corpus exposure failed"):
                MODULE.run(Path(temporary) / "score")
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_selector_hash_covers_query_policy_globals(self):
        original = MODULE.selector_sha256()
        with mock.patch.object(MODULE, "FORBIDDEN_QUERY_TERMS", (*MODULE.FORBIDDEN_QUERY_TERMS, "extra")):
            self.assertNotEqual(MODULE.selector_sha256(), original)

    def test_selector_and_selection_drift_fail_closed(self):
        pins = MODULE.freeze_info()
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", "sha256:wrong"), \
             mock.patch.object(MODULE, "EXPECTED_SELECTION_FINGERPRINT", pins["selection_fingerprint"]):
            with self.assertRaisesRegex(RuntimeError, "selector is not frozen"):
                MODULE.frozen_targets()
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", pins["selector_sha256"]), \
             mock.patch.object(MODULE, "EXPECTED_SELECTION_FINGERPRINT", "sha256:wrong"):
            with self.assertRaisesRegex(RuntimeError, "selection is not frozen"):
                MODULE.frozen_targets()

    def test_query_and_review_hash_drift_fail_closed(self):
        empty_queries = {
            "schema": "identifier-lane-queries.v1",
            "authoring": {
                "passes": 3,
                "authors": [
                    {"author_id": f"a{index}", "model": "fixture-model"} for index in range(3)
                ],
                "input_access": "canonical-source-and-identifiers-only",
                "ranking_results_seen": False,
                "arm_definitions_seen": False,
                "prior_results_seen": False,
            },
            "queries": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            query_path = Path(temporary) / "queries.json"
            review_path = Path(temporary) / "review.json"
            query_path.write_text(json.dumps(empty_queries), encoding="utf-8")
            review_path.write_text("{}", encoding="utf-8")
            with mock.patch.object(MODULE, "frozen_targets", return_value=([], [], {})), \
                 mock.patch.object(MODULE, "QUERY_PATH", query_path), \
                 mock.patch.object(MODULE, "QUERY_REVIEW_PATH", review_path), \
                 mock.patch.object(MODULE, "EXPECTED_QUERY_SHA256", "sha256:wrong"):
                with self.assertRaisesRegex(RuntimeError, "queries are not frozen"):
                    MODULE.load_frozen_inputs()
            query_hash = MODULE.sha256_bytes(query_path.read_bytes())
            with mock.patch.object(MODULE, "frozen_targets", return_value=([], [], {})), \
                 mock.patch.object(MODULE, "QUERY_PATH", query_path), \
                 mock.patch.object(MODULE, "QUERY_REVIEW_PATH", review_path), \
                 mock.patch.object(MODULE, "EXPECTED_QUERY_SHA256", query_hash), \
                 mock.patch.object(MODULE, "EXPECTED_QUERY_REVIEW_SHA256", "sha256:wrong"):
                with self.assertRaisesRegex(RuntimeError, "review is not frozen"):
                    MODULE.load_frozen_inputs()

    def test_decision_rules_distinguish_harm_from_uncertain_noninferiority(self):
        effects = {}
        for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms"):
            for control in ("body_only", "current_lexical_terms"):
                effects[f"{arm}_vs_{control}_identifier_mrr"] = {
                    "difference": 0.05,
                    "bootstrap_95_ci": [-0.01, 0.12],
                }
                effects[f"{arm}_vs_{control}_semantic_mrr"] = {
                    "difference": 0.0,
                    "bootstrap_95_ci": [-0.03, 0.02],
                }
        rules = MODULE.decision_rules(effects)
        self.assertEqual(
            rules["normalized_current_terms"]["classification"],
            "semantic-noninferiority-not-established",
        )
        effects["normalized_current_terms_vs_body_only_semantic_mrr"]["difference"] = -0.03
        self.assertEqual(MODULE.decision_rules(effects)["normalized_current_terms"]["classification"], "regressive")

    def test_output_pair_is_deterministic_and_refuses_stale_files(self):
        metrics = {
            "retrieval": {
                arm: {
                    "semantic": {"mrr": 0.5},
                    "identifier": {"mrr": 0.75, "recall_at_5": 1.0},
                    "exposure": {"full_order_changes_vs_body_only": 1},
                }
                for arm in MODULE.ARMS
            },
            "paired_effects": {
                f"{arm}_vs_{control}_identifier_mrr": {
                    "difference": 0.1,
                    "bootstrap_95_ci": [0.01, 0.2],
                    "improved_count": 3,
                    "regressed_count": 0,
                }
                for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms")
                for control in ("body_only", "current_lexical_terms")
            },
            "decision_rules": {
                arm: {"classification": "validated-on-this-holdout"}
                for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms")
            },
            "sensitivity_control": {"passes": True},
        }
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_output = Path(first) / "score"
            second_output = Path(second) / "score"
            MODULE.write_outputs(first_output, metrics)
            MODULE.write_outputs(second_output, metrics)
            for name in (
                "identifier-lane-metrics.json",
                "identifier-lane-results.md",
                "identifier-lane-run-manifest.json",
            ):
                self.assertEqual((first_output / name).read_bytes(), (second_output / name).read_bytes())
            with self.assertRaisesRegex(RuntimeError, "must not already exist"):
                MODULE.write_outputs(first_output, metrics)


if __name__ == "__main__":
    unittest.main()
