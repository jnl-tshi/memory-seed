"""Generate per-task Task Dispatches from a tranche plan's structured block.

Tranche plans stay prose for readers but carry exactly one fenced ```json block
declaring ``"schema": "memory-seed/plan-dispatch"``.  The block holds the
existing ``implementation_plan`` (validated by ``planning.validate_implementation_plan``
without changes to its schema) plus the dispatch context every task shares
(``defaults``) and one objective per task (``objectives``).  The generator is
pure: it reads the plan, emits dispatches in plan order, and never compiles,
dispatches workers, or writes files (task-packet-handoff-integration-plan.md, T2).
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .core import resolve_runtime
from .planning import PlanningValidationError, parse_delivery_quality, validate_implementation_plan
from .task_packet import TASK_DISPATCH_SCHEMA, TASK_DISPATCH_VERSION, TaskPacketValidationError, normalize_task_dispatch

PLAN_DISPATCH_SCHEMA = "memory-seed/plan-dispatch"
PLAN_DISPATCH_VERSION = 1
PLAN_DISPATCHES_SCHEMA = "memory-seed/plan-dispatches"
PLAN_DISPATCHES_VERSION = 1

_BLOCK_RE = re.compile(r"^```json[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_DECISION_REF_RE = re.compile(r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z")
_BLOCK_KEYS = frozenset({"schema", "version", "defaults", "objectives", "implementation_plan"})
_DEFAULT_KEYS = frozenset(
    {"project_context", "execution", "retrieval", "budget", "constitution_refs", "packet_version", "memory_update_policy"}
)
_DEFAULT_EXECUTION_KEYS = frozenset({"role", "persona", "capability_tier", "forbidden_files", "output_contract"})


def _fail(path: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
    raise TaskPacketValidationError("invalid_plan", message, path=path, stage="plan", details=details)


def extract_plan_block(markdown: str) -> dict[str, Any]:
    """Return the single plan-dispatch JSON block, refusing zero or several."""
    blocks = []
    for match in _BLOCK_RE.finditer(markdown):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("schema") == PLAN_DISPATCH_SCHEMA:
            blocks.append(payload)
    if len(blocks) != 1:
        _fail("$", f"plan must contain exactly one ```json block with schema {PLAN_DISPATCH_SCHEMA!r}",
              details={"found": len(blocks)})
    return blocks[0]


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact(value: Mapping[str, Any], path: str, allowed: frozenset[str], required: frozenset[str]) -> None:
    unknown, missing = set(value) - allowed, required - set(value)
    if unknown or missing:
        _fail(path, "has unknown or missing fields", details={"unknown": sorted(unknown), "missing": sorted(missing)})


def _plan_references(plan: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    """Every reference and path the plan itself declares, for the validator.

    The plan is the assessment here, so its own references define scope; the
    packet compiler still enforces evidence selection and file authority.
    """
    references = {str(plan.get("approval_reference", ""))}
    paths: set[str] = set()
    for task in plan.get("tasks") or []:
        if isinstance(task, Mapping):
            references.update(str(item) for item in task.get("evidence_references") or [])
            for edit in task.get("edit_ownership") or []:
                if isinstance(edit, Mapping):
                    paths.add(str(edit.get("path", "")))
    for exception in (plan.get("test_strategy") or {}).get("exceptions") or []:
        if isinstance(exception, Mapping):
            references.add(str(exception.get("authority_reference", "")))
            paths.update(str(item) for item in exception.get("affected_scope") or [])
    return references, paths


def plan_dispatches(markdown: str, cwd: str | Path = ".", *, source: str | None = None) -> dict[str, Any]:
    """Validate a plan block and return one normalized dispatch per task."""
    block = extract_plan_block(markdown)
    _exact(block, "$", _BLOCK_KEYS, _BLOCK_KEYS)
    if type(block["version"]) is not int or block["version"] != PLAN_DISPATCH_VERSION:
        _fail("version", f"must equal integer {PLAN_DISPATCH_VERSION}")
    defaults = _mapping(block["defaults"], "defaults")
    _exact(defaults, "defaults", _DEFAULT_KEYS, frozenset({"project_context", "execution", "retrieval", "budget"}))
    execution_defaults = _mapping(defaults["execution"], "defaults.execution")
    _exact(execution_defaults, "defaults.execution", _DEFAULT_EXECUTION_KEYS, _DEFAULT_EXECUTION_KEYS)
    objectives = _mapping(block["objectives"], "objectives")
    plan = _mapping(block["implementation_plan"], "implementation_plan")

    runtime = resolve_runtime(cwd)
    config = runtime.memory_dir / "project.yaml"
    policy = parse_delivery_quality(config.read_text(encoding="utf-8") if config.exists() else "")
    references, paths = _plan_references(plan)
    try:
        validated = validate_implementation_plan(
            plan, evidence_references=sorted(references), assessed_paths=sorted(paths), effective_policy=policy,
        )
    except PlanningValidationError as exc:
        _fail("implementation_plan", str(exc))
    assert validated is not None

    approval = validated["approval_reference"]
    if not _DECISION_REF_RE.fullmatch(approval):
        # The validator only checks the approval is among the plan's own
        # references, which the plan itself supplies; require a decision the
        # compiler can pin and prove exists.
        _fail("implementation_plan.approval_reference", "must be a canonical '<entry-id>:dN' decision reference")

    task_ids = [task["id"] for task in validated["tasks"]]
    missing = sorted(set(task_ids) - set(objectives))
    extra = sorted(set(objectives) - set(task_ids))
    if missing or extra:
        _fail("objectives", "must name exactly one objective per task", details={"missing": missing, "extra": extra})

    workspace = runtime.memory_dir.parent
    tasks = []
    for task in validated["tasks"]:
        identity = task["id"]
        objective = objectives[identity]
        if not isinstance(objective, str) or not objective.strip():
            _fail(f"objectives.{identity}", "must be nonempty text")
        edit_paths = list(dict.fromkeys(edit["path"] for edit in task["edit_ownership"]))
        implements = [ref for ref in task["evidence_references"] if _DECISION_REF_RE.fullmatch(ref)]
        retrieval = copy.deepcopy(dict(defaults["retrieval"]))
        overrides = copy.deepcopy(dict(retrieval.get("overrides") or {}))
        selectors = dict(overrides.get("selectors") or {})
        pinned = list(selectors.get("pinned") or [])
        pinned_ids = {(pin.get("kind"), pin.get("id")) for pin in pinned if isinstance(pin, Mapping)}
        for ref, reason in (
            *((ref, f"Task {identity} implements this decision.") for ref in implements),
            (approval, "The plan's approval; compiling proves it exists."),
        ):
            # A packet may only implement decisions it selects, and the
            # approval must resolve, so both are required pins.
            if ("decision", ref) not in pinned_ids:
                pinned.append({"kind": "decision", "id": ref, "reason": reason, "required": True})
                pinned_ids.add(("decision", ref))
        if pinned:
            selectors["pinned"] = pinned
            overrides["selectors"] = selectors
        retrieval["overrides"] = overrides
        dispatch: dict[str, Any] = {
            "schema": TASK_DISPATCH_SCHEMA,
            "version": TASK_DISPATCH_VERSION,
            "objective": objective,
            "constitution_refs": list(defaults.get("constitution_refs") or []),
            "project_context": copy.deepcopy(dict(defaults["project_context"])),
            "execution": {
                "role": execution_defaults["role"],
                "persona": execution_defaults["persona"],
                "capability_tier": execution_defaults["capability_tier"],
                "write_intent": "writing",
                "allowed_files": edit_paths,
                "forbidden_files": list(execution_defaults["forbidden_files"]),
                "validation": list(task["verification"]),
                "output_contract": [
                    *execution_defaults["output_contract"],
                    *(f"Acceptance: {item}" for item in task["acceptance_observables"]),
                    *(f"Stop and report NEEDS_CONTEXT if: {item}" for item in task["replan_conditions"]),
                ],
                "expected_absent": [
                    edit["path"] for edit in task["edit_ownership"]
                    if edit["line_range"] == [1, 1] and not (workspace / edit["path"]).exists()
                ],
                "acceptance_observables": [
                    {"name": f"{identity}-verification-{index}", "command": command, "expected_exit_code": 0}
                    for index, command in enumerate(task["verification"], start=1)
                ],
                "implements": implements,
            },
            "retrieval": retrieval,
            "budget": copy.deepcopy(dict(defaults["budget"])),
            "memory_update_policy": defaults.get("memory_update_policy", "orchestrator"),
            "packet_version": defaults.get("packet_version", 2),
        }
        try:
            normalized = normalize_task_dispatch(dispatch)
        except TaskPacketValidationError as exc:
            _fail(f"tasks.{identity}", f"generated dispatch is invalid: {exc.message}",
                  details={"dispatch_error": exc.to_dict()})
        tasks.append({"id": identity, "dependencies": list(task["dependencies"]), "dispatch": normalized})
    return {
        "schema": PLAN_DISPATCHES_SCHEMA,
        "version": PLAN_DISPATCHES_VERSION,
        "source": source,
        "approval_reference": validated["approval_reference"],
        "test_strategy": validated["test_strategy"],
        "tasks": tasks,
    }


def plan_dispatches_from_file(plan_file: str | Path, cwd: str | Path = ".") -> dict[str, Any]:
    path = Path(plan_file)
    if not path.is_absolute():
        # Resolve against the project, not the process: CLI and MCP servers can
        # run from different directories and must read the same plan.
        path = resolve_runtime(cwd).memory_dir.parent / path
    try:
        markdown = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail("$", f"plan file is unreadable: {exc.__class__.__name__}")
    return plan_dispatches(markdown, cwd, source=path.as_posix())
