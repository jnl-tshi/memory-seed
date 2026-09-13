import importlib.util
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock


PATH = Path(__file__).parents[1] / "experiments" / "semantic-compression" / "lean_draft_pilot.py"
SPEC = importlib.util.spec_from_file_location("lean_draft_pilot", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LeanDraftPilotTests(unittest.TestCase):
    def test_front_door_preserves_reason_constraint_and_exact_anchor(self):
        source = (
            "- D: Keep source entries immutable. The writer must refuse rewrites.\n"
            "- R: Topic assignments change over time. Canonical prose should not follow them.\n"
            "- A: Never keep derived metadata.\n"
            "- F: `memory_seed/topics.py`, `true`"
        )
        reps = MODULE.representations(source)
        self.assertIn("Keep source entries immutable.", reps["lean_front_door"])
        self.assertIn("Topic assignments change over time.", reps["lean_front_door"])
        self.assertIn("The writer must refuse rewrites.", reps["lean_front_door"])
        self.assertIn("`memory_seed/topics.py`", reps["lean_front_door"])
        self.assertNotIn("Never keep derived metadata.", reps["lean_front_door"])
        self.assertNotIn("`true`", reps["lean_front_door"])

    def test_anchor_ablation_changes_only_exact_file_evidence(self):
        source = "- D: Add the check.\n- R: It prevents drift.\n- F: `memory_seed/core.py`"
        reps = MODULE.representations(source)
        self.assertEqual(reps["lean_front_door"].splitlines()[:-1], reps["lean_no_supplemental_anchors"].splitlines())
        self.assertEqual(reps["lean_front_door"].splitlines()[-1], "- F: `memory_seed/core.py`")
        self.assertIn("core.py", MODULE.simple_anchors(source))

    def test_continuation_after_f_or_t_does_not_contaminate_rationale(self):
        source = "- D: Add the check.\n- R: It prevents drift.\n- F: `x.py`\n  more file prose\n- T: must pass"
        parsed = MODULE.parse_fields(source)
        self.assertEqual(parsed["R"], ["It prevents drift."])
        self.assertEqual(parsed["F"], ["`x.py` more file prose"])
        self.assertEqual(parsed["T"], ["must pass"])

    def test_rejected_alternative_is_never_an_accepted_boundary(self):
        source = "- D: Use a sidecar.\n- R: Source stays canonical.\n- A: Never persist derived output."
        self.assertNotIn("Never persist derived output.", MODULE.representations(source)["lean_front_door"])

    def test_query_selection_is_deterministic_and_length_stratified(self):
        @dataclass
        class Chunk:
            chunk_id: str
            text: str

        chunks = [Chunk(str(i), f"- D: Do {i}.\n- R: Because reason.\n- F: `file_{i}.py`" + (" x" * i))
                  for i in range(1, 91)]
        first = MODULE.choose_pilot(chunks)
        second = MODULE.choose_pilot(list(reversed(chunks)))
        self.assertEqual([c.chunk_id for c in first], [c.chunk_id for c in second])
        lengths = [len(c.text) for c in first]
        self.assertLess(min(lengths), 120)
        self.assertGreater(max(lengths), 200)

    def test_query_validation_rejects_copy_and_requires_anchor_separation(self):
        @dataclass
        class Chunk:
            chunk_id: str
            text: str

        chunk = Chunk("mse_x:d1", "- D: Keep source entries immutable.\n- R: Topics change over time.\n- F: `topics.py`")
        packet = MODULE.packet_id(chunk.chunk_id)
        valid = {"schema": "lean-draft-independent-queries.v1",
                 "queries": [{"packet_id": packet,
                              "semantic_query": "Which earlier choice prevents generated labels from altering permanent records?",
                              "anchor_query": "Where was topics.py chosen as the component for evolving classifications?"}]}
        diagnostics = MODULE.validate_queries(valid, [chunk])
        self.assertEqual(len(diagnostics), 2)
        copied = {"schema": "lean-draft-independent-queries.v1",
                  "queries": [{"packet_id": packet,
                               "semantic_query": "Why must source entries remain immutable forever?",
                               "anchor_query": valid["queries"][0]["anchor_query"]}]}
        with self.assertRaisesRegex(ValueError, "copies source phrase"):
            MODULE.validate_queries(copied, [chunk])

    def test_frozen_query_artifact_validates_and_matches_pin(self):
        decisions, identity = MODULE.BENCHMARK.frozen_corpus()
        selected = MODULE.choose_pilot(MODULE.BENCHMARK.choose_sample(decisions))
        payload = json.loads(MODULE.QUERY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(identity["source_revision"], MODULE.EXPECTED_SOURCE_REVISION)
        self.assertEqual(identity["corpus_fingerprint"], MODULE.EXPECTED_CORPUS_FINGERPRINT)
        selection_fingerprint = "sha256:" + MODULE.BENCHMARK.stable(
            json.dumps([chunk.chunk_id for chunk in selected])
        )
        self.assertEqual(selection_fingerprint, MODULE.EXPECTED_SELECTION_FINGERPRINT)
        self.assertEqual(MODULE.query_file_sha256(), MODULE.EXPECTED_QUERY_SHA256)
        self.assertEqual(len(MODULE.validate_queries(payload, selected)), 60)

    def test_query_hash_negative_control_fails_before_scoring(self):
        with mock.patch.object(MODULE, "EXPECTED_QUERY_SHA256", "sha256:" + "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "query artifact is not frozen"):
                MODULE.run(Path("unused-negative-control-output"))

    def test_selector_contract_matches_pin_and_negative_control_fails_before_scoring(self):
        self.assertEqual(MODULE.selector_sha256(), MODULE.EXPECTED_SELECTOR_SHA256)
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", "sha256:" + "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "selector is not frozen"):
                MODULE.run(Path("unused-negative-control-output"))

    def test_frozen_readability_artifacts_match_pins(self):
        actual = {path.name: MODULE.sha256_bytes(path.read_bytes())
                  for path in sorted(MODULE.REVIEW_DIR.glob("*.json"))}
        self.assertEqual(actual, MODULE.EXPECTED_REVIEW_SHA256)
        self.assertEqual(MODULE.sha256_bytes(MODULE.ADJUDICATION_PATH.read_bytes()),
                         MODULE.EXPECTED_ADJUDICATION_SHA256)

    def test_missing_review_inputs_fail_before_any_output_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with mock.patch.object(MODULE, "REVIEW_DIR", output / "missing-reviews"):
                with self.assertRaisesRegex(RuntimeError, "readability artifacts are missing"):
                    MODULE.run(output)
            self.assertFalse((output / "lean-draft-metrics.json").exists())
            self.assertFalse((output / "lean-draft-results.md").exists())

            with mock.patch.object(MODULE, "ADJUDICATION_PATH", output / "missing-adjudication.json"):
                with self.assertRaisesRegex(RuntimeError, "adjudication artifact is missing"):
                    MODULE.run(output)
            self.assertFalse((output / "lean-draft-metrics.json").exists())
            self.assertFalse((output / "lean-draft-results.md").exists())

    def test_exact_anchor_coverage_does_not_count_identifier_substrings(self):
        self.assertTrue(MODULE.contains_exact_anchor("Use `memory-seed` now.", "memory-seed"))
        self.assertFalse(MODULE.contains_exact_anchor("Use `memory-seed-explorer` now.", "memory-seed"))
        self.assertFalse(MODULE.contains_exact_anchor("Use `score.py` now.", "core.py"))

    def test_readability_metrics_require_two_ratings_per_opaque_card(self):
        @dataclass
        class Chunk:
            chunk_id: str

        selected = [Chunk("mse_x:d1")]
        ratings = []
        for arm in MODULE.ARMS:
            ratings.append({"card_id": MODULE.card_id("mse_x:d1", arm), "clarity": 4,
                            "findability": 5, "decision_complete": True,
                            "rationale_complete": True, "boundary_complete": True,
                            "critical_error": False, "critical_reasons": []})
        payload = {"schema": "lean-draft-readability-ratings.v1",
                   "reviews": [{"reviewer": "one", "ratings": ratings},
                               {"reviewer": "two", "ratings": ratings}]}
        measured = MODULE.readability_metrics(selected, payload)
        self.assertEqual(measured["lean_front_door"]["mean_clarity"], 4)
        self.assertEqual(measured["agreement"]["critical_raw_agreement"], 1)
        self.assertEqual(measured["agreement"]["reviewer_process_count"], 2)
        self.assertEqual(len(measured["agreement"]["critical_pair_agreement"]), 1)
        self.assertNotIn("critical_cohen_kappa", measured["agreement"])


if __name__ == "__main__":
    unittest.main()
