"""Frozen M0 contract for declarative Retrieval Specification v1 inline data.

This module validates only data and deliberately performs no retrieval.  M1 owns
selection and must use ``SUPPORTED_CLAUSE_READERS`` rather than inventing reader
semantics.  Profiles, composition, Trace, CLI/MCP surfaces, and advanced
selectors are intentionally rejected here before a resolver can inspect them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import PureWindowsPath
from typing import Any


SCHEMA = "memory-seed/retrieval-spec"
VERSION = 1

# Explicit M1 reader ownership.  These strings name existing or planned
# canonical readers, not executable hooks or permissions.
SUPPORTED_CLAUSE_READERS = {
    "required.constitution": "canonical Constitution Markdown reader",
    "required.related_decisions": "canonical session/link graph reader",
    "required.evidence": "canonical Markdown evidence reader",
    "optional.sessions": "canonical session-log reader",
    "filters.topics": "topic-sidecar reader with topic vocabulary expansion",
    "filters.paths": "runtime-bounded canonical Markdown path reader",
    "ordering": "M1 deterministic candidate ordering",
    "limits": "M1 bounded-pack limiter",
    "on_missing": "M1 completeness/failure classifier",
    "output": "M1 Evidence Pack formatter",
}

DEFAULT_ORDERING = ("required_first", "graph_distance", "recency", "stable_identity")
DEFAULT_LIMITS = {"max_entries": 40, "max_tokens": 16_000}
DEFAULT_ON_MISSING = {"required": "fail", "optional": "report"}
DEFAULT_OUTPUT = {"include_resolution_trace": False, "include_excerpts": False}

_TOP_LEVEL = frozenset({"schema", "version", "required", "optional", "filters", "ordering", "limits", "on_missing", "output"})
_DEFERRED = {
    "id": "named specs are deferred; submit an inline spec without 'id'",
    "profile": "profiles are deferred; submit an inline spec",
    "profiles": "profiles are deferred; submit an inline spec",
    "extends": "profile composition is deferred",
    "extensions": "extensions are deferred in the frozen v1 inline contract",
    "required.related_adrs": "ADR selectors are deferred",
    "optional.links": "link selectors are deferred",
    "optional.tests": "test selectors are deferred",
    "optional.alternatives": "alternative selectors are deferred",
    "filters.include_superseded": "supersession filtering is deferred",
    "limits.max_sections_per_entry": "per-entry section limits are deferred",
    "limits.timeout_ms": "timeouts are deferred",
    "output.format": "output format selection is deferred; M1 emits its fixed Evidence Pack format",
}


class RetrievalSpecValidationError(ValueError):
    """A precise fail-before-selection error for an inline Retrieval Spec."""


def _error(path: str, message: str) -> None:
    raise RetrievalSpecValidationError(f"retrieval spec {path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _error(path, "must be a mapping")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _error(path, "must be a boolean")
    return value


def _positive_int(value: Any, path: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > maximum:
        _error(path, f"must be an integer from 1 through {maximum}")
    return value


def _known_keys(mapping: Mapping[str, Any], path: str, allowed: set[str]) -> None:
    for key in mapping:
        if not isinstance(key, str):
            _error(path, "keys must be strings")
        full_path = f"{path}.{key}" if path else key
        if full_path in _DEFERRED:
            _error(full_path, f"is unsupported: {_DEFERRED[full_path]}")
        if key not in allowed:
            _error(full_path, "is unknown; unknown clauses are rejected before selection")


def _string_list(
    value: Any,
    path: str,
    *,
    path_values: bool = False,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        _error(
            path,
            "must be a list of strings"
            if allow_empty
            else "must be a non-empty list of strings",
        )
    result: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str) or not item.strip():
            _error(item_path, "must be a non-empty string")
        windows_path = PureWindowsPath(item)
        if path_values and (
            item.startswith(("/", "\\"))
            or "\\" in item
            or windows_path.drive
            or windows_path.is_absolute()
            or ".." in item.split("/")
        ):
            _error(item_path, "must be a runtime-relative POSIX path without parent traversal")
        result.append(item)
    if len(set(result)) != len(result):
        _error(path, "must not contain duplicates")
    return result


def normalize_retrieval_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return the complete, deterministic M0 v1 inline contract.

    Omitted optional clauses receive bounded defaults; omitted filters select no
    topic/path candidates rather than silently broadening a request.
    """
    spec = _mapping(spec, "$")
    _known_keys(spec, "", set(_TOP_LEVEL))
    for required_key in ("schema", "version", "required"):
        if required_key not in spec:
            _error(required_key, "is required")
    if spec["schema"] != SCHEMA:
        _error("schema", f"must equal {SCHEMA!r}")
    if type(spec["version"]) is not int or spec["version"] != VERSION:
        _error("version", f"must equal integer {VERSION}")

    required = _mapping(spec["required"], "required")
    _known_keys(required, "required", {"constitution", "related_decisions", "evidence"})
    for key in ("constitution", "related_decisions", "evidence"):
        if key not in required:
            _error(f"required.{key}", "is required for the M1 inline contract")
    if _bool(required["constitution"], "required.constitution") is not True:
        _error("required.constitution", "must be true; Constitution coverage cannot be disabled")
    related = _mapping(required["related_decisions"], "required.related_decisions")
    _known_keys(related, "required.related_decisions", {"depth"})
    if set(related) != {"depth"}:
        _error("required.related_decisions", "must contain exactly 'depth'")
    evidence = _mapping(required["evidence"], "required.evidence")
    _known_keys(evidence, "required.evidence", {"mode"})
    if evidence.get("mode") != "latest" or set(evidence) != {"mode"}:
        _error("required.evidence", "must contain exactly mode: 'latest'")

    optional_in = _mapping(spec.get("optional", {}), "optional")
    _known_keys(optional_in, "optional", {"sessions"})
    sessions: dict[str, int] | None = None
    if "sessions" in optional_in and optional_in["sessions"] is not None:
        session_map = _mapping(optional_in["sessions"], "optional.sessions")
        _known_keys(session_map, "optional.sessions", {"neighbouring_entries"})
        if set(session_map) != {"neighbouring_entries"}:
            _error("optional.sessions", "must contain exactly 'neighbouring_entries'")
        sessions = {"neighbouring_entries": _positive_int(session_map["neighbouring_entries"], "optional.sessions.neighbouring_entries", maximum=50)}

    filters_in = _mapping(spec.get("filters", {}), "filters")
    _known_keys(filters_in, "filters", {"topics", "paths"})
    filters: dict[str, list[str]] = {"topics": [], "paths": []}
    if "topics" in filters_in:
        filters["topics"] = _string_list(
            filters_in["topics"],
            "filters.topics",
            allow_empty=True,
        )
    if "paths" in filters_in:
        filters["paths"] = _string_list(
            filters_in["paths"],
            "filters.paths",
            path_values=True,
            allow_empty=True,
        )

    ordering = list(DEFAULT_ORDERING) if "ordering" not in spec else _string_list(spec["ordering"], "ordering")
    if ordering != list(DEFAULT_ORDERING):
        _error("ordering", f"must equal {list(DEFAULT_ORDERING)!r} in this v1 slice")

    limits_in = _mapping(spec.get("limits", {}), "limits")
    _known_keys(limits_in, "limits", {"max_entries", "max_tokens"})
    limits = dict(DEFAULT_LIMITS)
    for name, maximum in (("max_entries", 100), ("max_tokens", 20_000)):
        if name in limits_in:
            limits[name] = _positive_int(limits_in[name], f"limits.{name}", maximum=maximum)

    missing_in = _mapping(spec.get("on_missing", {}), "on_missing")
    _known_keys(missing_in, "on_missing", {"required", "optional"})
    on_missing = dict(DEFAULT_ON_MISSING)
    for name, value in missing_in.items():
        if value != DEFAULT_ON_MISSING[name]:
            _error(f"on_missing.{name}", f"must equal {DEFAULT_ON_MISSING[name]!r} in this v1 slice")

    output_in = _mapping(spec.get("output", {}), "output")
    _known_keys(output_in, "output", {"include_resolution_trace", "include_excerpts"})
    output = dict(DEFAULT_OUTPUT)
    for name in output:
        if name in output_in:
            output[name] = _bool(output_in[name], f"output.{name}")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "required": {
            "constitution": True,
            "related_decisions": {"depth": _positive_int(related["depth"], "required.related_decisions.depth", maximum=5)},
            "evidence": {"mode": "latest"},
        },
        "optional": {"sessions": sessions},
        "filters": filters,
        "ordering": ordering,
        "limits": limits,
        "on_missing": on_missing,
        "output": output,
    }


def canonical_retrieval_spec_json(spec: Mapping[str, Any]) -> str:
    """Return canonical normalized JSON used as the full v1 fingerprint input."""
    return json.dumps(normalize_retrieval_spec(spec), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def retrieval_spec_fingerprint(spec: Mapping[str, Any]) -> str:
    """Return the stable sha256 fingerprint of canonical normalized JSON."""
    return "sha256:" + hashlib.sha256(canonical_retrieval_spec_json(spec).encode("utf-8")).hexdigest()


def classify_missing_clause(required: bool) -> str:
    """Return M1's frozen missing-input disposition without performing selection."""
    return DEFAULT_ON_MISSING["required" if required else "optional"]
