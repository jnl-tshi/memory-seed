import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "experiments" / "semantic-compression" / "benchmark.py"
SPEC = importlib.util.spec_from_file_location("semantic_compression_benchmark", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SemanticCompressionBenchmarkTests(unittest.TestCase):
    def test_representations_are_source_grounded(self):
        source = "- D: Keep entries immutable.\n- R: Topics change over time.\n- A: Do not rewrite source entries.\n- F: must-not-be-a-constraint.txt\n- T: should-not-be-a-constraint"
        reps = MODULE.representations(source)
        self.assertEqual(reps["core"], "Keep entries immutable.")
        self.assertIn("Topics change over time.", reps["core_why"])
        self.assertNotIn("Do not rewrite source entries.", reps["core_why_constraint"])
        self.assertNotIn("must-not-be-a-constraint", reps["core_why_constraint"])
        self.assertNotIn("should-not-be-a-constraint", reps["core_why_constraint"])
        for span in reps["core_why_constraint"].splitlines():
            self.assertIn(span, source)

    def test_rejected_modal_alternative_never_becomes_a_constraint(self):
        source = "- D: Keep the source unchanged.\n- R: Derived output may change.\n- A: Never write a sidecar."
        reps = MODULE.representations(source)
        self.assertNotIn("Never write a sidecar.", reps["core_why_constraint"])
        self.assertNotIn("Never write a sidecar.", reps["labeled_spans"])

    def test_sample_is_deterministic_and_length_stratified(self):
        from dataclasses import dataclass
        @dataclass
        class Chunk:
            chunk_id: str
            text: str
        chunks = [Chunk(str(i), "x" * i) for i in range(1, 201)]
        first = MODULE.choose_sample(chunks)
        second = MODULE.choose_sample(list(reversed(chunks)))
        self.assertEqual([c.chunk_id for c in first], [c.chunk_id for c in second])
        lengths = [len(c.text) for c in first]
        self.assertLess(min(lengths), 41)
        self.assertGreater(max(lengths), 160)

    def test_token_proxy_is_positive(self):
        self.assertEqual(MODULE.token_proxy(""), 1)
        self.assertEqual(MODULE.token_proxy("abcd"), 1)

    def test_provenance_is_exact_and_rejects_paraphrase(self):
        source = "- D: Keep entries immutable.\n- R: Topics change."
        spans = MODULE.provenance(source, "claim: Keep entries immutable.\nbecause: Topics change.")
        self.assertEqual(source[spans[0]["start_char"]:spans[0]["end_char"]], "Keep entries immutable.")
        with self.assertRaises(ValueError):
            MODULE.provenance(source, "claim: Entries stay unchanged.")
        wrapped = MODULE.provenance("- D: Keep entries\n  immutable.", "claim: Keep entries immutable.")
        self.assertEqual(len(wrapped), 1)

    def test_frozen_corpus_identity_is_pinned_and_checked(self):
        decisions, identity = MODULE.frozen_corpus()
        self.assertEqual(identity["source_revision"], MODULE.SOURCE_REVISION)
        self.assertEqual(identity["corpus_fingerprint"], MODULE.EXPECTED_CORPUS_FINGERPRINT)
        self.assertEqual(identity["decision_count"], len(decisions))

    def test_results_narrative_reads_values_from_metrics(self):
        arms = {arm: {"mean_token_proxy": 1, "relative_context": 1, "recall_at_5": 0.25,
                      "mrr": 0.25, "efficiency_mrr_per_relative_context": 0.25}
                for arm in MODULE.ARMS}
        rel = {arm: {"f1": 0.5, "false_positive_rate": 0.0, "test_count": 7}
               for arm in MODULE.ARMS}
        arms["raw"]["mrr"] = 0.75
        report = MODULE.render_results({"retrieval": arms, "relationships": {"positive_count": 9, "arms": rel}})
        self.assertIn("`0.750`", report)
        self.assertIn("9 fully scoped positive decision edges yielded 7 test pairs", report)

    def test_generated_pair_table_is_reconstructable_and_has_corpus_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            with contextlib.redirect_stdout(io.StringIO()):
                metrics = MODULE.main(Path(temp))
            payload = json.loads((Path(temp) / "relationship-pairs.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["corpus"], metrics["corpus"])
        self.assertEqual(payload["selection_fingerprint"], metrics["selection_fingerprint"])
        self.assertEqual(len(payload["pairs"]), metrics["relationships"]["pair_count"])
        self.assertTrue(all(set(pair["scores"]) == set(MODULE.ARMS) for pair in payload["pairs"]))
        self.assertEqual(sum(pair["label"] for pair in payload["pairs"]), metrics["relationships"]["positive_count"])
        for arm, summary in metrics["relationships"]["arms"].items():
            pairs = [pair for pair in payload["pairs"] if pair["split"] == "test"]
            predictions = [(pair["scores"][arm] >= summary["threshold"], pair["label"]) for pair in pairs]
            self.assertEqual(sum(predicted and label for predicted, label in predictions), summary["tp"])
            self.assertEqual(sum(predicted and not label for predicted, label in predictions), summary["fp"])
            self.assertEqual(sum(not predicted and label for predicted, label in predictions), summary["fn"])
            self.assertEqual(sum(not predicted and not label for predicted, label in predictions), summary["tn"])


if __name__ == "__main__":
    unittest.main()
