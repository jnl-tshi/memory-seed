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
_PROFILE_KEYS = frozenset(
    {"schema", "schema_version", "id", "profile_version", "extends", "spec"}
)


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
    if (
        type(profile["schema_version"]) is not int
        or profile["schema_version"] != PROFILE_VERSION
    ):
        _error("schema_version", f"must equal integer {PROFILE_VERSION}")
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
        "schema_version": PROFILE_VERSION,
        "id": profile_id,
        "profile_version": profile_version,
        "extends": extends,
        "spec": copy.deepcopy(dict(spec)),
    }


_PROFILE_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")


def _profile_scalar(token: str, *, path: str, line: int) -> Any:
    """Parse the deliberately small YAML scalar/flow subset profiles document."""
    token = token.strip()
    if token == "[]":
        return []
    if token == "{}":
        return {}
    if token in {"null", "~"}:
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", token):
        return int(token)
    if token.startswith('"'):
        try:
            value = json.loads(token)
        except json.JSONDecodeError as exc:
            _error(path, f"line {line}: malformed quoted scalar")
            raise AssertionError("unreachable") from exc
        if not isinstance(value, str):
            _error(path, f"line {line}: quoted scalar must be a string")
        return value
    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1].replace("''", "'")
    if token.startswith("{") and token.endswith("}"):
        body = token[1:-1].strip()
        if not body:
            return {}
        result: dict[str, Any] = {}
        for item in body.split(","):
            if ":" not in item:
                _error(path, f"line {line}: unsupported flow mapping")
            key, value = item.split(":", 1)
            key = key.strip()
            if _PROFILE_KEY_RE.fullmatch(key) is None or key in result:
                _error(path, f"line {line}: invalid or duplicate flow mapping key")
            result[key] = _profile_scalar(value, path=path, line=line)
        return result
    if token.startswith("[") or token.endswith("]") or any(mark in token for mark in ("{", "}", "#")):
        _error(path, f"line {line}: unsupported YAML scalar")
    if not token:
        _error(path, f"line {line}: scalar cannot be empty")
    return token


