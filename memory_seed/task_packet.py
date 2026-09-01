"""Deterministic Task Dispatch and Task Packet compilation.

This module is the core, adapter-free M2 service.  It validates a semantic
``memory-seed/task-dispatch`` v1 object, measures an already-existing Git
checkout from a separate runtime binding, expands one exact project-local
retrieval profile, resolves and validates an Evidence Pack v2, and materializes
the pack's canonical Markdown slices exactly once.

The compiler is deliberately incapable of dispatching a worker, creating a
branch/worktree, writing a packet registry, querying a provider, or enlarging
the caller's authority.  All variable environment and pricing inputs are
caller-supplied data.  No clock or other ambient machine value enters the
canonical packet identity.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence

from .core import _git_text, resolve_runtime
from .retrieval import (
    EVIDENCE_PACK_SCHEMA,
    EVIDENCE_PACK_VERSION,
    RETRIEVAL_V2_RESOLVER_VERSION,
    RetrievalSpecResolutionError,
    _source_slice,
    get_chunk,
    resolve_retrieval_spec,
    validate_evidence_pack,
)
from .retrieval_profiles import load_retrieval_profile
from .retrieval_spec import normalize_retrieval_spec_v2, retrieval_spec_fingerprint


TASK_DISPATCH_SCHEMA = "memory-seed/task-dispatch"
TASK_DISPATCH_VERSION = 1
TASK_PACKET_SCHEMA = "memory-seed/task-packet"
TASK_PACKET_VERSION = 1
TOKEN_ESTIMATOR = "utf8-bytes-ceil-div-4/v1"

TIER_BANDS: dict[str, dict[str, int]] = {
    "economy": {"target_tokens": 16_000, "soft_cap_tokens": 24_000, "shard_threshold_tokens": 32_000},
    "balanced": {"target_tokens": 32_000, "soft_cap_tokens": 48_000, "shard_threshold_tokens": 64_000},
    "frontier": {"target_tokens": 64_000, "soft_cap_tokens": 96_000, "shard_threshold_tokens": 128_000},
}

_DISPATCH_KEYS = frozenset(
    {
        "schema",
        "version",
        "objective",
        "project_context",
        "execution",
        "retrieval",
        "budget",
        "memory_update_policy",
        "memory_checkpoints",
    }
)
_PROJECT_CONTEXT_KEYS = frozenset(
    {
        "project_type_and_purpose",
        "relevant_subsystem",
        "task_fit",
        "downstream_use",
        "non_goals",
    }
)
_EXECUTION_KEYS = frozenset(
    {
        "role",
        "persona",
        "capability_tier",
        "write_intent",
        "allowed_files",
        "forbidden_files",
        "validation",
        "output_contract",
    }
)
_RETRIEVAL_KEYS = frozenset({"profile", "profile_version", "overrides"})
_BUDGET_KEYS = frozenset(
    {
        "supplemental_input_tokens",
        "output_tokens",
        "over_soft_cap",
        "over_soft_cap_reason",
    }
)
_CHECKPOINT_KEYS = frozenset(
    {"names", "session_paths", "branch_local_only", "guarded_append"}
)
_BINDING_KEYS = frozenset(
    {
        "owner",
        "agent_type",
        "base_branch",
        "base_sha",
        "working_branch",
        "worktree",
        "expected_directory",
        "integration_artifact",
    }
)
_ENVIRONMENT_KEYS = frozenset(
    {"fixed_instructions", "tool_schemas", "cached_input_tokens"}
)
_PRICING_KEYS = frozenset(
    {
        "currency",
        "effective_date",
        "per_million_input",
        "per_million_cached_input",
        "per_million_output",
        "tool_cost",
    }
)
_PROFILE_ID_RE = re.compile(r"[a-z][a-z0-9-]*\Z")
_SLUG_RE = re.compile(r"[a-z][a-z0-9_-]*\Z")
_SHA_RE = re.compile(r"[0-9a-fA-F]{40}\Z")
_EXACT_SESSION_PATH_RE = re.compile(
    r"\.memory-seed/sessions/[A-Za-z0-9._/-]+\.md\Z", re.IGNORECASE
)
_BUDGET_STATUSES = (
    "within_target",
    "elevated",
    "allowed_above_soft_cap",
    "soft_cap_exceeded",
    "shard_required",
)
_BUDGET_STATUS_WIDTH = max(len(status) for status in _BUDGET_STATUSES)


class TaskPacketValidationError(ValueError):
    """Structured, fail-closed Task Dispatch/Packet compilation error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        path: str = "$",
        stage: str = "validation",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.path = path
        self.stage = stage
        self.details = dict(details or {})
        super().__init__(f"task packet {code} at {stage} ({path}): {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "stage": self.stage,
            "details": self.details,
        }


def _fail(
    path: str,
    message: str,
    *,
    code: str = "invalid_dispatch",
    stage: str = "validation",
    details: Mapping[str, Any] | None = None,
) -> None:
    raise TaskPacketValidationError(
        code, message, path=path, stage=stage, details=details
    )


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be a mapping")
    return value


