"""Project-local Retrieval Specification profile composition.

Profiles are derived control inputs.  They are read from the active runtime and
resolved to an inline Retrieval Specification before the resolver sees them;
they neither create durable evidence nor change the v2 Evidence Pack contract.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .core import resolve_runtime
from .retrieval_spec import SCHEMA, V2_VERSION, normalize_retrieval_spec_v2


PROFILE_SCHEMA = "memory-seed/retrieval-profile"
PROFILE_VERSION = 1
_PROFILE_ID_RE = re.compile(r"[a-z][a-z0-9-]*\Z")
_PROFILE_KEYS = frozenset({"schema", "version", "id", "profile_version", "extends", "spec"})


class RetrievalProfileValidationError(ValueError):
    """Fail-closed profile lookup, composition, or invariant error."""


def _error(path: str, message: str) -> None:
    raise RetrievalProfileValidationError(f"retrieval profile {path}: {message}")


def _identity(profile_id: Any, profile_version: Any, *, path: str) -> tuple[str, int]:
    if not isinstance(profile_id, str) or _PROFILE_ID_RE.fullmatch(profile_id) is None:
        _error(f"{path}.id", "must be a lowercase slug without traversal or separators")
    if isinstance(profile_version, bool) or not isinstance(profile_version, int) or profile_version < 1:
        _error(f"{path}.profile_version", "must be a positive integer")
    return profile_id, profile_version


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _error(path, "must be a mapping")
    return value


def normalize_retrieval_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the strict, file-level profile schema without resolving parents."""
    profile = _mapping(profile, "$")
    for key in profile:
        if not isinstance(key, str) or key not in _PROFILE_KEYS:
            _error(str(key), "is unknown")
    missing = [key for key in _PROFILE_KEYS if key not in profile]
    if missing:
        _error("$", "is missing required field(s): " + ", ".join(sorted(missing)))
    if profile["schema"] != PROFILE_SCHEMA:
        _error("schema", f"must equal {PROFILE_SCHEMA!r}")
    if type(profile["version"]) is not int or profile["version"] != PROFILE_VERSION:
        _error("version", f"must equal integer {PROFILE_VERSION}")
    profile_id, profile_version = _identity(
        profile["id"], profile["profile_version"], path="$"
    )
    extends_in = profile["extends"]
    if not isinstance(extends_in, list):
        _error("extends", "must be a list")
    extends: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for index, parent in enumerate(extends_in):
        parent = _mapping(parent, f"extends[{index}]")
        if set(parent) != {"id", "profile_version"}:
            _error(f"extends[{index}]", "must contain exactly id and profile_version")
        parent_id, parent_version = _identity(
            parent["id"], parent["profile_version"], path=f"extends[{index}]"
        )
        if (parent_id, parent_version) in seen:
            _error(f"extends[{index}]", "duplicates a parent identity")
        seen.add((parent_id, parent_version))
        extends.append({"id": parent_id, "profile_version": parent_version})
    spec = _mapping(profile["spec"], "spec")
    if not spec:
        _error("spec", "must not be empty")
    return {
        "schema": PROFILE_SCHEMA,
        "version": PROFILE_VERSION,
        "id": profile_id,
        "profile_version": profile_version,
        "extends": extends,
        "spec": copy.deepcopy(dict(spec)),
    }


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - package runtime guard
        raise RetrievalProfileValidationError(
            "retrieval profile YAML support is unavailable"
        ) from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RetrievalProfileValidationError(
            f"retrieval profile {path.as_posix()}: unreadable or malformed YAML"
        ) from exc
    return _mapping(data, path.as_posix())


def _profile_path(runtime_root: Path, profile_id: str, profile_version: int) -> Path:
    # Identity validation happens before this join.  The generated exact path is
    # therefore the only lookup surface; no caller-supplied path is accepted.
    return runtime_root / "retrieval-profiles" / profile_id / f"v{profile_version}.yaml"


def _list_operation(value: Mapping[str, Any]) -> bool:
    return bool(set(value) & {"append", "remove"})


