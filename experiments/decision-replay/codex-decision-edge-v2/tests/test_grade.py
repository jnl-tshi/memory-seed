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
        self.assertEqual(4, grade.SCHEMA_VERSION)
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
            "schema_version": 4,
            "grader_version": grade.GRADER_VERSION,
            "instrument": "codex-decision-edge-v2",
            "status": "fail",
            "ready_for_scoring": True,
            "baseline_integrity": {"status": "pass"},
            "candidate": {},
            "oracle": {},
            "candidate_test_runner": {},
            "gates": {name: {"status": "fail"} for name in grade.ALL_GATES},
            "outcomes": {name: False for name in grade.OUTCOME_KEYS},
            "protocol": grade.assess_protocol(None),
        }
        grade.validate_report_schema(report)
        round_trip = json.loads(json.dumps(report))
        self.assertEqual(4, round_trip["schema_version"])
        self.assertEqual("not_assessed", round_trip["protocol"]["status"])

    def test_schema_rejects_gate_drift(self) -> None:
        report = {
            "schema_version": 4,
            "grader_version": grade.GRADER_VERSION,
            "instrument": "codex-decision-edge-v2",
            "status": "fail",
            "ready_for_scoring": True,
            "baseline_integrity": {"status": "pass"},
            "candidate": {},
            "oracle": {},
            "candidate_test_runner": {},
            "gates": {},
            "outcomes": {name: False for name in grade.OUTCOME_KEYS},
            "protocol": grade.assess_protocol(None),
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
            "context_receipt": "ctx",
            "memory_evidence_used": ["none"],
            "rationale_propositions_used": ["none"],
            "diagnosis": "x",
            "implementation_choice": "x",
            "alternatives_rejected": ["none"],
            "files_changed": [grade.SERVICE_PATH.as_posix(), grade.PUBLIC_TEST_PATH.as_posix()],
            "validation": [{"command": "x", "result": "pass"}],
            "residual_risks": ["none"],
        }
        complete = grade.assess_protocol(complete_payload)
        self.assertEqual("complete", complete["status"])
        self.assertTrue(complete["complete"])

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