def _exact_keys(
    value: Mapping[str, Any], path: str, allowed: frozenset[str], *, required: frozenset[str]
) -> None:
    unknown = sorted(key for key in value if not isinstance(key, str) or key not in allowed)
    if unknown:
        _fail(path, "contains unknown fields", details={"unknown_fields": unknown})
    missing = sorted(required - set(value))
    if missing:
        _fail(path, "is missing required fields", details={"missing_fields": missing})


def _string(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string" + (" or null" if nullable else ""))
    return value.strip()


def _string_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        _fail(path, "must be a list")
    if nonempty and not value:
        _fail(path, "must contain at least one value")
    result: list[str] = []
    for index, item in enumerate(value):
        normalized = _string(item, f"{path}[{index}]")
        assert normalized is not None
        result.append(normalized)
    if len(set(result)) != len(result):
        _fail(path, "must not contain duplicates")
    return result


def _nonnegative_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(path, "must be a non-negative integer")
    return value


def _path_string(value: Any, path: str) -> str:
    text = _string(value, path)
    assert text is not None
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text)
    if (
        "\x00" in text
        or windows.is_absolute()
        or windows.drive
        or posix.is_absolute()
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        _fail(path, "must be a runtime-relative path without parent traversal")
    return PurePosixPath(text.replace("\\", "/")).as_posix()


def _canonical_scope_identity(value: str) -> str:
    """Compare declared path scopes using Windows separator/case semantics."""
    return PurePosixPath(value.replace("\\", "/")).as_posix().casefold()


def _scope_list(value: Any, path: str) -> list[str]:
    result = [item.replace("\\", "/") for item in _string_list(value, path)]
    identities = [_canonical_scope_identity(item) for item in result]
    if len(set(identities)) != len(identities):
        _fail(path, "must not contain separator/case aliases")
    return result


def estimate_tokens(value: str | bytes | Mapping[str, Any] | Sequence[Any]) -> int:
    """Return the shared deterministic offline estimate (UTF-8 bytes / 4)."""
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = canonical_json(value).encode("utf-8")
    return (len(payload) + 3) // 4 if payload else 0


def canonical_json(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def normalize_task_dispatch(dispatch: Mapping[str, Any]) -> dict[str, Any]:
    dispatch = _mapping(dispatch, "$")
    _exact_keys(
        dispatch,
        "$",
        _DISPATCH_KEYS,
        required=frozenset(
            {"schema", "version", "objective", "project_context", "execution", "retrieval", "budget"}
        ),
    )
    if dispatch["schema"] != TASK_DISPATCH_SCHEMA:
        _fail("schema", f"must equal {TASK_DISPATCH_SCHEMA!r}")
    if type(dispatch["version"]) is not int or dispatch["version"] != TASK_DISPATCH_VERSION:
        _fail("version", f"must equal integer {TASK_DISPATCH_VERSION}")
    objective = _string(dispatch["objective"], "objective")

    context_in = _mapping(dispatch["project_context"], "project_context")
    _exact_keys(
        context_in,
        "project_context",
        _PROJECT_CONTEXT_KEYS,
        required=_PROJECT_CONTEXT_KEYS,
    )
    context = {
        "project_type_and_purpose": _string(
            context_in["project_type_and_purpose"], "project_context.project_type_and_purpose"
        ),
        "relevant_subsystem": _string(
            context_in["relevant_subsystem"], "project_context.relevant_subsystem"
        ),
        "task_fit": _string(context_in["task_fit"], "project_context.task_fit"),
        "downstream_use": _string(
            context_in["downstream_use"], "project_context.downstream_use"
        ),
        "non_goals": _string_list(
            context_in["non_goals"], "project_context.non_goals", nonempty=True
        ),
    }
    context_text = "\n".join(
        [
            str(context["project_type_and_purpose"]),
            str(context["relevant_subsystem"]),
            str(context["task_fit"]),
            str(context["downstream_use"]),
            *context["non_goals"],
        ]
    )
    context_tokens = estimate_tokens(context_text)
    if context_tokens < 100 or context_tokens > 250:
        _fail(
            "project_context",
            "must estimate to 100-250 tokens",
            details={"estimated_tokens": context_tokens, "estimator": TOKEN_ESTIMATOR},
        )

    execution_in = _mapping(dispatch["execution"], "execution")
    _exact_keys(
        execution_in,
        "execution",
        _EXECUTION_KEYS,
        required=_EXECUTION_KEYS,
    )
    role = _string(execution_in["role"], "execution.role")
    if role not in {"worker", "validator", "researcher"}:
        _fail("execution.role", "must be 'worker', 'validator', or 'researcher'")
    persona = execution_in["persona"]
    if persona is not None:
        persona = _string(persona, "execution.persona")
        if persona == "none":
            persona = None
    tier = _string(execution_in["capability_tier"], "execution.capability_tier")
    if tier not in TIER_BANDS:
        _fail("execution.capability_tier", "must be 'economy', 'balanced', or 'frontier'")
    write_intent = _string(execution_in["write_intent"], "execution.write_intent")
    if write_intent not in {"read-only", "writing"}:
        _fail("execution.write_intent", "must be 'read-only' or 'writing'")
    allowed_files = _scope_list(execution_in["allowed_files"], "execution.allowed_files")
    forbidden_files = _scope_list(execution_in["forbidden_files"], "execution.forbidden_files")
    allowed_identities = {_canonical_scope_identity(item) for item in allowed_files}
    forbidden_identities = {_canonical_scope_identity(item) for item in forbidden_files}
    overlap = sorted(allowed_identities & forbidden_identities)
    if overlap:
        _fail(
            "execution",
            "allowed_files and forbidden_files must not overlap",
            details={"overlap": overlap},
        )
    if write_intent == "writing" and not allowed_files:
        _fail("execution.allowed_files", "writing dispatches require at least one allowed file")
    execution = {
        "role": role,
        "persona": persona,
        "capability_tier": tier,
        "write_intent": write_intent,
        "allowed_files": allowed_files,
        "forbidden_files": forbidden_files,
        "validation": _string_list(execution_in["validation"], "execution.validation"),
        "output_contract": _string_list(
            execution_in["output_contract"], "execution.output_contract", nonempty=True
        ),
    }

    retrieval_in = _mapping(dispatch["retrieval"], "retrieval")
    _exact_keys(
        retrieval_in,
        "retrieval",
        _RETRIEVAL_KEYS,
        required=frozenset({"profile", "profile_version"}),
    )
    profile_id = _string(retrieval_in["profile"], "retrieval.profile")
    assert profile_id is not None
    if _PROFILE_ID_RE.fullmatch(profile_id) is None:
        _fail("retrieval.profile", "must be a canonical lowercase profile id")
    profile_version = retrieval_in["profile_version"]
    if type(profile_version) is not int or profile_version < 1:
        _fail("retrieval.profile_version", "must be a positive integer")
    overrides_in = retrieval_in.get("overrides", {})
    overrides = copy.deepcopy(dict(_mapping(overrides_in, "retrieval.overrides")))
    retrieval = {
        "profile": profile_id,
        "profile_version": profile_version,
        "overrides": overrides,
    }

    budget_in = _mapping(dispatch["budget"], "budget")
    _exact_keys(
        budget_in,
        "budget",
        _BUDGET_KEYS,
        required=frozenset({"supplemental_input_tokens", "output_tokens", "over_soft_cap"}),
    )
    over_soft_cap = _string(budget_in["over_soft_cap"], "budget.over_soft_cap")
    if over_soft_cap not in {"fail", "allow"}:
        _fail("budget.over_soft_cap", "must be 'fail' or 'allow'")
    reason = _string(
        budget_in.get("over_soft_cap_reason"),
        "budget.over_soft_cap_reason",
        nullable=True,
    )
    if over_soft_cap == "allow" and reason is None:
        _fail(
            "budget.over_soft_cap_reason",
            "must be non-empty when over_soft_cap is 'allow'",
        )
    if over_soft_cap == "fail" and reason is not None:
        _fail(
            "budget.over_soft_cap_reason",
            "must be null or omitted when over_soft_cap is 'fail'",
        )
    budget = {
        "supplemental_input_tokens": _nonnegative_int(
            budget_in["supplemental_input_tokens"], "budget.supplemental_input_tokens"
        ),
        "output_tokens": _nonnegative_int(budget_in["output_tokens"], "budget.output_tokens"),
        "over_soft_cap": over_soft_cap,
        "over_soft_cap_reason": reason,
    }

    memory_policy = dispatch.get("memory_update_policy", "orchestrator")
    memory_policy = _string(memory_policy, "memory_update_policy")
    if memory_policy not in {"orchestrator", "worker_checkpoint"}:
        _fail("memory_update_policy", "must be 'orchestrator' or 'worker_checkpoint'")
    checkpoint_in = dispatch.get("memory_checkpoints")
    checkpoints: dict[str, Any] | None = None
    if memory_policy == "orchestrator":
        if checkpoint_in is not None:
            _fail("memory_checkpoints", "is allowed only for worker_checkpoint policy")
    else:
        if write_intent != "writing":
            _fail(
                "memory_update_policy",
                "worker_checkpoint requires writing intent",
            )
        checkpoint_map = _mapping(checkpoint_in, "memory_checkpoints")
        _exact_keys(
            checkpoint_map,
            "memory_checkpoints",
            _CHECKPOINT_KEYS,
            required=_CHECKPOINT_KEYS,
        )
        session_paths = [
            _path_string(item, f"memory_checkpoints.session_paths[{index}]")
            for index, item in enumerate(
                _string_list(
                    checkpoint_map["session_paths"],
                    "memory_checkpoints.session_paths",
                    nonempty=True,
                )
            )
        ]
        if not all(_EXACT_SESSION_PATH_RE.fullmatch(path) for path in session_paths):
            _fail(
                "memory_checkpoints.session_paths",
                "must name exact .memory-seed/sessions/*.md files without wildcard or pathspec metacharacters",
            )
        session_identities = {
            _canonical_scope_identity(path) for path in session_paths
        }
        if len(session_identities) != len(session_paths):
            _fail(
                "memory_checkpoints.session_paths",
                "must not contain separator/case aliases",
            )
        missing_authority = sorted(session_identities - allowed_identities)
        if missing_authority:
            _fail(
                "memory_checkpoints.session_paths",
                "must also be named exactly in execution.allowed_files",
                details={"missing_allowed_files": missing_authority},
            )
        if checkpoint_map["branch_local_only"] is not True:
            _fail("memory_checkpoints.branch_local_only", "must be true")
        if checkpoint_map["guarded_append"] is not True:
            _fail("memory_checkpoints.guarded_append", "must be true")
        checkpoints = {
            "names": _string_list(
                checkpoint_map["names"], "memory_checkpoints.names", nonempty=True
            ),
            "session_paths": session_paths,
            "branch_local_only": True,
            "guarded_append": True,
        }

    return {
        "schema": TASK_DISPATCH_SCHEMA,
        "version": TASK_DISPATCH_VERSION,
        "objective": objective,
        "project_context": context,
        "execution": execution,
        "retrieval": retrieval,
        "budget": budget,
        "memory_update_policy": memory_policy,
        "memory_checkpoints": checkpoints,
    }


def canonical_task_dispatch_json(dispatch: Mapping[str, Any]) -> str:
    return canonical_json(normalize_task_dispatch(dispatch))


def task_dispatch_fingerprint(dispatch: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_task_dispatch_json(dispatch).encode("utf-8")
    ).hexdigest()


def _git_required(root: Path, args: Sequence[str], *, label: str) -> str:
    code, value = _git_text(root, tuple(args))
    if code != 0 or not value:
        _fail(
            "runtime_binding",
            f"could not measure {label}",
            code="invalid_binding",
            stage="binding",
            details={"git_args": list(args)},
        )
    return value


def normalize_runtime_binding(
    binding: Mapping[str, Any],
    *,
    write_intent: str,
    cwd: str | Path = ".",
) -> dict[str, Any]:
    binding = _mapping(binding, "runtime_binding")
    _exact_keys(
        binding,
        "runtime_binding",
        _BINDING_KEYS,
        required=frozenset(
            {"owner", "agent_type", "base_branch", "base_sha", "expected_directory", "integration_artifact"}
        ),
    )
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root.resolve()
    measured_root = Path(
        _git_required(root, ("rev-parse", "--show-toplevel"), label="worktree root")
    ).resolve()
    if measured_root != root:
        _fail(
            "runtime_binding.expected_directory",
            "active runtime does not match Git's measured worktree root",
            code="invalid_binding",
            stage="binding",
        )
    expected_directory_raw = Path(
        str(_string(binding["expected_directory"], "runtime_binding.expected_directory"))
    )
    if not expected_directory_raw.is_absolute():
        _fail(
            "runtime_binding.expected_directory",
            "must be an absolute measured path",
            code="invalid_binding",
            stage="binding",
        )
    expected_directory = expected_directory_raw.resolve()
    if expected_directory != measured_root:
        _fail(
            "runtime_binding.expected_directory",
            "does not match the measured worktree root",
            code="binding_mismatch",
            stage="binding",
            details={"expected": str(expected_directory), "measured": str(measured_root)},
        )
    base_branch = _string(binding["base_branch"], "runtime_binding.base_branch")
    base_sha = _string(binding["base_sha"], "runtime_binding.base_sha")
    assert base_branch is not None and base_sha is not None
    if _SHA_RE.fullmatch(base_sha) is None:
        _fail(
            "runtime_binding.base_sha",
            "must be a full 40-character Git SHA",
            code="invalid_binding",
            stage="binding",
        )
    base_code, measured_base = _git_text(
        root,
        ("show-ref", "--verify", "--hash", f"refs/heads/{base_branch}"),
    )
    if base_code != 0 or not measured_base:
        _fail(
            "runtime_binding.base_branch",
            "must name an existing local branch exactly",
            code="invalid_binding",
            stage="binding",
        )
    measured_base = measured_base.lower()
    if measured_base != base_sha.lower():
        _fail(
            "runtime_binding.base_sha",
            "does not match the supplied base branch",
            code="binding_mismatch",
            stage="binding",
            details={"supplied": base_sha.lower(), "measured": measured_base},
        )
    head_sha = _git_required(root, ("rev-parse", "HEAD"), label="HEAD SHA").lower()
    measured_branch = _git_required(
        root, ("rev-parse", "--abbrev-ref", "HEAD"), label="working branch"
    )
    working_branch_in = binding.get("working_branch")
    worktree_in = binding.get("worktree")
    if write_intent == "writing":
        working_branch = _string(
            working_branch_in, "runtime_binding.working_branch"
        )
        worktree_raw = Path(str(_string(worktree_in, "runtime_binding.worktree")))
        if not worktree_raw.is_absolute():
            _fail(
                "runtime_binding.worktree",
                "must be an absolute measured path",
                code="invalid_binding",
                stage="binding",
            )
        worktree = worktree_raw.resolve()
        if measured_branch == "HEAD" or working_branch != measured_branch:
            _fail(
                "runtime_binding.working_branch",
                "does not match the measured non-detached branch",
                code="binding_mismatch",
                stage="binding",
                details={"supplied": working_branch, "measured": measured_branch},
            )
        if worktree != measured_root:
            _fail(
                "runtime_binding.worktree",
                "does not match the measured worktree root",
                code="binding_mismatch",
                stage="binding",
                details={"supplied": str(worktree), "measured": str(measured_root)},
            )
        code, _ = _git_text(root, ("merge-base", "--is-ancestor", base_sha, head_sha))
        if code != 0:
            _fail(
                "runtime_binding.base_sha",
                "must be an ancestor of the current writing checkout",
                code="binding_mismatch",
                stage="binding",
            )
    else:
        if working_branch_in is not None and _string(
            working_branch_in, "runtime_binding.working_branch"
        ) != measured_branch:
            _fail(
                "runtime_binding.working_branch",
                "does not match the measured current-tree branch",
                code="binding_mismatch",
                stage="binding",
            )
        if worktree_in is not None and Path(
            str(_string(worktree_in, "runtime_binding.worktree"))
        ).resolve() != measured_root:
            _fail(
                "runtime_binding.worktree",
                "does not match the measured current-tree root",
                code="binding_mismatch",
                stage="binding",
            )
        working_branch = None if measured_branch == "HEAD" else measured_branch
        worktree = measured_root

    integration_artifact = _string(
        binding["integration_artifact"], "runtime_binding.integration_artifact"
    )
    if integration_artifact not in {"pr", "merge-request", "patch", "branch", "handoff"}:
        _fail(
            "runtime_binding.integration_artifact",
            "must be 'pr', 'merge-request', 'patch', 'branch', or 'handoff'",
            code="invalid_binding",
            stage="binding",
        )
    owner = _string(binding["owner"], "runtime_binding.owner")
    agent_type = _string(binding["agent_type"], "runtime_binding.agent_type")
    assert owner is not None and agent_type is not None
    if _SLUG_RE.fullmatch(owner) is None:
        _fail(
            "runtime_binding.owner",
            "must be a lowercase identity slug",
            code="invalid_binding",
            stage="binding",
        )
    if _SLUG_RE.fullmatch(agent_type) is None:
        _fail(
            "runtime_binding.agent_type",
            "must be a lowercase identity slug",
            code="invalid_binding",
            stage="binding",
        )
    return {
        "owner": owner,
        "agent_type": agent_type,
        "base_branch": base_branch,
        "base_sha": base_sha.lower(),
        "working_branch": working_branch,
        "worktree": str(worktree),
        "expected_directory": str(expected_directory),
        "integration_artifact": integration_artifact,
    }


def normalize_environment(environment: Mapping[str, Any] | None) -> dict[str, Any]:
    if environment is None:
        environment = {}
    environment = _mapping(environment, "environment")
    _exact_keys(environment, "environment", _ENVIRONMENT_KEYS, required=frozenset())
    instructions = _string_list(
        environment.get("fixed_instructions", []), "environment.fixed_instructions"
    )
    tool_schemas = environment.get("tool_schemas", [])
    if not isinstance(tool_schemas, list) or not all(isinstance(item, Mapping) for item in tool_schemas):
        _fail("environment.tool_schemas", "must be a list of schema mappings")
    try:
        canonical_json(tool_schemas)
    except (TypeError, ValueError) as exc:
        _fail("environment.tool_schemas", "must contain canonical JSON values")
    cached = environment.get("cached_input_tokens")
    if cached is not None:
        cached = _nonnegative_int(cached, "environment.cached_input_tokens")
    return {
        "fixed_instructions": instructions,
        "tool_schemas": copy.deepcopy([dict(item) for item in tool_schemas]),
        "cached_input_tokens": cached,
    }


def normalize_pricing(pricing: Mapping[str, Any]) -> dict[str, Any]:
    pricing = _mapping(pricing, "pricing")
    _exact_keys(pricing, "pricing", _PRICING_KEYS, required=_PRICING_KEYS)
    currency = _string(pricing["currency"], "pricing.currency")
    effective_date = _string(pricing["effective_date"], "pricing.effective_date")
    try:
        date.fromisoformat(str(effective_date))
    except ValueError:
        _fail("pricing.effective_date", "must be an ISO-8601 calendar date")

    def amount(name: str, *, positive: bool = False) -> Decimal:
        value = pricing[name]
        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            _fail(f"pricing.{name}", "must be a finite non-negative number")
        try:
            parsed = Decimal(str(value))
        except InvalidOperation:
            _fail(f"pricing.{name}", "must be a finite non-negative number")
        if not parsed.is_finite() or parsed < 0 or (positive and parsed == 0):
            _fail(
                f"pricing.{name}",
                "must be a finite positive number" if positive else "must be a finite non-negative number",
            )
        return parsed

    values = {
        "per_million_input": amount("per_million_input", positive=True),
        "per_million_cached_input": amount("per_million_cached_input"),
        "per_million_output": amount("per_million_output"),
        "tool_cost": amount("tool_cost"),
    }
    converted = {name: float(value) for name, value in values.items()}
    if not all(math.isfinite(value) for value in converted.values()):
        _fail("pricing", "numeric values must fit finite JSON numbers")
    return {
        "currency": currency,
        "effective_date": effective_date,
        **converted,
    }


def assess_context_budget(
    tier: str,
    *,
    serialized_packet_tokens: int,
    fixed_instruction_tokens: int,
    tool_schema_tokens: int,
    supplemental_input_tokens: int,
    output_tokens: int,
    over_soft_cap: str,
    over_soft_cap_reason: str | None,
    _enforce: bool = True,
) -> dict[str, Any]:
    if tier not in TIER_BANDS:
        _fail("execution.capability_tier", "is unsupported", code="invalid_budget", stage="budget")
    components = {
        "serialized_packet_input_tokens": serialized_packet_tokens,
        "fixed_instruction_tokens": fixed_instruction_tokens,
        "tool_schema_input_tokens": tool_schema_tokens,
        "supplemental_input_reserve_tokens": supplemental_input_tokens,
        "output_reasoning_reserve_tokens": output_tokens,
    }
    for name, value in components.items():
        _nonnegative_int(value, f"input_ledger.{name}")
    total_input = (
        serialized_packet_tokens
        + fixed_instruction_tokens
        + tool_schema_tokens
        + supplemental_input_tokens
    )
    total = total_input + output_tokens
    band = dict(TIER_BANDS[tier])
    if total >= band["shard_threshold_tokens"]:
        status = "shard_required"
    elif total <= band["target_tokens"]:
        status = "within_target"
    elif total <= band["soft_cap_tokens"]:
        status = "elevated"
    else:
        if (
            over_soft_cap != "allow"
            or not isinstance(over_soft_cap_reason, str)
            or not over_soft_cap_reason.strip()
        ):
            status = "soft_cap_exceeded"
        else:
            status = "allowed_above_soft_cap"
    if _enforce and status == "shard_required":
        _fail(
            "budget",
            "context envelope meets or exceeds the tier shard threshold",
            code="shard_required",
            stage="budget",
            details={"total_context_tokens": total, **band},
        )
    if _enforce and status == "soft_cap_exceeded":
        _fail(
            "budget",
            "context envelope exceeds the soft cap without an explicit reasoned override",
            code="soft_cap_exceeded",
            stage="budget",
            details={"total_context_tokens": total, **band},
        )
    return {
        "estimator": TOKEN_ESTIMATOR,
        "tier": tier,
        "band": band,
        **components,
        "total_input_tokens": total_input,
        "total_context_envelope_tokens": total,
        "status": status,
        # The status strings have different lengths.  A fixed-width companion
        # keeps their combined serialized footprint constant so classifying an
        # exact boundary cannot change the boundary it just classified.
        "status_padding": " " * (_BUDGET_STATUS_WIDTH - len(status)),
        "soft_cap_override": {
            "mode": over_soft_cap,
            "reason": over_soft_cap_reason,
        },
    }


def calculate_cost_ledger(
    *,
    input_tokens: int,
    output_tokens: int,
    pricing: Mapping[str, Any] | None,
    cached_input_tokens: int | None = None,
    _validate_cached_input: bool = True,
) -> dict[str, Any]:
    _nonnegative_int(input_tokens, "cost.input_tokens")
    _nonnegative_int(output_tokens, "cost.output_tokens")
    if cached_input_tokens is not None:
        _nonnegative_int(cached_input_tokens, "cost.cached_input_tokens")
        if _validate_cached_input and cached_input_tokens > input_tokens:
            _fail(
                "cost.cached_input_tokens",
                "cannot exceed total input tokens",
                code="invalid_pricing",
                stage="cost",
            )
    if pricing is None:
        return {
            "status": "unavailable",
            "reason": "pricing_not_supplied",
            "currency": None,
            "effective_date": None,
            "uncached_ceiling": None,
            "expected_cost": None,
            "output_input_ratio": None,
            "input_equivalent_tokens": None,
            "cached_input_tokens": cached_input_tokens,
        }
    normalized = normalize_pricing(pricing)
    in_rate = Decimal(str(normalized["per_million_input"]))
    cached_rate = Decimal(str(normalized["per_million_cached_input"]))
    out_rate = Decimal(str(normalized["per_million_output"]))
    tool_cost = Decimal(str(normalized["tool_cost"]))
    million = Decimal(1_000_000)
    input_count = Decimal(input_tokens)
    output_count = Decimal(output_tokens)
    uncached = input_count * in_rate / million + output_count * out_rate / million + tool_cost
    expected: Decimal | None = None
    if cached_input_tokens is not None:
        cached_count = Decimal(cached_input_tokens)
        expected = (
            (input_count - cached_count) * in_rate / million
            + cached_count * cached_rate / million
            + output_count * out_rate / million
            + tool_cost
        )
    ratio = out_rate / in_rate
    input_equivalent = input_count + output_count * ratio + tool_cost * million / in_rate

    def number(value: Decimal | None) -> float | None:
        return None if value is None else float(value.quantize(Decimal("0.000000000001")))

    return {
        "status": "available",
        "reason": None,
        "currency": normalized["currency"],
        "effective_date": normalized["effective_date"],
        "pricing": normalized,
        "uncached_ceiling": number(uncached),
        "expected_cost": number(expected),
        "output_input_ratio": number(ratio),
        "input_equivalent_tokens": number(input_equivalent),
        "cached_input_tokens": cached_input_tokens,
    }


def materialize_evidence_pack(
    pack: Mapping[str, Any], cwd: str | Path = "."
) -> list[dict[str, Any]]:
    """Validate a current Evidence Pack, then read and re-digest exact slices."""
    validate_evidence_pack(pack, cwd)
    root = Path(resolve_runtime(cwd).workspace_root).resolve()
    materialized: list[dict[str, Any]] = []
    for item in pack["evidence"]:
        if item.get("chunk_id"):
            content = str(get_chunk(str(item["chunk_id"]), root).get("text", ""))
        else:
            source_path = (root / str(item["source"])).resolve()
            try:
                source_path.relative_to(root)
            except ValueError:
                _fail(
                    "evidence.source",
                    "resolved outside the runtime",
                    code="unfetchable_evidence",
                    stage="materialization",
                )
            content = _source_slice(source_path, item["line_range"])
        digest = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != item["content_digest"]:
            _fail(
                "evidence.content_digest",
                "canonical evidence changed during materialization",
                code="content_digest_mismatch",
                stage="materialization",
                details={"id": item["id"]},
            )
        materialized.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "source": item["source"],
                "line_range": list(item["line_range"]),
                "content_digest": digest,
                "selection_reasons": {
                    "source": list(item.get("reasons", [])),
                    "model": list(item.get("model_selection_reasons", [])),
                },
                "content": content,
            }
        )
    return materialized


