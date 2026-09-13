"""External structured runner for candidate-authored task tests."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import traceback
import unittest
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
RUNNER_VERSION = "codex-candidate-unittest-runner-v2"
MODULE_NAME = "candidate_task_tests"


class _HarnessResult(unittest.TestResult):
    """Result callbacks bound from stdlib before candidate import."""

    startTest = unittest.TestResult.startTest
    stopTest = unittest.TestResult.stopTest
    addError = unittest.TestResult.addError
    addFailure = unittest.TestResult.addFailure
    addSuccess = unittest.TestResult.addSuccess
    addSkip = unittest.TestResult.addSkip
    addExpectedFailure = unittest.TestResult.addExpectedFailure
    addUnexpectedSuccess = unittest.TestResult.addUnexpectedSuccess
    wasSuccessful = unittest.TestResult.wasSuccessful


class _HarnessSuite(unittest.TestSuite):
    """Suite operations bound from stdlib before candidate import."""

    addTest = unittest.TestSuite.addTest
    addTests = unittest.TestSuite.addTests
    run = unittest.TestSuite.run
    __iter__ = unittest.TestSuite.__iter__


class _HarnessLoader(unittest.TestLoader):
    """Discovery operations bound from stdlib before candidate import."""

    loadTestsFromModule = unittest.TestLoader.loadTestsFromModule
    loadTestsFromTestCase = unittest.TestLoader.loadTestsFromTestCase
    getTestCaseNames = unittest.TestLoader.getTestCaseNames


def _tests(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _tests(item)
        else:
            yield item


def _problem_rows(rows: list[tuple[unittest.TestCase, str]]) -> list[dict[str, str]]:
    return [{"id": test.id(), "detail": detail[-4000:]} for test, detail in rows]


def run_test_file(path: Path) -> dict[str, object]:
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    # Create and bind every runner-owned object/method before candidate code is
    # executed. The loaded candidate supplies TestCase classes only.
    loader = _HarnessLoader()
    loader.suiteClass = _HarnessSuite
    root_suite = _HarnessSuite()
    result = _HarnessResult()
    load_from_module = loader.loadTestsFromModule
    add_tests = root_suite.addTests
    run_suite = root_suite.run
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load candidate test module: {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            add_tests(load_from_module(module))
            discovered = sorted(test.id() for test in _tests(root_suite))
            run_suite(result)
    except BaseException as error:  # fail closed even for candidate SystemExit
        return {
            "schema_version": SCHEMA_VERSION,
            "runner_version": RUNNER_VERSION,
            "status": "error",
            "discovered_ids": [],
            "testsRun": 0,
            "failures": [],
            "errors": [],
            "skipped": [],
            "load_error": {
                "type": type(error).__name__,
                "detail": "".join(traceback.format_exception(error))[-4000:],
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "status": "ok",
        "discovered_ids": discovered,
        "testsRun": result.testsRun,
        "failures": _problem_rows(result.failures),
        "errors": _problem_rows(result.errors),
        "skipped": [{"id": test.id(), "reason": reason} for test, reason in result.skipped],
        "load_error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test_file", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_test_file(args.test_file.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


