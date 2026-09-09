"""Local scorer for declared delivery-quality scenarios.

This intentionally scores structured records.  It does not inspect skill prose or
attempt to infer provider measurements from estimates, budgets, or elapsed wall time.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


MEASUREMENT_NAMES = ("provider_token_usage", "latency", "cost")
EVIDENCE_CLASSES = {"fixture_instrument_validation", "real_agent_behavior"}
COMPARISON_PHASES = {"baseline", "post_adoption"}


def load_corpus(path: Path) -> dict[str, Any]:
    """Load the declared local corpus without fetching or executing anything."""
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus.get("schema") != "delivery-quality-scenarios/v1":
        raise ValueError("unsupported delivery-quality scenario schema")
    if not isinstance(corpus.get("scenarios"), list) or not corpus["scenarios"]:
        raise ValueError("corpus must contain at least one scenario")
    ids = [scenario.get("id") for scenario in corpus["scenarios"]]
    if any(not isinstance(identifier, str) or not identifier for identifier in ids):
        raise ValueError("every scenario needs a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("scenario ids must be unique")
    return corpus


def _scenario(corpus: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in corpus["scenarios"]:
        if scenario["id"] == scenario_id:
            return scenario
    raise ValueError(f"unknown scenario: {scenario_id}")


def _valid_evidence_ids(run: dict[str, Any]) -> set[str]:
    valid: set[str] = set()
    for evidence in run.get("evidence", []):
        if (
            isinstance(evidence, dict)
            and isinstance(evidence.get("id"), str)
            and evidence["id"].strip()
            and isinstance(evidence.get("source"), str)
            and evidence["source"].strip()
            and isinstance(evidence.get("record"), str)
            and evidence["record"].strip()
        ):
            valid.add(evidence["id"])
    return valid


def _matches(observation: dict[str, Any], contract: dict[str, Any]) -> bool:
    return all(observation.get(field) == contract.get(field) for field in ("action", "subject"))


def _validate_measurements(run: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    measurements = run.get("measurements")
    if not isinstance(measurements, dict):
        failures.append("measurements must be an object")
        return {}
    result: dict[str, Any] = {}
    for name in MEASUREMENT_NAMES:
        measurement = measurements.get(name)
        if not isinstance(measurement, dict):
            failures.append(f"measurement {name} is missing")
            continue
        availability = measurement.get("availability")
        if availability not in {"available", "unavailable"}:
            failures.append(f"measurement {name} has invalid availability")
            continue
        if availability == "unavailable":
            if measurement.get("value") is not None:
                failures.append(f"measurement {name} is unavailable but has an inferred value")
            if not isinstance(measurement.get("reason"), str) or not measurement["reason"].strip():
                failures.append(f"measurement {name} is unavailable without a reason")
        else:
            if measurement.get("value") is None:
                failures.append(f"measurement {name} is available without a value")
            if not isinstance(measurement.get("source"), str) or not measurement["source"].strip():
                failures.append(f"measurement {name} is available without an execution-surface source")
        result[name] = measurement
    return result


def _validate_result_schema(run: dict[str, Any], failures: list[str]) -> None:
    if (
        run.get("evidence_class") == "real_agent_behavior"
        and run.get("schema") != "delivery-quality-result-input/v1"
    ):
        failures.append("real-agent input must use delivery-quality-result-input/v1")
    if run.get("evidence_class") not in EVIDENCE_CLASSES:
        failures.append("evidence_class must distinguish fixture and real-agent evidence")
    if run.get("comparison_phase") not in COMPARISON_PHASES:
        failures.append("comparison_phase must be baseline or post_adoption")
    for field in ("limitations", "selection_bias", "rework_reopen_events"):
        if not isinstance(run.get(field), list):
            failures.append(f"{field} must be a list")
    for event in run.get("rework_reopen_events", []):
        if not isinstance(event, dict) or not event.get("event") or not event.get("cause"):
            failures.append("each rework_reopen_event requires event and cause")


def evaluate_run(corpus: dict[str, Any], scenario_id: str, run: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one structured run; no fixture result can support a workflow claim."""
    scenario = _scenario(corpus, scenario_id)
    failures: list[str] = []
    _validate_result_schema(run, failures)
    measurements = _validate_measurements(run, failures)
    observations = run.get("observations")
    if not isinstance(observations, list):
        failures.append("observations must be a list")
        observations = []
    valid_evidence = _valid_evidence_ids(run)

    for contract in scenario["required_observations"]:
        matches = [
            observation
            for observation in observations
            if isinstance(observation, dict)
            and observation.get("status") == "observed"
            and _matches(observation, contract)
        ]
        label = contract["id"]
        if not matches:
            failures.append(f"required observation {label} is absent")
            continue
        if not any(
            isinstance(observation.get("evidence_ids"), list)
            and set(observation["evidence_ids"]).intersection(valid_evidence)
            for observation in matches
        ):
            failures.append(f"required observation {label} has missing upstream evidence")

    for contract in scenario["prohibited_observations"]:
        if any(
            isinstance(observation, dict)
            and observation.get("status") == "observed"
            and _matches(observation, contract)
            for observation in observations
        ):
            failures.append(f"prohibited observation {contract['id']} was observed")

    passed = not failures
    evidence_class = run.get("evidence_class")
    return {
        "schema": "delivery-quality-result/v1",
        "scenario_id": scenario_id,
        "category": scenario["category"],
        "expected_routing": scenario["expected_routing"],
        "task_complexity": scenario["complexity"],
        "comparison_phase": run.get("comparison_phase"),
        "evidence_class": evidence_class,
        "passed": passed,
        "failures": failures,
        "measurements": measurements,
        "limitations": run.get("limitations", []),
        "selection_bias": run.get("selection_bias", []),
        "rework_reopen_events": run.get("rework_reopen_events", []),
        "workflow_claim_eligible": passed and evidence_class == "real_agent_behavior",
        "claim_boundary": (
            "fixture validates only the scorer; it does not support a workflow claim"
            if evidence_class == "fixture_instrument_validation"
            else "a passing real run is eligible evidence, not a comparative workflow conclusion"
        ),
    }


