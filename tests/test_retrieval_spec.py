import json
import unittest
from pathlib import Path

from memory_seed.retrieval_spec import (
    DEFAULT_LIMITS,
    RetrievalSpecValidationError,
    _DEFERRED,
    canonical_retrieval_spec_json,
    classify_missing_clause,
    normalize_retrieval_spec,
    retrieval_spec_fingerprint,
)


VALID = {
    "schema": "memory-seed/retrieval-spec",
    "version": 1,
    "required": {
        "constitution": True,
        "related_decisions": {"depth": 2},
        "evidence": {"mode": "latest"},
    },
}

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "retrieval-spec" / "validation-cases.json").read_text(encoding="utf-8")
)


class RetrievalSpecTests(unittest.TestCase):
    def test_normalizes_all_defaults_without_broadening_filters(self):
        normalized = normalize_retrieval_spec(FIXTURES["valid"])
        self.assertEqual(normalized["filters"], {"topics": [], "paths": []})
        self.assertEqual(normalized["limits"], DEFAULT_LIMITS)
        self.assertEqual(normalized["optional"]["sessions"], None)
        self.assertFalse(normalized["output"]["include_resolution_trace"])

    def test_mapping_order_has_identical_canonical_json_and_fingerprint(self):
        reordered = {
            "required": {"evidence": {"mode": "latest"}, "related_decisions": {"depth": 2}, "constitution": True},
            "version": 1,
            "schema": "memory-seed/retrieval-spec",
        }
        self.assertEqual(canonical_retrieval_spec_json(FIXTURES["valid"]), canonical_retrieval_spec_json(reordered))
        self.assertEqual(retrieval_spec_fingerprint(FIXTURES["valid"]), retrieval_spec_fingerprint(reordered))

    def test_unknown_and_deferred_clauses_fail_before_selection(self):
        with self.assertRaisesRegex(RetrievalSpecValidationError, "is unknown"):
            normalize_retrieval_spec(FIXTURES["unknown"])
        self.assertEqual(set(FIXTURES["deferred"]), set(_DEFERRED))
        for name, spec in FIXTURES["deferred"].items():
            with self.subTest(name=name), self.assertRaisesRegex(RetrievalSpecValidationError, "is unsupported"):
                normalize_retrieval_spec(spec)

    def test_limit_and_path_bounds_are_strict(self):
        with self.assertRaisesRegex(RetrievalSpecValidationError, "limits.max_entries"):
            normalize_retrieval_spec(FIXTURES["limits"])
        with self.assertRaisesRegex(RetrievalSpecValidationError, "runtime-relative"):
            normalize_retrieval_spec({**VALID, "filters": {"paths": ["../secret.md"]}})
        with self.assertRaisesRegex(RetrievalSpecValidationError, "runtime-relative"):
            normalize_retrieval_spec({**VALID, "filters": {"paths": ["C:/outside.md"]}})

    def test_version_must_be_an_integer_not_a_numeric_equivalent(self):
        with self.assertRaisesRegex(RetrievalSpecValidationError, "version"):
            normalize_retrieval_spec(FIXTURES["numeric_version"])

    def test_required_and_optional_missing_classification_is_frozen(self):
        self.assertEqual(classify_missing_clause(True), FIXTURES["missing_classification"]["required"])
        self.assertEqual(classify_missing_clause(False), FIXTURES["missing_classification"]["optional"])

    def test_topic_sidecar_shaped_inline_request(self):
        fixture = Path(__file__).parent / "fixtures" / "retrieval-spec" / "topic-sidecar-inline.json"
        spec = json.loads(fixture.read_text(encoding="utf-8"))
        normalized = normalize_retrieval_spec(spec)
        self.assertEqual(normalized["filters"]["topics"], ["session-fuse", "worktree-integration"])
        self.assertEqual(normalized["optional"]["sessions"], {"neighbouring_entries": 15})


if __name__ == "__main__":
    unittest.main()
