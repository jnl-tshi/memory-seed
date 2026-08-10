import importlib.util
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
        self.assertIn("Do not rewrite source entries.", reps["core_why_constraint"])
        self.assertNotIn("must-not-be-a-constraint", reps["core_why_constraint"])
        self.assertNotIn("should-not-be-a-constraint", reps["core_why_constraint"])
        for span in reps["core_why_constraint"].splitlines():
            self.assertIn(span, source)

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


if __name__ == "__main__":
    unittest.main()
