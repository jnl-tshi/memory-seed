"""Focused schema, scope, protocol, and discrimination guard tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

import grade  # noqa: E402


class GraderContractTests(unittest.TestCase):
    def test_frozen_gate_and_report_schema(self) -> None:
        self.assertEqual(7, grade.SCHEMA_VERSION)
        self.assertEqual("codex-decision-edge-v5-semantic-v1", grade.ORACLE_VERSION)
        self.assertEqual((sys.executable, "RUN_TASK_TESTS.py"), grade.PUBLIC_COMMAND)
        self.assertEqual(
            (
                "decision_row_target",
                "focused_membership",
                "entry_edge_set_equality",
                "entry_ref_regression",
                "invalid_ordinal_no_widening",
                "single_decision_d1",
                "public_task_tests",
                "bounded_scope",
                "candidate_test_discriminates",
            ),
            grade.ALL_GATES,
        )
        report = {
            "schema_version": 7,
            "grader_version": grade.GRADER_VERSION,
            "instrument": "codex-decision-edge-v5",
            "status": "fail",
            "ready_for_scoring": True,
            "baseline_integrity": {"status": "pass"},
            "candidate": {},
            "oracle": {},
            "candidate_test_runner": {},
            "gates": {name: {"status": "fail"} for name in grade.ALL_GATES},
            "outcomes": {name: False for name in grade.OUTCOME_KEYS},
            "protocol": grade.assess_protocol(None),
            "retrieval_compliance": grade.assess_retrieval_compliance(None, None),
        }
        grade.validate_report_schema(report)
        round_trip = json.loads(json.dumps(report))
        self.assertEqual(7, round_trip["schema_version"])
        self.assertEqual("not_assessed", round_trip["protocol"]["status"])

    def test_schema_rejects_gate_drift(self) -> None:
        report = {
            "schema_version": 7,
            "grader_version": grade.GRADER_VERSION,
            "instrument": "codex-decision-edge-v5",
            "status": "fail",
            "ready_for_scoring": True,
            "baseline_integrity": {"status": "pass"},
            "candidate": {},
            "oracle": {},
            "candidate_test_runner": {},
            "gates": {},
            "outcomes": {name: False for name in grade.OUTCOME_KEYS},
            "protocol": grade.assess_protocol(None),
            "retrieval_compliance": grade.assess_retrieval_compliance(None, None),
        }
        with self.assertRaisesRegex(ValueError, "gate order or membership"):
            grade.validate_report_schema(report)

    def test_scope_is_exact_and_reports_unexpected_paths(self) -> None:
        allowed = {
            "memory-trace/memory_trace/service.py",
            "memory-trace/tests/test_trail_decision_edges.py",
        }
        self.assertEqual("pass", grade.assess_scope(allowed)["status"])
        result = grade.assess_scope({*allowed, "TASK.md"})
        self.assertEqual("fail", result["status"])
        self.assertEqual(["TASK.md"], result["unexpected_changed_files"])

    def test_protocol_complete_incomplete_and_absent_are_distinct(self) -> None:
        absent = grade.assess_protocol(None)
        self.assertEqual("not_assessed", absent["status"])
        self.assertIsNone(absent["complete"])

        incomplete = grade.assess_protocol({"context_receipt": "ctx"})
        self.assertEqual("incomplete", incomplete["status"])
        self.assertFalse(incomplete["complete"])
        self.assertIn("diagnosis", incomplete["missing_fields"])

        complete_payload = {
            "pre_coding_receipt": {
                "context_receipt": "ctx",
                "evidence_ids_used": "none",
                "rationale_propositions_used": "none",
                "acknowledgement": "captured before candidate edits",
            },
            "context_receipt": "ctx",
            "memory_evidence_used": ["none"],
            "rationale_propositions_used": ["none"],
            "diagnosis": "x",
            "implementation_choice": "x",
            "alternatives_rejected": ["none"],
            "files_changed": [grade.SERVICE_PATH.as_posix(), grade.PUBLIC_TEST_PATH.as_posix()],
            "validation": [{"command": "x", "result": "pass"}],
            "residual_risks": ["none"],
            "retrieval_receipt": {
                "required": False,
                "query": "not-required",
                "selected_chunk_id": "not-required",
                "pre_edit_plan": {
                    "invariant": "preserve decision scope",
                    "affected_code_path": "memory-trace/memory_trace/service.py",
                    "acceptance_cases": ["d2 resolves"],
                    "non_goals": ["no response-model change"],
                },
            },
        }
        complete = grade.assess_protocol(complete_payload)
        self.assertEqual("complete", complete["status"])
        self.assertTrue(complete["complete"])

        missing_receipt = dict(complete_payload)
        missing_receipt.pop("pre_coding_receipt")
        self.assertEqual("incomplete", grade.assess_protocol(missing_receipt)["status"])
        malformed_receipt = dict(complete_payload)
        malformed_receipt["pre_coding_receipt"] = {"context_receipt": "ctx"}
        self.assertIn("pre_coding_receipt", grade.assess_protocol(malformed_receipt)["invalid_fields"])

        missing_validation = dict(complete_payload)
        missing_validation.pop("validation")
        missing_validation_result = grade.assess_protocol(missing_validation)
        self.assertEqual("incomplete", missing_validation_result["status"])
        self.assertIn("validation", missing_validation_result["missing_fields"])

        malformed_validation = dict(complete_payload)
        malformed_validation["validation"] = "not a list"
        malformed_validation_result = grade.assess_protocol(malformed_validation)
        self.assertEqual("incomplete", malformed_validation_result["status"])
        self.assertIn("validation", malformed_validation_result["wrong_shape_fields"])

    def test_retrieval_compliance_is_separate_from_semantic_scoring(self) -> None:
        receipt = {
            "retrieval_receipt": {
                "required": True,
                "query": grade.REQUIRED_RETRIEVAL_QUERY,
                "selected_chunk_id": grade.REQUIRED_RETRIEVAL_CHUNK_ID,
                "pre_edit_plan": {
                    "invariant": "do not project decision edges",
                    "affected_code_path": "memory-trace/memory_trace/service.py",
                    "acceptance_cases": ["d2", "d1", "d99"],
                    "non_goals": ["public shape"],
                },
            }
        }
        self.assertEqual("pass", grade.assess_retrieval_compliance(receipt, True)["status"])
        self.assertEqual("not_assessed", grade.assess_retrieval_compliance(receipt, None)["status"])
        receipt["retrieval_receipt"]["selected_chunk_id"] = "wrong:d1"
        self.assertEqual("fail", grade.assess_retrieval_compliance(receipt, True)["status"])

    def test_candidate_test_requires_real_test_and_assertion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-grade-test-code-") as temporary:
            path = Path(temporary) / "candidate.py"
            path.write_text("VALUE = 1\n", encoding="utf-8")
            self.assertFalse(grade._contains_actual_test_code(path)[0])
            path.write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_x(self):\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            self.assertTrue(grade._contains_actual_test_code(path)[0])

    def test_grader_source_does_not_name_or_read_sealed_mapping(self) -> None:
        source = Path(grade.__file__).read_text(encoding="utf-8")
        self.assertNotIn("condition-map", source)
        self.assertNotIn("treatment-deltas", source)


if __name__ == "__main__":
    unittest.main()
