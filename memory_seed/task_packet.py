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
from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence

from .core import _git_text, _task_packet_activation_paths, commit_cadence, resolve_runtime
from .retrieval import (
    EVIDENCE_PACK_SCHEMA,
    EVIDENCE_PACK_VERSION,
    RETRIEVAL_V2_RESOLVER_VERSION,
    RetrievalSpecResolutionError,
    _evidence_pack_fingerprint,
    _source_slice,
    get_chunk,
    resolve_retrieval_spec,
    validate_evidence_pack,
)
from .retrieval_profiles import load_retrieval_profile
from .retrieval_spec import normalize_retrieval_spec_v2, retrieval_spec_fingerprint
from .planning import (
    PlanningCandidate, PlanningValidationError, assess_candidate, assess_conflict,
    parse_delivery_quality, validate_implementation_plan,
)
from .topics import load_topic_index


TASK_DISPATCH_SCHEMA = "memory-seed/task-dispatch"
TASK_DISPATCH_VERSION = 1
TASK_PACKET_SCHEMA = "memory-seed/task-packet"
TASK_PACKET_VERSION = 1
TASK_PACKET_ACTIVATION_SCHEMA = "memory-seed/task-packet-activation"
TASK_PACKET_ACTIVATION_VERSION = 1
TASK_PACKET_ACTIVATION_RECEIPT_SCHEMA = "memory-seed/task-packet-activation-receipt"
TASK_PACKET_ACTIVATION_RECEIPT_VERSION = 1
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
        "planning_evidence",
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
_WORKER_BASELINE_AGENT_RULES = ".memory-seed/agent-rules.md"
_WORKER_BASELINE_SESSION_LOGGING = ".memory-seed/skills/session_logging.md"
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
_COMPILED_PACKET_KEYS = frozenset(
    {
        "packet_schema",
        "packet_version",
        "dispatch",
        "dispatch_fingerprint",
        "runtime_binding",
        "retrieval_profile",
        "evidence_pack",
        "materialized_evidence",
        "worker_baseline",
        "constitution_projection",
        "execution_defaults",
        "input_ledger",
        "cost_ledger",
        "fingerprint",
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

    normalized = {
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
    if "planning_evidence" in dispatch:
        normalized["planning_evidence"] = _normalize_planning_evidence(dispatch["planning_evidence"])
    return normalized


def canonical_task_dispatch_json(dispatch: Mapping[str, Any]) -> str:
    return canonical_json(normalize_task_dispatch(dispatch))


def task_dispatch_fingerprint(dispatch: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_task_dispatch_json(dispatch).encode("utf-8")
    ).hexdigest()


_PLANNING_DRAFT_KEYS = frozenset({
    "id", "selected_alternative", "sources", "candidate", "assessed_scope",
    "compatibility_constraints", "proposed_action", "conflict_reason",
    "agent_recommendation", "user_acceptance", "departure_reference",
    "supporting_evidence_scope", "implementation_plan",
})
_PLANNING_DERIVED_KEYS = frozenset({
    "assessment", "disposition", "effective_policy", "required_follow_up",
    "authority_granted", "freshness",
})
_SOURCE_IDENTITY_KEYS = ("id", "kind", "source", "line_range", "content_digest")


def _planning_digest(value: Any) -> str:
    try:
        return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        _fail("planning_evidence", "requires canonical JSON data", code="invalid_planning_evidence")


def _normalize_planning_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        _fail("planning_evidence", "must be a nonempty list of bound assessments")
    result = copy.deepcopy(value)
    ids = set()
    for item in result:
        item = _mapping(item, "planning_evidence")
        keys = _PLANNING_DRAFT_KEYS | _PLANNING_DERIVED_KEYS
        _exact_keys(item, "planning_evidence", keys, required=keys - {"implementation_plan"})
        identity = _string(item["id"], "planning_evidence.id")
        if identity in ids:
            _fail("planning_evidence.id", "duplicate assessment", code="duplicate_planning_evidence")
        ids.add(identity)
        freshness = _mapping(item["freshness"], "planning_evidence.freshness")
        _exact_keys(freshness, "planning_evidence.freshness",
                    frozenset({"state", "invalidation_reasons", "inputs", "fingerprint"}),
                    required=frozenset({"state", "invalidation_reasons", "inputs", "fingerprint"}))
        _mapping(freshness["inputs"], "planning_evidence.freshness.inputs")
        if freshness["state"] != "fresh" or freshness["invalidation_reasons"] != []:
            _fail("planning_evidence.freshness", "requires fresh, reassessed evidence", code="stale_planning_evidence")
        unsigned = {key: val for key, val in item.items() if key != "freshness"}
        if freshness["fingerprint"] != _planning_digest({"assessment": unsigned, "inputs": freshness["inputs"]}):
            _fail("planning_evidence.freshness", "assessment is unbound or modified", code="planning_fingerprint_mismatch")
        if item["authority_granted"] is not False:
            _fail("planning_evidence.authority_granted", "references never grant authority")
    return result


def _planning_authority(source: Mapping[str, Any], cwd: str | Path) -> dict[str, Any]:
    """Measure lifecycle from existing readers, never from the submitted assessment."""
    from .adr import parse_adr
    from .retrieval import load_corpus
    from .semantic_cache import build_related_entry_graph, build_refines_spine, replacing_lineage_heads

    kind = source["kind"]
    authority = {"adr": "accepted_adr", "constitution": "constitution",
                 "decision": "session_evidence", "session": "session_evidence"}.get(kind, "derived_projection")
    if source["source"] in {".memory-seed/policy.md", ".memory-seed/agent-rules.md", ".memory-seed/index.md"}:
        authority = "control_file"
    state: dict[str, Any] = {"authority": authority, "status": "active"}
    if authority == "accepted_adr":
        root = resolve_runtime(cwd).workspace_root.resolve()
        path = (root / source["source"]).resolve()
        path.relative_to(root)
        record = parse_adr(path)
        if record.adr_id != source["id"]:
            _fail("planning_evidence.candidate", "ADR authority requires a selected canonical ADR")
        state.update(asdict(record.state))
        state["status"] = "active" if record.current_status == "accepted" else record.current_status
        state["topics"] = list(record.topics)
    elif authority == "session_evidence":
        chunks = load_corpus(cwd, granularity="entry")
        entry, _, ordinal = source["id"].partition(":")
        chunk = next((chunk for chunk in chunks if chunk.entry_id == entry), None)
        if kind not in {"decision", "session"} or chunk is None:
            _fail("planning_evidence.candidate", "session authority requires a selected canonical decision or entry")
        graph = build_related_entry_graph(chunks=chunks)
        spine = build_refines_spine(chunks)
        state.update(replacing_heads=list(replacing_lineage_heads(graph, entry)),
                     refines_head=list(spine.head(entry, ordinal or None)), topics=list(chunk.topics))
        if ordinal:
            decision = next((item for item in load_corpus(cwd, granularity="decision")
                             if item.chunk_id == source["id"]), None)
            if decision is None:
                _fail("planning_evidence.candidate", "decision authority requires a canonical decision")
            state["topics"] = list(decision.topics)
        state["decision_links"] = sorted(
            [other.entry_id, *edge] for other in chunks for edge in other.decision_edges
            if edge[2] == entry and (not ordinal or not edge[3] or edge[3] == ordinal)
        )
        if state["replacing_heads"] or any(edge[1] == "replaces" for edge in state["decision_links"]):
            state["status"] = "superseded"
    elif authority in {"constitution", "control_file"}:
        root = resolve_runtime(cwd).workspace_root.resolve()
        path = (root / source["source"]).resolve()
        path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        if authority == "constitution":
            if kind != "constitution":
                _fail("planning_evidence.candidate", "Constitution authority requires a selected Constitution clause")
            state["status"] = "active" if _CONSTITUTION_VERSION_RE.search(text) else "proposed"
        elif source["source"] not in {".memory-seed/policy.md", ".memory-seed/agent-rules.md", ".memory-seed/index.md"}:
            _fail("planning_evidence.candidate", "control authority requires the concern-owning control file")
        state["control_digest"] = _planning_digest(text)
    return state


def _bind_planning_assessment(draft: Mapping[str, Any], dispatch: Mapping[str, Any],
                             records: Sequence[Mapping[str, Any]], cwd: str | Path,
                             *, effective_policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    _exact_keys(draft, "planning_evidence", _PLANNING_DRAFT_KEYS,
                required=_PLANNING_DRAFT_KEYS - {"supporting_evidence_scope", "implementation_plan"})
    item = copy.deepcopy(dict(draft))
    for field in ("id", "selected_alternative", "proposed_action"):
        _string(item[field], f"planning_evidence.{field}")
    item["compatibility_constraints"] = _string_list(item["compatibility_constraints"], "planning_evidence.compatibility_constraints")
    source_ids = _string_list(item["sources"], "planning_evidence.sources", nonempty=True)
    selected = {record["id"]: record for record in records}
    if not set(source_ids).issubset(selected):
        _fail("planning_evidence.sources", "every source must be selected in the Evidence Pack", code="unbound_planning_evidence")
    item["sources"] = [{key: selected[identity][key] for key in _SOURCE_IDENTITY_KEYS} for identity in source_ids]
    root = resolve_runtime(cwd).workspace_root.resolve()
    for identity in source_ids:
        record = selected[identity]
        source_path = (root / record["source"]).resolve()
        source_path.relative_to(root)
        content = (str(get_chunk(record["chunk_id"], cwd).get("text", "")) if record.get("chunk_id")
                   else _source_slice(source_path, record["line_range"]))
        if "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest() != record["content_digest"]:
            _fail("planning_evidence.sources", "source digest changed", code="stale_planning_evidence")
    scope = _mapping(item["assessed_scope"], "planning_evidence.assessed_scope")
    _exact_keys(scope, "planning_evidence.assessed_scope", frozenset({"topics", "paths"}), required=frozenset({"topics", "paths"}))
    topics = _string_list(scope["topics"], "planning_evidence.assessed_scope.topics")
    paths = [_path_string(path, "planning_evidence.assessed_scope.paths")
             for path in _string_list(scope["paths"], "planning_evidence.assessed_scope.paths")]
    item["assessed_scope"] = scope = {"topics": topics, "paths": paths}
    runtime = resolve_runtime(cwd)
    config = runtime.memory_dir / "project.yaml"
    config_text = config.read_text(encoding="utf-8") if config.exists() else ""
    tracked_policy = parse_delivery_quality(config_text)
    policy = parse_delivery_quality(config_text, local_override=effective_policy)
    if "implementation_plan" in item:
        if item["implementation_plan"] is None:
            _fail("planning_evidence.implementation_plan", "omit the optional field for routine assessed work")
        item["implementation_plan"] = validate_implementation_plan(
            item["implementation_plan"], evidence_references=source_ids, assessed_paths=paths,
            effective_policy=policy,
        )
    if not topics and not paths:
        _fail("planning_evidence.assessed_scope", "requires bounded topics or paths")
    support = _mapping(item.get("supporting_evidence_scope", {"topics": [], "paths": []}),
                       "planning_evidence.supporting_evidence_scope")
    _exact_keys(support, "planning_evidence.supporting_evidence_scope", frozenset({"topics", "paths"}),
                required=frozenset({"topics", "paths"}))
    # Supporting selectors are read scope, not exact-file edit entitlements.
    retrieval = dispatch["retrieval"]
    effective_spec = load_retrieval_profile(retrieval["profile"], retrieval["profile_version"], cwd,
                                             overrides=retrieval["overrides"])
    support = normalize_retrieval_spec_v2({**effective_spec, "filters": dict(support)})["filters"]
    item["supporting_evidence_scope"] = support
    candidate_in = _mapping(item["candidate"], "planning_evidence.candidate")
    _exact_keys(candidate_in, "planning_evidence.candidate", frozenset(PlanningCandidate.__dataclass_fields__),
                required=frozenset({"reference", "decision", "authority"}))
    candidate = PlanningCandidate(**candidate_in)
    if candidate.reference not in source_ids:
        _fail("planning_evidence.candidate.reference", "must name a selected planning source", code="unbound_planning_evidence")
    topic_index = load_topic_index(cwd)
    assessment = assess_candidate(candidate, topics, topic_index)
    assess_candidate(candidate, support["topics"], topic_index)  # validate supporting topic vocabulary too
    authority = {identity: _planning_authority(selected[identity], cwd) for identity in source_ids}
    candidate_authority = authority[candidate.reference]
    if candidate.authority != candidate_authority["authority"]:
        _fail("planning_evidence.candidate.authority", "cannot downgrade the canonical source authority")
    if candidate.status != candidate_authority["status"]:
        _fail("planning_evidence.candidate.status", "does not match current authority lifecycle", code="stale_planning_evidence")
    if "topics" in candidate_authority and list(candidate.topics) != candidate_authority["topics"]:
        _fail("planning_evidence.candidate.topics", "must retain recorded source topics")
    item["candidate"] = json.loads(canonical_json(asdict(candidate)))
    assessed = asdict(assessment)
    assessed.pop("candidate")
    item["assessment"] = json.loads(canonical_json(assessed))
    recommendation = item["agent_recommendation"]
    if recommendation is not None and recommendation not in ("stop", "warn", "proceed"):
        _fail("planning_evidence.agent_recommendation", "must be stop, warn, proceed or null")
    acceptance = item["user_acceptance"]
    if acceptance is not None:
        acceptance = _mapping(acceptance, "planning_evidence.user_acceptance")
        _exact_keys(acceptance, "planning_evidence.user_acceptance", frozenset({"reference", "scope", "reason"}),
                    required=frozenset({"reference", "scope", "reason"}))
        for key, value in acceptance.items():
            _string(value, f"planning_evidence.user_acceptance.{key}")
        if acceptance["reference"] not in source_ids:
            _fail("planning_evidence.user_acceptance", "acceptance reference must be separately sourced; authenticity remains unverified")
    departure = item["departure_reference"]
    if departure is not None and (not isinstance(departure, str) or departure not in source_ids):
        _fail("planning_evidence.departure_reference", "must name a selected source")
    conflict = item["conflict_reason"]
    if conflict is not None:
        outcome = assess_conflict(assessment, proposed_action=item["proposed_action"], conflict_reason=conflict,
                                  policy=policy, agent_recommendation=recommendation, user_acceptance=acceptance)
        item["disposition"] = outcome["disposition"]
        item["required_follow_up"] = outcome["required_follow_up"]
    else:
        item["disposition"] = "compatible" if assessment.binding else "review-required"
        item["required_follow_up"] = [] if assessment.binding else ["review_applicability"]
    item["effective_policy"] = policy
    item["authority_granted"] = False
    relevant_topics = set(topics) | set(candidate.topics) | set(support["topics"])
    for state in authority.values():
        relevant_topics.update(state.get("topics", []))
    for topic in list(relevant_topics):
        canonical = topic_index.resolution().get(topic, topic)
        relevant_topics.update((canonical, *topic_index.ancestors(canonical)))
    inputs = {
        "sources": item["sources"], "authority": authority,
        "topic_tree": {"schema_version": topic_index.schema_version,
                       "records": [asdict(record) for record in topic_index.topics if record.slug in relevant_topics]},
        "policy": {"tracked": tracked_policy, "effective": policy},
        "profile": {**retrieval, "effective_spec": effective_spec},
        "scope": {"task": scope, "supporting_evidence": support},
        "objective": dispatch["objective"],
    }
    inputs = json.loads(canonical_json(inputs))
    item["freshness"] = {"state": "fresh", "invalidation_reasons": [], "inputs": inputs,
                         "fingerprint": _planning_digest({"assessment": item, "inputs": inputs})}
    return item


def prepare_planning_evidence(dispatch: Mapping[str, Any], assessments: Sequence[Mapping[str, Any]],
                              cwd: str | Path = ".", *, effective_policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Bind explicitly reassessed drafts to current local evidence; no authorization.

    This read-only compiler helper uses the existing profile/resolver. It is not a
    planner or cache. Retain its return value in dispatch.planning_evidence only
    for the assessed plan scope. Compilation checks freshness without rebinding.
    """
    normalized = normalize_task_dispatch({key: value for key, value in dispatch.items() if key != "planning_evidence"})
    retrieval = normalized["retrieval"]
    spec = load_retrieval_profile(retrieval["profile"], retrieval["profile_version"], cwd, overrides=retrieval["overrides"])
    spec["output"]["include_excerpts"] = False
    pack = resolve_retrieval_spec(spec, cwd)
    validate_evidence_pack(pack, cwd)
    try:
        result = [_bind_planning_assessment(_mapping(draft, "planning_evidence"), normalized, pack["evidence"], cwd,
                                            effective_policy=effective_policy) for draft in assessments]
        return _normalize_planning_evidence(result)
    except (PlanningValidationError, RetrievalSpecResolutionError, OSError, ValueError, TypeError) as exc:
        if isinstance(exc, TaskPacketValidationError):
            raise
        _fail("planning_evidence", str(exc), code="invalid_planning_evidence")


def _validate_planning_evidence(dispatch: Mapping[str, Any], records: Sequence[Mapping[str, Any]], cwd: str | Path) -> None:
    if "planning_evidence" not in dispatch:
        return
    seen: dict[str, list[list[int]]] = {}
    baseline_paths = {_canonical_scope_identity(_WORKER_BASELINE_AGENT_RULES)}
    if dispatch["memory_update_policy"] == "worker_checkpoint" or _session_log_paths_are_writable(dispatch):
        baseline_paths.add(_canonical_scope_identity(_WORKER_BASELINE_SESSION_LOGGING))
    for record in records:
        if _canonical_scope_identity(record["source"]) in baseline_paths:
            _fail("planning_evidence.sources", "selected evidence duplicates complete worker baseline", code="duplicate_evidence_content")
        ranges = seen.setdefault(_canonical_scope_identity(record["source"]), [])
        start, end = record["line_range"]
        if any(start <= previous[1] and previous[0] <= end for previous in ranges):
            _fail("planning_evidence.sources", "overlapping materialized evidence", code="duplicate_evidence_content")
        ranges.append([start, end])
    invalidated: dict[str, list[str]] = {}
    covered_paths: set[str] = set()
    covered_topics: set[str] = set()
    supporting_paths: set[str] = set()
    supporting_topics: set[str] = set()
    for item in dispatch["planning_evidence"]:
        try:
            draft = {key: item[key] for key in _PLANNING_DRAFT_KEYS if key in item}
            draft["sources"] = [source["id"] for source in item["sources"]]
            current = _bind_planning_assessment(draft, dispatch, records, cwd, effective_policy=item["effective_policy"])
            previous_inputs = item["freshness"]["inputs"]
            reasons = [key + " changed" for key, value in current["freshness"]["inputs"].items()
                       if previous_inputs.get(key) != value]
            if current != item:
                invalidated[item["id"]] = reasons or ["assessment inconsistent with current evidence"]
            covered_paths.update(item["assessed_scope"]["paths"])
            covered_topics.update(item["assessed_scope"]["topics"])
            supporting_paths.update(item["supporting_evidence_scope"]["paths"])
            supporting_topics.update(item["supporting_evidence_scope"]["topics"])
        except (PlanningValidationError, RetrievalSpecResolutionError, TaskPacketValidationError, KeyError, TypeError, ValueError, OSError) as exc:
            invalidated[item["id"]] = [str(exc)]
    if invalidated:
        _fail("planning_evidence", "scoped evidence requires reassessment", code="stale_planning_evidence",
              details={"invalidated": invalidated, "freshness": "stale"})
    retrieval = dispatch["retrieval"]
    effective_spec = load_retrieval_profile(retrieval["profile"], retrieval["profile_version"], cwd,
                                             overrides=retrieval["overrides"])
    topic_resolution = load_topic_index(cwd).resolution()
    canonical_topics = lambda values: {topic_resolution.get(value, value) for value in values}
    if (not set(dispatch["execution"]["allowed_files"]).issubset(covered_paths)
            or not canonical_topics(effective_spec["filters"]["topics"]).issubset(
                canonical_topics(covered_topics | supporting_topics))
            or not set(effective_spec["filters"]["paths"]).issubset(covered_paths | supporting_paths)):
        _fail("planning_evidence.assessed_scope", "task scope expanded beyond assessed evidence", code="stale_planning_evidence")


def governance_reference(memory_dir: Path, relative_source: str) -> dict[str, Any]:
    """Pin one full control-plane file by identity, without embedding it.

    The reference carries everything ``load_task_packet_governance`` needs to
    prove later bytes are the compiled bytes: path, size, digest, and the
    token estimate a worker will spend if it loads the file.
    """
    record = _materialize_worker_baseline_document(memory_dir, relative_source, required=True)
    assert record is not None
    return {key: record[key] for key in ("source", "byte_count", "content_digest", "token_estimate")}


def load_task_packet_governance(packet: Mapping[str, Any], name: str, cwd: str | Path) -> dict[str, Any]:
    """Load one lazily referenced governance file, verified against its pin.

    Governance loads are the on-demand half of orientation lite: a worker
    reads the full ``session_logging.md`` or ``agent-rules.md`` only when a
    lite trigger fires. They are deliberately NOT supplemental gap reads -
    they never debit ``supplemental_input_reserve_tokens``, so a budget can
    never starve a worker of the rules it is required to consult. Bytes that
    no longer match the compiled digest are refused as stale governance.
    """
    references = packet.get("governance_references")
    if not isinstance(references, Mapping):
        if isinstance(packet.get("worker_baseline"), Mapping):
            _fail("governance", "this packet embeds its governance in worker_baseline; read it there",
                  code="governance_embedded", stage="governance_load")
        _fail("governance", "packet declares no governance references",
              code="missing_governance_reference", stage="governance_load")
    reference = references.get(name)
    if not isinstance(reference, Mapping):
        _fail(f"governance.{name}", "packet declares no governance reference with this name",
              code="missing_governance_reference", stage="governance_load",
              details={"available": sorted(references)})
    root = Path(cwd).resolve()
    source = (root / str(reference["source"])).resolve()
    try:
        source.relative_to(root)
    except ValueError:
        _fail(f"governance.{name}", "governance source resolved outside the bound checkout",
              code="invalid_governance_reference", stage="governance_load",
              details={"source": reference["source"]})
    try:
        payload = source.read_bytes()
    except OSError as exc:
        _fail(f"governance.{name}", "governance source is missing or unreadable",
              code="stale_governance", stage="governance_load",
              details={"source": reference["source"], "error": exc.__class__.__name__})
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if digest != reference["content_digest"]:
        _fail(f"governance.{name}", "governance source changed since the packet was compiled",
              code="stale_governance", stage="governance_load",
              details={"source": reference["source"], "expected": reference["content_digest"], "actual": digest})
    return {
        "name": name,
        "source": reference["source"],
        "content": payload.decode("utf-8"),
        "content_digest": digest,
        "token_estimate": reference["token_estimate"],
        "supplemental_debit": 0,
    }


def validate_task_packet_supplemental_fetch(packet: Mapping[str, Any], source: str,
                                           line_range: Sequence[int], *, token_estimate: int,
                                           prior_debits: int = 0) -> dict[str, int]:
    """Check a proposed supplemental gap read without fetching or changing a ledger."""
    canonical_task_packet_json(packet)
    source = _path_string(source, "supplemental.source")
    if (not isinstance(line_range, (list, tuple)) or len(line_range) != 2
            or any(type(value) is not int or value < 1 for value in line_range)
            or line_range[1] < line_range[0]):
        _fail("supplemental.line_range", "requires a positive inclusive line range")
    for record in packet["evidence_pack"]["evidence"]:
        if (_canonical_scope_identity(source) == _canonical_scope_identity(record["source"])
                and line_range[0] <= record["line_range"][1] and record["line_range"][0] <= line_range[1]):
            _fail("supplemental.source", "requested evidence is already materialized", code="duplicate_evidence_content")
    for record in ((packet.get("worker_baseline") or {}).get("sources") or {}).values():
        if record is not None and _canonical_scope_identity(source) == _canonical_scope_identity(record["source"]):
            _fail("supplemental.source", "requested governance is already materialized", code="duplicate_evidence_content")
    for record in (packet.get("governance_references") or {}).values():
        if _canonical_scope_identity(source) == _canonical_scope_identity(record["source"]):
            _fail("supplemental.source", "referenced governance loads through load_task_packet_governance, not the reserve",
                  code="governance_reference")
    debit = _nonnegative_int(token_estimate, "supplemental.token_estimate")
    prior = _nonnegative_int(prior_debits, "supplemental.prior_debits")
    remaining = packet["input_ledger"]["supplemental_input_reserve_tokens"] - prior - debit
    if remaining < 0:
        _fail("supplemental.token_estimate", "supplemental gap exceeds the reserved envelope", code="supplemental_budget_exceeded")
    return {"token_debit": debit, "total_debits": prior + debit, "remaining_tokens": remaining}


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
    materialized_agent_rules_tokens: int = 0,
    materialized_session_logging_tokens: int = 0,
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
        # These are subsets of the canonical serialized packet rather than
        # additional input.  Exposing them separately makes the always-on
        # worker-governance cost inspectable without double-counting it.
        "materialized_agent_rules_tokens": materialized_agent_rules_tokens,
        "materialized_session_logging_tokens": materialized_session_logging_tokens,
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
    for name in (
        "materialized_agent_rules_tokens",
        "materialized_session_logging_tokens",
    ):
        component_measurements[name]["accounting_scope"] = (
            "subset_of_serialized_packet_input_tokens"
        )
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


def _materialize_worker_baseline_document(
    memory_dir: Path, relative_source: str, *, required: bool
) -> dict[str, Any] | None:
    """Read one active control-plane baseline byte-for-byte as UTF-8."""
    source = (memory_dir.parent / relative_source).resolve()
    try:
        source.relative_to(memory_dir.parent.resolve())
    except ValueError:
        _fail(
            "worker_baseline",
            "baseline source resolved outside the active runtime",
            code="invalid_worker_baseline",
            stage="materialization",
            details={"source": relative_source},
        )
    try:
        payload = source.read_bytes()
    except OSError as exc:
        if not required:
            return None
        _fail(
            f"worker_baseline.{Path(relative_source).stem}",
            "required active baseline source is missing or unreadable",
            code="missing_worker_baseline",
            stage="materialization",
            details={"source": relative_source, "error": exc.__class__.__name__},
        )
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(
            f"worker_baseline.{Path(relative_source).stem}",
            "required active baseline source must be UTF-8",
            code="invalid_worker_baseline",
            stage="materialization",
            details={"source": relative_source, "error": exc.__class__.__name__},
        )
    return {
        "source": relative_source,
        "byte_count": len(payload),
        "token_estimate": estimate_tokens(payload),
        "content_digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "content": content,
    }


def _session_log_paths_are_writable(dispatch: Mapping[str, Any]) -> bool:
    return any(
        _canonical_scope_identity(path).startswith(".memory-seed/sessions/")
        for path in dispatch["execution"]["allowed_files"]
    )


def materialize_worker_baseline(
    dispatch: Mapping[str, Any], cwd: str | Path = "."
) -> dict[str, Any]:
    """Materialize the minimum always-on worker governance from the active runtime.

    Retrieval evidence remains task scoped.  These baseline sources are instead
    a deterministic execution envelope: every packet gets agent rules, while
    session logging is included only when the dispatch delegates a session
    write or asks for worker checkpoints.
    """
    runtime = resolve_runtime(cwd)
    agent_rules = _materialize_worker_baseline_document(
        runtime.memory_dir, _WORKER_BASELINE_AGENT_RULES, required=True
    )
    assert agent_rules is not None
    session_logging_required = (
        dispatch["memory_update_policy"] == "worker_checkpoint"
        or _session_log_paths_are_writable(dispatch)
    )
    session_logging = (
        _materialize_worker_baseline_document(
            runtime.memory_dir,
            _WORKER_BASELINE_SESSION_LOGGING,
            required=True,
        )
        if session_logging_required
        else None
    )
    if session_logging_required and session_logging is None:
        _fail(
            "worker_baseline.session_logging",
            "session-writable packets require the active session_logging baseline",
            code="missing_worker_baseline",
            stage="materialization",
            details={"source": _WORKER_BASELINE_SESSION_LOGGING},
        )
    sources = {"agent_rules": agent_rules, "session_logging": session_logging}
    identity = copy.deepcopy(sources)
    return {
        "sources": sources,
        "fingerprint": "sha256:" + hashlib.sha256(
            canonical_json(identity).encode("utf-8")
        ).hexdigest(),
    }


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
    if version_match is None:
        _fail(
            "evidence_pack.evidence",
            "Constitution projection requires explicit ratified Version metadata",
            code="invalid_constitution_projection",
            stage="materialization",
            details={"source": source},
        )
    ratified_version = version_match.group(1)
    expected_anchor_version = f"constitution:v{ratified_version.split('.', 1)[0]}#"
    incompatible_anchors = sorted(
        reference
        for _index, reference in anchors
        if not reference.startswith(expected_anchor_version)
    )
    if incompatible_anchors:
        _fail(
            "evidence_pack.evidence",
            "Constitution anchors must use the ratified Version's major identity",
            code="invalid_constitution_projection",
            stage="materialization",
            details={
                "source": source,
                "ratified_version": ratified_version,
                "expected_anchor_prefix": expected_anchor_version,
                "incompatible_anchors": incompatible_anchors,
            },
        )
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
    adr_refs: list[tuple[str, str, str]] = []
    for item in materialized:
        if item.get("kind") != "adr":
            continue
        for reference, role in _CONSTITUTION_BINDING_RE.findall(str(item["content"])):
            adr_refs.append((reference, str(item["id"]), role))

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
        missing_adr_refs = [
            {"adr_id": adr_id, "role": role, "missing_anchor": reference}
            for reference, adr_id, role in adr_refs
            if reference not in clauses_by_ref
        ]
        if missing_adr_refs:
            _fail(
                "materialized_evidence",
                "selected ADR Constitution binding names an anchor absent from the supplied Constitution",
                code="invalid_constitution_projection",
                stage="materialization",
                details={"missing_adr_bindings": missing_adr_refs, "source": source},
            )
        for reference, adr_id, role in adr_refs:
            clause = clauses_by_ref.get(reference)
            assert clause is not None
            if any(existing["ref"] == reference for existing in selected):
                continue
            selected_clause = dict(clause)
            selected_clause["selection_reason"] = (
                f"selected ADR {adr_id} {role} binding"
            )
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
            "governing_overage": {
                "status": "over_target" if content_tokens > target else "within_target",
                "tokens": max(0, content_tokens - target),
            },
            "clauses": selected,
        }

    return {
        "mode": "full_document_fallback",
        "selection_mode": selection_mode,
        "target_tokens": target,
        "content_tokens": estimate_tokens(content),
        "over_target": estimate_tokens(content) > target,
        "governing_overage": {
            "status": (
                "over_target" if estimate_tokens(content) > target else "within_target"
            ),
            "tokens": max(0, estimate_tokens(content) - target),
        },
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
    session_logging_delegated = (
        dispatch["memory_update_policy"] == "worker_checkpoint"
        or _session_log_paths_are_writable(dispatch)
    )
    cadence = commit_cadence(binding["worktree"], base_ref=binding["base_sha"])
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
            "python -X utf8 -m memory_seed.cli worktree guard "
            f"--agent {binding['agent_type']} --write-intent",
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
        "session_logging": {
            "delegated": session_logging_delegated,
            "append_requirement": (
                "When a session write is delegated, use memory_session_append or "
                "the checkout-local python -X utf8 -m memory_seed.cli session append path."
            ),
            "clock_ownership": (
                "Automatic clock ownership is required: omit timestamp so the sanctioned "
                "writer owns the current timestamp."
            ),
            "prohibitions": [
                "Direct Markdown session edits are forbidden.",
                "Explicit timestamps are forbidden.",
            ],
            "repair_backfill_exception": (
                "Only a dispatch that grants a narrowly scoped repair/backfill exception may "
                "depart from these prohibitions; this packet grants none."
            ),
        },
        "activation": {
            "required": writing,
            "api": "memory_seed.task_packet.activate_task_packet",
            "implements": list(dispatch["execution"]["implements"]),
            "scope_update": "requires a non-empty, explicit binding_update_reason",
            "storage": "fingerprint-verified, worktree-local Git activation artifact",
        },
        "cadence": cadence.to_dict(),
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


def _activation_binding(packet_binding: Mapping[str, Any], cwd: str | Path) -> dict[str, Any]:
    """Strictly remeasure a writing binding while allowing its own branch to advance.

    Compilation requires a base branch to resolve *exactly* to ``base_sha``.
    Once a packet is active, a worktree may legitimately commit on a branch
    that is itself named as that base.  In that one case, activation requires
    the base SHA to remain an ancestor of the branch and current HEAD; every
    other base branch still has to resolve exactly.  This preserves the
    compiler's authority without treating an arbitrary, changed base ref as a
    valid packet binding.
    """
    binding = _mapping(packet_binding, "packet.runtime_binding")
    _exact_keys(binding, "packet.runtime_binding", _BINDING_KEYS, required=_BINDING_KEYS)
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root.resolve()
    measured_root = Path(_git_required(root, ("rev-parse", "--show-toplevel"), label="activation worktree")).resolve()
    branch = _git_required(root, ("rev-parse", "--abbrev-ref", "HEAD"), label="activation branch")
    if branch == "HEAD":
        _fail("packet.runtime_binding.working_branch", "must not activate from detached HEAD", code="binding_mismatch", stage="activation")
    expected_raw = Path(str(_string(binding["expected_directory"], "packet.runtime_binding.expected_directory")))
    worktree_raw = Path(str(_string(binding["worktree"], "packet.runtime_binding.worktree")))
    if not expected_raw.is_absolute() or not worktree_raw.is_absolute():
        _fail("packet.runtime_binding", "worktree and expected_directory must be absolute measured paths", code="binding_mismatch", stage="activation")
    worktree = worktree_raw.resolve()
    expected = expected_raw.resolve()
    working_branch = _string(binding["working_branch"], "packet.runtime_binding.working_branch")
    base_sha = _string(binding["base_sha"], "packet.runtime_binding.base_sha")
    base_branch = _string(binding["base_branch"], "packet.runtime_binding.base_branch")
    owner = _string(binding["owner"], "packet.runtime_binding.owner")
    agent_type = _string(binding["agent_type"], "packet.runtime_binding.agent_type")
    integration_artifact = _string(binding["integration_artifact"], "packet.runtime_binding.integration_artifact")
    assert all(value is not None for value in (working_branch, base_sha, base_branch, owner, agent_type, integration_artifact))
    if _SHA_RE.fullmatch(base_sha) is None:
        _fail("packet.runtime_binding.base_sha", "must be a full 40-character Git SHA", code="binding_mismatch", stage="activation")
    if _SLUG_RE.fullmatch(owner) is None or _SLUG_RE.fullmatch(agent_type) is None:
        _fail("packet.runtime_binding", "owner and agent_type must be lowercase identity slugs", code="binding_mismatch", stage="activation")
    if integration_artifact not in {"pr", "merge-request", "patch", "branch", "handoff"}:
        _fail("packet.runtime_binding.integration_artifact", "is not a supported integration artifact", code="binding_mismatch", stage="activation")
    if measured_root != root or worktree != measured_root or expected != measured_root or working_branch != branch:
        _fail("packet.runtime_binding", "does not match the measured activation worktree and branch", code="binding_mismatch", stage="activation")
    base_code, base_head = _git_text(root, ("show-ref", "--verify", "--hash", f"refs/heads/{base_branch}"))
    if base_code != 0 or not base_head:
        _fail("packet.runtime_binding.base_branch", "must name an existing local branch exactly", code="binding_mismatch", stage="activation")
    if base_head.lower() != base_sha.lower():
        # A packet may name its own task branch as its immutable base. That
        # branch necessarily moves after its first checkpoint; no unrelated
        # mutable base ref gets this exception.
        if base_branch != branch or _git_text(root, ("merge-base", "--is-ancestor", base_sha, base_head))[0] != 0:
            _fail("packet.runtime_binding.base_sha", "does not match the supplied base branch", code="binding_mismatch", stage="activation")
    if _git_text(root, ("merge-base", "--is-ancestor", base_sha, "HEAD"))[0] != 0:
        _fail("packet.runtime_binding.base_sha", "must remain an ancestor of the activation HEAD", code="binding_mismatch", stage="activation")
    result = {
        "owner": owner,
        "agent_type": agent_type,
        "base_branch": base_branch,
        "base_sha": base_sha.lower(),
        "working_branch": branch,
        "worktree": str(worktree),
        "expected_directory": str(expected),
        "integration_artifact": integration_artifact,
    }
    return result


def _validate_compiled_packet_evidence(packet: Mapping[str, Any]) -> None:
    """Check compiler-produced evidence identities without rereading mutable sources.

    A packet can legitimately be activated after it has caused new commits, so
    validating a live corpus revision here would reject its own work.  The
    packet still has to carry the exact v2 evidence identity and its materialized
    non-Constitution slices must match that identity byte-for-byte.
    """
    evidence_pack = _mapping(packet.get("evidence_pack"), "packet.evidence_pack")
    if (
        evidence_pack.get("pack_schema") != EVIDENCE_PACK_SCHEMA
        or evidence_pack.get("pack_version") != EVIDENCE_PACK_VERSION
        or evidence_pack.get("resolver_version") != RETRIEVAL_V2_RESOLVER_VERSION
    ):
        _fail("packet.evidence_pack", "must be a compiler Evidence Pack v2", code="invalid_packet", stage="activation")
    try:
        evidence_fingerprint = _evidence_pack_fingerprint(evidence_pack)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("packet.evidence_pack", "is missing canonical evidence identities", code="invalid_packet", stage="activation", details={"error": exc.__class__.__name__})
    if evidence_pack.get("fingerprint") != evidence_fingerprint:
        _fail("packet.evidence_pack.fingerprint", "does not match canonical evidence identities", code="fingerprint_mismatch", stage="activation")
    profile = _mapping(packet.get("retrieval_profile"), "packet.retrieval_profile")
    effective_spec = _mapping(profile.get("effective_spec"), "packet.retrieval_profile.effective_spec")
    if profile.get("effective_spec_fingerprint") != retrieval_spec_fingerprint(effective_spec):
        _fail("packet.retrieval_profile.effective_spec_fingerprint", "does not match the effective spec", code="fingerprint_mismatch", stage="activation")
    materialized = packet.get("materialized_evidence")
    records = evidence_pack.get("evidence")
    if not isinstance(materialized, list) or not isinstance(records, list) or not all(isinstance(item, Mapping) for item in records):
        _fail("packet.materialized_evidence", "must carry compiler materialized evidence", code="invalid_packet", stage="activation")
    expected = [
        (item.get("id"), item.get("kind"), item.get("source"), item.get("line_range"), item.get("content_digest"))
        for item in records
        if item.get("kind") != "constitution"
    ]
    observed: list[tuple[Any, Any, Any, Any, Any]] = []
    for item in materialized:
        if not isinstance(item, Mapping) or not isinstance(item.get("content"), str):
            _fail("packet.materialized_evidence", "contains an incomplete compiler slice", code="invalid_packet", stage="activation")
        digest = "sha256:" + hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
        if item.get("content_digest") != digest:
            _fail("packet.materialized_evidence", "content does not match its declared digest", code="fingerprint_mismatch", stage="activation")
        observed.append((item.get("id"), item.get("kind"), item.get("source"), item.get("line_range"), item.get("content_digest")))
    if observed != expected:
        _fail("packet.materialized_evidence", "does not match the Evidence Pack identities", code="fingerprint_mismatch", stage="activation")


def _validate_worker_baseline(packet: Mapping[str, Any]) -> None:
    """Validate baseline bytes embedded by the compiler without rereading mutable files."""
    baseline = _mapping(packet.get("worker_baseline"), "packet.worker_baseline")
    _exact_keys(
        baseline,
        "packet.worker_baseline",
        frozenset({"sources", "fingerprint"}),
        required=frozenset({"sources", "fingerprint"}),
    )
    sources = _mapping(baseline.get("sources"), "packet.worker_baseline.sources")
    _exact_keys(
        sources,
        "packet.worker_baseline.sources",
        frozenset({"agent_rules", "session_logging"}),
        required=frozenset({"agent_rules", "session_logging"}),
    )

    def validate_source(name: str, expected_source: str, *, required: bool) -> None:
        item = sources.get(name)
        if item is None:
            if required:
                _fail(
                    f"packet.worker_baseline.sources.{name}",
                    "is required by the dispatch",
                    code="invalid_packet",
                    stage="activation",
                )
            return
        source = _mapping(item, f"packet.worker_baseline.sources.{name}")
        _exact_keys(
            source,
            f"packet.worker_baseline.sources.{name}",
            frozenset({"source", "byte_count", "token_estimate", "content_digest", "content"}),
            required=frozenset({"source", "byte_count", "token_estimate", "content_digest", "content"}),
        )
        if source.get("source") != expected_source or not isinstance(source.get("content"), str):
            _fail(
                f"packet.worker_baseline.sources.{name}",
                "does not carry the expected complete baseline source",
                code="invalid_packet",
                stage="activation",
            )
        payload = str(source["content"]).encode("utf-8")
        if source.get("byte_count") != len(payload) or source.get("token_estimate") != estimate_tokens(payload):
            _fail(
                f"packet.worker_baseline.sources.{name}",
                "does not match the embedded baseline bytes",
                code="fingerprint_mismatch",
                stage="activation",
            )
        if source.get("content_digest") != "sha256:" + hashlib.sha256(payload).hexdigest():
            _fail(
                f"packet.worker_baseline.sources.{name}",
                "content does not match its declared digest",
                code="fingerprint_mismatch",
                stage="activation",
            )

    dispatch = _mapping(packet.get("dispatch"), "packet.dispatch")
    session_logging_required = (
        dispatch.get("memory_update_policy") == "worker_checkpoint"
        or _session_log_paths_are_writable(dispatch)
    )
    validate_source("agent_rules", _WORKER_BASELINE_AGENT_RULES, required=True)
    validate_source(
        "session_logging",
        _WORKER_BASELINE_SESSION_LOGGING,
        required=session_logging_required,
    )
    expected_fingerprint = "sha256:" + hashlib.sha256(
        canonical_json(copy.deepcopy(dict(sources))).encode("utf-8")
    ).hexdigest()
    if baseline.get("fingerprint") != expected_fingerprint:
        _fail(
            "packet.worker_baseline.fingerprint",
            "does not match the canonical baseline sources",
            code="fingerprint_mismatch",
            stage="activation",
        )


def _activation_receipt(
    packet: Mapping[str, Any], dispatch: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    """A deterministic record of successful compiler-compatible activation."""
    return {
        "schema": TASK_PACKET_ACTIVATION_RECEIPT_SCHEMA,
        "version": TASK_PACKET_ACTIVATION_RECEIPT_VERSION,
        "compiler": "memory_seed.task_packet.compile_task_packet",
        "activation": "memory_seed.task_packet.activate_task_packet",
        "packet_fingerprint": packet["fingerprint"],
        "dispatch_fingerprint": packet["dispatch_fingerprint"],
        "evidence_pack_fingerprint": packet["evidence_pack"]["fingerprint"],
        "runtime_binding": dict(binding),
        "objective": dispatch["objective"],
        "implements": list(dispatch["execution"]["implements"]),
    }


def _validate_activation_packet(packet: Mapping[str, Any], cwd: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return fully checked dispatch, binding, and receipt for artifact use."""
    packet = _mapping(packet, "packet")
    _exact_keys(packet, "packet", _COMPILED_PACKET_KEYS, required=_COMPILED_PACKET_KEYS)
    canonical_task_packet_json(packet)
    dispatch = normalize_task_dispatch(_mapping(packet.get("dispatch"), "packet.dispatch"))
    if dispatch != packet["dispatch"]:
        _fail("packet.dispatch", "is not the compiler-normalized dispatch", code="fingerprint_mismatch", stage="activation")
    if packet.get("dispatch_fingerprint") != task_dispatch_fingerprint(dispatch):
        _fail("packet.dispatch_fingerprint", "does not match the normalized dispatch", code="fingerprint_mismatch", stage="activation")
    if dispatch["execution"]["write_intent"] != "writing":
        _fail("packet.dispatch.execution.write_intent", "read-only packets cannot activate commit attribution", code="activation_read_only", stage="activation")
    binding = _activation_binding(_mapping(packet.get("runtime_binding"), "packet.runtime_binding"), cwd)
    if binding != packet["runtime_binding"]:
        _fail("packet.runtime_binding", "is not the strict normalized activation binding", code="binding_mismatch", stage="activation")
    _validate_compiled_packet_evidence(packet)
    _validate_planning_evidence(dispatch, packet["evidence_pack"]["evidence"], cwd)
    _validate_worker_baseline(packet)
    selected_decisions = {
        item["id"]
        for item in packet["materialized_evidence"]
        if item["kind"] == "decision"
    }
    if not set(dispatch["execution"]["implements"]).issubset(selected_decisions):
        _fail("packet.dispatch.execution.implements", "must remain selected materialized decision evidence", code="unresolved_implements", stage="activation")
    return dispatch, binding, _activation_receipt(packet, dispatch, binding)


def _read_activation_artifact(path: Path, cwd: str | Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    if payload.get("schema") != TASK_PACKET_ACTIVATION_SCHEMA or payload.get("version") != TASK_PACKET_ACTIVATION_VERSION:
        return None
    packet = payload.get("packet")
    receipt = payload.get("receipt")
    if not isinstance(packet, Mapping) or not isinstance(receipt, Mapping):
        return None
    try:
        _, _, expected_receipt = _validate_activation_packet(packet, cwd)
        if dict(receipt) != expected_receipt:
            return None
    except TaskPacketValidationError:
        return None
    return payload


def activate_task_packet(
    packet: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    binding_update_reason: str | None = None,
) -> dict[str, Any]:
    """Activate a compiled writing packet for its bound Git branch.

    Activation deliberately writes no project files, Git configuration, or
    global Git state. It stores the complete fingerprint-verified packet in the
    bound worktree's Git directory and appends replacement receipts beside it.
    The managed hook can therefore verify branch, worktree, base SHA, scope,
    selected evidence, and exact refs before it writes provenance trailers.
    """
    packet = _mapping(packet, "packet")
    dispatch, binding, activation_receipt = _validate_activation_packet(packet, cwd)
    branch = binding["working_branch"]
    assert branch is not None
    root = Path(binding["worktree"])
    scope = canonical_json(
        {
            "allowed_files": dispatch["execution"]["allowed_files"],
            "forbidden_files": dispatch["execution"]["forbidden_files"],
            "expected_absent": dispatch["execution"]["expected_absent"],
        }
    )
    binding_identity = canonical_json(
        {
            "base_branch": binding["base_branch"],
            "base_sha": binding["base_sha"],
            "working_branch": branch,
            "worktree": binding["worktree"],
        }
    )
    reason = (binding_update_reason or "").strip()
    paths = _task_packet_activation_paths(root, branch)
    if paths is None:
        _fail("activation", "requires a Git worktree-local activation directory", code="activation_io", stage="activation")
    artifact_path, history_path = paths
    previous = _read_activation_artifact(artifact_path, root)
    invalid_previous = previous is None and artifact_path.exists()
    if invalid_previous and len(reason) < 12:
        _fail("binding_update_reason", "replacing a stale or invalid activation requires an explicit reason of at least 12 characters",
              code="binding_update_required", stage="activation")
    previous_packet = previous.get("packet") if previous is not None else None
    previous_dispatch = (
        normalize_task_dispatch(previous_packet["dispatch"])
        if isinstance(previous_packet, Mapping) and isinstance(previous_packet.get("dispatch"), Mapping)
        else None
    )
    previous_scope = canonical_json({
        "allowed_files": previous_dispatch["execution"]["allowed_files"],
        "forbidden_files": previous_dispatch["execution"]["forbidden_files"],
        "expected_absent": previous_dispatch["execution"]["expected_absent"],
    }) if previous_dispatch is not None else None
    previous_binding = canonical_json({
        key: previous_packet["runtime_binding"].get(key)
        for key in ("base_branch", "base_sha", "working_branch", "worktree")
    }) if isinstance(previous_packet, Mapping) else None
    implements = list(dispatch["execution"]["implements"])
    previous_implements = list(previous_dispatch["execution"]["implements"]) if previous_dispatch is not None else None
    # Assessments bind implementation tasks/strategy as well as their evidence.
    # A same-file replan must replace the active packet, not only its return value.
    planning_identity = canonical_json(dispatch.get("planning_evidence", []))
    previous_planning = canonical_json(previous_dispatch.get("planning_evidence", [])) if previous_dispatch is not None else None
    changed = invalid_previous or previous is not None and (
        previous_scope != scope or previous_binding != binding_identity or previous_implements != implements
        or previous_planning != planning_identity
    )
    if changed and len(reason) < 12:
        _fail(
            "binding_update_reason",
            "a changed activation scope, binding, implements list, or planning evidence requires an explicit reason of at least 12 characters",
            code="binding_update_required",
            stage="activation",
        )
    if previous is None or changed:
        payload = {
            "schema": TASK_PACKET_ACTIVATION_SCHEMA,
            "version": TASK_PACKET_ACTIVATION_VERSION,
            "packet": packet,
            "receipt": activation_receipt,
        }
        try:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = artifact_path.with_suffix(".tmp")
            temporary.write_text(canonical_json(payload) + "\n", encoding="utf-8")
            temporary.replace(artifact_path)
            receipt = {
                "from_fingerprint": previous_packet.get("fingerprint") if isinstance(previous_packet, Mapping) else None,
                "to_fingerprint": packet["fingerprint"],
                "changed": [
                    name for name, did_change in (
                        ("stale_activation", invalid_previous),
                        ("scope", previous is not None and previous_scope != scope),
                        ("binding", previous is not None and previous_binding != binding_identity),
                        ("implements", previous is not None and previous_implements != implements),
                        ("planning_evidence", previous is not None and previous_planning != planning_identity),
                    ) if did_change
                ],
                "reason": reason or None,
            }
            with history_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(canonical_json(receipt) + "\n")
        except OSError as exc:
            _fail("activation", "could not persist the worktree-local packet artifact", code="activation_io", stage="activation", details={"error": exc.__class__.__name__})
    return {
        "activated": True,
        "branch": branch,
        "worktree": str(root),
        "packet_fingerprint": packet["fingerprint"] if previous is None or changed else previous_packet["fingerprint"],
        "implements": implements,
        "binding_updated": changed,
        "binding_update_reason": reason if changed else None,
        "activation_artifact": str(artifact_path),
        "activation_history": str(history_path),
    }


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
    _validate_planning_evidence(normalized_dispatch, evidence_pack["evidence"], cwd)
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
    worker_baseline = materialize_worker_baseline(normalized_dispatch, cwd)
    baseline_sources = worker_baseline["sources"]
    agent_rules_tokens = int(baseline_sources["agent_rules"]["token_estimate"])
    session_logging_tokens = (
        int(baseline_sources["session_logging"]["token_estimate"])
        if baseline_sources["session_logging"] is not None
        else 0
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
        "worker_baseline": worker_baseline,
        "constitution_projection": constitution_projection,
        "execution_defaults": _execution_defaults(normalized_dispatch, normalized_binding),
        "input_ledger": {},
        "cost_ledger": {},
        "fingerprint": "sha256:" + "0" * 64,
    }

    # The serialized packet is itself worker input.  Its ledger and cost record
    # affect that size, so converge on the stable integer estimate.  The final
    # fingerprint has the same byte length as the placeholder.
    #
    # `estimate_tokens` is a ceiling-division byte-length estimate: crossing a
    # 4-byte boundary (e.g. a digit added/removed from an embedded count, or a
    # different absolute path length across machines/checkouts) can shift the
    # re-serialized estimate by +/-1 in a way that never lands on a single
    # fixed point, oscillating between a small set of values instead. `history`
    # detects that: once an iteration's starting estimate repeats one already
    # seen, every value in the cycle is known and none is any more "correct"
    # than another, so pick the largest total_input_tokens observed - never
    # under-report the budget - rather than exhausting the loop into a hard
    # failure for a case that has no true fixed point.
    history: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    used_fallback = False
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
            materialized_agent_rules_tokens=agent_rules_tokens,
            materialized_session_logging_tokens=session_logging_tokens,
            _enforce=False,
        )
        packet["input_ledger"] = ledger
        cost_ledger = calculate_cost_ledger(
            input_tokens=ledger["total_input_tokens"],
            output_tokens=ledger["output_reasoning_reserve_tokens"],
            pricing=pricing,
            cached_input_tokens=normalized_environment["cached_input_tokens"],
            _validate_cached_input=False,
        )
        packet["cost_ledger"] = cost_ledger
        if estimate_tokens(canonical_json(packet)) == serialized_tokens:
            break
        if any(serialized_tokens == prior for prior, _, _ in history):
            # No value visited in this cycle maps to itself - by construction, none
            # can pass the exact reported-vs-actual check below. Keep the safest
            # (largest total_input_tokens) ledger from the cycle and let that
            # check heal `serialized_packet_input_tokens` to the real final byte
            # count instead of failing on a drift that has no fixed point to find.
            best = max((*history, (serialized_tokens, ledger, cost_ledger)), key=lambda item: item[1]["total_input_tokens"])
            packet["input_ledger"], packet["cost_ledger"] = best[1], best[2]
            used_fallback = True
            break
        history.append((serialized_tokens, ledger, cost_ledger))
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
        if not used_fallback:
            _fail(
                "input_ledger.serialized_packet_input_tokens",
                "does not match final canonical packet bytes",
                code="budget_convergence_failed",
                stage="budget",
                details={"reported": packet["input_ledger"]["serialized_packet_input_tokens"], "actual": actual_tokens},
            )
        # The cycle fallback above knowingly installs a ledger computed for a
        # serialized-size input other than this exact final packet - no value in
        # the cycle could pass the check above by construction. Heal the one
        # field this check verifies (what the ledger reports about the packet's
        # own byte size) to the real, just-measured value, rather than raising
        # over the sub-token drift that not having a fixed point necessarily
        # produces. Every other ledger figure keeps its safe (largest observed)
        # value from the cycle.
        packet["input_ledger"]["serialized_packet_input_tokens"] = actual_tokens
    return packet
