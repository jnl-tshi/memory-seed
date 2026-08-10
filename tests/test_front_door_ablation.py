import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PATH = Path(__file__).parents[1] / "experiments" / "semantic-compression" / "front_door_ablation.py"
SPEC = importlib.util.spec_from_file_location("front_door_ablation", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class FrontDoorAblationTests(unittest.TestCase):
    def test_complete_dra_preserves_all_source_blocks_in_order_and_keeps_a_label(self):
        source = (
            "- D1: Keep the canonical record.\n"
            "  It remains immutable.\n"
            "- F: `memory_seed/core.py`\n"
            "- R1: Derived fields may change.\n"
            "  This rationale is deliberately multiline.\n"
            "- A1: Rewriting the source was rejected.\n"
            "- T: `python -m pytest`\n"
        )
        result = MODULE.complete_dra_or_raw(source)

        self.assertEqual(result.mode, "complete_dra")
        self.assertIsNone(result.fallback_reason)
        self.assertIn("- D1: Keep the canonical record.\n  It remains immutable.", result.text)
        self.assertIn("- R1: Derived fields may change.\n  This rationale is deliberately multiline.", result.text)
        self.assertIn("- A1: Rewriting the source was rejected.", result.text)
        self.assertNotIn("memory_seed/core.py", result.text)
        self.assertNotIn("python -m pytest", result.text)
        self.assertLess(result.text.index("- D1:"), result.text.index("- R1:"))
        self.assertLess(result.text.index("- R1:"), result.text.index("- A1:"))
        self.assertEqual([item["label"] for item in result.provenance], ["D", "R", "A"])

    def test_structural_failures_return_the_raw_source_and_a_reason(self):
        missing_reason = "- D: Keep the source.\n- F: `core.py`\n"
        unknown_field = "- D: Keep the source.\n- R: It is authoritative.\n- X: unexpected.\n"
        equal_projection = "- D: Keep the source.\n- R: It is authoritative.\n"

        for source, expected in (
            (missing_reason, "missing required D or R field"),
            (unknown_field, "unknown field-like bullet"),
            (equal_projection, "projection is not smaller than raw"),
        ):
            with self.subTest(expected=expected):
                result = MODULE.complete_dra_or_raw(source)
                self.assertEqual(result.mode, "raw_fallback")
                self.assertEqual(result.text, source.strip())
                self.assertIn(expected, result.fallback_reason)

    def test_identifier_boundaries_do_not_accept_substrings(self):
        self.assertTrue(MODULE.contains_exact_identifier("Use `memory-seed`.", "memory-seed"))
        self.assertFalse(MODULE.contains_exact_identifier("Use `memory-seed-explorer`.", "memory-seed"))
        self.assertFalse(MODULE.contains_exact_identifier("Use `score.py`.", "core.py"))

    def test_query_evidence_prioritizes_exact_identifier_then_overlap_then_source_order(self):
        source = (
            "- D: Keep source decisions canonical.\n"
            "- R: Derived views can evolve independently.\n"
            "- A: Persisting generated views was rejected.\n"
            "- F: generic handling for core implementation.\n"
            "- T: `memory_seed/core.py` verification.\n"
        )
        result = MODULE.with_query_evidence(source, "Where is memory_seed/core.py handled?")

        self.assertEqual(result.mode, "query_evidence")
        self.assertIn("- T: `memory_seed/core.py` verification.", result.text)
        self.assertNotIn("- F: generic handling for core implementation.", result.text)
        self.assertEqual(result.provenance[-1]["label"], "T")
        self.assertEqual(result.provenance[-1]["selection"], "query_content_or_exact_identifier")

        overlap = MODULE.with_query_evidence(
            source, "Which generic core implementation handling evolved independently?"
        )
        self.assertIn("- F: generic handling for core implementation.", overlap.text)

    def test_query_evidence_fails_open_when_appending_evidence_erases_context_saving(self):
        source = (
            "- D: Keep the source.\n"
            "- R: Views evolve.\n"
            "- A: Rewrite rejected.\n"
            "- F: `core.py`\n"
        )
        result = MODULE.with_query_evidence(source, "Where is core.py used?")
        self.assertEqual(result.mode, "raw_fallback")
        self.assertEqual(result.text, source.strip())
        self.assertIn("not smaller than raw", result.fallback_reason)

    def test_retrieval_arms_keep_raw_bodies_and_change_only_lexical_terms(self):
        sample, _, _, _ = MODULE.frozen_inputs()
        body = MODULE.corpus_for_arm(sample, "body_only")
        current = MODULE.corpus_for_arm(sample, "current_lexical_terms")
        authored = MODULE.corpus_for_arm(sample, "authored_exact_terms")
        union = MODULE.corpus_for_arm(sample, "union_terms")

        for index, source in enumerate(sample):
            self.assertEqual(body[index].text, source.text)
            self.assertEqual(current[index].text, source.text)
            self.assertEqual(authored[index].text, source.text)
            self.assertEqual(union[index].text, source.text)
            self.assertEqual(body[index].lexical_terms, ())
            self.assertEqual(current[index].lexical_terms, source.lexical_terms)
            self.assertEqual(
                union[index].lexical_terms,
                tuple(dict.fromkeys((*source.lexical_terms, *authored[index].lexical_terms))),
            )
            self.assertEqual(body[index].heading_path, ())
            self.assertEqual(body[index].topics, ())
        self.assertTrue(MODULE.raw_rank_body_invariant(sample)["holds"])

    def test_authored_exact_terms_never_synthesizes_path_aliases(self):
        source = "- D: Add a check.\n- R: It prevents drift.\n- F: `memory_seed/core.py`"
        terms = MODULE.authored_exact_terms(source)
        self.assertIn("memory_seed/core.py", terms)
        self.assertNotIn("core.py", terms)

    def test_frozen_query_and_selection_pins_validate(self):
        sample, selected, payload, identity = MODULE.frozen_inputs()
        self.assertEqual(identity["source_revision"], MODULE.EXPECTED_SOURCE_REVISION)
        self.assertEqual(len(sample), 100)
        self.assertEqual(len(selected), 30)
        self.assertEqual(MODULE.sha256_bytes(MODULE.QUERY_PATH.read_bytes()), MODULE.EXPECTED_QUERY_SHA256)
        self.assertEqual(len(MODULE.query_rows(selected, payload)), 60)

    def test_selector_pin_and_negative_control(self):
        self.assertEqual(MODULE.selector_sha256(), MODULE.EXPECTED_SELECTOR_SHA256)
        with mock.patch.object(MODULE, "EXPECTED_SELECTOR_SHA256", "sha256:" + "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "selector is not frozen"):
                MODULE.frozen_inputs()

    def test_oracle_validation_requires_exact_source_spans_for_every_query(self):
        class Chunk:
            chunk_id = "mse_frontdoorfixture:d1"
            text = "- D: Keep canonical text.\n- R: Views are derived.\n- F: `core.py`"

        selected = [Chunk()]
        packet = MODULE.LEAN.packet_id(Chunk.chunk_id)
        source = Chunk.text
        start = source.index("canonical")
        payload = {
            "schema": "front-door-answer-key.v1",
            "answers": [
                {"packet_id": packet, "kind": "semantic",
                 "spans": [{"start_char": start, "end_char": start + len("canonical"), "text": "canonical"}]},
                {"packet_id": packet, "kind": "anchor",
                 "spans": [{"start_char": source.index("core.py"), "end_char": source.index("core.py") + 7,
                            "text": "core.py"}]},
            ],
        }
        self.assertEqual(len(MODULE.validate_oracle(payload, selected, {"queries": []})), 2)
        payload["answers"][0]["spans"][0]["text"] = "rewritten"
        with self.assertRaisesRegex(ValueError, "not exact source text"):
            MODULE.validate_oracle(payload, selected, {"queries": []})
        payload["answers"][0]["spans"][0]["text"] = "canonical"
        payload["answers"][0]["spans"].append(payload["answers"][0]["spans"][0].copy())
        with self.assertRaisesRegex(ValueError, "duplicate source span"):
            MODULE.validate_oracle(payload, selected, {"queries": []})
        payload["answers"][0]["spans"] = [{"start_char": 0, "end_char": len(source), "text": source}]
        with self.assertRaisesRegex(ValueError, "whole source"):
            MODULE.validate_oracle(payload, selected, {"queries": []})

    def test_oracle_review_requires_matching_hash_and_every_review_accepted(self):
        class Chunk:
            chunk_id = "mse_frontdoorfixture:d1"
            text = "- D: Keep canonical text.\n- R: Views are derived."

        selected = [Chunk()]
        packet = MODULE.LEAN.packet_id(Chunk.chunk_id)
        payload = {
            "schema": "front-door-answer-key-review.v1",
            "oracle_sha256": "sha256:oracle",
            "reviewer_model": "fixture-reviewer",
            "input_access": "canonical-source-query-and-oracle-spans-only",
            "ranking_results_seen": False,
            "display_candidates_seen": False,
            "reviews": [
                {"packet_id": packet, "kind": "semantic", "accepted": True},
                {"packet_id": packet, "kind": "anchor", "accepted": True},
            ],
        }
        self.assertEqual(len(MODULE.validate_oracle_review(payload, "sha256:oracle", selected)), 2)
        payload["reviews"][1]["accepted"] = False
        with self.assertRaisesRegex(ValueError, "rejected or did not accept"):
            MODULE.validate_oracle_review(payload, "sha256:oracle", selected)

    def test_packets_work_before_oracle_but_scoring_writes_nothing_while_pending(self):
        packets = MODULE.oracle_packets()
        self.assertEqual(len(packets), 30)
        self.assertEqual(set(packets[0]), {"packet_id", "source", "semantic_query", "anchor_query"})
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "oracle pin is PENDING"):
                MODULE.run(output)
            self.assertFalse((output / "front-door-ablation-metrics.json").exists())
            self.assertFalse((output / "front-door-results.md").exists())

    def test_missing_or_pending_oracle_review_writes_no_partial_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with mock.patch.object(MODULE, "load_oracle", return_value={"answers": []}), \
                 mock.patch.object(MODULE, "ORACLE_PATH", MODULE.QUERY_PATH):
                with self.assertRaisesRegex(RuntimeError, "oracle review pin is PENDING"):
                    MODULE.run(output)
            self.assertFalse((output / "front-door-ablation-metrics.json").exists())
            self.assertFalse((output / "front-door-results.md").exists())

    def test_display_metrics_include_full_source_affordance_and_identifier_coverage(self):
        class Chunk:
            chunk_id = "mse_frontdoorfixture:d1"
            text = (
                "- D: Keep canonical text.\n- R: Views are derived.\n"
                "- A: Rewrite rejected.\n- F: `core.py`\n- T: check"
            )

        packet = MODULE.LEAN.packet_id(Chunk.chunk_id)
        payload = {"queries": [{"packet_id": packet, "semantic_query": "Why remain canonical?",
                                  "anchor_query": "Where is core.py checked?"}]}
        metrics = MODULE.display_metrics([Chunk()], payload)
        self.assertEqual(metrics["raw"]["mean_full_source_affordance_utf8_bytes"], 0)
        self.assertGreater(metrics["complete_dra"]["mean_full_source_affordance_utf8_bytes"], 0)
        self.assertGreater(metrics["query_evidence"]["query_identifier_display_coverage"], 0)
        self.assertIn("median_displayed_utf8_bytes", metrics["current_lean"])


if __name__ == "__main__":
    unittest.main()
