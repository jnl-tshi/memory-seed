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
CONSTITUTION_PROJECTION_TARGETS = {
    "economy": 2_000,
    "balanced": 4_000,
    "frontier": 8_000,
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
        "constitution_refs",
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
        "expected_absent",
        "acceptance_observables",
        "implements",
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
_DECISION_REF_RE = re.compile(
    r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z"
)
_CONSTITUTION_REF_RE = re.compile(r"constitution:v\d+#[a-z0-9][a-z0-9-]*\Z")
_CONSTITUTION_ANCHOR_RE = re.compile(
    r"<!--\s*constitution-ref:\s*(constitution:v\d+#[a-z0-9-]+)\s*-->"
)
_CONSTITUTION_VERSION_RE = re.compile(r"\*\*Version:\*\*\s*([0-9]+(?:\.[0-9]+)*)[^\n]*\*\*RATIFIED")
_CONSTITUTION_BINDING_RE = re.compile(
    r"`(constitution:v\d+#[a-z0-9][a-z0-9-]*)`\s*\((governing|supporting)\)"
)
_EXACT_SESSION_PATH_RE = re.compile(
    r"\.memory-seed/sessions/[A-Za-z0-9._/-]+\.md\Z", re.IGNORECASE
)
_PATH_SCOPE_METACHAR_RE = re.compile(r'[*?\[\]{}!<>:"|]')
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
    """Return one exact runtime-relative file identity.

    Dispatch edit scopes and checkpoint scopes are file authorities, not glob
    or pathspec selectors.  Normalize separators once, then reject every form
    that could escape the measured runtime or alias another Windows path.
    """
    text = _string(value, path)
    assert text is not None
    normalized = text.replace("\\", "/")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(normalized)
    segments = normalized.split("/")
    if (
        any(ord(character) < 32 for character in text)
        or windows.is_absolute()
        or windows.drive
        or posix.is_absolute()
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        _fail(
            path,
            "must name an exact runtime-relative file without absolute, device, or parent-traversal syntax",
        )
    if _PATH_SCOPE_METACHAR_RE.search(normalized) or any(
        segment.endswith((".", " "))
        or PureWindowsPath(segment).is_reserved()
        for segment in segments
    ):
        _fail(
            path,
            "must name exact runtime-relative files without wildcard, pathspec, or Windows alias metacharacters",
        )
    return PurePosixPath(normalized).as_posix()


def _canonical_scope_identity(value: str) -> str:
    """Compare declared path scopes using Windows separator/case semantics."""
    return PurePosixPath(value.replace("\\", "/")).as_posix().casefold()


def _scope_list(value: Any, path: str) -> list[str]:
    result = [
        _path_string(item, f"{path}[{index}]")
        for index, item in enumerate(_string_list(value, path))
    ]
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
    constitution_refs = _string_list(
        dispatch.get("constitution_refs", []), "constitution_refs"
    )
    for index, reference in enumerate(constitution_refs):
        if _CONSTITUTION_REF_RE.fullmatch(reference) is None:
            _fail(
                f"constitution_refs[{index}]",
                "must use a stable 'constitution:vN#slug' anchor",
            )

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
        required=frozenset(
            {
                "role",
                "persona",
                "capability_tier",
                "write_intent",
                "allowed_files",
                "forbidden_files",
                "validation",
                "output_contract",
                "expected_absent",
                "acceptance_observables",
                "implements",
            }
        ),
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
    expected_absent = _scope_list(
        execution_in["expected_absent"], "execution.expected_absent"
    )
    expected_absent_identities = {
        _canonical_scope_identity(item) for item in expected_absent
    }
    missing_creation_authority = sorted(expected_absent_identities - allowed_identities)
    if missing_creation_authority:
        _fail(
            "execution.expected_absent",
            "must also be named exactly in execution.allowed_files",
            details={"missing_allowed_files": missing_creation_authority},
        )
    observables_in = execution_in["acceptance_observables"]
    if not isinstance(observables_in, list) or not observables_in:
        _fail(
            "execution.acceptance_observables",
            "must contain at least one directly testable observable",
        )
    observables: list[dict[str, Any]] = []
    observable_names: set[str] = set()
    for index, observable_in in enumerate(observables_in):
        observable_path = f"execution.acceptance_observables[{index}]"
        observable = _mapping(observable_in, observable_path)
        _exact_keys(
            observable,
            observable_path,
            frozenset({"name", "command", "expected_exit_code"}),
            required=frozenset({"name", "command", "expected_exit_code"}),
        )
        name = _string(observable["name"], f"{observable_path}.name")
        command = _string(observable["command"], f"{observable_path}.command")
        exit_code = _nonnegative_int(
            observable["expected_exit_code"],
            f"{observable_path}.expected_exit_code",
        )
        assert name is not None and command is not None
        if name in observable_names:
            _fail("execution.acceptance_observables", "must not contain duplicate names")
        observable_names.add(name)
        observables.append(
            {"name": name, "command": command, "expected_exit_code": exit_code}
        )
    implements = _string_list(execution_in["implements"], "execution.implements")
    for index, reference in enumerate(implements):
        if _DECISION_REF_RE.fullmatch(reference) is None:
            _fail(
                f"execution.implements[{index}]",
                "must use an exact '<entry-id>:dN' decision identity",
            )
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
        "expected_absent": expected_absent,
        "acceptance_observables": observables,
        "implements": implements,
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
        "constitution_refs": constitution_refs,
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
    component_measurements = {
        name: {
            "tokens": value,
            "percentage_of_context_envelope": (
                # Fixed-width text keeps the ledger's self-accounting bytes
                # stable while still exposing an unambiguous percentage.
                f"{(value * 100 / total if total else 0):07.3f}%"
            ),
        }
        for name, value in components.items()
    }
    return {
        "estimator": TOKEN_ESTIMATOR,
        "tier": tier,
        "band": band,
        **components,
        "component_measurements": component_measurements,
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


def _content_digest(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _constitution_clauses(
    constitution: Mapping[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    """Parse complete, anchor-delimited constitutional clauses from packet evidence.

    The packet compiler deliberately projects only from its already-materialized
    evidence.  It does not reread the Constitution or manufacture excerpts from
    a second authority path.  An anchor owns every line through the line before
    the next anchor, so a selected clause is always complete.
    """
    content = str(constitution["content"])
    source = str(constitution["source"])
    lines = content.splitlines()
    anchors = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := _CONSTITUTION_ANCHOR_RE.search(line)) is not None
    ]
    version_match = _CONSTITUTION_VERSION_RE.search(content)
    ratified_version = version_match.group(1) if version_match else "unknown"
    full_digest = _content_digest(content)
    clauses: list[dict[str, Any]] = []
    for ordinal, (start, reference) in enumerate(anchors):
        end = anchors[ordinal + 1][0] if ordinal + 1 < len(anchors) else len(lines)
        # A following section heading belongs to the clause whose anchor comes
        # after that heading, not to this clause.  This matters for markers
        # placed immediately below their headings and keeps line ranges honest.
        for candidate_index in range(start + 1, end):
            if lines[candidate_index].startswith("#"):
                end = candidate_index
                break
        heading = ""
        for candidate in reversed(lines[: start + 1]):
            if candidate.startswith("#"):
                heading = candidate.strip()
                break
        clause_content = "\n".join(lines[start:end])
        clauses.append(
            {
                "ref": reference,
                "path": source,
                "ratified_version": ratified_version,
                "heading": heading or "(unheaded constitutional clause)",
                "line_range": [start + 1, max(start + 1, end)],
                "full_document_digest": full_digest,
                "clause_digest": _content_digest(clause_content),
                "full_document_reference": {
                    "path": source,
                    "line_range": [1, max(1, len(lines))],
                    "content_digest": full_digest,
                },
                "content": clause_content,
            }
        )
    return content, ratified_version, clauses


def _constitution_ranking_terms(dispatch: Mapping[str, Any]) -> set[str]:
    text = "\n".join(
        [
            str(dispatch["objective"]),
            *(
                str(value)
                for value in dispatch["project_context"].values()
                if not isinstance(value, list)
            ),
            *dispatch["project_context"]["non_goals"],
            *(item["name"] for item in dispatch["execution"]["acceptance_observables"]),
            *(item["command"] for item in dispatch["execution"]["acceptance_observables"]),
        ]
    ).casefold()
    return {word for word in re.findall(r"[a-z][a-z0-9_-]*", text) if len(word) >= 4}


def project_constitution(
    dispatch: Mapping[str, Any], materialized: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Return bounded, complete governing evidence or an explicit full fallback."""
    constitution_items = [item for item in materialized if item.get("kind") == "constitution"]
    if len(constitution_items) != 1:
        _fail(
            "materialized_evidence",
            "must contain exactly one required Constitution before projection",
            code="invalid_constitution_projection",
            stage="materialization",
        )
    constitution = constitution_items[0]
    content, ratified_version, clauses = _constitution_clauses(constitution)
    source = str(constitution["source"])
    full_digest = _content_digest(content)
    target = CONSTITUTION_PROJECTION_TARGETS[dispatch["execution"]["capability_tier"]]
    clauses_by_ref = {clause["ref"]: clause for clause in clauses}
    explicit_refs = list(dispatch["constitution_refs"])
    adr_refs: list[tuple[str, str]] = []
    for item in materialized:
        if item.get("kind") != "adr":
            continue
        for reference, role in _CONSTITUTION_BINDING_RE.findall(str(item["content"])):
            adr_refs.append((reference, f"selected ADR {item['id']} {role} binding"))

    selected: list[dict[str, Any]] = []
    if explicit_refs:
        missing = sorted(set(explicit_refs) - set(clauses_by_ref))
        if missing:
            _fail(
                "constitution_refs",
                "names anchor(s) absent from the supplied Constitution",
                code="invalid_constitution_projection",
                stage="materialization",
                details={"missing_refs": missing, "source": source},
            )
        for reference in explicit_refs:
            clause = dict(clauses_by_ref[reference])
            clause["selection_reason"] = "explicit dispatch Constitution reference"
            selected.append(clause)
        selection_mode = "explicit_dispatch_refs"
    elif adr_refs:
        for reference, reason in adr_refs:
            clause = clauses_by_ref.get(reference)
            if clause is None:
                continue
            if any(existing["ref"] == reference for existing in selected):
                continue
            selected_clause = dict(clause)
            selected_clause["selection_reason"] = reason
            selected.append(selected_clause)
        selection_mode = "selected_adr_refs"
    if not selected and not explicit_refs:
        terms = _constitution_ranking_terms(dispatch)
        ranked = sorted(
            (
                (len(terms & set(re.findall(r"[a-z][a-z0-9_-]*", (clause["heading"] + "\n" + clause["content"]).casefold()))), clause)
                for clause in clauses
            ),
            key=lambda item: (-item[0], item[1]["ref"]),
        )
        for score, clause in ranked:
            if score == 0:
                break
            projected_tokens = sum(estimate_tokens(item["content"]) for item in selected)
            clause_tokens = estimate_tokens(clause["content"])
            if selected and projected_tokens + clause_tokens > target:
                break
            selected_clause = dict(clause)
            selected_clause["selection_reason"] = f"ranked whole-clause lexical score {score}"
            selected.append(selected_clause)
        selection_mode = "ranked_whole_clauses"

    if selected:
        content_tokens = sum(estimate_tokens(item["content"]) for item in selected)
        return {
            "mode": "anchored_clauses",
            "selection_mode": selection_mode,
            "target_tokens": target,
            "content_tokens": content_tokens,
            "over_target": content_tokens > target,
            "clauses": selected,
        }

    return {
        "mode": "full_document_fallback",
        "selection_mode": selection_mode,
        "target_tokens": target,
        "content_tokens": estimate_tokens(content),
        "over_target": estimate_tokens(content) > target,
        "fallback_reason": (
            "Constitution anchors were unavailable or no ranked whole clause met the confidence threshold; "
            "the complete governing document is supplied without truncation."
        ),
        "full_document": {
            "path": source,
            "ratified_version": ratified_version,
            "heading": str(content.splitlines()[0]) if content.splitlines() else "Constitution",
            "line_range": [1, max(1, len(content.splitlines()))],
            "full_document_digest": full_digest,
            "clause_digest": full_digest,
            "selection_reason": "explicit complete-document fallback",
            "full_document_reference": {
                "path": source,
                "line_range": [1, max(1, len(content.splitlines()))],
                "content_digest": full_digest,
            },
            "content": content,
        },
    }


def _execution_defaults(dispatch: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    writing = dispatch["execution"]["write_intent"] == "writing"
    preflight = [
        f"Set-Location -LiteralPath {binding['worktree']!r}",
        "pwd",
        "git rev-parse --show-toplevel",
        "git branch --show-current",
        "git rev-parse HEAD",
        "git status --short",
    ]
    if writing:
        preflight.insert(
            1,
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
            "base_sha",
            "final_head_sha",
            "all_commit_hashes",
            "validation_results",
            "known_risks_or_conflicts",
            "supplemental_context_debits",
        ],
        "scope_blocker_check": {
            "required": "name the required file and compare it with dispatch.execution.allowed_files",
            "allowed_files": list(dispatch["execution"]["allowed_files"]),
        },
        "escalated_shell": {
            "required_location": binding["worktree"],
            "required_branch": binding["working_branch"],
            "verification": [
                f"Set-Location -LiteralPath {binding['worktree']!r}",
                "git rev-parse --show-toplevel",
                "git branch --show-current",
            ],
        },
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

    root = Path(normalized_binding["worktree"])
    existing_expected_absent = [
        path
        for path in normalized_dispatch["execution"]["expected_absent"]
        if (root / path).exists()
    ]
    if existing_expected_absent:
        _fail(
            "execution.expected_absent",
            "must name paths that are absent from the measured worktree",
            code="unexpected_existing_path",
            stage="binding",
            details={"existing_paths": existing_expected_absent},
        )

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
    materialized_all = materialize_evidence_pack(evidence_pack, cwd)
    if any(item.get("excerpt") is not None for item in evidence_pack["evidence"]):
        _fail(
            "evidence_pack.evidence",
            "compiled manifests must disable excerpts",
            code="duplicate_evidence_content",
            stage="materialization",
        )
    selected_decisions = {
        str(item["id"])
        for item in materialized_all
        if item.get("kind") == "decision"
    }
    missing_implements = sorted(
        set(normalized_dispatch["execution"]["implements"]) - selected_decisions
    )
    if missing_implements:
        _fail(
            "execution.implements",
            "must name exact decision evidence selected for this packet",
            code="unresolved_implements",
            stage="materialization",
            details={"missing_decisions": missing_implements},
        )
    constitution_projection = project_constitution(normalized_dispatch, materialized_all)
    materialized = [
        item for item in materialized_all if item.get("kind") != "constitution"
    ]

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
        "constitution_projection": constitution_projection,
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