def _profile_lines(text: str, *, path: str) -> list[tuple[int, int, str]]:
    lines: list[tuple[int, int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        if "\t" in raw:
            _error(path, f"line {number}: tabs are unsupported")
        stripped = raw.lstrip(" ")
        if stripped.startswith("#"):
            continue
        indent = len(raw) - len(stripped)
        if indent % 2:
            _error(path, f"line {number}: indentation must use two-space levels")
        lines.append((indent, number, stripped))
    return lines


def _read_profile_yaml(text: str, *, path: str) -> Mapping[str, Any]:
    """Read strict profile YAML without adding a package dependency.

    This is intentionally not a general YAML parser.  It accepts exactly the
    profile language: indentation-based maps/lists, list-of-map inheritance,
    documented scalars, and simple flow maps/lists used by list overlays.
    """
    lines = _profile_lines(text, path=path)
    if not lines:
        _error(path, "profile is empty")
    index = 0

    def split_mapping(content: str, number: int) -> tuple[str, str]:
        if ":" not in content:
            _error(path, f"line {number}: expected mapping key")
        key, value = content.split(":", 1)
        key = key.strip()
        if _PROFILE_KEY_RE.fullmatch(key) is None:
            _error(path, f"line {number}: invalid mapping key")
        return key, value.strip()

    def parse_block(indent: int) -> Any:
        nonlocal index
        if index >= len(lines) or lines[index][0] != indent:
            _error(path, "expected an indented profile value")
        is_list = lines[index][2].startswith("- ") or lines[index][2] == "-"
        if is_list:
            values: list[Any] = []
            while index < len(lines) and lines[index][0] == indent:
                _indent, number, content = lines[index]
                if not (content.startswith("- ") or content == "-"):
                    _error(path, f"line {number}: cannot mix maps and lists")
                tail = content[1:].strip()
                index += 1
                if not tail:
                    if index >= len(lines) or lines[index][0] != indent + 2:
                        _error(path, f"line {number}: list item requires a value")
                    values.append(parse_block(indent + 2))
                    continue
                if ":" not in tail:
                    values.append(_profile_scalar(tail, path=path, line=number))
                    continue
                key, value = split_mapping(tail, number)
                item: dict[str, Any] = {}
                if value:
                    item[key] = _profile_scalar(value, path=path, line=number)
                elif index < len(lines) and lines[index][0] == indent + 2:
                    item[key] = parse_block(indent + 2)
                else:
                    _error(path, f"line {number}: mapping value is required")
                if index < len(lines) and lines[index][0] == indent + 2:
                    extra = parse_block(indent + 2)
                    if not isinstance(extra, Mapping):
                        _error(path, f"line {number}: list mapping item requires map fields")
                    if set(item) & set(extra):
                        _error(path, f"line {number}: duplicate mapping key")
                    item.update(extra)
                values.append(item)
            return values

        result: dict[str, Any] = {}
        while index < len(lines) and lines[index][0] == indent:
            _indent, number, content = lines[index]
            if content.startswith("- ") or content == "-":
                _error(path, f"line {number}: cannot mix maps and lists")
            key, value = split_mapping(content, number)
            if key in result:
                _error(path, f"line {number}: duplicate mapping key")
            index += 1
            if value:
                result[key] = _profile_scalar(value, path=path, line=number)
            elif index < len(lines) and lines[index][0] == indent + 2:
                result[key] = parse_block(indent + 2)
            else:
                _error(path, f"line {number}: mapping value is required")
        return result

    result = parse_block(0)
    if index != len(lines):
        _error(path, f"line {lines[index][1]}: unsupported indentation structure")
    return _mapping(result, path)


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RetrievalProfileValidationError(
            f"retrieval profile {path.as_posix()}: unreadable profile file"
        ) from exc
    return _read_profile_yaml(text, path=path.as_posix())


def _profile_path(runtime_root: Path, profile_id: str, profile_version: int) -> Path:
    # Identity validation happens before this join.  The generated exact path is
    # therefore the only lookup surface; no caller-supplied path is accepted.
    candidate = runtime_root / "retrieval-profiles" / profile_id / f"v{profile_version}.yaml"
    try:
        resolved = candidate.resolve()
        resolved.relative_to(runtime_root.resolve())
    except (OSError, ValueError) as exc:
        _error("lookup", "profile path resolves outside the active runtime")
        raise AssertionError("unreachable") from exc
    return resolved


def _list_operation(value: Mapping[str, Any]) -> bool:
    return bool(set(value) & {"append", "remove"})


def _stable_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _empty_list_base(path: str) -> list[Any]:
    """Return the sole list default applicable to a raw partial overlay leaf.

    Parent profiles compose as partial specs.  An append/remove overlay at a
    previously absent leaf therefore needs a list to operate on, but must not
    materialize the rest of the Retrieval Specification defaults.  ``ordering``
    is the one leaf whose semantic baseline is its published default; the
    selector and filter lists start empty.
    """
    if path in {"spec.filters.topics", "spec.filters.paths", "spec.selectors.pinned"}:
        return []
    if path == "spec.ordering":
        return copy.deepcopy(_PROFILE_BASE_SPEC["ordering"])
    _error(path, "append/remove operations require a list parent value")
    raise AssertionError("unreachable")


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
            if key in result:
                result[key] = _merge(result[key], value, path=next_path)
            elif isinstance(value, Mapping) and _list_operation(value):
                result[key] = _merge(_empty_list_base(next_path), value, path=next_path)
            elif isinstance(value, Mapping):
                # Recurse into a new raw map so an operation at a nested
                # absent leaf is applied now, rather than being carried into a
                # later parent as an invalid map-vs-list merge.
                result[key] = _merge({}, value, path=next_path)
            else:
                result[key] = copy.deepcopy(value)
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
        before_required_pins = {
            (str(pin.get("kind")), str(pin.get("id"))): pin
            for pin in before.get("selectors", {}).get("pinned", [])
            if isinstance(pin, Mapping) and pin.get("required", True) is True
        }
        after_pins = {
            (str(pin.get("kind")), str(pin.get("id"))): pin
            for pin in after.get("selectors", {}).get("pinned", [])
            if isinstance(pin, Mapping)
        }
        for identity, pin in before_required_pins.items():
            replacement = after_pins.get(identity)
            if replacement is None:
                _error(path, f"cannot remove required pinned selector {identity[0]}:{identity[1]}")
            if replacement.get("required", True) is not True:
                _error(path, f"cannot demote required pinned selector {identity[0]}:{identity[1]}")
            if replacement.get("reason") != pin.get("reason"):
                _error(path, f"cannot change reason for required pinned selector {identity[0]}:{identity[1]}")
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
        # Profiles are partial overlays.  Defaults are applied exactly once,
        # after the complete parent/child/dispatch composition, so a later
        # parent's omitted clauses cannot reset an earlier parent to defaults.
        combined: dict[str, Any] = {}
        for parent in profile["extends"]:
            parent_spec = visit((parent["id"], parent["profile_version"]))
            before_parent = _merge(_PROFILE_BASE_SPEC, combined, path="spec")
            combined = _merge(combined, parent_spec, path="spec")
            _assert_no_weakening(
                before_parent,
                _merge(_PROFILE_BASE_SPEC, combined, path="spec"),
                path=f"{profile['id']}:v{profile['profile_version']}",
            )
        before = _merge(_PROFILE_BASE_SPEC, combined, path="spec")
        after = _merge(combined, profile["spec"], path="spec")
        _assert_no_weakening(
            before,
            _merge(_PROFILE_BASE_SPEC, after, path="spec"),
            path=f"{profile['id']}:v{profile['profile_version']}",
        )
        stack.pop()
        seen.add(identity)
        return after

    effective = _merge(_PROFILE_BASE_SPEC, visit(requested), path="spec")
    if overrides is not None:
        overrides = _mapping(overrides, "overrides")
        overridden = _merge(effective, overrides, path="overrides")
        _assert_no_weakening(effective, overridden, path="overrides")
        effective = overridden
    return normalize_retrieval_spec_v2(effective)