def _stable_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _merge(base: Any, patch: Any, *, path: str) -> Any:
    """Depth-merge maps, replace normal lists/scalars, and operate on lists explicitly."""
    if isinstance(patch, Mapping) and _list_operation(patch):
        if set(patch) != {"append", "remove"}:
            _error(path, "list operations must contain exactly append and remove")
        if not isinstance(base, list):
            _error(path, "append/remove operations require a list parent value")
        for key, items in patch.items():
            if not isinstance(items, list):
                _error(f"{path}.{key}", "must be a list")
        removed = {_stable_value(item) for item in patch.get("remove", [])}
        result = [item for item in copy.deepcopy(base) if _stable_value(item) not in removed]
        result.extend(copy.deepcopy(patch.get("append", [])))
        return result
    if isinstance(base, Mapping) and isinstance(patch, Mapping):
        result = copy.deepcopy(dict(base))
        for key, value in patch.items():
            if not isinstance(key, str):
                _error(path, "keys must be strings")
            next_path = f"{path}.{key}" if path else key
            result[key] = _merge(result[key], value, path=next_path) if key in result else copy.deepcopy(value)
        return result
    return copy.deepcopy(patch)


_PROFILE_BASE_SPEC: dict[str, Any] = {
    "schema": SCHEMA,
    "version": V2_VERSION,
    "required": {
        "constitution": True,
        "related_decisions": {"depth": 1},
        "evidence": {"mode": "latest"},
    },
    "optional": {"sessions": None},
    "filters": {"topics": [], "paths": []},
    "ordering": ["required_first", "graph_distance", "recency", "stable_identity"],
    "limits": {"max_entries": 40, "max_tokens": 16000},
    "on_missing": {"required": "fail", "optional": "report"},
    "output": {"include_resolution_trace": False, "include_excerpts": False},
    "selectors": {"pinned": []},
}


def _assert_no_weakening(before: Mapping[str, Any], after: Mapping[str, Any], *, path: str) -> None:
    """Required retrieval coverage is monotonic through inheritance and overrides."""
    try:
        if before["required"]["constitution"] is True and after["required"]["constitution"] is not True:
            _error(path, "cannot weaken required.constitution")
        if before["required"]["evidence"] == {"mode": "latest"} and after["required"]["evidence"] != {"mode": "latest"}:
            _error(path, "cannot weaken required.evidence")
        if after["required"]["related_decisions"]["depth"] < before["required"]["related_decisions"]["depth"]:
            _error(path, "cannot reduce required.related_decisions.depth")
        if before["on_missing"]["required"] == "fail" and after["on_missing"]["required"] != "fail":
            _error(path, "cannot weaken on_missing.required")
    except (KeyError, TypeError):
        # The complete v2 schema validator emits the structural error below.
        return


def load_retrieval_profile(
    profile_id: str,
    profile_version: int,
    cwd: str | Path = ".",
    *,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load one exact project-local profile and return its effective v2 spec.

    Parents compose depth-first in their declared order.  A profile is admitted
    only once in the composition graph; that makes duplicate identities and
    ambiguous diamond reapplication fail before selection.
    """
    requested = _identity(profile_id, profile_version, path="requested")
    runtime = resolve_runtime(cwd)
    profile_root = runtime.memory_dir.resolve()
    stack: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()

    def visit(identity: tuple[str, int]) -> dict[str, Any]:
        if identity in stack:
            cycle = " -> ".join(f"{item_id}:v{item_version}" for item_id, item_version in [*stack, identity])
            _error("extends", f"composition cycle: {cycle}")
        if identity in seen:
            _error("extends", f"duplicate profile identity: {identity[0]}:v{identity[1]}")
        path = _profile_path(profile_root, *identity)
        if not path.is_file():
            _error("lookup", f"profile version was not found: {identity[0]}:v{identity[1]}")
        profile = normalize_retrieval_profile(_read_yaml(path))
        if (profile["id"], profile["profile_version"]) != identity:
            _error("lookup", f"profile identity does not match exact path: {path.as_posix()}")
        stack.append(identity)
        combined = copy.deepcopy(_PROFILE_BASE_SPEC)
        for parent in profile["extends"]:
            parent_spec = visit((parent["id"], parent["profile_version"]))
            combined = _merge(combined, parent_spec, path="spec")
        after = _merge(combined, profile["spec"], path="spec")
        _assert_no_weakening(combined, after, path=f"{profile['id']}:v{profile['profile_version']}")
        stack.pop()
        seen.add(identity)
        return after

    effective = visit(requested)
    if overrides is not None:
        overrides = _mapping(overrides, "overrides")
        overridden = _merge(effective, overrides, path="overrides")
        _assert_no_weakening(effective, overridden, path="overrides")
        effective = overridden
    return normalize_retrieval_spec_v2(effective)
