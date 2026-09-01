"""Mechanical scorer for one Task Packet calibration run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # Package import under pytest; direct-script fallback for the CLI.
    from .contracts import (
        GOLD_SCHEMA,
        RUN_SCHEMA,
        SCORE_SCHEMA,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
        validate_answer,
    )
except ImportError:  # pragma: no cover - exercised by live direct-script runs
    from contracts import (
        GOLD_SCHEMA,
        RUN_SCHEMA,
        SCORE_SCHEMA,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
        validate_answer,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for offset, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("response contains no JSON object")


def _available_evidence(run: dict[str, Any], packet: dict[str, Any] | None) -> set[str]:
    available: set[str] = set()
    if packet is not None:
        available.update(str(row["id"]) for row in packet.get("materialized_evidence", []))
    for call in run.get("tool_calls", []):
        available.update(str(item) for item in call.get("evidence_ids", []))
    return available


def score_run(
    run: dict[str, Any], task: dict[str, Any], gold: dict[str, Any], packet: dict[str, Any] | None
) -> dict[str, Any]:
    require_schema(run, RUN_SCHEMA)
    require_schema(gold, GOLD_SCHEMA)
    protocol_error = None
    answer = None
    try:
        answer = validate_answer(parse_json_object(run.get("response", "")), task)
    except (TypeError, ValueError) as exc:
        protocol_error = str(exc)

    expected = gold["tasks"][run["task_id"]]
    by_id = {row["proposition_id"]: row for row in answer["answers"]} if answer else {}
    available = _available_evidence(run, packet)
    rows: list[dict[str, Any]] = []
    for proposition in task["propositions"]:
        proposition_id = proposition["id"]
        actual = by_id.get(proposition_id)
        if run["arm"] == "no_memory":
            expected_verdict = "insufficient"
            allowed_evidence: set[str] = set()
        else:
            expected_row = expected["propositions"][proposition_id]
            expected_verdict = expected_row["verdict"]
            allowed_evidence = set(expected_row["evidence_ids"])
        actual_verdict = actual.get("verdict") if actual else None
        cited = set(actual.get("evidence_ids", [])) if actual else set()
        verdict_correct = actual_verdict == expected_verdict
        citation_resolves = cited <= available
        citation_supports = (
            not cited if expected_verdict == "insufficient" else bool(cited & allowed_evidence)
        )
        rows.append(
            {
                "proposition_id": proposition_id,
                "expected_verdict": expected_verdict,
                "actual_verdict": actual_verdict,
                "verdict_correct": verdict_correct,
                "citation_resolves": citation_resolves,
                "citation_supports": citation_supports,
                "correct": verdict_correct and citation_resolves and citation_supports,
            }
        )

    materialized_ids = (
        {str(row["id"]) for row in packet.get("materialized_evidence", [])}
        if packet is not None
        else set()
    )
    fetched_ids = {
        str(item)
        for call in run.get("tool_calls", [])
        for item in call.get("evidence_ids", [])
    }
    stable = {
        "schema": SCORE_SCHEMA,
        "version": 1,
        "run_fingerprint": run["run_fingerprint"],
        "task_id": run["task_id"],
        "arm": run["arm"],
        "model": run["model"],
        "protocol_ok": answer is not None,
        "protocol_error": protocol_error,
        "propositions": rows,
        "correct_count": sum(1 for row in rows if row["correct"]),
        "proposition_count": len(rows),
        "complete_correct": bool(rows) and all(row["correct"] for row in rows),
        "tool_call_count": run.get("tool_call_count", 0),
        "repeated_materialized_fetch": bool(materialized_ids & fetched_ids),
        "usage": run.get("usage"),
        "wall_seconds": run.get("wall_seconds"),
    }
    return {**stable, "score_fingerprint": fingerprint(stable)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    run = load_json(args.run)
    tasks = load_json(args.tasks)
    task = next(row for row in tasks["tasks"] if row["id"] == run["task_id"])
    gold = load_json(args.gold)
    packet = load_json(args.packet) if args.packet else None
    result = score_run(run, task, gold, packet)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite score: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(canonical_json({"complete_correct": result["complete_correct"], "score_fingerprint": result["score_fingerprint"]}))
    return 0 if result["complete_correct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
