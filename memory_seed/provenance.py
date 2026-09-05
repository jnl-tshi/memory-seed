"""Reference-only contracts for decision-to-Git provenance.

This module deliberately defines data contracts only.  It neither invokes Git
nor reads or writes a provenance sidecar.  Git adapters can derive bindings,
while hook and surface adapters can use the deterministic validation and
activation contracts below without duplicating policy.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence, TypedDict


PROVENANCE_BINDING_SCHEMA = "memory-seed/provenance-binding"
PROVENANCE_LEDGER_SCHEMA = "memory-seed/provenance-ledger"
PROVENANCE_REPLACEMENT_SCHEMA = "memory-seed/provenance-replacement"
PROVENANCE_PROJECTION_SCHEMA = "memory-seed/provenance-projection"
PROVENANCE_RUNTIME_SCHEMA = "memory-seed/provenance-runtime"
PACKET_IMPLEMENTS_ACTIVATION_SCHEMA = "memory-seed/packet-implements-activation"
PATCH_BYTES_SCHEMA = "memory-seed/git-unified-hunk-patch-bytes"
PROVENANCE_SCHEMA_VERSION = 1
PATCH_BYTES_VERSION = 1
PATCH_BYTES_CANONICALIZATION = "exact-hunk-body-bytes-v1"

_DECISION_REF_RE = re.compile(
    r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z"
)
_GIT_OBJECT_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OWNER_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
_ACTOR_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_PATH_METACHAR_RE = re.compile(r'[*?\[\]{}!<>:"|]')
_HEX_ID_RE = re.compile(r"(?:msh|msb|msr|mspa)_[0-9a-f]{64}\Z")
_BINDING_ID_RE = re.compile(r"msb_[0-9a-f]{64}\Z")
REPLACEMENT_REASONS = frozenset(
    {"corrected-reference", "superseded-reference", "withdrawn-reference"}
)
PROJECTION_EVIDENCE_STATES = frozenset(
    {"unverified", "available", "git-unavailable", "missing-git-object", "projection-unavailable"}
)
_RANGE_KEYS = frozenset({"start", "count"})
_PATCH_BYTES_KEYS = frozenset({"schema", "version", "canonicalization", "digest"})
_AUTHOR_KEYS = frozenset({"provenance", "actor"})
_ACTOR_KEYS = frozenset({"kind", "id"})
_HUNK_KEYS = frozenset({"hunk_id", "old_range", "new_range", "patch_bytes", "context_hint"})
_BINDING_KEYS = frozenset(
    {
        "schema",
        "version",
        "binding_id",
        "decision_ref",
        "authorship",
        "commit",
        "parent",
        "file",
        "old_blob",
        "new_blob",
        "hunks",
    }
)
_REPLACEMENT_KEYS = frozenset(
    {
        "schema",
        "version",
        "replacement_id",
        "replaces",
        "replacement",
        "reason",
        "reason_decision_ref",
    }
)
_LEDGER_KEYS = frozenset({"schema", "version", "runtime", "bindings", "replacements"})
_RUNTIME_KEYS = frozenset(
    {"schema", "version", "runtime_path", "owner", "sidecar_path"}
)
_OWNER_KEYS = frozenset({"kind", "id", "state"})
_ACTIVATION_KEYS = frozenset(
    {
        "schema",
        "version",
        "activation_id",
        "packet_fingerprint",
        "implements",
        "binding_ids",
        "runtime",
    }
)


class HunkReference(TypedDict):
    """One reference-only changed range; it never contains source lines."""

    hunk_id: str
    old_range: dict[str, int]
    new_range: dict[str, int]
    patch_bytes: dict[str, Any]
    context_hint: None


class ProvenanceBinding(TypedDict):
    """One decision's immutable reference to one commit/file diff."""

    schema: str
    version: int
    binding_id: str
    decision_ref: str
    authorship: dict[str, Any]
    commit: str
    parent: str | None
    file: str
    old_blob: str | None
    new_blob: str | None
    hunks: list[HunkReference]


class PacketImplementsActivation(TypedDict):
    """Normalized hook-ready data, intentionally without a commit message."""

    schema: str
    version: int
    activation_id: str
    packet_fingerprint: str
    implements: list[str]
    binding_ids: list[str]
    runtime: dict[str, Any]


