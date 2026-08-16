"""Adversarial tests for the hardened grader trust boundaries."""

from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

import grade  # noqa: E402


def run_result(code: int | None, output: str, *, timed_out: bool = False) -> dict[str, object]:
    return {"returncode": code, "timed_out": timed_out, "stdout": output, "stderr": ""}


class GraderHardeningTests(unittest.TestCase):
    def test_baseline_match_mismatch_absence_and_pre_archive_rejection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-grade-baseline-") as temporary:
            repo = Path(temporary)
            grade._git(repo, "init", "-b", "main")
            grade._git(repo, "config", "user.name", "Qualification")
            grade._git(repo, "config", "user.email", "qualification@example.invalid")
            (repo / "x.txt").write_text("x\n", encoding="utf-8")
            grade._git(repo, "add", "x.txt")
            grade._git(repo, "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
            expected = grade._git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()
            self.assertEqual("pass", grade.assess_baseline(repo, expected)["status"])
            grade._git(repo, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "drift")
            self.assertEqual("error", grade.assess_baseline(repo, expected)["status"])
            self.assertEqual("error", grade.assess_baseline(repo, "f" * 40)["status"])
            with mock.patch.object(grade, "_external_copies", side_effect=AssertionError("archive called")):
                report = grade.grade_candidate(repo, expected_baseline="f" * 40)
            self.assertEqual("error", report["status"])
            self.assertFalse(report["ready_for_scoring"])
            self.assertTrue(all(gate["status"] == "error" for gate in report["gates"].values()))

    def test_deep_protocol_and_report_shapes(self) -> None:
        payload = {
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
        self.assertTrue(grade.assess_protocol(payload)["complete"])
        malformed = dict(payload)
        malformed.update(
            {"context_receipt": " ", "memory_evidence_used": [1], "validation": [{"command": "x", "result": 1}]}
        )
        self.assertCountEqual(
            ["context_receipt", "memory_evidence_used", "validation"],
            grade.assess_protocol(malformed)["invalid_fields"],
        )
        report = {
            "schema_version": grade.SCHEMA_VERSION,
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
        for mutation in ("gate", "outcome", "protocol"):
            bad = json.loads(json.dumps(report))
            if mutation == "gate":
                bad["gates"][grade.ALL_GATES[0]]["status"] = "maybe"
            elif mutation == "outcome":
                bad["outcomes"]["extra"] = False
            else:
                bad["protocol"].pop("invalid_fields")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                grade.validate_report_schema(bad)

    def test_structured_runner_accepts_real_assertion_and_rejects_fabricated_transcript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-structured-runner-") as temporary:
            root = Path(temporary)
            pristine = root / "pristine"
            candidate = root / "candidate"
            for copy, value in ((pristine, "False"), (candidate, "True")):
                test_path = copy / grade.PUBLIC_TEST_PATH
                test_path.parent.mkdir(parents=True)
                (copy / "behavior.py").write_text(f"VALUE = {value}\n", encoding="utf-8")
                test_path.write_text(
                    "import unittest\nfrom behavior import VALUE\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_behavior(self):\n        self.assertTrue(VALUE)\n",
                    encoding="utf-8",
                )
            real_pristine = grade._run_candidate_test_runner(pristine)
            real_candidate = grade._run_candidate_test_runner(candidate)
            self.assertEqual(
                "pass",
                grade._assess_discrimination_results(real_pristine, real_candidate)["status"],
            )

            fake_source = (
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_fake(self):\n"
                "        print('FAIL: test_fake\\nAssertionError\\nRan 1 test\\nFAILED (failures=1)')\n"
                "        self.assertTrue(True)\n"
            )
            for copy in (pristine, candidate):
                (copy / grade.PUBLIC_TEST_PATH).write_text(fake_source, encoding="utf-8")
            fake_pristine = grade._run_candidate_test_runner(pristine)
            fake_candidate = grade._run_candidate_test_runner(candidate)
            self.assertEqual(
                "fail",
                grade._assess_discrimination_results(fake_pristine, fake_candidate)["status"],
            )
            self.assertEqual([], fake_pristine["payload"]["failures"])

    def test_structured_discriminator_rejects_suite_drift_errors_and_runner_failure(self) -> None:
        payload = {
            "schema_version": 1,
            "runner_version": "codex-candidate-unittest-runner-v2",
            "status": "ok",
            "discovered_ids": ["candidate_task_tests.T.test_x"],
            "testsRun": 1,
            "failures": [{"id": "candidate_task_tests.T.test_x", "detail": "assertion"}],
            "errors": [],
            "skipped": [],
            "load_error": None,
        }
        pristine = {"process_ok": True, "runner_schema_ok": True, "payload": payload}
        passing_payload = {**payload, "failures": []}
        candidate = {"process_ok": True, "runner_schema_ok": True, "payload": passing_payload}
        self.assertEqual("pass", grade._assess_discrimination_results(pristine, candidate)["status"])
        drift = {**passing_payload, "discovered_ids": ["candidate_task_tests.T.test_y"]}
        error = {**passing_payload, "errors": [{"id": "candidate_task_tests.T.test_x", "detail": "boom"}]}
        broken = {"process_ok": False, "runner_schema_ok": False, "payload": None}
        for bad_candidate in (
            {**candidate, "payload": drift},
            {**candidate, "payload": error},
            broken,
        ):
            with self.subTest(candidate=bad_candidate):
                self.assertEqual(
                    "fail",
                    grade._assess_discrimination_results(pristine, bad_candidate)["status"],
                )
        self.assertEqual(
            "fail",
            grade._assess_discrimination_results(
                pristine,
                candidate,
                test_files_identical=False,
            )["status"],
        )

    def test_reviewer_unittest_result_and_suite_monkeypatch_is_rejected_and_ineffective(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-runner-monkeypatch-") as temporary:
            candidate = Path(temporary)
            test_path = candidate / grade.PUBLIC_TEST_PATH
            test_path.parent.mkdir(parents=True)
            test_path.write_text(
                "import unittest\n"
                "unittest.TestResult.addFailure = lambda self, test, err: self.addSuccess(test)\n"
                "unittest.TestSuite.run = lambda self, result, debug=False: result\n"
                "class T(unittest.TestCase):\n"
                "    def test_x(self):\n        self.assertTrue(False)\n",
                encoding="utf-8",
            )
            allowed, detail = grade._contains_actual_test_code(test_path)
            self.assertFalse(allowed)
            self.assertIn("runner tampering", detail)
            execution = grade._run_candidate_test_runner(candidate)
            self.assertTrue(execution["process_ok"])
            self.assertTrue(execution["runner_schema_ok"])
            self.assertEqual(1, execution["payload"]["testsRun"])
            self.assertEqual(1, len(execution["payload"]["failures"]))
            self.assertEqual([], execution["payload"]["errors"])

    def test_ast_rejects_exec_eval_main_and_sys_modules_runner_introspection(self) -> None:
        snippets = (
            "import unittest\nexec('x=1')\n",
            "import unittest\neval('1')\n",
            "import __main__\n",
            "import sys\nvalue = sys.modules['__main__']\n",
            "from sys import modules\nvalue = modules['__main__']\n",
            "import unittest\nsetattr(unittest.TestResult, 'addFailure', lambda *a: None)\n",
        )
        for source in snippets:
            with self.subTest(source=source):
                tree = compile(source, "candidate.py", "exec", ast.PyCF_ONLY_AST)
                self.assertTrue(grade._runner_tamper_violations(tree))

    def test_hidden_oracle_requires_successful_non_timeout_exit(self) -> None:
        payload = json.dumps(
            {
                "schema_version": 1,
                "gates": {gate: {"status": "pass", "detail": "x"} for gate in grade.SEMANTIC_GATES},
            }
        )
        for result in (run_result(1, payload), run_result(None, payload, timed_out=True)):
            with self.subTest(result=result), mock.patch.object(grade, "_run", return_value=result):
                observed = grade._run_hidden_oracle(Path("candidate"))
            self.assertTrue(all(gate["status"] == "error" for gate in observed.values()))

    def test_subprocess_environment_drops_inherited_redirections(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"PYTHONPATH": "evil", "PYTHONHOME": "evil", "GIT_DIR": "evil", "GIT_WORK_TREE": "evil"},
            clear=False,
        ):
            candidate = Path("C:/candidate").resolve()
            environment = grade._minimal_environment(cwd=candidate, pythonpath=True)
        self.assertEqual(
            os.pathsep.join((str(candidate / "memory-trace"), str(candidate))),
            environment["PYTHONPATH"],
        )
        for name in ("PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE"):
            self.assertNotIn(name, environment)


if __name__ == "__main__":
    unittest.main()
