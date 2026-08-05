"""Validate the reviewable revision-scoped Constitution benchmark draft.

This deliberately has no execution entry point: v2 is a reviewed definition
layer, not a replacement for the frozen v1 runner or an approval bypass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "tasks" / "revision_constitution_manifest.v2.json"
GOLD = ROOT / "tasks" / "revision_constitution_gold.v2.json"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return value


def load_draft() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, gold = _read(MANIFEST), _read(GOLD)
    if manifest.get("schema") != "context-benchmark-manifest.v2":
        raise ValueError("manifest schema must be context-benchmark-manifest.v2")
    if gold.get("schema") != "context-gold.v2":
        raise ValueError("gold schema must be context-gold.v2")
    if manifest.get("status") != "DRAFT-PENDING-OWNER-REVIEW" or gold.get("approval_status") != "DRAFT-PENDING-OWNER-REVIEW":
        raise ValueError("v2 definition must remain an owner-review draft")
    tasks, labels = manifest.get("tasks"), gold.get("tasks")
    if not isinstance(tasks, list) or not isinstance(labels, list) or len(tasks) != 12 or len(labels) != 12:
        raise ValueError("v2 definition must contain exactly twelve task and gold rows")
    expected = [f"CTX-{number:02d}" for number in range(1, 13)]
    if [row.get("task_id") for row in tasks] != expected or [row.get("task_id") for row in labels] != expected:
        raise ValueError("v2 task and gold IDs must be complete and ordered")
    for task, label in zip(tasks, labels):
        if task.get("schema") != "context-benchmark-task.v2" or not isinstance(task.get("question"), str):
            raise ValueError(f"{task.get('task_id')} has an invalid v2 task shape")
        bindings = label.get("required_constitution_bindings")
        if not isinstance(bindings, list):
            raise ValueError(f"{task['task_id']} must declare revision-scoped Constitution bindings")
        if task["task_id"] == "CTX-12":
            if bindings or not label.get("insufficient_evidence"):
                raise ValueError("CTX-12 is the Constitution-negative abstention control")
            continue
        if not bindings:
            raise ValueError(f"{task['task_id']} must require Constitution evidence")
        seen: set[tuple[str, str]] = set()
        for binding in bindings:
            if not isinstance(binding, Mapping):
                raise ValueError(f"{task['task_id']} has an invalid binding")
            adr_id, decision_ref, refs = binding.get("adr_id"), binding.get("decision_ref"), binding.get("constitution_refs")
            key = (str(adr_id), str(decision_ref))
            if not isinstance(adr_id, str) or not isinstance(decision_ref, str) or not isinstance(refs, list) or not refs or key in seen:
                raise ValueError(f"{task['task_id']} binding must be a unique ADR/revision pair with sections")
            seen.add(key)
    return manifest, gold
