"""Apply the predeclared development-only stopping rule to measured iterations.

Inputs are aggregate measurements from the same frozen development IDs. This
gate cannot generate a source alignment or infer semantic sufficiency; those
must be measured separately against adjudicated citations. Do not put sealed
held-out metrics in this file while choosing settings.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MAX_ITERATIONS = 6
MIN_EFFICIENCY_GAIN = 0.05


def assess(prior: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if prior["development_ids_sha256"] != current["development_ids_sha256"]:
        raise ValueError("development cohort drift")
    if int(current["iteration"]) != int(prior["iteration"]) + 1:
        raise ValueError("iterations must be consecutive")
    for name in ("verified_source_recovered", "verified_all_evidence_in_20", "retrieval_payload_tokens"):
        if float(current[name]) < 0 or float(prior[name]) < 0:
            raise ValueError(f"{name} cannot be negative")
    for row in (prior, current):
        if row.get("runtime_seconds") is not None and float(row["runtime_seconds"]) < 0:
            raise ValueError("runtime_seconds cannot be negative")
    source_gain = int(current["verified_source_recovered"]) - int(prior["verified_source_recovered"])
    envelope_gain = int(current["verified_all_evidence_in_20"]) - int(prior["verified_all_evidence_in_20"])
    token_gain = (
        1 - float(current["retrieval_payload_tokens"]) / float(prior["retrieval_payload_tokens"])
        if float(prior["retrieval_payload_tokens"]) > 0 else 0.0
    )
    runtime_gain = None
    if prior.get("runtime_seconds") is not None and current.get("runtime_seconds") is not None:
        runtime_gain = (
            1 - float(current["runtime_seconds"]) / float(prior["runtime_seconds"])
            if float(prior["runtime_seconds"]) > 0 else 0.0
        )
    accepted = source_gain >= 0 and envelope_gain >= 0
    material = accepted and (
        source_gain > 0 or envelope_gain > 0
        or token_gain >= MIN_EFFICIENCY_GAIN
        or runtime_gain is not None and runtime_gain >= MIN_EFFICIENCY_GAIN
    )
    return {
        "accepted": accepted,
        "reason": "verified_recall_regression" if not accepted else "eligible",
        "material_improvement": material,
        "new_verified_sources": max(0, source_gain),
        "twenty_turn_recall_delta": envelope_gain,
        "retrieval_token_reduction": token_gain,
        "runtime_reduction": runtime_gain,
    }


def should_stop(history: list[dict[str, Any]]) -> bool:
    if len(history) < 3:
        return False
    assessments = assess_history(history)
    return (
        int(history[-1]["iteration"]) >= MAX_ITERATIONS
        or not assessments[-1]["material_improvement"] and not assessments[-2]["material_improvement"]
    )


def assess_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare each trial with the last accepted champion, not a rejected trial."""
    if not history or int(history[0]["iteration"]) != 0:
        raise ValueError("measurements need a baseline iteration 0")
    champion = history[0]
    results = []
    for index in range(1, len(history)):
        trial = history[index]
        if int(trial["iteration"]) != int(history[index - 1]["iteration"]) + 1:
            raise ValueError("iterations must be consecutive")
        comparable = dict(trial, iteration=int(champion["iteration"]) + 1)
        result = assess(champion, comparable)
        result["champion_iteration"] = champion["iteration"]
        results.append(result)
        if result["material_improvement"]:
            champion = trial
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.measurements.read_text(encoding="utf-8"))
    history = document["iterations"]
    results = assess_history(history)
    print(json.dumps({"attempts": len(results), "stop": should_stop(history), "assessments": results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
