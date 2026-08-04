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
