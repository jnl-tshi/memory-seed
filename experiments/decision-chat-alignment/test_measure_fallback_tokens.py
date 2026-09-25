from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("measure_fallback_tokens", BASE / "measure_fallback_tokens.py")
assert SPEC and SPEC.loader
measure = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = measure
SPEC.loader.exec_module(measure)


class FallbackTokenTests(unittest.TestCase):
    def test_full_fallback_retains_initial_safety_scope(self) -> None:
        baseline = {("initial", 1)}
        neighbors = {("nearby", 2)}
        self.assertEqual(measure.staged_full_scope(baseline, neighbors), baseline | neighbors)

    def test_conditional_oracle_only_expands_verified_baseline_miss(self) -> None:
        baseline = {("a", 1)}
        fallback = {("a", 1), ("b", 2)}
        evidence = {("b", 2)}
        self.assertEqual(measure.conditional_oracle_scope(baseline, fallback, evidence, "verified_source"), fallback)
        self.assertEqual(measure.conditional_oracle_scope(baseline, fallback, evidence, "unresolved"), baseline)
        self.assertEqual(measure.conditional_oracle_scope(baseline, fallback, baseline, "verified_source"), baseline)


if __name__ == "__main__":
    unittest.main()