def _execution_defaults(dispatch: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    writing = dispatch["execution"]["write_intent"] == "writing"
    preflight = [
        "pwd",
        "git rev-parse --show-toplevel",
        "git rev-parse HEAD",
        "git status --short",
    ]
    if writing:
        preflight.insert(
            0,
            f"memory-seed worktree guard --agent {binding['agent_type']} --write-intent",
        )
    return {
        "safety": {
            # Execution/write authority only. Retrieval scope is governed by
            # the Retrieval Specification and resolver's runtime-local bounds;
            # allowed_files/forbidden_files do not filter memory reads.
            "authority": "execution_write_dispatch_and_binding_intersection",
            "network": "not_authorized",
            "worker_dispatch": "not_performed",
            "worktree_creation": "forbidden",
            "packet_registry_write": "forbidden",
            "shared_file_policy": (
                "guarded_worker_checkpoint"
                if dispatch["memory_update_policy"] == "worker_checkpoint"
                else "orchestrator_only"
            ),
        },
        "preflight": preflight,
        "handoff": [
            "status",
            "summary",
            "files_changed",
            "commit_range_and_hashes",
            "validation_results",
            "known_risks_or_conflicts",
            "supplemental_context_debits",
        ],
        "conflict_escalation": [
            "authority_or_scope_conflict",
            "required_evidence_gap",
            "base_or_worktree_mismatch",
            "validation_failure_not_owned_by_dispatch",
        ],
        "review": {
            "current_iteration": 0,
            "max_iterations": 2,
            "escalation": "orchestrator",
        },
    }


def _packet_fingerprint(packet: Mapping[str, Any]) -> str:
    identity = copy.deepcopy(dict(packet))
    identity.pop("fingerprint", None)
    return "sha256:" + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()


def canonical_task_packet_json(packet: Mapping[str, Any]) -> str:
    if packet.get("packet_schema") != TASK_PACKET_SCHEMA or packet.get("packet_version") != TASK_PACKET_VERSION:
        _fail(
            "packet",
            "unsupported Task Packet identity",
            code="invalid_packet",
            stage="serialization",
        )
    if packet.get("fingerprint") != _packet_fingerprint(packet):
        _fail(
            "packet.fingerprint",
            "does not match the canonical packet",
            code="fingerprint_mismatch",
            stage="serialization",
        )
    return canonical_json(packet)


def compile_task_packet(
    dispatch: Mapping[str, Any],
    binding: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    environment: Mapping[str, Any] | None = None,
    pricing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one deterministic, fully materialized Task Packet v1."""
    normalized_dispatch = normalize_task_dispatch(dispatch)
    normalized_binding = normalize_runtime_binding(
        binding,
        write_intent=normalized_dispatch["execution"]["write_intent"],
        cwd=cwd,
    )
    normalized_environment = normalize_environment(environment)

    retrieval = normalized_dispatch["retrieval"]
    effective_spec = load_retrieval_profile(
        retrieval["profile"],
        retrieval["profile_version"],
        cwd,
        overrides=retrieval["overrides"],
    )
    if not (
        effective_spec["selectors"]["pinned"]
        or effective_spec["filters"]["topics"]
        or effective_spec["filters"]["paths"]
    ):
        _fail(
            "retrieval",
            "effective retrieval must contain at least one pinned ID, topic, or path selector",
            code="empty_retrieval_scope",
            stage="profile_expansion",
        )
    # Manifest content must never duplicate the separately materialized slices.
    effective_spec = copy.deepcopy(effective_spec)
    effective_spec["output"]["include_excerpts"] = False
    effective_spec = normalize_retrieval_spec_v2(effective_spec)
    evidence_pack = resolve_retrieval_spec(effective_spec, cwd)
    if (
        evidence_pack["pack_schema"] != EVIDENCE_PACK_SCHEMA
        or evidence_pack["pack_version"] != EVIDENCE_PACK_VERSION
        or evidence_pack["resolver_version"] != RETRIEVAL_V2_RESOLVER_VERSION
    ):
        _fail(
            "evidence_pack",
            "compiler requires Evidence Pack v2 from the v2 resolver",
            code="invalid_evidence_pack",
            stage="resolution",
        )
    materialized = materialize_evidence_pack(evidence_pack, cwd)
    if any(item.get("excerpt") is not None for item in evidence_pack["evidence"]):
        _fail(
            "evidence_pack.evidence",
            "compiled manifests must disable excerpts",
            code="duplicate_evidence_content",
            stage="materialization",
        )

    fixed_tokens = estimate_tokens("\n".join(normalized_environment["fixed_instructions"]))
    tool_tokens = estimate_tokens(normalized_environment["tool_schemas"])
    budget = normalized_dispatch["budget"]
    packet: dict[str, Any] = {
        "packet_schema": TASK_PACKET_SCHEMA,
        "packet_version": TASK_PACKET_VERSION,
        "dispatch": normalized_dispatch,
        "dispatch_fingerprint": task_dispatch_fingerprint(dispatch),
        "runtime_binding": normalized_binding,
        "retrieval_profile": {
            "id": retrieval["profile"],
            "profile_version": retrieval["profile_version"],
            "effective_spec": effective_spec,
            "effective_spec_fingerprint": retrieval_spec_fingerprint(effective_spec),
        },
        "evidence_pack": evidence_pack,
        "materialized_evidence": materialized,
        "execution_defaults": _execution_defaults(normalized_dispatch, normalized_binding),
        "input_ledger": {},
        "cost_ledger": {},
        "fingerprint": "sha256:" + "0" * 64,
    }

    # The serialized packet is itself worker input.  Its ledger and cost record
    # affect that size, so converge on the stable integer estimate.  The final
    # fingerprint has the same byte length as the placeholder.
    for _ in range(20):
        serialized_tokens = estimate_tokens(canonical_json(packet))
        ledger = assess_context_budget(
            normalized_dispatch["execution"]["capability_tier"],
            serialized_packet_tokens=serialized_tokens,
            fixed_instruction_tokens=fixed_tokens,
            tool_schema_tokens=tool_tokens,
            supplemental_input_tokens=budget["supplemental_input_tokens"],
            output_tokens=budget["output_tokens"],
            over_soft_cap=budget["over_soft_cap"],
            over_soft_cap_reason=budget["over_soft_cap_reason"],
            _enforce=False,
        )
        packet["input_ledger"] = ledger
        packet["cost_ledger"] = calculate_cost_ledger(
            input_tokens=ledger["total_input_tokens"],
            output_tokens=ledger["output_reasoning_reserve_tokens"],
            pricing=pricing,
            cached_input_tokens=normalized_environment["cached_input_tokens"],
            _validate_cached_input=False,
        )
        if estimate_tokens(canonical_json(packet)) == serialized_tokens:
            break
    else:
        _fail(
            "input_ledger",
            "serialized packet token estimate did not converge",
            code="budget_convergence_failed",
            stage="budget",
        )

    # The input total is now stable.  Validate cached input against that final
    # value, not an undersized provisional iteration.  Recalculation is byte
    # identical because the validation flag is not serialized.
    packet["cost_ledger"] = calculate_cost_ledger(
        input_tokens=packet["input_ledger"]["total_input_tokens"],
        output_tokens=packet["input_ledger"]["output_reasoning_reserve_tokens"],
        pricing=pricing,
        cached_input_tokens=normalized_environment["cached_input_tokens"],
    )
    final_status = packet["input_ledger"]["status"]
    final_total = packet["input_ledger"]["total_context_envelope_tokens"]
    final_band = packet["input_ledger"]["band"]
    if final_status == "shard_required":
        _fail(
            "budget",
            "context envelope meets or exceeds the tier shard threshold",
            code="shard_required",
            stage="budget",
            details={"total_context_tokens": final_total, **final_band},
        )
    if final_status == "soft_cap_exceeded":
        _fail(
            "budget",
            "context envelope exceeds the soft cap without an explicit reasoned override",
            code="soft_cap_exceeded",
            stage="budget",
            details={"total_context_tokens": final_total, **final_band},
        )
    packet["fingerprint"] = _packet_fingerprint(packet)
    # Fingerprint replacement is fixed-width.  Assert the reported serialization
    # count is the real final packet rather than silently accepting drift.
    actual_tokens = estimate_tokens(canonical_json(packet))
    if actual_tokens != packet["input_ledger"]["serialized_packet_input_tokens"]:
        _fail(
            "input_ledger.serialized_packet_input_tokens",
            "does not match final canonical packet bytes",
            code="budget_convergence_failed",
            stage="budget",
            details={"reported": packet["input_ledger"]["serialized_packet_input_tokens"], "actual": actual_tokens},
        )
    return packet