@dataclass(frozen=True)
class ProvenanceValidationIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class ProvenanceValidationResult:
    """Non-throwing result for adapters that need machine-readable failures."""

    value: dict[str, Any] | None
    issues: tuple[ProvenanceValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "value": self.value,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class ProvenanceValidationError(ValueError):
    """Fail-closed validation error for malformed provenance contracts."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"provenance {code} at {path}: {message}")

    def to_issue(self) -> ProvenanceValidationIssue:
        return ProvenanceValidationIssue(self.code, self.path, self.message)


def _fail(path: str, message: str, *, code: str = "invalid_provenance") -> None:
    raise ProvenanceValidationError(code, path, message)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be a mapping")
    return value


def _exact_keys(
    value: Mapping[str, Any], path: str, allowed: frozenset[str]
) -> None:
    unknown = sorted(str(key) for key in value if key not in allowed)
    missing = sorted(allowed - set(value))
    if unknown:
        _fail(path, f"contains unknown fields: {', '.join(unknown)}")
    if missing:
        _fail(path, f"is missing required fields: {', '.join(missing)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _nonnegative_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(path, "must be a non-negative integer")
    return value


def _exact_decision_ref(value: Any, path: str) -> str:
    result = _string(value, path)
    if not _DECISION_REF_RE.fullmatch(result):
        _fail(path, "must be an exact <entry_id>:dN decision reference")
    return result


def _object_id(value: Any, path: str, *, nullable: bool = False) -> str | None:
    result = _optional_string(value, path) if nullable else _string(value, path)
    if result is not None and not _GIT_OBJECT_RE.fullmatch(result):
        _fail(path, "must be a lower-case 40- or 64-character Git object id")
    return result


def _sha256(value: Any, path: str) -> str:
    result = _string(value, path)
    if not _SHA256_RE.fullmatch(result):
        _fail(path, "must be a sha256:<64 lowercase hex> digest")
    return result


def _relative_path(value: Any, path: str) -> str:
    text = _string(value, path)
    normalized = text.replace("\\", "/")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(normalized)
    segments = normalized.split("/")
    if (
        windows.is_absolute()
        or windows.drive
        or posix.is_absolute()
        or any(part in {"", ".", ".."} for part in segments)
        or _PATH_METACHAR_RE.search(normalized)
        or any(part.endswith((".", " ")) or PureWindowsPath(part).is_reserved() for part in segments)
    ):
        _fail(path, "must be one exact safe runtime-relative POSIX path")
    return PurePosixPath(normalized).as_posix()


def _runtime_relative_path(value: Any, path: str) -> str:
    """Accept the runtime root itself while retaining file-path safety rules."""

    text = _string(value, path)
    if text == ".":
        return text
    return _relative_path(text, path)


def _range(value: Any, path: str) -> dict[str, int]:
    item = _mapping(value, path)
    _exact_keys(item, path, _RANGE_KEYS)
    return {
        "start": _nonnegative_int(item["start"], f"{path}.start"),
        "count": _nonnegative_int(item["count"], f"{path}.count"),
    }


def _patch_bytes(value: Any, path: str) -> dict[str, Any]:
    """Validate the digest of one exact, unstored Git hunk-body byte sequence."""

    item = _mapping(value, path)
    _exact_keys(item, path, _PATCH_BYTES_KEYS)
    if item["schema"] != PATCH_BYTES_SCHEMA:
        _fail(f"{path}.schema", f"must equal {PATCH_BYTES_SCHEMA!r}")
    if item["version"] != PATCH_BYTES_VERSION:
        _fail(f"{path}.version", f"must equal {PATCH_BYTES_VERSION}")
    if item["canonicalization"] != PATCH_BYTES_CANONICALIZATION:
        _fail(f"{path}.canonicalization", f"must equal {PATCH_BYTES_CANONICALIZATION!r}")
    return {
        "schema": PATCH_BYTES_SCHEMA,
        "version": PATCH_BYTES_VERSION,
        "canonicalization": PATCH_BYTES_CANONICALIZATION,
        "digest": _sha256(item["digest"], f"{path}.digest"),
    }


def patch_bytes_digest(digest: str) -> dict[str, Any]:
    """Build a patch-byte contribution without accepting or storing patch bytes."""

    return _patch_bytes(
        {
            "schema": PATCH_BYTES_SCHEMA,
            "version": PATCH_BYTES_VERSION,
            "canonicalization": PATCH_BYTES_CANONICALIZATION,
            "digest": digest,
        },
        "patch_bytes",
    )


def _authorship(value: Any, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_keys(item, path, _AUTHOR_KEYS)
    provenance = _string(item["provenance"], f"{path}.provenance")
    if provenance not in {"first-hand", "reconstructed"}:
        _fail(f"{path}.provenance", "must be 'first-hand' or 'reconstructed'")
    actor = _mapping(item["actor"], f"{path}.actor")
    _exact_keys(actor, f"{path}.actor", _ACTOR_KEYS)
    kind = _string(actor["kind"], f"{path}.actor.kind")
    actor_id = _string(actor["id"], f"{path}.actor.id")
    if kind not in {"person", "agent", "system"}:
        _fail(f"{path}.actor.kind", "must be 'person', 'agent', or 'system'")
    if not _ACTOR_ID_RE.fullmatch(actor_id):
        _fail(f"{path}.actor.id", "must be a compact actor identifier")
    return {"provenance": provenance, "actor": {"kind": kind, "id": actor_id}}


def _canonical_json(value: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _identity(prefix: str, value: Mapping[str, Any] | Sequence[Any]) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def hunk_id(
    *,
    commit: str,
    parent: str | None,
    file: str,
    old_range: Mapping[str, Any],
    new_range: Mapping[str, Any],
    patch_bytes: Mapping[str, Any],
) -> str:
    """Return the stable identity for a reference-only hunk.

    The identifier is independent of a decision so one observed change can be
    linked to several decisions without inventing multiple hunks.
    """

    normalized_old = _range(old_range, "old_range")
    normalized_new = _range(new_range, "new_range")
    normalized_patch = _patch_bytes(patch_bytes, "patch_bytes")
    return _identity(
        "msh",
        {
            "commit": _object_id(commit, "commit"),
            "parent": _object_id(parent, "parent", nullable=True),
            "file": _relative_path(file, "file"),
            "old_range": normalized_old,
            "new_range": normalized_new,
            "patch_bytes": normalized_patch,
        },
    )


def _normalize_hunk(
    value: Any,
    path: str,
    *,
    commit: str,
    parent: str | None,
    file: str,
)-> HunkReference:
    item = _mapping(value, path)
    _exact_keys(item, path, _HUNK_KEYS)
    old_range = _range(item["old_range"], f"{path}.old_range")
    new_range = _range(item["new_range"], f"{path}.new_range")
    if item["context_hint"] is not None:
        _fail(f"{path}.context_hint", "must be null; source locators are derived later")
    patch = _patch_bytes(item["patch_bytes"], f"{path}.patch_bytes")
    expected_id = hunk_id(
        commit=commit,
        parent=parent,
        file=file,
        old_range=old_range,
        new_range=new_range,
        patch_bytes=patch,
    )
    supplied_id = _string(item["hunk_id"], f"{path}.hunk_id")
    if supplied_id != expected_id:
        _fail(f"{path}.hunk_id", "does not match the deterministic hunk identity")
    return {
        "hunk_id": supplied_id,
        "old_range": old_range,
        "new_range": new_range,
        "patch_bytes": patch,
        "context_hint": None,
    }


def binding_id(binding: Mapping[str, Any]) -> str:
    """Return a binding identity after validating its immutable payload."""

    normalized = normalize_binding(binding, verify_binding_id=False)
    identity_fields = {key: value for key, value in normalized.items() if key != "binding_id"}
    return _identity("msb", identity_fields)


def normalize_binding(
    value: Mapping[str, Any], *, verify_binding_id: bool = True
) -> ProvenanceBinding:
    """Normalize one binding and reject text-bearing or unknown fields."""

    item = _mapping(value, "binding")
    _exact_keys(item, "binding", _BINDING_KEYS)
    if item["schema"] != PROVENANCE_BINDING_SCHEMA:
        _fail("binding.schema", f"must equal {PROVENANCE_BINDING_SCHEMA!r}")
    if item["version"] != PROVENANCE_SCHEMA_VERSION:
        _fail("binding.version", f"must equal {PROVENANCE_SCHEMA_VERSION}")
    commit = _object_id(item["commit"], "binding.commit")
    assert commit is not None
    parent = _object_id(item["parent"], "binding.parent", nullable=True)
    file = _relative_path(item["file"], "binding.file")
    old_blob = _object_id(item["old_blob"], "binding.old_blob", nullable=True)
    new_blob = _object_id(item["new_blob"], "binding.new_blob", nullable=True)
    if old_blob is None and new_blob is None:
        _fail("binding", "must reference an old or new blob")
    hunks_value = item["hunks"]
    if not isinstance(hunks_value, list) or not hunks_value:
        _fail("binding.hunks", "must be a non-empty list")
    hunks = [
        _normalize_hunk(
            hunk,
            f"binding.hunks[{index}]",
            commit=commit,
            parent=parent,
            file=file,
        )
        for index, hunk in enumerate(hunks_value)
    ]
    hunk_ids = [hunk["hunk_id"] for hunk in hunks]
    if len(hunk_ids) != len(set(hunk_ids)):
        _fail("binding.hunks", "must not repeat a deterministic hunk identity")
    normalized: ProvenanceBinding = {
        "schema": PROVENANCE_BINDING_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "binding_id": _string(item["binding_id"], "binding.binding_id"),
        "decision_ref": _exact_decision_ref(item["decision_ref"], "binding.decision_ref"),
        "authorship": _authorship(item["authorship"], "binding.authorship"),
        "commit": commit,
        "parent": parent,
        "file": file,
        "old_blob": old_blob,
        "new_blob": new_blob,
        "hunks": hunks,
    }
    expected_id = binding_id(normalized) if verify_binding_id else None
    if verify_binding_id and normalized["binding_id"] != expected_id:
        _fail("binding.binding_id", "does not match the deterministic binding identity")
    return normalized


def build_binding(
    *,
    decision_ref: str,
    authorship: Mapping[str, Any],
    commit: str,
    parent: str | None,
    file: str,
    old_blob: str | None,
    new_blob: str | None,
    hunks: Sequence[Mapping[str, Any]],
) -> ProvenanceBinding:
    """Build a canonical binding from Git-derived references supplied by an adapter."""

    base: dict[str, Any] = {
        "schema": PROVENANCE_BINDING_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "binding_id": "pending",
        "decision_ref": decision_ref,
        "authorship": dict(authorship),
        "commit": commit,
        "parent": parent,
        "file": file,
        "old_blob": old_blob,
        "new_blob": new_blob,
        "hunks": list(hunks),
    }
    normalized_without_id = normalize_binding(base, verify_binding_id=False)
    base["binding_id"] = binding_id(normalized_without_id)
    return normalize_binding(base)


def replacement_id(
    *, replaces: str, replacement: Mapping[str, Any], reason: str, reason_decision_ref: str
) -> str:
    normalized = normalize_binding(replacement)
    replacement_ref = _binding_reference(replaces, "replaces")
    return _identity(
        "msr",
        {
            "replaces": replacement_ref,
            "replacement": normalized["binding_id"],
            "reason": _replacement_reason(reason, "reason"),
            "reason_decision_ref": _exact_decision_ref(reason_decision_ref, "reason_decision_ref"),
        },
    )


def _binding_reference(value: Any, path: str) -> str:
    result = _string(value, path)
    if not _BINDING_ID_RE.fullmatch(result):
        _fail(path, "must be an msb_<sha256> binding identity")
    return result


def _replacement_reason(value: Any, path: str) -> str:
    reason = _string(value, path)
    if reason not in REPLACEMENT_REASONS:
        _fail(path, "must be a declared replacement reason code")
    return reason


def normalize_replacement(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _mapping(value, "replacement")
    _exact_keys(item, "replacement", _REPLACEMENT_KEYS)
    if item["schema"] != PROVENANCE_REPLACEMENT_SCHEMA:
        _fail("replacement.schema", f"must equal {PROVENANCE_REPLACEMENT_SCHEMA!r}")
    if item["version"] != PROVENANCE_SCHEMA_VERSION:
        _fail("replacement.version", f"must equal {PROVENANCE_SCHEMA_VERSION}")
    replaces = _binding_reference(item["replaces"], "replacement.replaces")
    successor = normalize_binding(_mapping(item["replacement"], "replacement.replacement"))
    reason = _replacement_reason(item["reason"], "replacement.reason")
    reason_ref = _exact_decision_ref(item["reason_decision_ref"], "replacement.reason_decision_ref")
    supplied_id = _string(item["replacement_id"], "replacement.replacement_id")
    expected_id = replacement_id(replaces=replaces, replacement=successor, reason=reason, reason_decision_ref=reason_ref)
    if supplied_id != expected_id:
        _fail("replacement.replacement_id", "does not match the deterministic replacement identity")
    if replaces == successor["binding_id"]:
        _fail("replacement.replaces", "cannot replace itself")
    return {
        "schema": PROVENANCE_REPLACEMENT_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "replacement_id": supplied_id,
        "replaces": replaces,
        "replacement": successor,
        "reason": reason,
        "reason_decision_ref": reason_ref,
    }


def build_replacement(
    *, replaces: str, replacement: Mapping[str, Any], reason: str, reason_decision_ref: str
) -> dict[str, Any]:
    successor = normalize_binding(replacement)
    record = {
        "schema": PROVENANCE_REPLACEMENT_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "replacement_id": "pending",
        "replaces": replaces,
        "replacement": successor,
        "reason": reason,
        "reason_decision_ref": reason_decision_ref,
    }
    record["replacement_id"] = replacement_id(
        replaces=replaces, replacement=successor, reason=reason, reason_decision_ref=reason_decision_ref
    )
    return normalize_replacement(record)


def normalize_ledger(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the complete append-only record set and replacement graph."""

    item = _mapping(value, "ledger")
    _exact_keys(item, "ledger", _LEDGER_KEYS)
    if item["schema"] != PROVENANCE_LEDGER_SCHEMA:
        _fail("ledger.schema", f"must equal {PROVENANCE_LEDGER_SCHEMA!r}")
    if item["version"] != PROVENANCE_SCHEMA_VERSION:
        _fail("ledger.version", f"must equal {PROVENANCE_SCHEMA_VERSION}")
    runtime = normalize_runtime_ownership(_mapping(item["runtime"], "ledger.runtime"))
    raw_bindings = item["bindings"]
    raw_replacements = item["replacements"]
    if not isinstance(raw_bindings, list) or not isinstance(raw_replacements, list):
        _fail("ledger", "bindings and replacements must be lists")
    bindings = [normalize_binding(_mapping(record, f"ledger.bindings[{index}]")) for index, record in enumerate(raw_bindings)]
    binding_by_id = {record["binding_id"]: record for record in bindings}
    if len(binding_by_id) != len(bindings):
        _fail("ledger.bindings", "must not repeat a binding identity")
    replacements = [
        normalize_replacement(_mapping(record, f"ledger.replacements[{index}]"))
        for index, record in enumerate(raw_replacements)
    ]
    replacement_ids = [record["replacement_id"] for record in replacements]
    if len(replacement_ids) != len(set(replacement_ids)):
        _fail("ledger.replacements", "must not repeat a replacement identity")
    replaced_ids: set[str] = set()
    successor_ids: set[str] = set()
    for index, record in enumerate(replacements):
        target = record["replaces"]
        successor = record["replacement"]
        successor_id = successor["binding_id"]
        if target not in binding_by_id:
            _fail(f"ledger.replacements[{index}].replaces", "must refer to a ledger binding")
        if successor_id not in binding_by_id:
            _fail(f"ledger.replacements[{index}].replacement", "must be present in ledger.bindings")
        if binding_by_id[successor_id] != successor:
            _fail(f"ledger.replacements[{index}].replacement", "must exactly match its ledger binding")
        if target in replaced_ids:
            _fail("ledger.replacements", "must not create competing replacements")
        if successor_id in successor_ids:
            _fail("ledger.replacements", "must not reuse one successor for multiple replacements")
        replaced_ids.add(target)
        successor_ids.add(successor_id)
    _assert_acyclic_replacements(replacements)
    return {
        "schema": PROVENANCE_LEDGER_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "runtime": runtime,
        "bindings": bindings,
        "replacements": replacements,
    }


def build_ledger(
    *, runtime: Mapping[str, Any], bindings: Sequence[Mapping[str, Any]] = (),
    replacements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return normalize_ledger(
        {
            "schema": PROVENANCE_LEDGER_SCHEMA,
            "version": PROVENANCE_SCHEMA_VERSION,
            "runtime": dict(runtime),
            "bindings": list(bindings),
            "replacements": list(replacements),
        }
    )


def _assert_acyclic_replacements(replacements: Sequence[Mapping[str, Any]]) -> None:
    successors = {
        record["replaces"]: record["replacement"]["binding_id"]
        for record in replacements
    }
    for start in successors:
        seen: set[str] = set()
        current = start
        while current in successors:
            if current in seen:
                _fail("ledger.replacements", "must not create a replacement cycle")
            seen.add(current)
            current = successors[current]


def validate_binding(value: Mapping[str, Any]) -> ProvenanceValidationResult:
    try:
        return ProvenanceValidationResult(dict(normalize_binding(value)))
    except ProvenanceValidationError as error:
        return ProvenanceValidationResult(None, (error.to_issue(),))


def validate_ledger(value: Mapping[str, Any]) -> ProvenanceValidationResult:
    try:
        return ProvenanceValidationResult(normalize_ledger(value))
    except ProvenanceValidationError as error:
        return ProvenanceValidationResult(None, (error.to_issue(),))


def append_replacement(
    ledger: Mapping[str, Any], *, replaces: str, replacement: Mapping[str, Any], reason: str,
    reason_decision_ref: str,
) -> dict[str, Any]:
    """Return an append-only corrected ledger; no existing record is mutated."""

    normalized = normalize_ledger(ledger)
    authorization = authorize_runtime_operation(normalized["runtime"], operation="append")
    if not authorization.ok:
        issue = authorization.issues[0]
        _fail(issue.path, issue.message, code=issue.code)
    target = _binding_reference(replaces, "replaces")
    existing = {binding["binding_id"] for binding in normalized["bindings"]}
    if target not in existing:
        _fail("replaces", "must refer to an existing ledger binding")
    if any(record["replaces"] == target for record in normalized["replacements"]):
        _fail("replaces", "already has a replacement")
    successor = normalize_binding(replacement)
    if successor["binding_id"] in existing:
        _fail("replacement.binding_id", "must be a newly appended binding")
    record = build_replacement(
        replaces=target, replacement=successor, reason=reason,
        reason_decision_ref=reason_decision_ref,
    )
    return normalize_ledger(
        {
            **normalized,
            "bindings": [*normalized["bindings"], successor],
            "replacements": [*normalized["replacements"], record],
        }
    )


def validate_append_only_update(
    previous: Mapping[str, Any], candidate: Mapping[str, Any]
) -> ProvenanceValidationResult:
    """Ensure a proposed write only extends, never rewrites, the ledger."""

    try:
        before = normalize_ledger(previous)
        after = normalize_ledger(candidate)
        if before["runtime"] != after["runtime"]:
            _fail("candidate.runtime", "must retain the owned runtime", code="not_append_only")
        before_bindings = [record["binding_id"] for record in before["bindings"]]
        after_bindings = [record["binding_id"] for record in after["bindings"]]
        before_replacements = [record["replacement_id"] for record in before["replacements"]]
        after_replacements = [record["replacement_id"] for record in after["replacements"]]
        if after_bindings[: len(before_bindings)] != before_bindings:
            _fail("candidate.bindings", "must retain every existing binding in order", code="not_append_only")
        if after_replacements[: len(before_replacements)] != before_replacements:
            _fail("candidate.replacements", "must retain every existing replacement in order", code="not_append_only")
        if (
            len(after_bindings) > len(before_bindings)
            or len(after_replacements) > len(before_replacements)
        ):
            authorization = authorize_runtime_operation(before["runtime"], operation="append")
            if not authorization.ok:
                issue = authorization.issues[0]
                _fail(issue.path, issue.message, code=issue.code)
        return ProvenanceValidationResult(after)
    except ProvenanceValidationError as error:
        return ProvenanceValidationResult(None, (error.to_issue(),))


def project_ledger(
    ledger: Mapping[str, Any], *, evidence_state: str = "unverified"
) -> dict[str, Any]:
    """Return records plus an adapter-supplied Git evidence state; never probe Git here."""

    normalized = normalize_ledger(ledger)
    replaced = {record["replaces"] for record in normalized["replacements"]}
    active = [
        record["binding_id"]
        for record in normalized["bindings"]
        if record["binding_id"] not in replaced
    ]
    state = _string(evidence_state, "evidence_state")
    if state not in PROJECTION_EVIDENCE_STATES:
        _fail("evidence_state", "must be a declared projection evidence state")
    return {
        "schema": PROVENANCE_PROJECTION_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "runtime": normalized["runtime"],
        "bindings": normalized["bindings"],
        "replacements": normalized["replacements"],
        "active_binding_ids": active,
        "replaced_binding_ids": sorted(replaced),
        "evidence_state": state,
    }


def provenance_sidecar_path(owner: Mapping[str, Any]) -> str:
    """Return the only sidecar path owned by the declared runtime owner."""

    normalized = _normalize_owner(owner, "owner")
    if normalized["kind"] == "runtime":
        return ".memory-seed/provenance/bindings.md"
    if normalized["kind"] == "pod":
        return f".memory-seed/provenance/pods/{normalized['id']}.md"
    return f".memory-seed/provenance/detached-roots/{normalized['id']}.md"


def _normalize_owner(value: Any, path: str) -> dict[str, str]:
    item = _mapping(value, path)
    _exact_keys(item, path, _OWNER_KEYS)
    kind = _string(item["kind"], f"{path}.kind")
    owner_id = _string(item["id"], f"{path}.id")
    state = _string(item["state"], f"{path}.state")
    if kind not in {"runtime", "pod", "detached-former-root"}:
        _fail(f"{path}.kind", "must be 'runtime', 'pod', or 'detached-former-root'")
    if not _OWNER_ID_RE.fullmatch(owner_id):
        _fail(f"{path}.id", "must be a lower-case owner identifier")
    if kind == "runtime" and owner_id != "root":
        _fail(f"{path}.id", "must be 'root' for a runtime owner")
    valid_states = {
        "runtime": {"active"},
        "pod": {"active", "retired"},
        "detached-former-root": {"detached"},
    }
    if state not in valid_states[kind]:
        _fail(f"{path}.state", "is not valid for this owner kind")
    return {"kind": kind, "id": owner_id, "state": state}


def normalize_runtime_ownership(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate owner state without reading a runtime or mutating lifecycle state."""

    item = _mapping(value, "runtime")
    _exact_keys(item, "runtime", _RUNTIME_KEYS)
    if item["schema"] != PROVENANCE_RUNTIME_SCHEMA:
        _fail("runtime.schema", f"must equal {PROVENANCE_RUNTIME_SCHEMA!r}")
    if item["version"] != PROVENANCE_SCHEMA_VERSION:
        _fail("runtime.version", f"must equal {PROVENANCE_SCHEMA_VERSION}")
    runtime_path = _runtime_relative_path(item["runtime_path"], "runtime.runtime_path")
    owner = _normalize_owner(item["owner"], "runtime.owner")
    sidecar_path = _relative_path(item["sidecar_path"], "runtime.sidecar_path")
    expected_path = provenance_sidecar_path(owner)
    if sidecar_path != expected_path:
        _fail("runtime.sidecar_path", f"must equal runtime-owned path {expected_path!r}")
    return {
        "schema": PROVENANCE_RUNTIME_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "runtime_path": runtime_path,
        "owner": owner,
        "sidecar_path": sidecar_path,
    }


def build_runtime_ownership(
    *, runtime_path: str, owner_kind: str, owner_id: str, owner_state: str
) -> dict[str, Any]:
    owner = {"kind": owner_kind, "id": owner_id, "state": owner_state}
    record = {
        "schema": PROVENANCE_RUNTIME_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "runtime_path": runtime_path,
        "owner": owner,
        "sidecar_path": provenance_sidecar_path(owner),
    }
    return normalize_runtime_ownership(record)


def authorize_runtime_operation(
    runtime: Mapping[str, Any], *, operation: str
) -> ProvenanceValidationResult:
    """Allow reads everywhere; only active root and pod owners may append."""

    try:
        normalized = normalize_runtime_ownership(runtime)
        if operation not in {"read", "append"}:
            _fail("operation", "must be 'read' or 'append'")
        owner = normalized["owner"]
        if operation == "append" and owner["kind"] == "pod" and owner["state"] == "retired":
            _fail(
                "runtime.owner.state",
                "a retired pod remains readable but cannot receive a new binding",
                code="retired_owner",
            )
        if operation == "append" and owner["kind"] == "detached-former-root":
            _fail(
                "runtime.owner.state",
                "a detached former root is metadata-only and remains readable",
                code="detached_owner",
            )
        return ProvenanceValidationResult(normalized)
    except ProvenanceValidationError as error:
        return ProvenanceValidationResult(None, (error.to_issue(),))


def normalize_packet_implements(value: Sequence[Any]) -> list[str]:
    """Normalize exact Task Packet decision references independently of task_packet.py."""

    if not isinstance(value, (list, tuple)) or not value:
        _fail("implements", "must be a non-empty list of exact decision references")
    refs = [_exact_decision_ref(item, f"implements[{index}]") for index, item in enumerate(value)]
    if len(refs) != len(set(refs)):
        _fail("implements", "must not repeat a decision reference")
    return sorted(refs)


def activation_id(
    *,
    packet_fingerprint: str,
    implements: Sequence[Any],
    binding_ids: Sequence[Any],
    runtime: Mapping[str, Any],
) -> str:
    normalized_runtime = normalize_runtime_ownership(runtime)
    normalized_implements = normalize_packet_implements(implements)
    normalized_binding_ids = _normalize_binding_ids(binding_ids, "binding_ids")
    return _identity(
        "mspa",
        {
            "packet_fingerprint": _sha256(packet_fingerprint, "packet_fingerprint"),
            "implements": normalized_implements,
            "binding_ids": normalized_binding_ids,
            "runtime_path": normalized_runtime["runtime_path"],
            "owner": normalized_runtime["owner"],
            "sidecar_path": normalized_runtime["sidecar_path"],
        },
    )


def _normalize_binding_ids(value: Sequence[Any], path: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or not value:
        _fail(path, "must be a non-empty list of binding identities")
    result = [_binding_reference(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        _fail(path, "must not repeat a binding identity")
    return sorted(result)


def _owned_active_bindings(
    ledger: Mapping[str, Any] | None,
    runtime: Mapping[str, Any],
    binding_ids: Sequence[str],
    implements: Sequence[str],
) -> dict[str, Any]:
    if ledger is None:
        _fail("ledger", "is required for packet activation", code="ledger_required")
    normalized = normalize_ledger(ledger)
    if normalized["runtime"] != normalize_runtime_ownership(runtime):
        _fail("ledger.runtime", "must exactly match the activation runtime", code="unowned_ledger")
    bindings = {binding["binding_id"]: binding for binding in normalized["bindings"]}
    missing = [binding_id for binding_id in binding_ids if binding_id not in bindings]
    if missing:
        _fail(
            "activation.binding_ids",
            f"contains bindings absent from the owned ledger: {', '.join(missing)}",
        )
    replaced = {record["replaces"] for record in normalized["replacements"]}
    stale = [binding_id for binding_id in binding_ids if binding_id in replaced]
    if stale:
        _fail(
            "activation.binding_ids",
            f"must not include replaced bindings: {', '.join(stale)}",
            code="replaced_binding",
        )
    represented = {bindings[binding_id]["decision_ref"] for binding_id in binding_ids}
    if represented != set(implements):
        _fail(
            "activation.binding_ids",
            "must represent exactly the packet implements decision references",
        )
    return normalized


def normalize_packet_implements_activation(
    value: Mapping[str, Any], *, ledger: Mapping[str, Any] | None = None
) -> PacketImplementsActivation:
    """Validate hook-ready activation data without stamping a Git commit message."""

    item = _mapping(value, "activation")
    _exact_keys(item, "activation", _ACTIVATION_KEYS)
    if item["schema"] != PACKET_IMPLEMENTS_ACTIVATION_SCHEMA:
        _fail("activation.schema", f"must equal {PACKET_IMPLEMENTS_ACTIVATION_SCHEMA!r}")
    if item["version"] != PROVENANCE_SCHEMA_VERSION:
        _fail("activation.version", f"must equal {PROVENANCE_SCHEMA_VERSION}")
    runtime = normalize_runtime_ownership(_mapping(item["runtime"], "activation.runtime"))
    implements = normalize_packet_implements(item["implements"])
    binding_ids = _normalize_binding_ids(item["binding_ids"], "activation.binding_ids")
    fingerprint = _sha256(item["packet_fingerprint"], "activation.packet_fingerprint")
    expected_id = activation_id(
        packet_fingerprint=fingerprint,
        implements=implements,
        binding_ids=binding_ids,
        runtime=runtime,
    )
    if _string(item["activation_id"], "activation.activation_id") != expected_id:
        _fail("activation.activation_id", "does not match the deterministic activation identity")
    _owned_active_bindings(ledger, runtime, binding_ids, implements)
    return {
        "schema": PACKET_IMPLEMENTS_ACTIVATION_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "activation_id": expected_id,
        "packet_fingerprint": fingerprint,
        "implements": implements,
        "binding_ids": binding_ids,
        "runtime": runtime,
    }


def build_packet_implements_activation(
    *,
    packet_fingerprint: str,
    implements: Sequence[Any],
    binding_ids: Sequence[Any],
    runtime: Mapping[str, Any],
    ledger: Mapping[str, Any] | None = None,
) -> PacketImplementsActivation:
    """Build normalized activation data for a later commit-hook adapter."""

    record = {
        "schema": PACKET_IMPLEMENTS_ACTIVATION_SCHEMA,
        "version": PROVENANCE_SCHEMA_VERSION,
        "activation_id": "pending",
        "packet_fingerprint": packet_fingerprint,
        "implements": list(implements),
        "binding_ids": list(binding_ids),
        "runtime": dict(runtime),
    }
    record["activation_id"] = activation_id(
        packet_fingerprint=packet_fingerprint,
        implements=implements,
        binding_ids=binding_ids,
        runtime=runtime,
    )
    return normalize_packet_implements_activation(record, ledger=ledger)


def validate_packet_implements_activation(
    value: Mapping[str, Any], *, ledger: Mapping[str, Any] | None = None
) -> ProvenanceValidationResult:
    try:
        normalized = normalize_packet_implements_activation(value, ledger=ledger)
        allowed = authorize_runtime_operation(normalized["runtime"], operation="append")
        if not allowed.ok:
            return allowed
        return ProvenanceValidationResult(dict(normalized))
    except ProvenanceValidationError as error:
        return ProvenanceValidationResult(None, (error.to_issue(),))