def evaluate_declared_fixtures(corpus: dict[str, Any], *, kind: str) -> dict[str, Any]:
    """Run all declared controls, treating expected negative failures as a successful check."""
    if kind not in {"valid", "negative"}:
        raise ValueError("fixture kind must be valid or negative")
    results: list[dict[str, Any]] = []
    for scenario in corpus["scenarios"]:
        fixtures = [scenario["valid_fixture"]] if kind == "valid" else scenario["negative_controls"]
        for fixture in fixtures:
            result = evaluate_run(corpus, scenario["id"], copy.deepcopy(fixture))
            result["fixture_id"] = fixture["id"]
            result["expected_fixture_outcome"] = "pass" if kind == "valid" else "fail"
            results.append(result)
    expected = (lambda result: result["passed"]) if kind == "valid" else (lambda result: not result["passed"])
    return {
        "schema": "delivery-quality-fixture-report/v1",
        "fixture_kind": kind,
        "passed": sum(1 for result in results if expected(result)),
        "failed": sum(1 for result in results if not expected(result)),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate local delivery-quality scenario evidence.")
    parser.add_argument("--corpus", type=Path, default=Path(__file__).with_name("scenarios.json"))
    parser.add_argument("--fixture", choices=("valid", "negative"))
    parser.add_argument("--input", type=Path, help="A real-run JSON object containing scenario_id.")
    args = parser.parse_args()
    if bool(args.fixture) == bool(args.input):
        parser.error("supply exactly one of --fixture or --input")
    corpus = load_corpus(args.corpus)
    if args.fixture:
        report = evaluate_declared_fixtures(corpus, kind=args.fixture)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["failed"] == 0 else 1
    run = json.loads(args.input.read_text(encoding="utf-8"))
    scenario_id = run.pop("scenario_id", None)
    if not isinstance(scenario_id, str):
        parser.error("--input must contain a string scenario_id")
    result = evaluate_run(corpus, scenario_id, run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
