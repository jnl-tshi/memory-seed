"""Frozen experiment-only contracts for ADR context derivation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


TASK_SCHEMA = "context-benchmark-task.v1"
STRATEGY_SCHEMA = "context-strategy.v1"
RUN_SCHEMA = "context-run-manifest.v1"
ANSWER_SCHEMA = "context-answer.v1"
SCHEDULE_SEED = 20260804
TASK_COUNT = 12
REPETITIONS = 3
ARMS = (
    "search-mcp",
    "retrieval-v1-packet",
    "adr-candidate-packet",
    "adr-mcp-workflow",
)
AGENTS = ("claude", "codex")
EXPECTED_SUBJECT_RUNS = TASK_COUNT * len(ARMS) * REPETITIONS * len(AGENTS)
MAX_AGENT_CONCURRENCY = 3
MAX_TOTAL_CONCURRENCY = 6
LIVE_MATRIX_SCHEMA = "context-live-matrix.v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any, *, prefix: str = "sha256") -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_schema(value: Mapping[str, Any], expected: str) -> None:
    actual = value.get("schema")
    if actual != expected:
        raise ValueError(f"schema must be {expected!r}, got {actual!r}")


def answer_template() -> dict[str, Any]:
    return {
        "schema": ANSWER_SCHEMA,
        "adr_ids": [],
        "authoritative_refs": [],
        "adr_statuses": {},
        "lineage_edges": [],
        "related_edges": [],
        "citations": [],
        "explanation": "",
        "insufficient_evidence": False,
        "missing_refs": [],
    }


_ADR_STATUSES = frozenset({"accepted", "proposed", "rejected", "superseded", "empty"})


def validate_answer(value: Any) -> dict[str, Any]:
    """Validate the exact context-answer.v1 wire contract without optional deps."""
    if not isinstance(value, dict) or set(value) != set(answer_template()):
        raise ValueError("answer must contain exactly the context-answer.v1 keys")
    require_schema(value, ANSWER_SCHEMA)
    for key in ("adr_ids", "authoritative_refs", "citations", "missing_refs"):
        items = value[key]
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{key} must be an array of strings")
        if len(items) != len(set(items)):
            raise ValueError(f"{key} must be unique")
    statuses = value["adr_statuses"]
    if not isinstance(statuses, dict) or not all(
        isinstance(key, str) and isinstance(status, str) and status in _ADR_STATUSES
        for key, status in statuses.items()
    ):
        raise ValueError("adr_statuses must map IDs to known statuses")
    for key, types in (("lineage_edges", {"evolves", "replaces"}), ("related_edges", {"related"})):
        edges = value[key]
        if not isinstance(edges, list):
            raise ValueError(f"{key} must be an array")
        seen: set[tuple[str, str, str]] = set()
        for edge in edges:
            if not isinstance(edge, dict) or set(edge) != {"source", "target", "type"}:
                raise ValueError(f"{key} has malformed edge")
            encoded = (edge.get("source"), edge.get("target"), edge.get("type"))
            if not all(isinstance(item, str) for item in encoded) or encoded[2] not in types:
                raise ValueError(f"{key} has invalid edge")
            if encoded in seen:
                raise ValueError(f"{key} must be unique")
            seen.add(encoded)
    if not isinstance(value["explanation"], str) or not isinstance(value["insufficient_evidence"], bool):
        raise ValueError("explanation and insufficient_evidence have invalid types")
    return value


def execution_approved(experiment_root: str | Path) -> bool:
    """Require both owner-reviewed artifacts; a CLI flag alone cannot unfreeze scoring."""
    root = Path(experiment_root)
    preregistration = root / "PREREGISTRATION.md"
    gold_path = root / "tasks" / "gold.json"
    if not preregistration.exists() or not gold_path.exists():
        return False
    preregistered = "Status: **APPROVED**" in preregistration.read_text(encoding="utf-8")
    try:
        gold = load_json(gold_path)
    except (OSError, json.JSONDecodeError):
        return False
    return preregistered and gold.get("approval_status") == "APPROVED"


def live_execution_approved(experiment_root: str | Path) -> bool:
    """Require frozen candidate and pinned live matrix in addition to gold approval."""
    root = Path(experiment_root)
    if not execution_approved(root):
        return False
    try:
        candidate = load_json(root / "FROZEN_CANDIDATE.json")
        matrix = load_json(root / "LIVE_MATRIX.json")
    except (OSError, json.JSONDecodeError):
        return False
    expected = {
        "task_count": TASK_COUNT,
        "arms": list(ARMS),
        "repetitions": REPETITIONS,
        "agents": list(AGENTS),
        "subject_runs": EXPECTED_SUBJECT_RUNS,
        "schedule_seed": SCHEDULE_SEED,
        "max_agent_concurrency": MAX_AGENT_CONCURRENCY,
        "max_total_concurrency": MAX_TOTAL_CONCURRENCY,
    }
    if candidate.get("schema") != "context-candidate-manifest.v1" or not candidate.get("strategy_fingerprint"):
        return False
    if matrix.get("schema") != LIVE_MATRIX_SCHEMA or matrix.get("status") != "FROZEN":
        return False
    if any(matrix.get(key) != value for key, value in expected.items()):
        return False
    pins = matrix.get("pins") or {}
    return all(
        isinstance(pins.get(agent), dict)
        and pins[agent].get("model") not in (None, "", "PENDING_UNSCORED_PROBE")
        and pins[agent].get("cli_version") not in (None, "", "PENDING_UNSCORED_PROBE")
        for agent in AGENTS
    ) and matrix.get("candidate_fingerprint") == candidate.get("strategy_fingerprint") \
        and isinstance(matrix.get("retrieval_v1_fingerprint"), str) \
        and bool(matrix.get("retrieval_v1_fingerprint")) \
        and isinstance(matrix.get("live_tasks_fingerprint"), str) \
        and bool(matrix.get("live_tasks_fingerprint"))


def live_pin_matches(experiment_root: str | Path, agent: str, model: str, cli_version: str) -> bool:
    if not live_execution_approved(experiment_root):
        return False
    matrix = load_json(Path(experiment_root) / "LIVE_MATRIX.json")
    pin = (matrix.get("pins") or {}).get(agent) or {}
    return pin.get("model") == model and pin.get("cli_version") == cli_version


def live_tasks_match(experiment_root: str | Path, tasks_path: str | Path) -> bool:
    if not live_execution_approved(experiment_root):
        return False
    try:
        matrix = load_json(Path(experiment_root) / "LIVE_MATRIX.json")
        tasks = load_json(tasks_path)
    except (OSError, json.JSONDecodeError):
        return False
    rows = tasks.get("tasks", [])
    expected_ids = {f"CTX-{number:02d}" for number in range(1, TASK_COUNT + 1)}
    actual_ids = {str(row.get("task_id")) for row in rows if isinstance(row, dict)}
    stable = {key: value for key, value in tasks.items() if key != "fingerprint"}
    packet_arms = {"retrieval-v1-packet", "adr-candidate-packet"}
    return (
        tasks.get("schema") == "context-live-tasks.v1"
        and len(rows) == TASK_COUNT
        and actual_ids == expected_ids
        and all(set((row.get("packets") or {}).keys()) == packet_arms for row in rows)
        and all(all(isinstance(packet, str) and packet for packet in row["packets"].values()) for row in rows)
        and tasks.get("candidate_fingerprint") == matrix.get("candidate_fingerprint")
        and tasks.get("retrieval_strategy_fingerprint") == matrix.get("retrieval_v1_fingerprint")
        and tasks.get("fingerprint") == fingerprint(stable)
        and tasks.get("fingerprint") == matrix.get("live_tasks_fingerprint")
    )
