"""Stable contracts for the Task Packet calibration harness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


TASKS_SCHEMA = "memory-seed/task-packet-calibration-tasks"
GOLD_SCHEMA = "memory-seed/task-packet-calibration-gold"
BUNDLE_SCHEMA = "memory-seed/task-packet-calibration-bundle"
ANSWER_SCHEMA = "memory-seed/task-packet-calibration-answer"
RUN_SCHEMA = "memory-seed/task-packet-calibration-run"
SCORE_SCHEMA = "memory-seed/task-packet-calibration-score"

ARMS = ("no_memory", "memory_tools", "compiled_packet")
VERDICTS = frozenset({"true", "false", "insufficient"})
READ_ONLY_TOOLS = frozenset(
    {"memory_search", "memory_get_chunk", "memory_adrs_list", "memory_adr_show"}
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_schema(value: Mapping[str, Any], expected: str) -> None:
    if value.get("schema") != expected:
        raise ValueError(f"schema must be {expected!r}, got {value.get('schema')!r}")


def answer_template(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": ANSWER_SCHEMA,
        "answers": [
            {"proposition_id": row["id"], "verdict": "insufficient", "evidence_ids": []}
            for row in task["propositions"]
        ],
        "missing_questions": [],
    }


def validate_answer(value: Any, task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "answers", "missing_questions"}:
        raise ValueError("answer must contain exactly schema, answers, and missing_questions")
    require_schema(value, ANSWER_SCHEMA)
    expected_ids = [row["id"] for row in task["propositions"]]
    answers = value["answers"]
    if not isinstance(answers, list) or len(answers) != len(expected_ids):
        raise ValueError("answers must contain exactly one row per proposition")
    actual_ids: list[str] = []
    for row in answers:
        if not isinstance(row, dict) or set(row) != {"proposition_id", "verdict", "evidence_ids"}:
            raise ValueError("each answer row has an invalid shape")
        if row["verdict"] not in VERDICTS:
            raise ValueError("answer verdict is invalid")
        evidence_ids = row["evidence_ids"]
        if not isinstance(evidence_ids, list) or not all(isinstance(item, str) for item in evidence_ids):
            raise ValueError("evidence_ids must be an array of strings")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        actual_ids.append(row["proposition_id"])
    if actual_ids != expected_ids:
        raise ValueError("answers must preserve proposition order")
    if not isinstance(value["missing_questions"], list) or not all(
        isinstance(item, str) for item in value["missing_questions"]
    ):
        raise ValueError("missing_questions must be an array of strings")
    return value


def task_by_id(tasks: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    require_schema(tasks, TASKS_SCHEMA)
    for task in tasks.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise ValueError(f"unknown task {task_id!r}")
