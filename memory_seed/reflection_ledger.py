"""Strict, temporary reflection-ledger kernel.

This module deliberately has no dependency on the session readers.  A
reflection board is coordination state, rather than a second source of durable
memory, so its format, discovery, and fuse are all kept separate from
``memory_seed.core``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256, sha512
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence
import json
import os
import re
import subprocess
import unicodedata


REFLECTION_ROOT = ".memory-seed/reflections/active"
MANIFEST_NAME = "manifest.yaml"
CANONICAL_MODE = "100644"
RESERVATION_ALGORITHM = "sha256-crockford-v1"
RESERVATION_DOMAIN = b"memory-seed/reflection-reservation/v1\0"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
ID_SUFFIX_RE = re.compile(r"^[0-9abcdefghjkmnpqrstvwxyz]{20}$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./:+@=-]+$")
ROLE_VALUES = {"worker", "validator", "orchestrator"}
RECORD_KINDS = {"observation", "opinion", "risk", "correction", "resolution", "promotion", "closeout"}
RELATIONSHIPS = {"refines", "responds", "corrects", "challenges", "combines", "orphan"}
WORKER_KINDS = {"observation", "opinion", "risk", "correction"}


@dataclass(frozen=True)
class ReflectionDiagnostic:
    code: str
    path: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "message": self.message, "details": dict(self.details)}


class ReflectionValidationError(ValueError):
    """A fail-closed parse/validation error with a stable diagnostic payload."""

    def __init__(self, code: str, path: str, message: str, **details: Any) -> None:
        self.diagnostic = ReflectionDiagnostic(code, path, message, details)
        super().__init__(f"{path}: {message}")


def _fail(code: str, path: str, message: str, **details: Any) -> None:
    raise ReflectionValidationError(code, path, message, **details)


def _canonical_text(raw: bytes | str, path: str) -> str:
    if isinstance(raw, bytes):
        if raw.startswith(b"\xef\xbb\xbf"):
            _fail("encoding", path, "UTF-8 BOM is not canonical")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            _fail("encoding", path, "could not decode canonical UTF-8", reason=str(exc))
    else:
        text = raw
    if "\r" in text:
        _fail("line-endings", path, "canonical text uses LF only")
    if not text.endswith("\n") or text.endswith("\n\n"):
        _fail("final-lf", path, "canonical text has exactly one final LF")
    if unicodedata.normalize("NFC", text) != text:
        _fail("unicode-nfc", path, "canonical text must be Unicode NFC")
    if any(line.endswith((" ", "\t")) for line in text.splitlines()):
        _fail("trailing-whitespace", path, "canonical text has no trailing whitespace")
    return text


def _quote(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        _fail("schema", "<renderer>", "unsupported scalar type", type=type(value).__name__)
    return value if SAFE_SCALAR_RE.fullmatch(value) else json.dumps(value, ensure_ascii=False)


def _split_flow(value: str, delimiter: str = ",") -> list[str]:
    """Split a small YAML flow collection without pretending to parse YAML."""
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    if quote or depth != 0:
        _fail("yaml", "<flow>", "unbalanced flow collection")
    parts.append(value[start:].strip())
    return parts


def _parse_scalar(value: str, path: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"0|[1-9]\d*", value):
        return int(value)
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            _fail("yaml", path, "invalid quoted scalar", reason=str(exc))
    if value.startswith("[") and value.endswith("]"):
        inside = value[1:-1].strip()
        return [] if not inside else [_parse_scalar(part, path) for part in _split_flow(inside)]
    if value.startswith("{") and value.endswith("}"):
        result: dict[str, Any] = {}
        inside = value[1:-1].strip()
        if not inside:
            return result
        for part in _split_flow(inside):
            if ":" not in part:
                _fail("yaml", path, "flow map item lacks ':'", item=part)
            key, item_value = part.split(":", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in result:
                _fail("yaml", path, "invalid or duplicate flow-map key", key=key)
            result[key] = _parse_scalar(item_value, path)
        return result
    if value.startswith("'") or "#" in value or value.startswith(("-", "?", "!", "&", "*")):
        _fail("yaml", path, "unsupported non-canonical scalar", value=value)
    return value


def _parse_yaml_mapping(text: str, path: str) -> dict[str, Any]:
    """Parse the intentionally small, canonical YAML subset used by this module."""
    lines = text.splitlines()
    result: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line.startswith("  ") or line.startswith("-") or ":" not in line:
            _fail("yaml", path, "expected top-level key/value line", line=index + 1)
        key, value = line.split(":", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in result:
            _fail("yaml", path, "invalid or duplicate key", line=index + 1, key=key)
        value = value.strip()
        index += 1
        if value:
            result[key] = _parse_scalar(value, path)
            continue
        members: list[Any] = []
        while index < len(lines) and lines[index].startswith("  - "):
            first = lines[index][4:]
            index += 1
            if ":" not in first:
                members.append(_parse_scalar(first, path))
                continue
            item: dict[str, Any] = {}
            item_key, item_value = first.split(":", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item_key):
                _fail("yaml", path, "invalid list-map key", line=index, key=item_key)
            item[item_key] = _parse_scalar(item_value.strip(), path)
            while index < len(lines) and lines[index].startswith("    "):
                nested = lines[index][4:]
                if ":" not in nested:
                    _fail("yaml", path, "expected list-map key/value line", line=index + 1)
                nested_key, nested_value = nested.split(":", 1)
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nested_key) or nested_key in item:
                    _fail("yaml", path, "invalid or duplicate list-map key", line=index + 1, key=nested_key)
                item[nested_key] = _parse_scalar(nested_value.strip(), path)
                index += 1
            members.append(item)
        if not members:
            _fail("yaml", path, "empty block collection is not canonical", key=key)
        result[key] = members
    return result


def _yaml_mapping(items: Sequence[tuple[str, Any]]) -> str:
    lines: list[str] = []
    for key, value in items:
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for member in value:
                if isinstance(member, Mapping):
                    member_items = list(member.items())
                    if not member_items:
                        _fail("schema", "<renderer>", "empty list map is unsupported")
                    first_key, first_value = member_items[0]
                    lines.append(f"  - {first_key}: {_yaml_inline(first_value)}")
                    for nested_key, nested_value in member_items[1:]:
                        lines.append(f"    {nested_key}: {_yaml_inline(nested_value)}")
                else:
                    lines.append(f"  - {_yaml_inline(member)}")
        else:
            lines.append(f"{key}: {_yaml_inline(value)}")
    return "\n".join(lines) + "\n"


def _yaml_inline(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_inline(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{key}: {_yaml_inline(item)}" for key, item in value.items()) + "}"
    return _quote(value)


def _required(mapping: Mapping[str, Any], keys: Sequence[str], path: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        _fail("schema", path, "missing required fields", fields=missing)


def _only(mapping: Mapping[str, Any], keys: Sequence[str], path: str) -> None:
    unexpected = sorted(set(mapping) - set(keys))
    if unexpected:
        _fail("schema", path, "unexpected fields", fields=unexpected)


def _text(value: Any, path: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("schema", path, "field must be a non-empty string", field=field_name)
    return value


def _timestamp(value: Any, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    if not RFC3339_UTC_RE.fullmatch(value):
        _fail("timestamp", path, "timestamp must be RFC3339 UTC to seconds", field=field_name, value=value)
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _fail("timestamp", path, "invalid timestamp", field=field_name, value=value)
    return value


def _as_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _relative_path(value: Any, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or "\\" in value
        or value.startswith(".")
        or value != candidate.as_posix()
        or "//" in value
    ):
        _fail("path", path, "path must be a clean relative POSIX path", field=field_name, value=value)
    return value


def _id(value: Any, prefix: str, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    if not value.startswith(prefix) or not ID_SUFFIX_RE.fullmatch(value[len(prefix):]):
        _fail("id", path, "invalid canonical identifier", field=field_name, value=value, prefix=prefix)
    return value


def crockford(raw: bytes) -> str:
    if len(raw) != 12:
        raise ValueError("ID digest must be exactly 12 bytes")
    number = int.from_bytes(raw, "big")
    return "".join(CROCKFORD[(number >> (5 * shift)) & 31] for shift in range(19, -1, -1))


def canonical_id(prefix: str, seed: str, *parts: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise ValueError("reservation seed must be 64 lowercase hex characters")
    frame = RESERVATION_DOMAIN + bytes.fromhex(seed)
    for part in parts:
        raw = part.encode("utf-8")
        frame += len(raw).to_bytes(4, "big") + raw
    return prefix + crockford(sha256(frame).digest()[:12])


def reservation_id(prefix: str, seed: str, plan: str, participant: str, track: str, sequence: int, slot: str) -> str:
    return canonical_id(prefix, seed, plan, participant, track, str(sequence), slot)


def record_id(seed: str, fragment_id: str, ordinal: int) -> str:
    if not 1 <= ordinal <= 9999:
        raise ValueError("record ordinal must be 1..9999")
    return canonical_id("rlr_", seed, "reflection-record-v1", fragment_id, f"record:{ordinal:04d}")


@dataclass(frozen=True)
class ReflectionReservation:
    sequence: int
    report_id: str
    fragment_id: str
    report_path: str
    fragment_path: str

    def as_dict(self) -> dict[str, Any]:
        return {"sequence": self.sequence, "report_id": self.report_id, "fragment_id": self.fragment_id,
                "report_path": self.report_path, "fragment_path": self.fragment_path}


@dataclass(frozen=True)
class ReflectionParticipant:
    participant: str
    role: str
    branch: str
    track: str
    reservations: tuple[ReflectionReservation, ...]


@dataclass(frozen=True)
class ReflectionManifest:
    plan_id: str
    base_branch: str
    base_sha: str
    state: str
    created_at: str
    reflection_retention_days: int
    reservation_algorithm: str
    reservation_seed: str
    participants_seal: str
    early_expiry_approval_key_id: str
    early_expiry_approval_public_key: str
    orchestrator: Mapping[str, str]
    participants: tuple[ReflectionParticipant, ...]

    @property
    def active_dir(self) -> str:
        return f"{REFLECTION_ROOT}/{self.plan_id}"

    @property
    def manifest_path(self) -> str:
        return f"{self.active_dir}/{MANIFEST_NAME}"

    def reservation(self, participant: str, sequence: int) -> ReflectionReservation | None:
        for person in self.participants:
            if person.participant == participant:
                return next((item for item in person.reservations if item.sequence == sequence), None)
        return None

    def participant_for_branch(self, branch: str) -> ReflectionParticipant | None:
        matches = [item for item in self.participants if item.branch == branch]
        return matches[0] if len(matches) == 1 else None


def roster_bytes(manifest: ReflectionManifest) -> bytes:
    participants = []
    for person in manifest.participants:
        participants.append({
            "participant": person.participant, "role": person.role, "branch": person.branch, "track": person.track,
            "reservations": [reservation.as_dict() for reservation in person.reservations],
        })
    return _yaml_mapping([
        ("plan_id", manifest.plan_id), ("base_branch", manifest.base_branch), ("base_sha", manifest.base_sha),
        ("participants", participants),
    ]).encode("utf-8")


def participants_seal(manifest: ReflectionManifest) -> str:
    return sha256(roster_bytes(manifest)).hexdigest()


def _participant_from_mapping(value: Any, path: str) -> ReflectionParticipant:
    if not isinstance(value, Mapping):
        _fail("schema", path, "participant must be a mapping")
    _required(value, ("participant", "role", "branch", "track", "reservations"), path)
    _only(value, ("participant", "role", "branch", "track", "reservations"), path)
    role = _text(value["role"], path, "role")
    if role not in ROLE_VALUES:
        _fail("role", path, "unknown participant role", role=role)
    reservations_value = value["reservations"]
    if not isinstance(reservations_value, list) or not reservations_value:
        _fail("schema", path, "participant needs a non-empty reservation list")
    reservations: list[ReflectionReservation] = []
    for item in reservations_value:
        if not isinstance(item, Mapping):
            _fail("schema", path, "reservation must be a mapping")
        _required(item, ("sequence", "report_id", "fragment_id", "report_path", "fragment_path"), path)
        _only(item, ("sequence", "report_id", "fragment_id", "report_path", "fragment_path"), path)
        if not isinstance(item["sequence"], int) or item["sequence"] < 1:
            _fail("sequence", path, "reservation sequence must be a positive integer")
        reservations.append(ReflectionReservation(
            item["sequence"], _id(item["report_id"], "rpr_", path, "report_id"),
            _id(item["fragment_id"], "rfl_", path, "fragment_id"),
            _relative_path(item["report_path"], path, "report_path"),
            _relative_path(item["fragment_path"], path, "fragment_path"),
        ))
    return ReflectionParticipant(_text(value["participant"], path, "participant"), role,
                                 _text(value["branch"], path, "branch"), _text(value["track"], path, "track"),
                                 tuple(reservations))


def manifest_from_dict(value: Mapping[str, Any], path: str = MANIFEST_NAME) -> ReflectionManifest:
    fields = ("schema", "version", "plan_id", "base_branch", "base_sha", "state", "created_at",
              "reflection_retention_days", "reservation_algorithm", "reservation_seed", "participants_seal",
              "early_expiry_approval_key_id", "early_expiry_approval_public_key", "orchestrator", "participants")
    _required(value, fields, path)
    _only(value, fields, path)
    if value["schema"] != "memory-seed/reflection-plan" or value["version"] != 1:
        _fail("schema", path, "unsupported reflection manifest schema/version")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", _text(value["base_sha"], path, "base_sha")):
        _fail("base", path, "base_sha must be a resolved lowercase Git SHA")
    if value["state"] not in {"active", "review", "closed"}:
        _fail("state", path, "invalid manifest state")
    days = value["reflection_retention_days"]
    if not isinstance(days, int) or days < 1:
        _fail("retention", path, "reflection_retention_days must be a positive integer")
    if value["reservation_algorithm"] != RESERVATION_ALGORITHM:
        _fail("reservation-algorithm", path, "unsupported reservation algorithm")
    seed = _text(value["reservation_seed"], path, "reservation_seed")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        _fail("reservation-seed", path, "reservation_seed must be 64 lowercase hex")
    orchestrator = value["orchestrator"]
    if not isinstance(orchestrator, Mapping):
        _fail("schema", path, "orchestrator must be a mapping")
    _required(orchestrator, ("participant", "branch"), path)
    _only(orchestrator, ("participant", "branch"), path)
    participants_value = value["participants"]
    if not isinstance(participants_value, list) or not participants_value:
        _fail("schema", path, "manifest needs a non-empty participants list")
    participants = tuple(_participant_from_mapping(item, path) for item in participants_value)
    manifest = ReflectionManifest(
        _text(value["plan_id"], path, "plan_id"), _text(value["base_branch"], path, "base_branch"),
        _text(value["base_sha"], path, "base_sha"), value["state"], _timestamp(value["created_at"], path, "created_at"),
        days, RESERVATION_ALGORITHM, seed, _text(value["participants_seal"], path, "participants_seal"),
        _text(value["early_expiry_approval_key_id"], path, "early_expiry_approval_key_id"),
        _text(value["early_expiry_approval_public_key"], path, "early_expiry_approval_public_key"),
        {"participant": _text(orchestrator["participant"], path, "orchestrator.participant"),
         "branch": _text(orchestrator["branch"], path, "orchestrator.branch")}, participants,
    )
    validate_manifest(manifest, path)
    return manifest


def validate_manifest(manifest: ReflectionManifest, path: str = MANIFEST_NAME) -> None:
    names = [person.participant for person in manifest.participants]
    branches = [person.branch for person in manifest.participants]
    if len(names) != len(set(names)) or len(branches) != len(set(branches)):
        _fail("roster", path, "participants and branches must be unique")
    orchestrators = [person for person in manifest.participants if person.role == "orchestrator"]
    if len(orchestrators) != 1 or orchestrators[0].participant != manifest.orchestrator["participant"] or orchestrators[0].branch != manifest.orchestrator["branch"]:
        _fail("orchestrator", path, "orchestrator mapping must name the sole orchestrator participant")
    paths: set[str] = set()
    ids: set[str] = set()
    sequences: set[tuple[str, int]] = set()
    for person in manifest.participants:
        for reservation in person.reservations:
            key = (person.participant, reservation.sequence)
            if key in sequences:
                _fail("sequence", path, "duplicate participant reservation sequence", participant=person.participant, sequence=reservation.sequence)
            sequences.add(key)
            expected_report = reservation_id("rpr_", manifest.reservation_seed, manifest.plan_id, person.participant, person.track, reservation.sequence, "report")
            expected_fragment = reservation_id("rfl_", manifest.reservation_seed, manifest.plan_id, person.participant, person.track, reservation.sequence, "fragment")
            if reservation.report_id != expected_report or reservation.fragment_id != expected_fragment:
                _fail("reservation-id", path, "reservation ID does not match deterministic manifest derivation", participant=person.participant, sequence=reservation.sequence)
            for identifier in (reservation.report_id, reservation.fragment_id):
                if identifier in ids:
                    _fail("collision", path, "duplicate reserved identifier", identifier=identifier)
                ids.add(identifier)
            for rel_path, expected_prefix, identifier in ((reservation.report_path, "reports/", reservation.report_id), (reservation.fragment_path, "fragments/", reservation.fragment_id)):
                if not rel_path.startswith(expected_prefix) or not rel_path.endswith(identifier + ".md"):
                    _fail("reservation-path", path, "reservation path must be a matching canonical reports/fragments path", path=rel_path)
                if rel_path in paths:
                    _fail("collision", path, "duplicate reserved path", path=rel_path)
                paths.add(rel_path)
    if not re.fullmatch(r"[0-9a-f]{64}", manifest.participants_seal) or manifest.participants_seal != participants_seal(manifest):
        _fail("roster-seal", path, "participants_seal does not match canonical participant roster")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", manifest.early_expiry_approval_key_id):
        _fail("approval-key", path, "early expiry approval key ID must be a stable token")
    if not re.fullmatch(r"ed25519:[0-9a-f]{64}", manifest.early_expiry_approval_public_key):
        _fail("approval-key", path, "early expiry approval public key must be ed25519:<32-byte lowercase hex>")


def render_manifest(manifest: ReflectionManifest) -> str:
    validate_manifest(manifest)
    participants = []
    for person in manifest.participants:
        participants.append({"participant": person.participant, "role": person.role, "branch": person.branch,
                             "track": person.track, "reservations": [item.as_dict() for item in person.reservations]})
    return _yaml_mapping([
        ("schema", "memory-seed/reflection-plan"), ("version", 1), ("plan_id", manifest.plan_id),
        ("base_branch", manifest.base_branch), ("base_sha", manifest.base_sha), ("state", manifest.state),
        ("created_at", manifest.created_at), ("reflection_retention_days", manifest.reflection_retention_days),
        ("reservation_algorithm", manifest.reservation_algorithm), ("reservation_seed", manifest.reservation_seed),
        ("participants_seal", manifest.participants_seal), ("early_expiry_approval_key_id", manifest.early_expiry_approval_key_id),
        ("early_expiry_approval_public_key", manifest.early_expiry_approval_public_key), ("orchestrator", dict(manifest.orchestrator)),
        ("participants", participants),
    ])


def parse_manifest(raw: bytes | str, path: str = MANIFEST_NAME) -> ReflectionManifest:
    text = _canonical_text(raw, path)
    manifest = manifest_from_dict(_parse_yaml_mapping(text, path), path)
    if render_manifest(manifest) != text:
        _fail("canonical-bytes", path, "manifest is valid YAML but not the canonical rendering")
    return manifest


@dataclass(frozen=True)
class ReflectionReport:
    report_id: str
    plan_id: str
    participant: str
    track: str
    working_branch: str
    base_sha: str
    task_packet_fingerprint: str
    status: str
    created_at: str
    validation: tuple[Mapping[str, Any], ...]
    body: str


def report_from_dict(value: Mapping[str, Any], body: str, path: str = "report.md") -> ReflectionReport:
    fields = ("schema", "version", "report_id", "plan_id", "participant", "track", "working_branch", "base_sha",
              "task_packet_fingerprint", "status", "created_at", "validation")
    _required(value, fields, path)
    _only(value, fields, path)
    if value["schema"] != "memory-seed/reflection-report" or value["version"] != 1:
        _fail("schema", path, "unsupported reflection report schema/version")
    validation = value["validation"]
    if not isinstance(validation, list) or not validation:
        _fail("validation", path, "report validation must be a non-empty list")
    normalized: list[Mapping[str, Any]] = []
    for item in validation:
        if not isinstance(item, Mapping) or set(item) != {"command", "exit_code"} or not isinstance(item["exit_code"], int):
            _fail("validation", path, "validation items require command and integer exit_code")
        normalized.append({"command": _text(item["command"], path, "validation.command"), "exit_code": item["exit_code"]})
    fingerprint = _text(value["task_packet_fingerprint"], path, "task_packet_fingerprint")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        _fail("report-provenance", path, "task_packet_fingerprint must be sha256:<64 lowercase hex>")
    status = _text(value["status"], path, "status")
    if status not in {"DONE", "DONE_WITH_CONCERNS", "BLOCKED"}:
        _fail("status", path, "invalid report status", status=status)
    if not body or not body.strip() or not body.endswith("\n"):
        _fail("report-body", path, "report body must be non-empty and end in one LF")
    return ReflectionReport(_id(value["report_id"], "rpr_", path, "report_id"), _text(value["plan_id"], path, "plan_id"),
                            _text(value["participant"], path, "participant"), _text(value["track"], path, "track"),
                            _text(value["working_branch"], path, "working_branch"), _text(value["base_sha"], path, "base_sha"),
                            fingerprint, status, _timestamp(value["created_at"], path, "created_at"), tuple(normalized), body)


def render_report(report: ReflectionReport) -> str:
    header = _yaml_mapping([
        ("schema", "memory-seed/reflection-report"), ("version", 1), ("report_id", report.report_id),
        ("plan_id", report.plan_id), ("participant", report.participant), ("track", report.track),
        ("working_branch", report.working_branch), ("base_sha", report.base_sha),
        ("task_packet_fingerprint", report.task_packet_fingerprint), ("status", report.status),
        ("created_at", report.created_at), ("validation", list(report.validation)),
    ])
    return "---\n" + header + "---\n\n# Worker report\n\n" + report.body


def parse_report(raw: bytes | str, path: str = "report.md") -> ReflectionReport:
    text = _canonical_text(raw, path)
    match = re.fullmatch(r"---\n(?P<header>.*?)---\n\n# Worker report\n\n(?P<body>[\s\S]+)", text, re.DOTALL)
    if not match:
        _fail("markdown", path, "report must use canonical frontmatter and Worker report heading")
    report = report_from_dict(_parse_yaml_mapping(match.group("header"), path), match.group("body"), path)
    if render_report(report) != text:
        _fail("canonical-bytes", path, "report is valid but not the canonical rendering")
    return report


def validate_report(report: ReflectionReport, manifest: ReflectionManifest, *, branch: str | None = None, path: str = "report.md") -> ReflectionReservation:
    if report.plan_id != manifest.plan_id or report.base_sha != manifest.base_sha:
        _fail("report-provenance", path, "report plan/base does not match manifest")
    participant = next((item for item in manifest.participants if item.participant == report.participant), None)
    if participant is None or participant.track != report.track or participant.branch != report.working_branch:
        _fail("ownership", path, "report participant/track/branch does not match manifest")
    if branch is not None and report.working_branch != branch:
        _fail("ownership", path, "report branch does not match fused source branch", branch=branch)
    reservation = next((item for item in participant.reservations if item.report_id == report.report_id), None)
    if reservation is None:
        _fail("reservation", path, "report_id is not reserved for participant")
    return reservation


@dataclass(frozen=True)
class ReflectionRecord:
    record_id: str
    ordinal: int
    kind: str
    chain_id: str
    parents: tuple[str, ...]
    relationship: str
    area: str
    activity: str
    topics: tuple[str, ...]
    related_decisions: tuple[str, ...]
    confidence: str
    source: str
    created_at: str
    conclusion: str
    reasoning: str
    assumptions: str | None = None
    alternatives: str | None = None
    next_step: str | None = None
    corrects: str | None = None
    no_related_thread: bool = False


@dataclass(frozen=True)
class ReflectionFragment:
    fragment_id: str
    plan_id: str
    participant: str
    track: str
    working_branch: str
    sequence: int
    source: str
    report_id: str
    base_sha: str
    created_at: str
    title: str
    records: tuple[ReflectionRecord, ...]


_FRAGMENT_FIELDS = ("schema", "version", "fragment_id", "plan_id", "participant", "track", "working_branch", "sequence", "source", "report_id", "base_sha")
_RECORD_FIELDS = ("record_id", "ordinal", "kind", "chain_id", "parents", "relationship", "area", "activity", "topics", "related_decisions", "confidence", "source", "created_at", "corrects", "no_related_thread")


def _record_from_dict(value: Mapping[str, Any], sections: Mapping[str, str], path: str) -> ReflectionRecord:
    _required(value, _RECORD_FIELDS[:14], path)
    _only(value, _RECORD_FIELDS, path)
    ordinal = value["ordinal"]
    if not isinstance(ordinal, int) or not 1 <= ordinal <= 9999:
        _fail("ordinal", path, "record ordinal must be 1..9999")
    kind = _text(value["kind"], path, "kind")
    relationship = _text(value["relationship"], path, "relationship")
    if kind not in RECORD_KINDS or relationship not in RELATIONSHIPS:
        _fail("relationship", path, "invalid record kind or relationship", kind=kind, relationship=relationship)
    for field_name in ("parents", "topics", "related_decisions"):
        if not isinstance(value[field_name], list) or any(not isinstance(item, str) or not item for item in value[field_name]):
            _fail("schema", path, "record list field must be a string list", field=field_name)
    if len(set(value["parents"])) != len(value["parents"]):
        _fail("relationship", path, "record parents must be unique")
    if value["confidence"] not in {"low", "medium", "high"}:
        _fail("confidence", path, "confidence must be low, medium, or high")
    if value["source"] not in {"write-time", "derived"}:
        _fail("source", path, "record source must be write-time or derived")
    conclusion = sections.get("Conclusion", "")
    reasoning = sections.get("Reasoning", "")
    if not conclusion.strip() or not reasoning.strip():
        _fail("conclusion", path, "record requires Conclusion then Reasoning sections")
    corrects = value.get("corrects")
    if corrects is not None:
        corrects = _id(corrects, "rlr_", path, "corrects")
    no_related_thread = value.get("no_related_thread", False)
    if not isinstance(no_related_thread, bool):
        _fail("relationship", path, "no_related_thread must be boolean")
    return ReflectionRecord(_id(value["record_id"], "rlr_", path, "record_id"), ordinal, kind,
                            _id(value["chain_id"], "rlc_", path, "chain_id"), tuple(value["parents"]), relationship,
                            _text(value["area"], path, "area"), _text(value["activity"], path, "activity"),
                            tuple(value["topics"]), tuple(value["related_decisions"]), value["confidence"], value["source"],
                            _timestamp(value["created_at"], path, "created_at"), conclusion, reasoning,
                            sections.get("Assumptions and uncertainty"), sections.get("Alternatives and objections"),
                            sections.get("Challenge or next step"), corrects, no_related_thread)


def _record_metadata(record: ReflectionRecord) -> list[tuple[str, Any]]:
    return [("record_id", record.record_id), ("ordinal", record.ordinal), ("kind", record.kind), ("chain_id", record.chain_id),
            ("parents", list(record.parents)), ("relationship", record.relationship), ("area", record.area),
            ("activity", record.activity), ("topics", list(record.topics)), ("related_decisions", list(record.related_decisions)),
            ("confidence", record.confidence), ("source", record.source), ("created_at", record.created_at),
            ("corrects", record.corrects), ("no_related_thread", record.no_related_thread)]


def _render_sections(record: ReflectionRecord) -> str:
    sections = [("Conclusion", record.conclusion), ("Reasoning", record.reasoning),
                ("Assumptions and uncertainty", record.assumptions), ("Alternatives and objections", record.alternatives),
                ("Challenge or next step", record.next_step)]
    return "\n".join(f"#### {title}\n\n{body.rstrip()}" for title, body in sections if body is not None) + "\n"


def render_fragment(fragment: ReflectionFragment) -> str:
    header = _yaml_mapping([
        ("schema", "memory-seed/reflection-fragment"), ("version", 1), ("fragment_id", fragment.fragment_id),
        ("plan_id", fragment.plan_id), ("participant", fragment.participant), ("track", fragment.track),
        ("working_branch", fragment.working_branch), ("sequence", fragment.sequence), ("source", fragment.source),
        ("report_id", fragment.report_id), ("base_sha", fragment.base_sha),
    ])
    pieces = [f"## {fragment.created_at} - {fragment.title}\n\n```yaml\n{header}```\n"]
    for record in fragment.records:
        pieces.append(f"\n### R{record.ordinal} - {record.kind}\n\n```yaml\n{_yaml_mapping(_record_metadata(record))}```\n\n{_render_sections(record)}")
    return "".join(pieces)


def _parse_sections(text: str, path: str) -> dict[str, str]:
    matches = list(re.finditer(r"^#### (Conclusion|Reasoning|Assumptions and uncertainty|Alternatives and objections|Challenge or next step)\n\n", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1)
        if name in sections:
            _fail("markdown", path, "duplicate record section", section=name)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].rstrip("\n")
        sections[name] = body
    return sections


def parse_fragment(raw: bytes | str, path: str = "fragment.md") -> ReflectionFragment:
    text = _canonical_text(raw, path)
    prefix = re.match(r"^## (?P<created>[^\n]+) - (?P<title>[^\n]+)\n\n```yaml\n(?P<header>.*?)```\n", text, re.DOTALL)
    if not prefix:
        _fail("markdown", path, "fragment must start with a timestamped heading and YAML envelope")
    created_at = _timestamp(prefix.group("created"), path, "heading.created_at")
    header = _parse_yaml_mapping(prefix.group("header"), path)
    _required(header, _FRAGMENT_FIELDS, path)
    _only(header, _FRAGMENT_FIELDS, path)
    if header["schema"] != "memory-seed/reflection-fragment" or header["version"] != 1:
        _fail("schema", path, "unsupported reflection fragment schema/version")
    body = text[prefix.end():]
    blocks = list(re.finditer(r"^\n### R(?P<ordinal>\d+) - (?P<title>[^\n]+)\n\n```yaml\n(?P<meta>.*?)```\n\n", body, re.MULTILINE | re.DOTALL))
    if not blocks:
        _fail("records", path, "fragment needs at least one canonical record")
    records: list[ReflectionRecord] = []
    for index, block in enumerate(blocks):
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(body)
        record_body = body[block.end():end]
        if record_body.endswith("\n"):
            record_body = record_body[:-1]
        metadata = _parse_yaml_mapping(block.group("meta"), path)
        if metadata.get("ordinal") != int(block.group("ordinal")) or metadata.get("kind") != block.group("title"):
            _fail("records", path, "record heading must match record metadata")
        records.append(_record_from_dict(metadata, _parse_sections(record_body, path), path))
    fragment = ReflectionFragment(
        _id(header["fragment_id"], "rfl_", path, "fragment_id"), _text(header["plan_id"], path, "plan_id"),
        _text(header["participant"], path, "participant"), _text(header["track"], path, "track"),
        _text(header["working_branch"], path, "working_branch"), header["sequence"], _text(header["source"], path, "source"),
        _id(header["report_id"], "rpr_", path, "report_id"), _text(header["base_sha"], path, "base_sha"),
        created_at, prefix.group("title"), tuple(records),
    )
    if not isinstance(fragment.sequence, int) or fragment.sequence < 1 or fragment.source not in {"write-time", "derived"}:
        _fail("schema", path, "invalid fragment sequence or source")
    if render_fragment(fragment) != text:
        _fail("canonical-bytes", path, "fragment is valid but not the canonical rendering")
    return fragment


def validate_fragment(fragment: ReflectionFragment, manifest: ReflectionManifest, report: ReflectionReport, *, branch: str | None = None, path: str = "fragment.md") -> ReflectionReservation:
    if fragment.plan_id != manifest.plan_id or fragment.base_sha != manifest.base_sha:
        _fail("ownership", path, "fragment plan/base does not match manifest")
    participant = next((item for item in manifest.participants if item.participant == fragment.participant), None)
    if participant is None or (participant.track, participant.branch) != (fragment.track, fragment.working_branch):
        _fail("ownership", path, "fragment participant/track/branch does not match manifest")
    if branch is not None and branch != fragment.working_branch:
        _fail("ownership", path, "fragment branch does not match fused source branch", branch=branch)
    reservation = manifest.reservation(fragment.participant, fragment.sequence)
    if reservation is None or (reservation.fragment_id, reservation.report_id) != (fragment.fragment_id, fragment.report_id):
        _fail("reservation", path, "fragment sequence/IDs are not reserved for participant")
    validate_report(report, manifest, branch=branch, path=path)
    if report.report_id != fragment.report_id or report.participant != fragment.participant:
        _fail("report-provenance", path, "fragment does not cite its participant's report")
    ordinals = [record.ordinal for record in fragment.records]
    if ordinals != list(range(1, len(ordinals) + 1)):
        _fail("ordinal", path, "fragment record ordinals must start at one and be contiguous")
    for record in fragment.records:
        if record.record_id != record_id(manifest.reservation_seed, fragment.fragment_id, record.ordinal):
            _fail("record-id", path, "record_id does not match deterministic fragment/ordinal derivation", record_id=record.record_id)
        if participant.role != "orchestrator" and record.kind not in WORKER_KINDS:
            _fail("authority", path, "non-orchestrator cannot author resolution/promotion/closeout", kind=record.kind)
        if participant.role == "orchestrator" and record.kind == "correction" and record.source != "write-time":
            _fail("authority", path, "derived corrections cannot override write-time records")
    return reservation


def _record_index(fragments: Iterable[ReflectionFragment]) -> dict[str, tuple[ReflectionFragment, ReflectionRecord]]:
    result: dict[str, tuple[ReflectionFragment, ReflectionRecord]] = {}
    for fragment in fragments:
        for record in fragment.records:
            if record.record_id in result:
                _fail("collision", "<records>", "duplicate reflection record ID", record_id=record.record_id)
            result[record.record_id] = (fragment, record)
    return result


def validate_relationships(fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest) -> None:
    index = _record_index(fragments)
    for record_id_value, (fragment, record) in index.items():
        if record.relationship == "orphan":
            if record.parents or not record.no_related_thread:
                _fail("orphan", fragment.fragment_id, "orphan records need no parents and explicit no-related-thread judgment", record_id=record_id_value)
        else:
            if record.no_related_thread or not record.parents:
                _fail("relationship", fragment.fragment_id, "non-orphan relationship needs parents and cannot assert no-related-thread", record_id=record_id_value)
            if record.relationship == "combines" and len(record.parents) < 2:
                _fail("relationship", fragment.fragment_id, "combines requires at least two parents", record_id=record_id_value)
            if record.relationship != "combines" and len(record.parents) != 1:
                _fail("relationship", fragment.fragment_id, "relationship requires exactly one parent", record_id=record_id_value)
        for parent_id in record.parents:
            parent_pair = index.get(parent_id)
            if parent_pair is None:
                _fail("dangling-parent", fragment.fragment_id, "record parent is absent from admitted fragments", record_id=record_id_value, parent_id=parent_id)
            parent_fragment, parent = parent_pair
            if parent.chain_id != record.chain_id:
                _fail("foreign-parent", fragment.fragment_id, "record parent belongs to another chain", record_id=record_id_value, parent_id=parent_id)
            if parent.created_at > record.created_at or (parent.created_at == record.created_at and parent_id >= record_id_value):
                _fail("relationship-order", fragment.fragment_id, "parents must precede their child deterministically", record_id=record_id_value, parent_id=parent_id)
        if record.kind == "correction":
            if not record.corrects or record.corrects not in index:
                _fail("correction", fragment.fragment_id, "correction needs an existing corrects record ID", record_id=record_id_value)
            corrected_fragment, corrected = index[record.corrects]
            if corrected_fragment.participant != fragment.participant or corrected.created_at >= record.created_at:
                _fail("correction-ownership", fragment.fragment_id, "correction may target only an earlier record by its participant", record_id=record_id_value)
            if record.corrects not in record.parents or record.relationship != "corrects":
                _fail("correction", fragment.fragment_id, "correction must use corrects relationship and name target as parent", record_id=record_id_value)
        elif record.corrects is not None:
            _fail("correction", fragment.fragment_id, "only correction records may name corrects")
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(identifier: str) -> None:
        if identifier in visiting:
            _fail("cycle", index[identifier][0].fragment_id, "record relationship graph contains a cycle", record_id=identifier)
        if identifier in visited:
            return
        visiting.add(identifier)
        for parent_id in index[identifier][1].parents:
            visit(parent_id)
        visiting.remove(identifier)
        visited.add(identifier)
    for identifier in index:
        visit(identifier)


def validate_admitted_fragments(
    fragments: Iterable[ReflectionFragment],
    reports: Iterable[ReflectionReport],
    manifest: ReflectionManifest,
    *,
    branch: str | None = None,
) -> tuple[ReflectionFragment, ...]:
    """Validate the admission boundary used by projections and closure.

    A relationship graph alone is not an admission check: the same structurally
    plausible fragment can have a forged owner, sequence, report, or record ID.
    """
    fragments = tuple(fragments)
    reports_by_id: dict[str, ReflectionReport] = {}
    for report in reports:
        existing = reports_by_id.get(report.report_id)
        if existing is not None and existing != report:
            _fail("report-collision", "<reports>", "conflicting reports share an ID", report_id=report.report_id)
        reports_by_id[report.report_id] = report
    for fragment in fragments:
        report = reports_by_id.get(fragment.report_id)
        if report is None:
            _fail("report-provenance", fragment.fragment_id, "fragment has no admitted report", report_id=fragment.report_id)
        validate_fragment(fragment, manifest, report, branch=branch)
    validate_relationships(fragments, manifest)
    return fragments


@dataclass(frozen=True)
class AdmittedReflectionSet:
    """Reflection documents loaded from one immutable Git tree.

    This is evidence, not a caller-authored assertion. Every close/expiry use
    re-loads the stated repository and commit, checks the manifest and every
    report/fragment blob OID, then compares the resulting value in full.
    """

    repository: str
    source_commit: str
    manifest_path: str
    manifest_oid: str
    manifest_sha256: str
    document_oids: tuple[tuple[str, str], ...]
    manifest: ReflectionManifest
    fragments: tuple[ReflectionFragment, ...]
    reports: tuple[ReflectionReport, ...]


def admit_reflection_git_tree(cwd: Path | str, *, source: str, plan_id: str) -> AdmittedReflectionSet:
    """Load canonical active reflection pairs from an immutable Git commit.

    Raw mappings and parsed dataclasses are intentionally not accepted here:
    the repository, resolved commit, paths, modes, and object IDs are the
    provenance proof consumed by closeout validation.
    """
    root = Path(cwd).resolve()
    source_commit = _commit(root, source)
    if source_commit is None:
        _fail("git-ref", str(root), "reflection admission source does not resolve to a commit", source=source)
    manifest_path = f"{REFLECTION_ROOT}/{plan_id}/{MANIFEST_NAME}"
    manifest_blob = _tree_blob(root, source_commit, manifest_path)
    if manifest_blob is None:
        _fail("manifest", manifest_path, "admission source has no reflection manifest")
    if manifest_blob.mode != CANONICAL_MODE:
        _fail("mode", manifest_path, "reflection manifest must be regular mode 100644", mode=manifest_blob.mode)
    manifest = parse_manifest(manifest_blob.content, manifest_path)
    if manifest.plan_id != plan_id:
        _fail("manifest", manifest_path, "admission manifest plan_id does not match requested plan")
    reports: list[ReflectionReport] = []
    fragments: list[ReflectionFragment] = []
    document_oids: list[tuple[str, str]] = []
    for participant in manifest.participants:
        for reservation in participant.reservations:
            report_path = f"{manifest.active_dir}/{reservation.report_path}"
            fragment_path = f"{manifest.active_dir}/{reservation.fragment_path}"
            report_blob = _tree_blob(root, source_commit, report_path)
            fragment_blob = _tree_blob(root, source_commit, fragment_path)
            if report_blob is None and fragment_blob is None:
                continue
            if report_blob is None or fragment_blob is None:
                _fail("report-provenance", manifest.active_dir, "admitted reservation must contain both report and fragment", sequence=reservation.sequence)
            if report_blob.mode != CANONICAL_MODE or fragment_blob.mode != CANONICAL_MODE:
                _fail("mode", report_path if report_blob.mode != CANONICAL_MODE else fragment_path, "reflection files must be regular mode 100644")
            reports.append(parse_report(report_blob.content, report_path))
            fragments.append(parse_fragment(fragment_blob.content, fragment_path))
            document_oids.extend(((report_path, report_blob.oid), (fragment_path, fragment_blob.oid)))
    admitted = validate_admitted_fragments(fragments, reports, manifest)
    return AdmittedReflectionSet(
        str(root), source_commit, manifest_path, manifest_blob.oid, manifest_blob.raw_sha256,
        tuple(sorted(document_oids)), manifest, admitted, tuple(reports),
    )


def _verified_admitted_set(admitted: AdmittedReflectionSet) -> AdmittedReflectionSet:
    if not isinstance(admitted, AdmittedReflectionSet):
        _fail("admission", "closeout.md", "closeout validation requires Git-admitted reflection documents")
    if (
        not isinstance(admitted.repository, str)
        or not re.fullmatch(r"[0-9a-f]{40}", admitted.source_commit)
        or not isinstance(admitted.manifest, ReflectionManifest)
    ):
        _fail("admission", "closeout.md", "Git admission evidence has malformed repository or commit identity")
    fresh = admit_reflection_git_tree(admitted.repository, source=admitted.source_commit, plan_id=admitted.manifest.plan_id)
    if admitted != fresh:
        _fail("admission", "closeout.md", "admission evidence does not match the declared immutable Git tree")
    return fresh


def live_heads(
    fragments: Iterable[ReflectionFragment],
    manifest: ReflectionManifest | None = None,
    *,
    reports: Iterable[ReflectionReport] | None = None,
) -> dict[str, tuple[ReflectionRecord, ...]]:
    fragments = tuple(fragments)
    if manifest is not None:
        if reports is None:
            _fail("admission", "<view>", "manifest-backed live-head projection requires admitted reports")
        validate_admitted_fragments(fragments, reports, manifest)
    index = _record_index(fragments)
    heads = set(index)
    for record_id_value, (_fragment, record) in index.items():
        if record.relationship in {"refines", "corrects", "combines"}:
            heads.difference_update(record.parents)
    grouped: dict[str, list[ReflectionRecord]] = {}
    for identifier in sorted(heads):
        record = index[identifier][1]
        grouped.setdefault(record.chain_id, []).append(record)
    return {chain: tuple(sorted(records, key=lambda item: (item.created_at, item.record_id))) for chain, records in grouped.items()}


def common_view(fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest | None = None, *, reports: Iterable[ReflectionReport] | None = None, plan_id: str | None = None,
                area: str | None = None, activity: str | None = None, topic: str | None = None,
                related_decision: str | None = None, chain: str | None = None, responds_to: str | None = None,
                transitive: bool = False) -> tuple[ReflectionRecord, ...]:
    fragments = tuple(fragments)
    if manifest is not None:
        if reports is None:
            _fail("admission", "<view>", "manifest-backed common view requires admitted reports")
        validate_admitted_fragments(fragments, reports, manifest)
    index = _record_index(fragments)
    wanted: set[str] | None = None
    if responds_to is not None:
        if responds_to not in index:
            return ()
        children: dict[str, list[str]] = {}
        for identifier, (_fragment, record) in index.items():
            for parent_id in record.parents:
                children.setdefault(parent_id, []).append(identifier)
        direct = set(children.get(responds_to, []))
        wanted = set(direct)
        if transitive:
            stack = list(direct)
            while stack:
                current = stack.pop()
                for child in children.get(current, []):
                    if child not in wanted:
                        wanted.add(child)
                        stack.append(child)
    selected: list[tuple[ReflectionFragment, ReflectionRecord]] = []
    for identifier, pair in index.items():
        fragment, record = pair
        if wanted is not None and identifier not in wanted:
            continue
        if plan_id is not None and fragment.plan_id != plan_id:
            continue
        if area is not None and record.area != area:
            continue
        if activity is not None and record.activity != activity:
            continue
        if topic is not None and topic not in record.topics:
            continue
        if related_decision is not None and related_decision not in record.related_decisions:
            continue
        if chain is not None and chain != record.chain_id:
            continue
        selected.append(pair)
    return tuple(record for _fragment, record in sorted(selected, key=lambda pair: (pair[1].created_at, pair[0].participant, pair[0].sequence, pair[0].fragment_id, pair[1].ordinal)))


def render_common_view(records: Iterable[ReflectionRecord]) -> str:
    records = tuple(records)
    lines = ["# Reflection common view", ""]
    for record in records:
        lines.extend([f"## {record.record_id} — {record.kind}", "", f"- Chain: `{record.chain_id}`", f"- Relationship: `{record.relationship}`", f"- Area/activity: `{record.area}` / `{record.activity}`", f"- Topics: {', '.join(record.topics)}", "", "### Conclusion", "", record.conclusion, "", "### Reasoning", "", record.reasoning, ""])
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class ReflectionReceipt:
    receipt_id: str
    plan_id: str
    chain_id: str
    head_record_ids: tuple[str, ...]
    member_record_ids: tuple[str, ...]
    conclusion: str
    disposition: str
    promoted_to: tuple[str, ...]
    recorded_at: str
    detail_digest: str


_RECEIPT_FIELDS = ("schema", "version", "receipt_id", "plan_id", "chain_id", "head_record_ids", "member_record_ids", "conclusion", "disposition", "promoted_to", "recorded_at", "detail_digest")


def receipt_from_dict(value: Mapping[str, Any], path: str = "receipt.yaml") -> ReflectionReceipt:
    _required(value, _RECEIPT_FIELDS, path)
    _only(value, _RECEIPT_FIELDS, path)
    if value["schema"] != "memory-seed/reflection-receipt" or value["version"] != 1:
        _fail("schema", path, "unsupported reflection receipt schema/version")
    for field_name in ("head_record_ids", "member_record_ids", "promoted_to"):
        if not isinstance(value[field_name], list) or any(not isinstance(item, str) or not item for item in value[field_name]):
            _fail("receipt", path, "receipt list field must be a string list", field=field_name)
    receipt = ReflectionReceipt(_id(value["receipt_id"], "rrc_", path, "receipt_id"), _text(value["plan_id"], path, "plan_id"),
                                _id(value["chain_id"], "rlc_", path, "chain_id"), tuple(value["head_record_ids"]), tuple(value["member_record_ids"]),
                                _text(value["conclusion"], path, "conclusion"), _text(value["disposition"], path, "disposition"),
                                tuple(value["promoted_to"]), _timestamp(value["recorded_at"], path, "recorded_at"),
                                _text(value["detail_digest"], path, "detail_digest"))
    validate_receipt(receipt, path)
    return receipt


def render_receipt(receipt: ReflectionReceipt) -> str:
    validate_receipt(receipt)
    return _yaml_mapping([
        ("schema", "memory-seed/reflection-receipt"), ("version", 1), ("receipt_id", receipt.receipt_id),
        ("plan_id", receipt.plan_id), ("chain_id", receipt.chain_id), ("head_record_ids", list(receipt.head_record_ids)),
        ("member_record_ids", list(receipt.member_record_ids)), ("conclusion", receipt.conclusion),
        ("disposition", receipt.disposition), ("promoted_to", list(receipt.promoted_to)), ("recorded_at", receipt.recorded_at),
        ("detail_digest", receipt.detail_digest),
    ])


def parse_receipt(raw: bytes | str, path: str = "receipt.yaml") -> ReflectionReceipt:
    text = _canonical_text(raw, path)
    receipt = receipt_from_dict(_parse_yaml_mapping(text, path), path)
    if render_receipt(receipt) != text:
        _fail("canonical-bytes", path, "receipt is valid but not the canonical rendering")
    return receipt


SESSION_ROOT = ".memory-seed/sessions/"
SESSION_ENTRY_ID_RE = re.compile(r"^mse_[0-9abcdefghjkmnpqrstvwxyz]{16}$")
SESSION_DECISION_ID_RE = re.compile(r"^D[1-9][0-9]*$")


def _session_path(value: Any, path: str, field_name: str) -> str:
    """Validate the one repository-owned location permitted for receipts."""
    value = _text(value, path, field_name)
    candidate = PurePosixPath(value)
    if (
        not value.startswith(SESSION_ROOT)
        or value == SESSION_ROOT
        or candidate.is_absolute()
        or ".." in candidate.parts
        or "\\" in value
        or value != candidate.as_posix()
        or "//" in value
    ):
        _fail("session-path", path, "receipt evidence must name a clean .memory-seed/sessions POSIX path", field=field_name, value=value)
    return value


def _session_receipt_from_blob(raw: bytes, path: str, entry_id: str,
                               decision_id: str | None) -> ReflectionReceipt:
    """Find one canonical receipt in one committed SessionStart-style entry.

    Session prose is intentionally not a second reflection document grammar.
    The durable receipt itself is canonical YAML, while this routine binds it to
    an exact entry (and, where supplied, decision) location in the Git blob.
    """
    _session_path(path, path, "session_path")
    if not SESSION_ENTRY_ID_RE.fullmatch(entry_id):
        _fail("session-locator", path, "receipt entry_id must be a canonical session entry ID", entry_id=entry_id)
    if decision_id is not None and not SESSION_DECISION_ID_RE.fullmatch(decision_id):
        _fail("session-locator", path, "receipt decision_id must be a canonical decision locator", decision_id=decision_id)
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail("encoding", path, "session receipt evidence cannot use a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("encoding", path, "could not decode UTF-8 session receipt evidence", reason=str(exc))
    if "\r" in text or unicodedata.normalize("NFC", text) != text:
        _fail("session-canonical", path, "session receipt evidence must use NFC UTF-8 with LF line endings")

    entry_matches = list(re.finditer(r"^## [^\n]+\n\n```yaml\n(?P<meta>.*?)```\n", text, re.MULTILINE | re.DOTALL))
    matching_entries: list[tuple[re.Match[str], int]] = []
    for index, entry in enumerate(entry_matches):
        try:
            metadata = _parse_yaml_mapping(entry.group("meta"), path)
        except ReflectionValidationError:
            continue
        if metadata.get("entry_id") == entry_id:
            matching_entries.append((entry, index))
    if len(matching_entries) != 1:
        _fail("session-locator", path, "receipt evidence must resolve exactly one committed session entry", entry_id=entry_id)
    entry, entry_index = matching_entries[0]
    entry_end = entry_matches[entry_index + 1].start() if entry_index + 1 < len(entry_matches) else len(text)
    scope = text[entry.end():entry_end]
    if decision_id is not None:
        decision_matches = list(re.finditer(rf"^#### {re.escape(decision_id)}(?:\s|-|$)[^\n]*\n", scope, re.MULTILINE))
        if len(decision_matches) != 1:
            _fail("session-locator", path, "receipt evidence must resolve exactly one decision in its session entry", entry_id=entry_id, decision_id=decision_id)
        decision = decision_matches[0]
        following = re.search(r"^#### D[1-9][0-9]*(?:\s|-|$)[^\n]*\n", scope[decision.end():], re.MULTILINE)
        decision_end = decision.end() + following.start() if following is not None else len(scope)
        scope = scope[decision.start():decision_end]

    matches: list[ReflectionReceipt] = []
    for fenced in re.finditer(r"```yaml\n(?P<document>.*?)```\n", scope, re.DOTALL):
        document = fenced.group("document")
        if not document.startswith("schema: memory-seed/reflection-receipt\n"):
            continue
        receipt = parse_receipt(document, path)
        matches.append(receipt)
    if len(matches) != 1:
        _fail("session-receipt", path, "receipt evidence must resolve exactly one canonical durable receipt", entry_id=entry_id, decision_id=decision_id)
    return matches[0]


@dataclass(frozen=True)
class AdmittedReflectionReceipt:
    """A durable receipt reloaded from one immutable Git session blob."""

    repository: str
    source_commit: str
    session_path: str
    session_blob_oid: str
    entry_id: str
    decision_id: str | None
    receipt: ReflectionReceipt


def admit_reflection_receipt(cwd: Path | str = ".", *, source: str, session_path: str,
                             entry_id: str, decision_id: str | None) -> AdmittedReflectionReceipt:
    """Load the sole canonical receipt from a committed session entry/decision.

    This verifier deliberately takes no receipt ID or raw receipt object. A
    later trusted close/promote surface must generate and persist the canonical
    receipt through the sanctioned session writer, then call this loader to
    return the evidence it actually committed.
    """
    root = Path(cwd).resolve()
    commit = _commit(root, source)
    if commit is None:
        _fail("git-ref", str(root), "receipt evidence source does not resolve to a commit", source=source)
    session_path = _session_path(session_path, str(root), "session_path")
    blob = _tree_blob(root, commit, session_path)
    if blob is None:
        _fail("session-receipt", session_path, "receipt evidence session path is absent from the declared Git commit")
    if blob.mode != CANONICAL_MODE:
        _fail("mode", session_path, "receipt evidence session file must be regular mode 100644", mode=blob.mode)
    receipt = _session_receipt_from_blob(blob.content, session_path, entry_id, decision_id)
    return AdmittedReflectionReceipt(str(root), commit, session_path, blob.oid, entry_id, decision_id, receipt)


def _verified_admitted_receipts(values: Iterable[AdmittedReflectionReceipt], admitted: AdmittedReflectionSet) -> tuple[AdmittedReflectionReceipt, ...]:
    """Reopen every receipt evidence reference; objects themselves carry no authority."""
    evidence = _verified_admitted_set(admitted)
    result: list[AdmittedReflectionReceipt] = []
    seen: dict[str, AdmittedReflectionReceipt] = {}
    for value in values:
        if not isinstance(value, AdmittedReflectionReceipt):
            _fail("admission", "closeout.md", "closeout validation requires Git/session-admitted durable receipts")
        if (
            not isinstance(value.repository, str)
            or not isinstance(value.source_commit, str)
            or not isinstance(value.session_path, str)
            or not isinstance(value.session_blob_oid, str)
            or not isinstance(value.entry_id, str)
            or (value.decision_id is not None and not isinstance(value.decision_id, str))
            or not isinstance(value.receipt, ReflectionReceipt)
        ):
            _fail("admission", "closeout.md", "receipt evidence has malformed immutable Git/session fields")
        fresh = admit_reflection_receipt(
            value.repository,
            source=value.source_commit,
            session_path=value.session_path,
            entry_id=value.entry_id,
            decision_id=value.decision_id,
        )
        if value != fresh:
            _fail("admission", value.session_path, "receipt evidence does not match its declared immutable Git session blob")
        if fresh.repository != evidence.repository or fresh.source_commit != evidence.source_commit:
            _fail("admission", value.session_path, "receipt evidence must be admitted from the reflection closeout's trusted integration commit")
        existing = seen.get(fresh.receipt.receipt_id)
        if existing is not None and existing != fresh:
            _fail("receipt-collision", value.session_path, "conflicting durable receipt evidence shares one receipt ID", receipt_id=fresh.receipt.receipt_id)
        seen[fresh.receipt.receipt_id] = fresh
        result.append(fresh)
    return tuple(result)


@dataclass(frozen=True)
class ReflectionChainClose:
    chain_id: str
    closed_at: str
    retention_days: int
    expires_at: str
    implementer_record_ids: tuple[str, ...]
    reviewer_record_ids: tuple[str, ...]
    orchestrator_record_ids: tuple[str, ...]
    synthesis_record_id: str
    resolved_head_ids: tuple[str, ...]
    disposed_head_ids: tuple[str, ...]
    validation_receipt: str
    receipt_ids: tuple[str, ...]
    path: str = "closeout.md"


def _close_shape(close: ReflectionChainClose, path: str | None = None) -> None:
    """Validate closeout scalar/list shapes before any temporal or graph work."""
    close_path = path or close.path
    _id(close.chain_id, "rlc_", close_path, "chain_id")
    _timestamp(close.closed_at, close_path, "closed_at")
    _timestamp(close.expires_at, close_path, "expires_at")
    if not isinstance(close.retention_days, int) or isinstance(close.retention_days, bool) or close.retention_days < 1:
        _fail("close", close_path, "retention_days must be a positive integer")
    for field_name, values, prefix, required in (
        ("implementer_record_ids", close.implementer_record_ids, "rlr_", True),
        ("reviewer_record_ids", close.reviewer_record_ids, "rlr_", True),
        ("orchestrator_record_ids", close.orchestrator_record_ids, "rlr_", True),
        ("resolved_head_ids", close.resolved_head_ids, "rlr_", False),
        ("disposed_head_ids", close.disposed_head_ids, "rlr_", False),
        ("receipt_ids", close.receipt_ids, "rrc_", True),
    ):
        if not isinstance(values, tuple) or (required and not values) or len(set(values)) != len(values):
            _fail("close", close_path, "close record list must be a unique tuple with required coverage", field=field_name)
        for identifier in values:
            _id(identifier, prefix, close_path, field_name)
    _id(close.synthesis_record_id, "rlr_", close_path, "synthesis_record_id")
    _id(close.validation_receipt, "rrc_", close_path, "validation_receipt")
    if close.validation_receipt not in close.receipt_ids:
        _fail("close", close_path, "validation_receipt must be included in receipt_ids")
    _relative_path(close.path, close_path, "path")


def render_closeout(plan_id: str, closes: Iterable[ReflectionChainClose]) -> str:
    closes = tuple(closes)
    _text(plan_id, "closeout.md", "plan_id")
    for close in closes:
        _close_shape(close)
    header = _yaml_mapping([("schema", "memory-seed/reflection-closeout"), ("version", 1), ("plan_id", plan_id)])
    pieces = ["---\n" + header + "---\n"]
    for close in sorted(closes, key=lambda item: (item.chain_id, item.closed_at)):
        metadata = _yaml_mapping([
            ("chain_id", close.chain_id), ("closed_at", close.closed_at), ("retention_days", close.retention_days), ("expires_at", close.expires_at),
            ("implementer_record_ids", list(close.implementer_record_ids)), ("reviewer_record_ids", list(close.reviewer_record_ids)),
            ("orchestrator_record_ids", list(close.orchestrator_record_ids)), ("synthesis_record_id", close.synthesis_record_id),
            ("resolved_head_ids", list(close.resolved_head_ids)), ("disposed_head_ids", list(close.disposed_head_ids)),
            ("validation_receipt", close.validation_receipt), ("receipt_ids", list(close.receipt_ids)),
        ])
        pieces.append(f"\n## Chain {close.chain_id}\n\n```yaml\n{metadata}```\n")
    return "".join(pieces)


def parse_closeout(raw: bytes | str, path: str = "closeout.md") -> tuple[str, tuple[ReflectionChainClose, ...]]:
    text = _canonical_text(raw, path)
    prefix = re.match(r"^---\n(?P<header>.*?)---\n", text, re.DOTALL)
    if not prefix:
        _fail("markdown", path, "closeout needs canonical frontmatter")
    header = _parse_yaml_mapping(prefix.group("header"), path)
    if header != {"schema": "memory-seed/reflection-closeout", "version": 1, "plan_id": header.get("plan_id")} or not isinstance(header.get("plan_id"), str):
        _fail("schema", path, "unsupported reflection closeout schema/version")
    blocks = list(re.finditer(r"^\n## Chain (?P<chain>rlc_[0-9abcdefghjkmnpqrstvwxyz]{20})\n\n```yaml\n(?P<meta>.*?)```\n", text[prefix.end():], re.MULTILINE | re.DOTALL))
    closes: list[ReflectionChainClose] = []
    required = ("chain_id", "closed_at", "retention_days", "expires_at", "implementer_record_ids", "reviewer_record_ids", "orchestrator_record_ids", "synthesis_record_id", "resolved_head_ids", "disposed_head_ids", "validation_receipt", "receipt_ids")
    for block in blocks:
        item = _parse_yaml_mapping(block.group("meta"), path)
        _required(item, required, path)
        _only(item, required, path)
        if item["chain_id"] != block.group("chain"):
            _fail("close", path, "closeout heading and metadata chain differ")
        for list_key in ("implementer_record_ids", "reviewer_record_ids", "orchestrator_record_ids", "resolved_head_ids", "disposed_head_ids", "receipt_ids"):
            if not isinstance(item[list_key], list) or any(not isinstance(value, str) for value in item[list_key]):
                _fail("close", path, "close record list field must be a string list", field=list_key)
        close = ReflectionChainClose(
            _id(item["chain_id"], "rlc_", path, "chain_id"), _timestamp(item["closed_at"], path, "closed_at"), item["retention_days"],
            _timestamp(item["expires_at"], path, "expires_at"), tuple(item["implementer_record_ids"]), tuple(item["reviewer_record_ids"]),
            tuple(item["orchestrator_record_ids"]), _id(item["synthesis_record_id"], "rlr_", path, "synthesis_record_id"),
            tuple(item["resolved_head_ids"]), tuple(item["disposed_head_ids"]), _id(item["validation_receipt"], "rrc_", path, "validation_receipt"), tuple(item["receipt_ids"]), path,
        )
        _close_shape(close, path)
        closes.append(close)
    result = (header["plan_id"], tuple(closes))
    if render_closeout(result[0], result[1]) != text:
        _fail("canonical-bytes", path, "closeout is valid but not the canonical rendering")
    return result


def validate_receipt(receipt: ReflectionReceipt, path: str = "receipt") -> None:
    _id(receipt.receipt_id, "rrc_", path, "receipt_id")
    _id(receipt.chain_id, "rlc_", path, "chain_id")
    if not receipt.member_record_ids or not receipt.head_record_ids or receipt.disposition not in {"promoted", "already-covered", "expired-unpromoted", "early-deletion"}:
        _fail("receipt", path, "receipt needs heads, members, and a valid disposition")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", receipt.detail_digest):
        _fail("receipt", path, "detail_digest must be sha256:<64 lowercase hex>")
    _timestamp(receipt.recorded_at, path, "recorded_at")


@dataclass(frozen=True)
class AdmittedChainClose:
    """One close record loaded from a Git-tracked canonical closeout blob."""

    repository: str
    source_commit: str
    closeout_path: str
    closeout_oid: str
    close: ReflectionChainClose


def admit_reflection_closeout(admitted: AdmittedReflectionSet) -> tuple[AdmittedChainClose, ...]:
    """Load closeout records from the same immutable tree as an admission."""
    evidence = _verified_admitted_set(admitted)
    closeout_path = f"{evidence.manifest.active_dir}/closeout.md"
    blob = _tree_blob(Path(evidence.repository), evidence.source_commit, closeout_path)
    if blob is None:
        _fail("closeout", closeout_path, "Git-admitted reflection tree has no closeout document")
    if blob.mode != CANONICAL_MODE:
        _fail("mode", closeout_path, "reflection closeout must be regular mode 100644", mode=blob.mode)
    plan_id, closes = parse_closeout(blob.content, "closeout.md")
    if plan_id != evidence.manifest.plan_id:
        _fail("closeout", closeout_path, "closeout plan_id does not match its admitted manifest")
    return tuple(AdmittedChainClose(evidence.repository, evidence.source_commit, closeout_path, blob.oid, close) for close in closes)


def _verified_admitted_close(value: AdmittedChainClose, admitted: AdmittedReflectionSet) -> ReflectionChainClose:
    if not isinstance(value, AdmittedChainClose):
        _fail("admission", "closeout.md", "closeout validation requires a Git-admitted closeout record")
    evidence = _verified_admitted_set(admitted)
    fresh = admit_reflection_closeout(evidence)
    if value not in fresh:
        _fail("admission", "closeout.md", "closeout evidence does not match the declared immutable Git tree")
    return value.close


def validate_chain_close(value: AdmittedChainClose, admitted: AdmittedReflectionSet,
                         receipts: Iterable[AdmittedReflectionReceipt]) -> None:
    """Validate a closeout only against canonically admitted ledger state.

    Parsed records are not sufficient authority here. Both the reflection
    records and closeout are re-loaded from their declared Git commit.
    """
    evidence = _verified_admitted_set(admitted)
    manifest = evidence.manifest
    close = _verified_admitted_close(value, evidence)
    fragments = evidence.fragments
    _close_shape(close)
    if close.retention_days != manifest.reflection_retention_days:
        _fail("retention", close.path, "close retention_days must equal the manifest policy", expected=manifest.reflection_retention_days, actual=close.retention_days)
    if _as_utc(close.expires_at) != _as_utc(close.closed_at) + timedelta(days=manifest.reflection_retention_days):
        _fail("close", close.path, "expires_at must equal closed_at plus manifest retention_days")
    index = _record_index(fragments)
    members = {identifier for identifier, (_fragment, record) in index.items() if record.chain_id == close.chain_id}
    if not members:
        _fail("close", close.path, "close record names an unknown chain")
    heads = {record.record_id for record in live_heads(fragments).get(close.chain_id, ())}
    resolved = set(close.resolved_head_ids)
    disposed = set(close.disposed_head_ids)
    if resolved & disposed or resolved | disposed != heads:
        _fail("close", close.path, "all and only divergent live heads must be resolved or explicitly disposed")
    roles = {"worker": set(close.implementer_record_ids), "validator": set(close.reviewer_record_ids), "orchestrator": set(close.orchestrator_record_ids)}
    participants = {person.participant: person for person in manifest.participants}
    for role, identifiers in roles.items():
        if not identifiers:
            _fail("close", close.path, "close lacks required independent role coverage", role=role)
        for identifier in identifiers:
            pair = index.get(identifier)
            if pair is None or pair[1].chain_id != close.chain_id:
                _fail("close", close.path, "role coverage references an absent/foreign record", record_id=identifier)
            participant = participants.get(pair[0].participant)
            if participant is None:
                _fail("ownership", close.path, "close coverage references a fragment participant absent from manifest", record_id=identifier)
            if participant.role != role:
                _fail("close", close.path, "role coverage record has wrong participant role", record_id=identifier, role=role)

    def ancestors(identifier: str) -> set[str]:
        result: set[str] = set()
        pending = list(index[identifier][1].parents)
        while pending:
            current = pending.pop()
            if current not in result:
                result.add(current)
                pending.extend(index[current][1].parents)
        return result

    for implementer_id in roles["worker"]:
        if not any(implementer_id in ancestors(reviewer_id) for reviewer_id in roles["validator"]):
            _fail("close-topology", close.path, "reviewer coverage is not connected to an implementer record", implementer_record_id=implementer_id)
    for reviewer_id in roles["validator"]:
        if not any(reviewer_id in ancestors(orchestrator_id) for orchestrator_id in roles["orchestrator"]):
            _fail("close-topology", close.path, "orchestrator coverage is not connected to reviewer coverage", reviewer_record_id=reviewer_id)
    synthesis = index.get(close.synthesis_record_id)
    if synthesis is None or synthesis[1].chain_id != close.chain_id or synthesis[1].kind not in {"resolution", "closeout", "promotion"}:
        _fail("close", close.path, "close needs an orchestrator synthesis record in its chain")
    synthesis_participant = participants.get(synthesis[0].participant) if synthesis is not None else None
    if (
        synthesis_participant is None
        or synthesis_participant.role != "orchestrator"
        or synthesis_participant.participant != manifest.orchestrator["participant"]
        or close.synthesis_record_id not in roles["orchestrator"]
    ):
        _fail("close-topology", close.path, "synthesis must be authored by and declared under the manifest orchestrator")
    admitted_receipts = _verified_admitted_receipts(receipts, evidence)
    receipts_by_id = {item.receipt.receipt_id: item.receipt for item in admitted_receipts}
    validation_receipt = receipts_by_id.get(close.validation_receipt)
    if validation_receipt is None:
        _fail("receipt", close.path, "close references an unavailable durable receipt required for validation", receipt_id=close.validation_receipt)
    covered: set[str] = set()
    for receipt_id_value in close.receipt_ids:
        receipt = receipts_by_id.get(receipt_id_value)
        if receipt is None:
            _fail("receipt", close.path, "close references an unavailable durable receipt", receipt_id=receipt_id_value)
        validate_receipt(receipt, close.path)
        if receipt.plan_id != manifest.plan_id or receipt.chain_id != close.chain_id:
            _fail("receipt", close.path, "receipt plan/chain does not match close")
        if not set(receipt.head_record_ids).issubset(heads):
            _fail("receipt", close.path, "receipt names a non-live head", heads=sorted(set(receipt.head_record_ids) - heads))
        covered.update(receipt.member_record_ids)
    if covered != members:
        _fail("receipt-coverage", close.path, "durable receipts must cover every chain member", missing=sorted(members - covered), foreign=sorted(covered - members))


def validate_board_close(closes: Iterable[AdmittedChainClose], admitted: AdmittedReflectionSet,
                         receipts: Iterable[AdmittedReflectionReceipt]) -> None:
    evidence = _verified_admitted_set(admitted)
    fragments = evidence.fragments
    receipts = tuple(receipts)
    chains = {record.chain_id for _fragment, record in _record_index(fragments).values()}
    by_chain: dict[str, AdmittedChainClose] = {}
    for close in closes:
        parsed_close = _verified_admitted_close(close, evidence)
        if parsed_close.chain_id in by_chain:
            _fail("close-collision", parsed_close.path, "multiple close records name one chain", chain=parsed_close.chain_id)
        by_chain[parsed_close.chain_id] = close
    if chains != set(by_chain):
        _fail("board-close", "closeout.md", "board cannot close until every admitted chain has a close record", missing=sorted(chains - set(by_chain)))
    for close in by_chain.values():
        validate_chain_close(close, evidence, receipts)


@dataclass(frozen=True)
class EarlyExpiryApprovalReceipt:
    """A canonical host-signed receipt for one early-deletion request.

    The signing private key is never accepted or stored by this module. The
    immutable manifest supplies the corresponding Ed25519 public trust anchor.
    """

    key_id: str
    plan_id: str
    chain_id: str
    member_record_ids: tuple[str, ...]
    reason: str
    approved_at: str
    expires_at: str
    signature: str


EARLY_EXPIRY_APPROVAL_FIELDS = (
    "schema", "version", "key_id", "plan_id", "chain_id", "member_record_ids", "reason", "approved_at", "expires_at", "signature",
)
ED25519_P = 2**255 - 19
ED25519_L = 2**252 + 27742317777372353535851937790883648493
ED25519_D = (-121665 * pow(121666, ED25519_P - 2, ED25519_P)) % ED25519_P
ED25519_I = pow(2, (ED25519_P - 1) // 4, ED25519_P)
ED25519_BASE_Y = (4 * pow(5, ED25519_P - 2, ED25519_P)) % ED25519_P


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an RFC 8032 Ed25519 signature without an issuer callback."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    encoded_r, encoded_s = signature[:32], signature[32:]
    scalar_s = int.from_bytes(encoded_s, "little")
    if scalar_s >= ED25519_L:
        return False

    def decode_point(encoded: bytes) -> tuple[int, int] | None:
        y = int.from_bytes(encoded, "little") & ((1 << 255) - 1)
        sign = encoded[31] >> 7
        if y >= ED25519_P:
            return None
        xx = ((y * y - 1) * pow(ED25519_D * y * y + 1, ED25519_P - 2, ED25519_P)) % ED25519_P
        x = pow(xx, (ED25519_P + 3) // 8, ED25519_P)
        if (x * x - xx) % ED25519_P:
            x = (x * ED25519_I) % ED25519_P
        if (x * x - xx) % ED25519_P:
            return None
        if (x & 1) != sign:
            x = ED25519_P - x
        return (x, y)

    def add(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        x1, y1 = left
        x2, y2 = right
        denominator_x = pow((1 + ED25519_D * x1 * x2 * y1 * y2) % ED25519_P, ED25519_P - 2, ED25519_P)
        denominator_y = pow((1 - ED25519_D * x1 * x2 * y1 * y2) % ED25519_P, ED25519_P - 2, ED25519_P)
        return (
            ((x1 * y2 + x2 * y1) * denominator_x) % ED25519_P,
            ((y1 * y2 + x1 * x2) * denominator_y) % ED25519_P,
        )

    def multiply(point: tuple[int, int], scalar: int) -> tuple[int, int]:
        total = (0, 1)
        current = point
        while scalar:
            if scalar & 1:
                total = add(total, current)
            current = add(current, current)
            scalar >>= 1
        return total

    def has_prime_order(point: tuple[int, int]) -> bool:
        return point != (0, 1) and multiply(point, ED25519_L) == (0, 1)

    public_point = decode_point(public_key)
    r_point = decode_point(encoded_r)
    if public_point is None or r_point is None or not has_prime_order(public_point) or not has_prime_order(r_point):
        return False
    base_x_squared = ((ED25519_BASE_Y * ED25519_BASE_Y - 1) * pow(ED25519_D * ED25519_BASE_Y * ED25519_BASE_Y + 1, ED25519_P - 2, ED25519_P)) % ED25519_P
    base_x = pow(base_x_squared, (ED25519_P + 3) // 8, ED25519_P)
    if base_x & 1:
        base_x = ED25519_P - base_x
    digest = int.from_bytes(sha512(encoded_r + public_key + message).digest(), "little") % ED25519_L
    return multiply((base_x, ED25519_BASE_Y), scalar_s) == add(r_point, multiply(public_point, digest))


def early_expiry_approval_from_dict(value: Mapping[str, Any], path: str = "early-expiry-approval.yaml") -> EarlyExpiryApprovalReceipt:
    _required(value, EARLY_EXPIRY_APPROVAL_FIELDS, path)
    _only(value, EARLY_EXPIRY_APPROVAL_FIELDS, path)
    if value["schema"] != "memory-seed/reflection-early-expiry-approval" or value["version"] != 1:
        _fail("schema", path, "unsupported early-expiry approval schema/version")
    members = value["member_record_ids"]
    if not isinstance(members, list) or not members or any(not isinstance(item, str) for item in members) or len(set(members)) != len(members):
        _fail("live-user-approval", path, "approval member_record_ids must be a non-empty unique string list")
    receipt = EarlyExpiryApprovalReceipt(
        _text(value["key_id"], path, "key_id"), _text(value["plan_id"], path, "plan_id"),
        _id(value["chain_id"], "rlc_", path, "chain_id"), tuple(members), _text(value["reason"], path, "reason"),
        _timestamp(value["approved_at"], path, "approved_at"), _timestamp(value["expires_at"], path, "expires_at"),
        _text(value["signature"], path, "signature"),
    )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", receipt.key_id):
        _fail("live-user-approval", path, "approval key_id must be a stable token")
    if any(not re.fullmatch(r"rlr_[0-9abcdefghjkmnpqrstvwxyz]{20}", item) for item in receipt.member_record_ids):
        _fail("live-user-approval", path, "approval member_record_ids must be reflection record IDs")
    if not re.fullmatch(r"ed25519:[0-9a-f]{128}", receipt.signature):
        _fail("live-user-approval", path, "approval signature must be ed25519:<64-byte lowercase hex>")
    return receipt


def early_expiry_approval_payload(receipt: EarlyExpiryApprovalReceipt) -> bytes:
    return _yaml_mapping([
        ("schema", "memory-seed/reflection-early-expiry-approval"), ("version", 1), ("key_id", receipt.key_id),
        ("plan_id", receipt.plan_id), ("chain_id", receipt.chain_id), ("member_record_ids", list(receipt.member_record_ids)),
        ("reason", receipt.reason), ("approved_at", receipt.approved_at), ("expires_at", receipt.expires_at),
    ]).encode("utf-8")


def render_early_expiry_approval(receipt: EarlyExpiryApprovalReceipt) -> str:
    early_expiry_approval_from_dict({
        "schema": "memory-seed/reflection-early-expiry-approval", "version": 1, "key_id": receipt.key_id,
        "plan_id": receipt.plan_id, "chain_id": receipt.chain_id, "member_record_ids": list(receipt.member_record_ids),
        "reason": receipt.reason, "approved_at": receipt.approved_at, "expires_at": receipt.expires_at, "signature": receipt.signature,
    })
    return _yaml_mapping([
        ("schema", "memory-seed/reflection-early-expiry-approval"), ("version", 1), ("key_id", receipt.key_id),
        ("plan_id", receipt.plan_id), ("chain_id", receipt.chain_id), ("member_record_ids", list(receipt.member_record_ids)),
        ("reason", receipt.reason), ("approved_at", receipt.approved_at), ("expires_at", receipt.expires_at), ("signature", receipt.signature),
    ])


def parse_early_expiry_approval(raw: bytes | str, path: str = "early-expiry-approval.yaml") -> EarlyExpiryApprovalReceipt:
    text = _canonical_text(raw, path)
    receipt = early_expiry_approval_from_dict(_parse_yaml_mapping(text, path), path)
    if render_early_expiry_approval(receipt) != text:
        _fail("canonical-bytes", path, "early-expiry approval is valid but not the canonical rendering")
    return receipt


def validate_early_expiry_approval(receipt: EarlyExpiryApprovalReceipt, *, manifest: ReflectionManifest,
                                   close: ReflectionChainClose, member_record_ids: tuple[str, ...]) -> None:
    if receipt.key_id != manifest.early_expiry_approval_key_id:
        _fail("live-user-approval", close.path, "approval key_id does not match the manifest trust anchor")
    if (
        receipt.plan_id != manifest.plan_id or receipt.chain_id != close.chain_id
        or tuple(sorted(receipt.member_record_ids)) != member_record_ids or receipt.expires_at != close.expires_at
    ):
        _fail("live-user-approval", close.path, "approval receipt does not bind this exact expiry request")
    public_key = bytes.fromhex(manifest.early_expiry_approval_public_key.removeprefix("ed25519:"))
    signature = bytes.fromhex(receipt.signature.removeprefix("ed25519:"))
    if not ed25519_verify(public_key, early_expiry_approval_payload(receipt), signature):
        _fail("live-user-approval", close.path, "approval receipt signature does not verify against the manifest trust anchor")


def eligible_expiry_paths(closes: Iterable[AdmittedChainClose], admitted: AdmittedReflectionSet,
                          receipts: Iterable[AdmittedReflectionReceipt], *, now: datetime, chain: str | None = None,
                          early: bool = False, approval_receipt: bytes | str | None = None) -> tuple[str, ...]:
    if now.tzinfo is None:
        _fail("expiry", "closeout.md", "expiry comparison requires timezone-aware now")
    evidence = _verified_admitted_set(admitted)
    manifest = evidence.manifest
    fragments = evidence.fragments
    receipts = _verified_admitted_receipts(receipts, evidence)
    close_map: dict[str, AdmittedChainClose] = {}
    for value in closes:
        close = _verified_admitted_close(value, evidence)
        if close.chain_id in close_map:
            _fail("close-collision", close.path, "multiple close records name one chain", chain=close.chain_id)
        close_map[close.chain_id] = value
    if chain is None and early:
        _fail("expiry", "closeout.md", "early expiry requires one exact chain")
    candidates = [close_map[chain]] if chain is not None and chain in close_map else ([] if chain is not None else list(close_map.values()))
    if chain is not None and not candidates:
        _fail("expiry", "closeout.md", "requested chain has no close record", chain=chain)
    eligible: list[str] = []
    for value in candidates:
        close = _verified_admitted_close(value, evidence)
        # Early disposal has the same closure/receipt gate as ordinary expiry;
        # a user can approve deletion, not bypass unresolved coordination work.
        validate_chain_close(value, evidence, receipts)
        if early:
            member_ids = tuple(sorted(record.record_id for _fragment, record in _record_index(fragments).values() if record.chain_id == close.chain_id))
            if not isinstance(approval_receipt, (bytes, str)):
                _fail("live-user-approval", close.path, "early deletion requires a canonical signed approval receipt")
            approval = parse_early_expiry_approval(approval_receipt)
            validate_early_expiry_approval(approval, manifest=manifest, close=close, member_record_ids=member_ids)
            receipts_by_id = {item.receipt.receipt_id: item.receipt for item in receipts}
            if any(receipts_by_id[item].disposition == "promoted" for item in close.receipt_ids if item in receipts_by_id):
                _fail("early-expiry", close.path, "early deletion is limited to unpromoted chains")
        else:
            if now < _as_utc(close.expires_at):
                continue
        eligible.append(value.closeout_path)
    return tuple(sorted(set(eligible)))


@dataclass(frozen=True)
class ReflectionBlob:
    path: str
    oid: str
    raw_sha256: str
    mode: str
    content: bytes


@dataclass(frozen=True)
class _ReflectionFusePlan:
    plan_id: str
    source_branch: str
    base_ref: str
    source_tip: str
    base_tip: str
    manifest_oid: str
    manifest_sha256: str
    additions: tuple[ReflectionBlob, ...]
    already_present: tuple[str, ...]
    token: str
    created_at: datetime


@dataclass
class ReflectionFuseResult:
    changed: bool
    plan_id: str | None = None
    source_tip: str | None = None
    base_tip: str | None = None
    manifest_sha256: str | None = None
    planned_paths: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    preview_token: str | None = None
    issues: list[ReflectionDiagnostic] = field(default_factory=list)
    _plan: _ReflectionFusePlan | None = field(default=None, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {"changed": self.changed, "plan_id": self.plan_id, "source_tip": self.source_tip, "base_tip": self.base_tip,
                "manifest_sha256": self.manifest_sha256, "planned_paths": list(self.planned_paths),
                "already_present": list(self.already_present), "preview_token": self.preview_token,
                "issues": [issue.as_dict() for issue in self.issues]}


def _git(root: Path, *args: str, binary: bool = False) -> tuple[int, bytes | str]:
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if binary:
        return result.returncode, result.stdout
    return result.returncode, result.stdout.decode("utf-8", errors="replace").strip()


def _commit(root: Path, ref: str) -> str | None:
    code, output = _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return output if code == 0 and isinstance(output, str) and re.fullmatch(r"[0-9a-f]{40}", output) else None


def _tree_blob(root: Path, commit: str, path: str) -> ReflectionBlob | None:
    code, line = _git(root, "ls-tree", commit, "--", path)
    if code or not isinstance(line, str) or not line:
        return None
    match = re.fullmatch(r"(?P<mode>\d+) (?P<kind>\w+) (?P<oid>[0-9a-f]{40})\t(?P<path>.+)", line)
    if not match or match.group("path") != path:
        _fail("git", path, "could not read unique Git tree entry")
    # Reading the resolved object ID avoids Windows treating a long
    # ``<commit>:<path>`` revision expression as an overlong filesystem path.
    code, content = _git(root, "cat-file", "blob", match.group("oid"), binary=True)
    if code or not isinstance(content, bytes):
        _fail("git", path, "could not read Git blob")
    return ReflectionBlob(path, match.group("oid"), sha256(content).hexdigest(), match.group("mode"), content)


def _changed_paths(root: Path, base: str, source: str, family: str) -> list[tuple[str, tuple[str, ...]]]:
    code, output = _git(root, "diff", "--name-status", "-z", "--find-renames", "--find-copies", f"{base}...{source}", "--", family, binary=True)
    if code or not isinstance(output, bytes):
        _fail("git-diff", family, "could not compute three-dot reflection changes")
    fields = output.decode("utf-8", errors="strict").split("\0")
    result: list[tuple[str, tuple[str, ...]]] = []
    index = 0
    while index < len(fields) - 1:
        status = fields[index]
        index += 1
        if not status:
            break
        if status.startswith(("R", "C")):
            result.append((status[0], (fields[index], fields[index + 1])))
            index += 2
        else:
            result.append((status[0], (fields[index],)))
            index += 1
    return result


def _admitted_fragments_at_commit(root: Path, commit: str, manifest: ReflectionManifest) -> AdmittedReflectionSet:
    """Load every complete reserved pair visible at one immutable Git commit."""
    admitted = admit_reflection_git_tree(root, source=commit, plan_id=manifest.plan_id)
    if render_manifest(admitted.manifest) != render_manifest(manifest):
        _fail("manifest-immutable", manifest.manifest_path, "source admission manifest differs from the immutable base manifest")
    return admitted


def reflection_fuse_preview(cwd: Path | str = ".", *, plan_id: str, branch: str, base: str = "HEAD") -> ReflectionFuseResult:
    root = Path(cwd).resolve()
    source_tip = _commit(root, branch)
    base_tip = _commit(root, base)
    if source_tip is None or base_tip is None:
        issue = ReflectionDiagnostic("git-ref", str(root), "source branch or base ref does not resolve", {"branch": branch, "base": base})
        return ReflectionFuseResult(False, plan_id=plan_id, issues=[issue])
    manifest_path = f"{REFLECTION_ROOT}/{plan_id}/{MANIFEST_NAME}"
    manifest_blob = _tree_blob(root, base_tip, manifest_path)
    if manifest_blob is None:
        issue = ReflectionDiagnostic("manifest", manifest_path, "base tree has no reflection manifest", {})
        return ReflectionFuseResult(False, plan_id=plan_id, source_tip=source_tip, base_tip=base_tip, issues=[issue])
    try:
        if manifest_blob.mode != CANONICAL_MODE:
            _fail("mode", manifest_path, "reflection manifest must be regular mode 100644", mode=manifest_blob.mode)
        manifest = parse_manifest(manifest_blob.content, manifest_path)
        if manifest.plan_id != plan_id:
            _fail("manifest", manifest_path, "manifest plan_id does not match requested plan")
        code, _ = _git(root, "merge-base", "--is-ancestor", manifest.base_sha, source_tip)
        if code != 0:
            _fail("base", manifest_path, "source tip is not descended from manifest base", source_tip=source_tip)
        participant = manifest.participant_for_branch(branch)
        if participant is None:
            _fail("ownership", manifest_path, "source branch has no unique manifest participant", branch=branch)
        changes = _changed_paths(root, base_tip, source_tip, f"{REFLECTION_ROOT}/{plan_id}")
        additions: list[ReflectionBlob] = []
        already_present: list[str] = []
        allowed_paths = {f"{manifest.active_dir}/{reservation.report_path}": reservation for reservation in participant.reservations}
        allowed_paths.update({f"{manifest.active_dir}/{reservation.fragment_path}": reservation for reservation in participant.reservations})
        changed_add_paths: set[str] = set()
        for status, paths in changes:
            if status in {"R", "C"}:
                _fail("path-change", f"{REFLECTION_ROOT}/{plan_id}", "renames and copies of active reflection files are forbidden", status=status, paths=list(paths))
            rel_path = paths[0]
            if rel_path == manifest_path:
                _fail("manifest-immutable", rel_path, "active manifest may not change on a participant branch")
            base_blob = _tree_blob(root, base_tip, rel_path)
            source_blob = _tree_blob(root, source_tip, rel_path)
            if status == "D" or source_blob is None:
                _fail("active-immutability", rel_path, "active reflection paths may not be deleted")
            if base_blob is not None:
                if base_blob.mode == source_blob.mode == CANONICAL_MODE and base_blob.content == source_blob.content:
                    already_present.append(rel_path)
                    continue
                _fail("active-immutability", rel_path, "base reflection path changed bytes or mode")
            if rel_path not in allowed_paths:
                _fail("reserved-path", rel_path, "source added an unreserved reflection path")
            if source_blob.mode != CANONICAL_MODE:
                _fail("mode", rel_path, "reflection files must be regular mode 100644", mode=source_blob.mode)
            additions.append(source_blob)
            changed_add_paths.add(rel_path)
        if not additions and not already_present:
            _fail("empty", manifest.active_dir, "source branch has no reflection additions")
        reservations = {reservation.sequence: reservation for reservation in participant.reservations}
        for reservation in reservations.values():
            report_path = f"{manifest.active_dir}/{reservation.report_path}"
            fragment_path = f"{manifest.active_dir}/{reservation.fragment_path}"
            touched = {path for path in (report_path, fragment_path) if path in changed_add_paths}
            if touched and touched != {report_path, fragment_path}:
                _fail("report-provenance", manifest.active_dir, "a reservation's report and fragment must arrive together", sequence=reservation.sequence)
        for reservation in reservations.values():
            report_path = f"{manifest.active_dir}/{reservation.report_path}"
            fragment_path = f"{manifest.active_dir}/{reservation.fragment_path}"
            if report_path not in changed_add_paths:
                continue
            report_blob = next(blob for blob in additions if blob.path == report_path)
            fragment_blob = next(blob for blob in additions if blob.path == fragment_path)
            report = parse_report(report_blob.content, report_path)
            fragment = parse_fragment(fragment_blob.content, fragment_path)
            validate_fragment(fragment, manifest, report, branch=branch, path=fragment_path)
        # Parse every visible pair, not merely the new pair: a source record may
        # respond to a base record, and graph validity is an admission property.
        _admitted_fragments_at_commit(root, source_tip, manifest)
        token_source = "\0".join([plan_id, branch, base, source_tip, base_tip, manifest_blob.oid] + sorted(blob.oid for blob in additions))
        token = sha256(token_source.encode("utf-8")).hexdigest()
        plan = _ReflectionFusePlan(plan_id, branch, base, source_tip, base_tip, manifest_blob.oid, manifest_blob.raw_sha256,
                                   tuple(sorted(additions, key=lambda item: item.path)), tuple(sorted(already_present)), token,
                                   datetime.now(timezone.utc))
        return ReflectionFuseResult(bool(additions), plan_id, source_tip, base_tip, manifest_blob.raw_sha256,
                                    [blob.path for blob in plan.additions], list(plan.already_present), token, [], plan)
    except ReflectionValidationError as exc:
        return ReflectionFuseResult(False, plan_id, source_tip, base_tip, manifest_blob.raw_sha256, issues=[exc.diagnostic])


def reflection_fuse(cwd: Path | str = ".", *, plan_id: str, branch: str, base: str = "HEAD", apply: bool = False) -> ReflectionFuseResult:
    if apply:
        return ReflectionFuseResult(False, plan_id=plan_id, issues=[ReflectionDiagnostic("internal-only", "reflection fuse", "reflection apply is internal to coordinated session/reflection integration", {})])
    return reflection_fuse_preview(cwd, plan_id=plan_id, branch=branch, base=base)


def _apply_reflection_fuse_plan(cwd: Path | str, plan: _ReflectionFusePlan, *, preview_token: str, max_age_seconds: int = 300) -> ReflectionFuseResult:
    """Internal coordinated-integration primitive; never exposed as a CLI path."""
    root = Path(cwd).resolve()
    if preview_token != plan.token or datetime.now(timezone.utc) - plan.created_at > timedelta(seconds=max_age_seconds):
        return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[ReflectionDiagnostic("preview-token", "reflection fuse", "preview token is invalid or expired", {})])
    current_tip = _commit(root, plan.source_branch)
    if current_tip != plan.source_tip:
        return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[ReflectionDiagnostic("source-tip", "reflection fuse", "source tip changed after preview", {"expected": plan.source_tip, "actual": current_tip})])
    current_base = _commit(root, plan.base_ref)
    if current_base != plan.base_tip or _commit(root, "HEAD") != plan.base_tip:
        return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[ReflectionDiagnostic("base-tip", "reflection fuse", "base ref or integration HEAD changed after preview", {"expected": plan.base_tip, "base_ref": plan.base_ref, "actual_base": current_base, "actual_head": _commit(root, "HEAD")})])
    manifest_path = f"{REFLECTION_ROOT}/{plan.plan_id}/{MANIFEST_NAME}"
    manifest_blob = _tree_blob(root, current_base, manifest_path)
    if manifest_blob is None or manifest_blob.oid != plan.manifest_oid or manifest_blob.raw_sha256 != plan.manifest_sha256:
        return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[ReflectionDiagnostic("manifest-toctou", manifest_path, "base manifest identity changed after preview", {})])
    for blob in plan.additions:
        if _tree_blob(root, current_base, blob.path) is not None:
            return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[ReflectionDiagnostic("base-state-toctou", blob.path, "planned addition is no longer absent from the base state", {})])
    written: list[str] = []
    try:
        for blob in plan.additions:
            target = root / Path(blob.path)
            if target.exists() or target.is_symlink():
                _fail("base-collision", blob.path, "integration target is unexpectedly occupied")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob.content)
            written.append(blob.path)
    except ReflectionValidationError as exc:
        for rel_path in reversed(written):
            (root / Path(rel_path)).unlink(missing_ok=True)
        return ReflectionFuseResult(False, plan_id=plan.plan_id, issues=[exc.diagnostic])
    return ReflectionFuseResult(bool(written), plan.plan_id, plan.source_tip, plan.base_tip, plan.manifest_sha256,
                                written, list(plan.already_present), plan.token)


# ---------------------------------------------------------------------------
# Reflection workstream ledger v2
# ---------------------------------------------------------------------------
#
# The v1 fragment/fuse format above is intentionally left intact.  New boards
# are selected by an explicit discriminator and use the types below; there is
# no heuristic conversion between the two families.

WORKSTREAM_LEDGER_SCHEMA = "memory-seed/reflection-workstream-ledger"
WORKSTREAM_LEDGER_VERSION = 2
WORKSTREAM_LEDGER_NAME = "ledger.md"
WORKSTREAM_LEDGER_DOMAIN = b"memory-seed/reflection-workstream-ledger/v2/ledger\0"
WORKSTREAM_DETAIL_DOMAIN = b"memory-seed/reflection-workstream-ledger/v2/detail\0"
WORKSTREAM_ID_DOMAIN = b"memory-seed/reflection-workstream-ledger/v2\0"
WORKSTREAM_HEADER_FIELDS = (
    "schema", "version", "workstream_id", "working_branch", "base_sha", "created_at",
    "reflection_retention_days", "retention_extension_receipt", "retention_approval_key_id", "id_salt",
)
WORKSTREAM_RECORD_FIELDS = (
    "record_id", "created_at", "role", "from_phase", "to_phase", "closed_at", "chain_id", "parents",
    "relationship", "no_related_thread", "depends_on", "source", "related_decisions", "confidence",
    "pre_ledger_digest", "detail_digest",
)
WORKSTREAM_REBIND_FIELDS = (
    "record_id", "created_at", "role", "from_branch", "to_branch", "source_tip", "target_pre_merge_tip",
    "integration_commit", "pre_ledger_digest", "detail_digest", "reason",
)
WORKSTREAM_PHASES = ("plan", "implement", "review", "orchestrate", "closed")
WORKSTREAM_ROLES = {"planner", "implementer", "reviewer", "orchestrator"}
WORKSTREAM_RELATIONSHIPS = {"no_related_thread", "refines", "responds", "challenges", "corrects", "combines", "orphan"}
WORKSTREAM_TRANSITIONS = {
    ("plan", "implement"): "planner",
    ("implement", "review"): "implementer",
    ("review", "implement"): "reviewer",
    ("review", "orchestrate"): "reviewer",
    ("orchestrate", "closed"): "orchestrator",
}
WORKSTREAM_PHASE_OWNERS = {"plan": "planner", "implement": "implementer", "review": "reviewer", "orchestrate": "orchestrator"}
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_OID_RE = re.compile(r"^[0-9a-f]{40,64}$")


def _v2_digest(domain: bytes, raw: bytes) -> str:
    return "sha256:" + sha256(domain + raw).hexdigest()


def _v2_yaml_inline(value: Any) -> str:
    """The v2 renderer preserves all-digit IDs/nonces as strings."""
    if isinstance(value, list):
        return "[" + ", ".join(_v2_yaml_inline(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{key}: {_v2_yaml_inline(item)}" for key, item in value.items()) + "}"
    if isinstance(value, str) and re.fullmatch(r"0|[1-9]\d*", value):
        return json.dumps(value, ensure_ascii=False)
    return _quote(value)


def _v2_yaml_mapping(items: Sequence[tuple[str, Any]]) -> str:
    lines: list[str] = []
    for key, value in items:
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for member in value:
                if isinstance(member, Mapping):
                    member_items = list(member.items())
                    if not member_items:
                        _fail("schema", "<renderer>", "empty list map is unsupported")
                    first_key, first_value = member_items[0]
                    lines.append(f"  - {first_key}: {_v2_yaml_inline(first_value)}")
                    for nested_key, nested_value in member_items[1:]:
                        lines.append(f"    {nested_key}: {_v2_yaml_inline(nested_value)}")
                else:
                    lines.append(f"  - {_v2_yaml_inline(member)}")
        else:
            lines.append(f"{key}: {_v2_yaml_inline(value)}")
    return "\n".join(lines) + "\n"


def workstream_ledger_digest(raw: bytes | str) -> str:
    """Return the domain-separated digest of canonical ledger bytes."""
    text = _canonical_text(raw, "ledger.md")
    return _v2_digest(WORKSTREAM_LEDGER_DOMAIN, text.encode("utf-8"))


def workstream_detail_digest(raw: bytes | str) -> str:
    """Return the domain-separated digest of one canonical record/rebind block."""
    text = _canonical_text(raw, "record")
    return _v2_digest(WORKSTREAM_DETAIL_DOMAIN, text.encode("utf-8"))


def _digest(value: Any, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    if not SHA256_RE.fullmatch(value):
        _fail("digest", path, "field must be a lowercase sha256 digest", field=field_name, value=value)
    return value


def _git_sha(value: Any, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    if not GIT_OID_RE.fullmatch(value):
        _fail("git-oid", path, "field must be a lowercase Git object ID", field=field_name, value=value)
    return value


def _v2_id(prefix: str, id_salt: str, *components: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", id_salt):
        raise ValueError("id_salt must be 64 lowercase hex characters")
    frame = WORKSTREAM_ID_DOMAIN + bytes.fromhex(id_salt)
    for component in components:
        if not isinstance(component, str):
            raise TypeError("ID components must be strings")
        encoded = component.encode("utf-8")
        frame += len(encoded).to_bytes(4, "big") + encoded
    return prefix + crockford(sha256(frame).digest()[:12])


def workstream_id(id_salt: str, working_branch: str, base_sha: str, created_at: str) -> str:
    return _v2_id("rwl_", id_salt, "workstream", working_branch, base_sha, created_at)


def workstream_record_id(id_salt: str, workstream: str, created_at: str, pre_ledger_digest: str) -> str:
    return _v2_id("rlr_", id_salt, "record", workstream, created_at, pre_ledger_digest)


def workstream_chain_id(id_salt: str, workstream: str, first_record_id: str) -> str:
    return _v2_id("rlc_", id_salt, "chain", workstream, first_record_id)


def workstream_receipt_id(id_salt: str, workstream: str, chain_id: str, detail_digest: str) -> str:
    return _v2_id("rrc_", id_salt, "receipt", workstream, chain_id, detail_digest)


def workstream_ledger_path(workstream: str) -> str:
    _id(workstream, "rwl_", "workstream path", "workstream_id")
    return f"{REFLECTION_ROOT}/{workstream}/{WORKSTREAM_LEDGER_NAME}"


def _sorted_unique(values: Sequence[str], path: str, field_name: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value for value in result):
        _fail("schema", path, "list must contain non-empty strings", field=field_name)
    if result != tuple(sorted(result)) or len(set(result)) != len(result):
        _fail("canonical-order", path, "list must be sorted and unique", field=field_name)
    return result


def _clock_timestamp(clock: Callable[[], datetime] | None = None) -> str:
    value = (clock or (lambda: datetime.now(timezone.utc)))()
    if value.tzinfo is None:
        _fail("timestamp", "clock", "clock must return an aware UTC timestamp")
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class RetentionExtensionReceipt:
    """The six immutable locator fields copied into a v2 ledger header."""

    nonce: str
    session_path: str
    entry_id: str
    commit: str
    blob: str
    signature: str

    def as_dict(self) -> dict[str, str]:
        return {"nonce": self.nonce, "session_path": self.session_path, "entry_id": self.entry_id,
                "commit": self.commit, "blob": self.blob, "signature": self.signature}


@dataclass(frozen=True)
class WorkstreamLedgerHeader:
    workstream_id: str
    working_branch: str
    base_sha: str
    created_at: str
    reflection_retention_days: int
    retention_extension_receipt: RetentionExtensionReceipt | None
    retention_approval_key_id: str | None
    id_salt: str
    schema: str = WORKSTREAM_LEDGER_SCHEMA
    version: int = WORKSTREAM_LEDGER_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "version": self.version, "workstream_id": self.workstream_id,
            "working_branch": self.working_branch, "base_sha": self.base_sha, "created_at": self.created_at,
            "reflection_retention_days": self.reflection_retention_days,
            "retention_extension_receipt": (None if self.retention_extension_receipt is None else self.retention_extension_receipt.as_dict()),
            "retention_approval_key_id": self.retention_approval_key_id, "id_salt": self.id_salt,
        }


@dataclass(frozen=True)
class WorkstreamDependencyReceipt:
    session_path: str
    entry_id: str
    decision_id: str
    receipt_id: str
    receipt_digest: str

    def as_dict(self) -> dict[str, str]:
        return {"session_path": self.session_path, "entry_id": self.entry_id, "decision_id": self.decision_id,
                "receipt_id": self.receipt_id, "receipt_digest": self.receipt_digest}


@dataclass(frozen=True)
class WorkstreamDependency:
    workstream_id: str
    record_id: str
    record_digest: str
    reason: str
    receipt: WorkstreamDependencyReceipt | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"workstream_id": self.workstream_id, "record_id": self.record_id, "record_digest": self.record_digest,
                "reason": self.reason, "receipt": None if self.receipt is None else self.receipt.as_dict()}


@dataclass(frozen=True)
class WorkstreamRecord:
    record_id: str
    created_at: str
    role: str
    from_phase: str
    to_phase: str
    closed_at: str | None
    chain_id: str
    parents: tuple[str, ...]
    relationship: str
    no_related_thread: bool
    depends_on: tuple[WorkstreamDependency, ...]
    source: str
    related_decisions: tuple[str, ...]
    confidence: str
    pre_ledger_digest: str
    detail_digest: str
    conclusion: str
    reasoning: str
    assumptions: str | None = None
    alternatives: str | None = None
    evidence: str | None = None
    next_step: str | None = None

    def metadata(self, *, zero_detail_digest: bool = False) -> dict[str, Any]:
        return {
            "record_id": self.record_id, "created_at": self.created_at, "role": self.role,
            "from_phase": self.from_phase, "to_phase": self.to_phase, "closed_at": self.closed_at,
            "chain_id": self.chain_id, "parents": list(self.parents), "relationship": self.relationship,
            "no_related_thread": self.no_related_thread, "depends_on": [item.as_dict() for item in self.depends_on],
            "source": self.source, "related_decisions": list(self.related_decisions), "confidence": self.confidence,
            "pre_ledger_digest": self.pre_ledger_digest,
            "detail_digest": "sha256:" + "0" * 64 if zero_detail_digest else self.detail_digest,
        }


@dataclass(frozen=True)
class TrustedRebind:
    record_id: str
    created_at: str
    from_branch: str
    to_branch: str
    source_tip: str
    target_pre_merge_tip: str
    integration_commit: str
    pre_ledger_digest: str
    detail_digest: str
    reason: str
    role: str = "orchestrator"

    def metadata(self, *, zero_detail_digest: bool = False) -> dict[str, Any]:
        return {
            "record_id": self.record_id, "created_at": self.created_at, "role": self.role,
            "from_branch": self.from_branch, "to_branch": self.to_branch, "source_tip": self.source_tip,
            "target_pre_merge_tip": self.target_pre_merge_tip, "integration_commit": self.integration_commit,
            "pre_ledger_digest": self.pre_ledger_digest,
            "detail_digest": "sha256:" + "0" * 64 if zero_detail_digest else self.detail_digest,
            "reason": self.reason,
        }


WorkstreamEntry = WorkstreamRecord | TrustedRebind


@dataclass(frozen=True)
class WorkstreamLedger:
    header: WorkstreamLedgerHeader
    entries: tuple[WorkstreamEntry, ...] = ()

    @property
    def records(self) -> tuple[WorkstreamRecord, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, WorkstreamRecord))

    @property
    def rebinds(self) -> tuple[TrustedRebind, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, TrustedRebind))

    @property
    def effective_branch(self) -> str:
        return self.rebinds[-1].to_branch if self.rebinds else self.header.working_branch


def _retention_receipt_from_dict(value: Any, path: str) -> RetentionExtensionReceipt:
    if not isinstance(value, Mapping):
        _fail("retention-approval", path, "retention extension receipt must be a mapping")
    fields = ("nonce", "session_path", "entry_id", "commit", "blob", "signature")
    _required(value, fields, path)
    _only(value, fields, path)
    nonce = _text(value["nonce"], path, "nonce")
    if not re.fullmatch(r"[0-9a-f]{64}", nonce):
        _fail("retention-approval", path, "nonce must be 64 lowercase hex characters")
    entry_id = _text(value["entry_id"], path, "entry_id")
    if not SESSION_ENTRY_ID_RE.fullmatch(entry_id):
        _fail("retention-approval", path, "entry_id is not canonical")
    signature = _text(value["signature"], path, "signature")
    if not re.fullmatch(r"ed25519:[0-9a-f]{128}", signature):
        _fail("retention-approval", path, "signature is not canonical Ed25519 hex")
    return RetentionExtensionReceipt(nonce, _session_path(value["session_path"], path, "session_path"), entry_id,
                                    _git_sha(value["commit"], path, "commit"), _git_sha(value["blob"], path, "blob"), signature)


def _header_from_dict(value: Mapping[str, Any], path: str) -> WorkstreamLedgerHeader:
    _required(value, WORKSTREAM_HEADER_FIELDS, path)
    _only(value, WORKSTREAM_HEADER_FIELDS, path)
    if value["schema"] != WORKSTREAM_LEDGER_SCHEMA or value["version"] != WORKSTREAM_LEDGER_VERSION:
        _fail("discriminator", path, "unsupported or mixed reflection ledger discriminator")
    branch = _text(value["working_branch"], path, "working_branch")
    base = value["base_sha"]
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{40}", base):
        _fail("base-sha", path, "base_sha must be 40 lowercase hex characters")
    created = _timestamp(value["created_at"], path, "created_at")
    salt = value["id_salt"]
    if not isinstance(salt, str) or not re.fullmatch(r"[0-9a-f]{64}", salt):
        _fail("id-salt", path, "id_salt must be 64 lowercase hex characters")
    identifier = _id(value["workstream_id"], "rwl_", path, "workstream_id")
    if identifier != workstream_id(salt, branch, base, created):
        _fail("id", path, "workstream_id does not match its frozen ID preimage")
    retention = value["reflection_retention_days"]
    if retention not in {7, 14, 30} or isinstance(retention, bool):
        _fail("retention", path, "retention must be exactly 7, 14, or 30 days")
    receipt_value = value["retention_extension_receipt"]
    key_id = value["retention_approval_key_id"]
    if retention == 7:
        if receipt_value is not None or key_id is not None:
            _fail("retention", path, "seven-day retention requires literal null extension fields")
        receipt = None
    else:
        if not isinstance(key_id, str) or not key_id:
            _fail("retention-approval", path, "extended retention needs a key identifier")
        receipt = _retention_receipt_from_dict(receipt_value, path)
    return WorkstreamLedgerHeader(identifier, branch, base, created, retention, receipt, key_id, salt)


def reflection_ledger_family(raw: bytes | str, path: str = "reflection") -> str:
    """Return an explicit family discriminator; never infer v2 from a v1 plan."""
    text = _canonical_text(raw, path)
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end < 0:
            _fail("discriminator", path, "front matter is not closed")
        mapping = _parse_yaml_mapping(text[4:end], path)
    else:
        mapping = _parse_yaml_mapping(text, path)
    schema = mapping.get("schema")
    version = mapping.get("version")
    if schema == "memory-seed/reflection-plan" and version == 1:
        return "v1"
    if schema == WORKSTREAM_LEDGER_SCHEMA and version == WORKSTREAM_LEDGER_VERSION:
        return "v2"
    _fail("discriminator", path, "unsupported, absent, duplicate, or mixed reflection ledger family")


def render_workstream_header(header: WorkstreamLedgerHeader) -> str:
    # Parse the rendered mapping as a final renderer guard, including field order.
    rendered = _v2_yaml_mapping([(name, header.as_dict()[name]) for name in WORKSTREAM_HEADER_FIELDS])
    parsed = _parse_yaml_mapping(rendered, "ledger header")
    _header_from_dict(parsed, "ledger header")
    return "---\n" + rendered + "---\n"


def _dependency_receipt_from_dict(value: Any, path: str) -> WorkstreamDependencyReceipt:
    if not isinstance(value, Mapping):
        _fail("dependency", path, "dependency receipt must be a mapping")
    fields = ("session_path", "entry_id", "decision_id", "receipt_id", "receipt_digest")
    _required(value, fields, path)
    _only(value, fields, path)
    entry = _text(value["entry_id"], path, "entry_id")
    if not SESSION_ENTRY_ID_RE.fullmatch(entry):
        _fail("dependency", path, "dependency receipt entry_id is not canonical")
    decision = _text(value["decision_id"], path, "decision_id")
    if not SESSION_DECISION_ID_RE.fullmatch(decision):
        _fail("dependency", path, "dependency receipt decision_id is not canonical")
    return WorkstreamDependencyReceipt(
        _session_path(value["session_path"], path, "session_path"), entry, decision,
        _id(value["receipt_id"], "rrc_", path, "receipt_id"), _digest(value["receipt_digest"], path, "receipt_digest"),
    )


def _dependency_from_dict(value: Any, path: str) -> WorkstreamDependency:
    if not isinstance(value, Mapping):
        _fail("dependency", path, "dependency must be a mapping")
    fields = ("workstream_id", "record_id", "record_digest", "reason", "receipt")
    _required(value, fields, path)
    _only(value, fields, path)
    receipt = value["receipt"]
    return WorkstreamDependency(
        _id(value["workstream_id"], "rwl_", path, "workstream_id"),
        _id(value["record_id"], "rlr_", path, "record_id"),
        _digest(value["record_digest"], path, "record_digest"),
        _text(value["reason"], path, "reason"),
        None if receipt is None else _dependency_receipt_from_dict(receipt, path),
    )


def _dependency_key(value: WorkstreamDependency) -> tuple[str, str, str, str, str]:
    receipt = "" if value.receipt is None else json.dumps(value.receipt.as_dict(), separators=(",", ":"), ensure_ascii=False)
    return (value.workstream_id, value.record_id, value.record_digest, value.reason, receipt)


def _record_from_v2_dict(value: Mapping[str, Any], sections: Mapping[str, str], path: str) -> WorkstreamRecord:
    _required(value, WORKSTREAM_RECORD_FIELDS, path)
    _only(value, WORKSTREAM_RECORD_FIELDS, path)
    record = _id(value["record_id"], "rlr_", path, "record_id")
    created = _timestamp(value["created_at"], path, "created_at")
    role = _text(value["role"], path, "role")
    if role not in WORKSTREAM_ROLES:
        _fail("role", path, "record role is not permitted", role=role)
    from_phase = _text(value["from_phase"], path, "from_phase")
    to_phase = _text(value["to_phase"], path, "to_phase")
    if from_phase not in WORKSTREAM_PHASES or to_phase not in WORKSTREAM_PHASES:
        _fail("phase", path, "record phase is not recognised")
    closed_at = value["closed_at"]
    if closed_at is not None:
        closed_at = _timestamp(closed_at, path, "closed_at")
    chain = _id(value["chain_id"], "rlc_", path, "chain_id")
    parents_value = value["parents"]
    if not isinstance(parents_value, list):
        _fail("schema", path, "parents must be a list")
    parents = _sorted_unique([_id(parent, "rlr_", path, "parents") for parent in parents_value], path, "parents")
    relationship = _text(value["relationship"], path, "relationship")
    if relationship not in WORKSTREAM_RELATIONSHIPS:
        _fail("relationship", path, "record relationship is not recognised", relationship=relationship)
    no_related = value["no_related_thread"]
    if not isinstance(no_related, bool):
        _fail("schema", path, "no_related_thread must be a boolean")
    dependencies_value = value["depends_on"]
    if not isinstance(dependencies_value, list):
        _fail("schema", path, "depends_on must be a list")
    dependencies = tuple(_dependency_from_dict(item, path) for item in dependencies_value)
    if tuple(_dependency_key(item) for item in dependencies) != tuple(sorted(_dependency_key(item) for item in dependencies)) or len(set(_dependency_key(item) for item in dependencies)) != len(dependencies):
        _fail("canonical-order", path, "depends_on must be sorted and unique")
    decisions_value = value["related_decisions"]
    if not isinstance(decisions_value, list):
        _fail("schema", path, "related_decisions must be a list")
    decisions = _sorted_unique([_text(item, path, "related_decisions") for item in decisions_value], path, "related_decisions")
    expected_sections = ["Conclusion", "Reasoning"] + [name for name in ("Assumptions", "Alternatives", "Evidence", "Next step") if name in sections]
    if list(sections) != expected_sections:
        _fail("sections", path, "record sections are not canonical")
    conclusion = _text(sections.get("Conclusion"), path, "Conclusion")
    reasoning = _text(sections.get("Reasoning"), path, "Reasoning")
    return WorkstreamRecord(record, created, role, from_phase, to_phase, closed_at, chain, parents, relationship,
                            no_related, dependencies, _text(value["source"], path, "source"), decisions,
                            _text(value["confidence"], path, "confidence"), _digest(value["pre_ledger_digest"], path, "pre_ledger_digest"),
                            _digest(value["detail_digest"], path, "detail_digest"), conclusion, reasoning,
                            sections.get("Assumptions"), sections.get("Alternatives"), sections.get("Evidence"), sections.get("Next step"))


def _rebind_from_v2_dict(value: Mapping[str, Any], path: str) -> TrustedRebind:
    _required(value, WORKSTREAM_REBIND_FIELDS, path)
    _only(value, WORKSTREAM_REBIND_FIELDS, path)
    if value["role"] != "orchestrator":
        _fail("rebind", path, "only the orchestrator may create a rebind")
    return TrustedRebind(
        _id(value["record_id"], "rlr_", path, "record_id"), _timestamp(value["created_at"], path, "created_at"),
        _text(value["from_branch"], path, "from_branch"), _text(value["to_branch"], path, "to_branch"),
        _git_sha(value["source_tip"], path, "source_tip"), _git_sha(value["target_pre_merge_tip"], path, "target_pre_merge_tip"),
        _git_sha(value["integration_commit"], path, "integration_commit"), _digest(value["pre_ledger_digest"], path, "pre_ledger_digest"),
        _digest(value["detail_digest"], path, "detail_digest"), _text(value["reason"], path, "reason"),
    )


def _render_v2_sections(record: WorkstreamRecord) -> str:
    values = (("Conclusion", record.conclusion), ("Reasoning", record.reasoning), ("Assumptions", record.assumptions),
              ("Alternatives", record.alternatives), ("Evidence", record.evidence), ("Next step", record.next_step))
    result: list[str] = []
    for heading, body in values:
        if body is None:
            continue
        body = _text(body, "record", heading)
        if body != body.strip() or "\r" in body or "\n\n\n" in body:
            _fail("sections", "record", "section prose must be non-empty trimmed canonical text", section=heading)
        result.append(f"### {heading}\n{body}\n")
    return "\n".join(result)


def render_workstream_record(record: WorkstreamRecord, *, zero_detail_digest: bool = False) -> str:
    metadata = _v2_yaml_mapping([(name, record.metadata(zero_detail_digest=zero_detail_digest)[name]) for name in WORKSTREAM_RECORD_FIELDS])
    return f"## Record {record.record_id}\n\n```yaml\n{metadata}```\n\n{_render_v2_sections(record)}"


def render_trusted_rebind(rebind: TrustedRebind, *, zero_detail_digest: bool = False) -> str:
    metadata = _v2_yaml_mapping([(name, rebind.metadata(zero_detail_digest=zero_detail_digest)[name]) for name in WORKSTREAM_REBIND_FIELDS])
    return f"## Rebind {rebind.record_id}\n\n```yaml\n{metadata}```\n"


def _parse_v2_sections(raw: str, path: str) -> dict[str, str]:
    allowed = ("Conclusion", "Reasoning", "Assumptions", "Alternatives", "Evidence", "Next step")
    matches = list(re.finditer(r"^### (Conclusion|Reasoning|Assumptions|Alternatives|Evidence|Next step)\n", raw, re.MULTILINE))
    if not matches or matches[0].start() != 0:
        _fail("sections", path, "record must start with Conclusion and Reasoning sections")
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        body = raw[match.end():end]
        if body.endswith("\n\n"):
            body = body[:-1]
        if body.endswith("\n"):
            body = body[:-1]
        if heading in result or not body or body != body.strip():
            _fail("sections", path, "record has duplicate or non-canonical section prose", section=heading)
        result[heading] = body
    if tuple(result) != tuple(item for item in allowed if item in result) or "Conclusion" not in result or "Reasoning" not in result:
        _fail("sections", path, "record sections have the wrong order")
    return result


def _parse_v2_entry(raw: str, path: str) -> WorkstreamEntry:
    if raw.startswith("## Record "):
        match = re.fullmatch(r"## Record ([^\n]+)\n\n```yaml\n(.*?)```\n\n(.*)", raw, re.DOTALL)
        if not match:
            _fail("record", path, "record block is malformed")
        metadata = _parse_yaml_mapping(match.group(2), path)
        if metadata.get("record_id") != match.group(1):
            _fail("record", path, "record heading and metadata ID differ")
        return _record_from_v2_dict(metadata, _parse_v2_sections(match.group(3), path), path)
    if raw.startswith("## Rebind "):
        match = re.fullmatch(r"## Rebind ([^\n]+)\n\n```yaml\n(.*?)```\n", raw, re.DOTALL)
        if not match:
            _fail("rebind", path, "rebind block is malformed")
        metadata = _parse_yaml_mapping(match.group(2), path)
        if metadata.get("record_id") != match.group(1):
            _fail("rebind", path, "rebind heading and metadata ID differ")
        return _rebind_from_v2_dict(metadata, path)
    _fail("entry", path, "ledger contains an unsupported block")


def render_workstream_ledger(ledger: WorkstreamLedger) -> str:
    result = render_workstream_header(ledger.header)
    if ledger.entries:
        blocks = [render_workstream_record(entry) if isinstance(entry, WorkstreamRecord) else render_trusted_rebind(entry)
                  for entry in ledger.entries]
        result += "\n" + "\n".join(blocks)
    _canonical_text(result, "ledger.md")
    return result


def _split_workstream_ledger(raw: bytes | str, path: str) -> tuple[dict[str, Any], list[str], str]:
    text = _canonical_text(raw, path)
    if not text.startswith("---\n"):
        _fail("discriminator", path, "v2 ledger requires canonical front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        _fail("yaml", path, "front matter is not closed")
    header = _parse_yaml_mapping(text[4:end], path)
    remainder = text[end + 5:]
    if not remainder:
        return header, [], text
    if not remainder.startswith("\n"):
        _fail("format", path, "ledger blocks require one blank line after header")
    body = remainder[1:]
    starts = list(re.finditer(r"^## (?:Record|Rebind) [^\n]+\n", body, re.MULTILINE))
    if not starts or starts[0].start() != 0:
        _fail("format", path, "ledger body contains no canonical record blocks")
    entries = [body[match.start():starts[index + 1].start()] if index + 1 < len(starts) else body[match.start():]
               for index, match in enumerate(starts)]
    return header, entries, text


def parse_workstream_ledger(raw: bytes | str, path: str = "ledger.md") -> WorkstreamLedger:
    header_value, blocks, text = _split_workstream_ledger(raw, path)
    header = _header_from_dict(header_value, path)
    entries = tuple(_parse_v2_entry(block, path) for block in blocks)
    ledger = WorkstreamLedger(header, entries)
    validate_workstream_ledger(ledger, path)
    if render_workstream_ledger(ledger) != text:
        _fail("canonical-bytes", path, "ledger does not use the canonical v2 renderer")
    return ledger


def _detail_digest_for_record(record: WorkstreamRecord) -> str:
    return workstream_detail_digest(render_workstream_record(record, zero_detail_digest=True))


def _detail_digest_for_rebind(rebind: TrustedRebind) -> str:
    return workstream_detail_digest(render_trusted_rebind(rebind, zero_detail_digest=True))


def _records_by_chain(ledger: WorkstreamLedger) -> dict[str, list[WorkstreamRecord]]:
    result: dict[str, list[WorkstreamRecord]] = {}
    for record in ledger.records:
        result.setdefault(record.chain_id, []).append(record)
    return result


def workstream_chain_heads(ledger: WorkstreamLedger, chain_id: str) -> tuple[str, ...]:
    """Return every visible graph head, never a silently selected winner."""
    records = _records_by_chain(ledger).get(chain_id, [])
    if not records:
        _fail("chain", "ledger", "chain does not exist", chain_id=chain_id)
    parents = {parent for record in records for parent in record.parents}
    return tuple(sorted(record.record_id for record in records if record.record_id not in parents))


def workstream_chain_phase(ledger: WorkstreamLedger, chain_id: str) -> str:
    records = _records_by_chain(ledger).get(chain_id, [])
    if not records:
        _fail("chain", "ledger", "chain does not exist", chain_id=chain_id)
    return records[-1].to_phase


def validate_workstream_ledger(ledger: WorkstreamLedger, path: str = "ledger.md", *, verify_predecessors: bool = True) -> None:
    """Validate all v2 invariants that can be established from ledger bytes alone."""
    # Header construction is deliberately repeated so direct dataclass use cannot
    # evade schema, frozen preimage, or retention checks.
    _header_from_dict(ledger.header.as_dict(), path)
    seen_ids: set[str] = set()
    records_by_id: dict[str, WorkstreamRecord] = {}
    chains: dict[str, list[WorkstreamRecord]] = {}
    effective_branch = ledger.header.working_branch
    for ordinal, entry in enumerate(ledger.entries):
        entry_path = f"{path}#{ordinal + 1}"
        if verify_predecessors:
            preceding = WorkstreamLedger(ledger.header, ledger.entries[:ordinal])
            expected_predecessor = workstream_ledger_digest(render_workstream_ledger(preceding))
            if entry.pre_ledger_digest != expected_predecessor:
                _fail("pre-ledger-digest", entry_path, "entry does not bind the exact preceding canonical ledger bytes",
                      expected=expected_predecessor, actual=entry.pre_ledger_digest)
        if entry.record_id in seen_ids:
            _fail("id-collision", entry_path, "record IDs must be unique", record_id=entry.record_id)
        seen_ids.add(entry.record_id)
        if isinstance(entry, TrustedRebind):
            _rebind_from_v2_dict(entry.metadata(), entry_path)
            if entry.from_branch != effective_branch:
                _fail("rebind", entry_path, "rebind source is not the effective owning branch", expected=effective_branch)
            expected_id = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, entry.created_at, entry.pre_ledger_digest)
            if entry.record_id != expected_id:
                _fail("id", entry_path, "rebind ID does not match its frozen preimage")
            if entry.detail_digest != _detail_digest_for_rebind(entry):
                _fail("detail-digest", entry_path, "rebind detail digest is invalid")
            effective_branch = entry.to_branch
            continue
        _record_from_v2_dict(entry.metadata(), {
            name: value for name, value in (("Conclusion", entry.conclusion), ("Reasoning", entry.reasoning),
                                               ("Assumptions", entry.assumptions), ("Alternatives", entry.alternatives),
                                               ("Evidence", entry.evidence), ("Next step", entry.next_step)) if value is not None
        }, entry_path)
        expected_id = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, entry.created_at, entry.pre_ledger_digest)
        if entry.record_id != expected_id:
            _fail("id", entry_path, "record ID does not match its frozen preimage")
        if entry.detail_digest != _detail_digest_for_record(entry):
            _fail("detail-digest", entry_path, "record detail digest is invalid")
        if entry.chain_id not in chains:
            if entry.parents or entry.relationship != "no_related_thread" or entry.no_related_thread is not True:
                _fail("root", entry_path, "a new chain requires an explicit no_related_thread root")
            if entry.role != "planner" or entry.from_phase != "plan" or entry.to_phase != "plan" or entry.closed_at is not None:
                _fail("phase", entry_path, "a root must be a planner-owned plan note")
            expected_chain = workstream_chain_id(ledger.header.id_salt, ledger.header.workstream_id, entry.record_id)
            if entry.chain_id != expected_chain:
                _fail("id", entry_path, "root chain ID does not match its first record")
            chains[entry.chain_id] = []
        else:
            if entry.no_related_thread:
                _fail("relationship", entry_path, "only a root may declare no_related_thread")
            current_phase = chains[entry.chain_id][-1].to_phase
            if current_phase == "closed":
                _fail("phase", entry_path, "a closed chain accepts no ordinary append")
            if entry.from_phase != current_phase:
                _fail("phase", entry_path, "record from_phase is not this chain's current phase", expected=current_phase)
            if entry.from_phase == entry.to_phase:
                expected_role = WORKSTREAM_PHASE_OWNERS.get(current_phase)
                if entry.role != expected_role:
                    _fail("phase-owner", entry_path, "only the current phase owner may add a note", expected=expected_role)
            elif WORKSTREAM_TRANSITIONS.get((entry.from_phase, entry.to_phase)) != entry.role:
                _fail("transition", entry_path, "record transition is not allowed for this role")
            if entry.closed_at is not None and not (entry.role == "orchestrator" and entry.from_phase == "orchestrate" and entry.to_phase == "closed" and entry.closed_at == entry.created_at):
                _fail("closed-at", entry_path, "closed_at is permitted only on the close transition and equals created_at")
            if entry.closed_at is None and entry.to_phase == "closed":
                _fail("closed-at", entry_path, "close transition requires closed_at equal to created_at")
            if entry.parents:
                for parent in entry.parents:
                    source = records_by_id.get(parent)
                    if source is None:
                        _fail("parent", entry_path, "parent must be an earlier local record", parent=parent)
                    if source.chain_id != entry.chain_id:
                        _fail("parent", entry_path, "parent must stay within its own chain", parent=parent)
            elif entry.relationship != "orphan":
                _fail("parent", entry_path, "a non-root record without parents must explicitly be orphaned")
            if entry.relationship == "orphan" and "orphan" not in entry.reasoning.casefold():
                _fail("orphan-judgment", entry_path, "orphan relationship needs an explicit judgment in Reasoning")
            if any(dependency.workstream_id == ledger.header.workstream_id for dependency in entry.depends_on):
                _fail("dependency", entry_path, "a workstream cannot depend on itself")
        if entry.closed_at is not None and not (entry.role == "orchestrator" and entry.from_phase == "orchestrate" and entry.to_phase == "closed" and entry.closed_at == entry.created_at):
            _fail("closed-at", entry_path, "closed_at is invalid")
        chains[entry.chain_id].append(entry)
        records_by_id[entry.record_id] = entry


@dataclass(frozen=True)
class RetentionPreflight:
    """Host-generated candidate, retained so adapters can prove exact replay."""

    key_id: str
    workstream_id: str
    working_branch: str
    base_sha: str
    id_salt: str
    created_at: str
    retention_days: int
    nonce: str
    approved_at: str
    expires_at: str
    reason: str
    session_path: str
    entry_id: str


@dataclass(frozen=True)
class RetentionApproval:
    """The host-signed payload.  Its private key never enters this module."""

    preflight: RetentionPreflight
    commit: str
    blob: str
    signature: str


@dataclass(frozen=True)
class RetentionApprovalAdmission:
    """Host/Git facts required before an extended-retention header can exist."""

    approval: RetentionApproval
    trust: "RetentionApprovalTrust"
    trust_anchor_at_base: Callable[[str], "RetentionApprovalTrust"]
    session_contains_preflight: Callable[[RetentionPreflight, str, str], bool]
    commit_is_reachable: Callable[[str], bool]
    object_at: Callable[[str, str], str | None]
    admitted_headers: tuple[WorkstreamLedgerHeader, ...] = ()


class RetentionPreflightVerifier:
    """Adapter contract for the host-owned, Git-admitted 14/30-day flow."""

    def admit(self, handle: object, *, working_branch: str, base_sha: str, now: datetime) -> RetentionApprovalAdmission:
        raise NotImplementedError


def _validate_retention_preflight(preflight: RetentionPreflight, path: str = "retention preflight") -> None:
    if not preflight.key_id or preflight.retention_days not in {14, 30}:
        _fail("retention-approval", path, "preflight has an unsupported key or period")
    _id(preflight.workstream_id, "rwl_", path, "workstream_id")
    if preflight.workstream_id != workstream_id(preflight.id_salt, preflight.working_branch, preflight.base_sha, preflight.created_at):
        _fail("retention-approval", path, "preflight workstream ID does not match its preimage")
    if not re.fullmatch(r"[0-9a-f]{64}", preflight.id_salt) or not re.fullmatch(r"[0-9a-f]{64}", preflight.nonce):
        _fail("retention-approval", path, "preflight salt and nonce must be 64 lowercase hex")
    if not re.fullmatch(r"[0-9a-f]{40}", preflight.base_sha):
        _fail("retention-approval", path, "preflight base SHA is invalid")
    for name in ("created_at", "approved_at", "expires_at"):
        _timestamp(getattr(preflight, name), path, name)
    if not _as_utc(preflight.approved_at) < _as_utc(preflight.expires_at) <= _as_utc(preflight.approved_at) + timedelta(hours=24):
        _fail("retention-approval", path, "preflight expiry must be after approval and no more than 24 hours later")
    _session_path(preflight.session_path, path, "session_path")
    if not SESSION_ENTRY_ID_RE.fullmatch(preflight.entry_id):
        _fail("retention-approval", path, "preflight entry ID is invalid")
    _text(preflight.reason, path, "reason")


def initialize_workstream_ledger(*, working_branch: str, base_sha: str, retention_days: int = 7,
                                 clock: Callable[[], datetime] | None = None,
                                 entropy: Callable[[int], bytes] = os.urandom,
                                 retention_preflight_handle: object | None = None,
                                 retention_verifier: RetentionPreflightVerifier | None = None) -> WorkstreamLedger:
    """Create an empty canonical ledger without accepting caller-selected identity.

    The extension path only accepts an opaque host handle.  Caller-supplied IDs,
    timestamps, approval text, and signature material are deliberately absent
    from this API.
    """
    if not isinstance(working_branch, str) or not working_branch:
        _fail("branch", "ledger init", "working branch must be non-empty")
    if not isinstance(base_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        _fail("base-sha", "ledger init", "base_sha must be 40 lowercase hex")
    if retention_days not in {7, 14, 30} or isinstance(retention_days, bool):
        _fail("retention", "ledger init", "retention must be exactly 7, 14, or 30 days")
    now = (clock or (lambda: datetime.now(timezone.utc)))()
    if retention_days == 7:
        if retention_preflight_handle is not None or retention_verifier is not None:
            _fail("retention", "ledger init", "seven-day init accepts no approval or preflight")
        salt = entropy(32).hex()
        created = _clock_timestamp(lambda: now)
        header = WorkstreamLedgerHeader(workstream_id(salt, working_branch, base_sha, created), working_branch, base_sha,
                                        created, 7, None, None, salt)
    else:
        if retention_preflight_handle is None or retention_verifier is None:
            _fail("retention-approval", "ledger init", "extended retention requires a host-issued preflight handle")
        admission = retention_verifier.admit(retention_preflight_handle, working_branch=working_branch, base_sha=base_sha, now=now)
        if not isinstance(admission, RetentionApprovalAdmission):
            _fail("retention-approval", "ledger init", "host must return a concrete retained-approval admission")
        if admission.trust_anchor_at_base(base_sha) != admission.trust:
            _fail("retention-approval", "ledger init", "retention key is not the exact protected-base trust anchor")
        approval = admission.approval
        _validate_retention_preflight(approval.preflight)
        preflight = approval.preflight
        if preflight.working_branch != working_branch or preflight.base_sha != base_sha or preflight.retention_days != retention_days:
            _fail("retention-approval", "ledger init", "host preflight does not bind this branch, base, and period")
        if not re.fullmatch(r"ed25519:[0-9a-f]{128}", approval.signature):
            _fail("retention-approval", "ledger init", "host approval signature is not canonical")
        receipt = RetentionExtensionReceipt(preflight.nonce, preflight.session_path, preflight.entry_id,
                                            _git_sha(approval.commit, "ledger init", "commit"), _git_sha(approval.blob, "ledger init", "blob"), approval.signature)
        header = WorkstreamLedgerHeader(preflight.workstream_id, working_branch, base_sha, preflight.created_at,
                                        retention_days, receipt, preflight.key_id, preflight.id_salt)
        validate_retention_approval_admission(
            header, approval, trust=admission.trust, now=now,
            session_contains_preflight=admission.session_contains_preflight,
            commit_is_reachable=admission.commit_is_reachable,
            object_at=admission.object_at, admitted_headers=admission.admitted_headers,
        )
    ledger = WorkstreamLedger(header)
    validate_workstream_ledger(ledger)
    return ledger


@dataclass(frozen=True)
class WorkstreamAppendRequest:
    """Caller-authored content only; writer-owned fields are intentionally absent."""

    role: str
    chain_id: str | None
    relationship: str
    parents: tuple[str, ...]
    no_related_thread: bool
    conclusion: str
    reasoning: str
    source: str
    confidence: str
    depends_on: tuple[WorkstreamDependency, ...] = ()
    related_decisions: tuple[str, ...] = ()
    assumptions: str | None = None
    alternatives: str | None = None
    evidence: str | None = None
    next_step: str | None = None
    to_phase: str | None = None


def _append_pre_digest(ledger: WorkstreamLedger) -> str:
    return workstream_ledger_digest(render_workstream_ledger(ledger))


def _append_record(ledger: WorkstreamLedger, request: WorkstreamAppendRequest, *, created_at: str,
                   pre_ledger_digest: str, branch: str, active_ledgers: Iterable[WorkstreamLedger],
                   durable_receipts: Iterable[AdmittedWorkstreamReceipt],
                   receipt_verifier: WorkstreamReceiptVerifier | None) -> WorkstreamRecord:
    validate_workstream_ledger(ledger)
    if branch != ledger.effective_branch:
        _fail("branch-owner", "ledger append", "branch is not the current effective ledger owner", expected=ledger.effective_branch, actual=branch)
    if request.role not in WORKSTREAM_ROLES:
        _fail("role", "ledger append", "role is not permitted", role=request.role)
    if request.relationship not in WORKSTREAM_RELATIONSHIPS:
        _fail("relationship", "ledger append", "relationship is not permitted")
    if not isinstance(request.no_related_thread, bool):
        _fail("schema", "ledger append", "no_related_thread must be a boolean")
    parents = _sorted_unique(tuple(request.parents), "ledger append", "parents")
    for parent in parents:
        _id(parent, "rlr_", "ledger append", "parents")
    decisions = _sorted_unique(tuple(request.related_decisions), "ledger append", "related_decisions")
    dependencies = tuple(request.depends_on)
    if tuple(_dependency_key(item) for item in dependencies) != tuple(sorted(_dependency_key(item) for item in dependencies)) or len(set(_dependency_key(item) for item in dependencies)) != len(dependencies):
        _fail("canonical-order", "ledger append", "depends_on must be sorted and unique")
    if request.chain_id is None:
        if request.role != "planner" or request.relationship != "no_related_thread" or not request.no_related_thread or parents:
            _fail("root", "ledger append", "only a planner may open a root with no_related_thread")
        from_phase = to_phase = "plan"
        identifier = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, created_at, pre_ledger_digest)
        chain = workstream_chain_id(ledger.header.id_salt, ledger.header.workstream_id, identifier)
    else:
        chain = _id(request.chain_id, "rlc_", "ledger append", "chain_id")
        current = workstream_chain_phase(ledger, chain)
        if current == "closed":
            _fail("phase", "ledger append", "a closed chain cannot be appended")
        if request.no_related_thread or request.relationship == "no_related_thread":
            _fail("relationship", "ledger append", "no_related_thread is only legal for a root")
        if not parents and request.relationship != "orphan":
            _fail("parent", "ledger append", "a non-root record needs local parents or an orphan judgment")
        known = {record.record_id: record for record in ledger.records}
        for parent in parents:
            target = known.get(parent)
            if target is None or target.chain_id != chain:
                _fail("parent", "ledger append", "parent must be an existing record in this chain", parent=parent)
        if request.relationship == "orphan" and "orphan" not in request.reasoning.casefold():
            _fail("orphan-judgment", "ledger append", "orphan relationship needs an explicit reasoning judgment")
        owner = WORKSTREAM_PHASE_OWNERS[current]
        transitions = [(candidate, owner_role) for (from_value, candidate), owner_role in WORKSTREAM_TRANSITIONS.items()
                       if from_value == current and owner_role == request.role and candidate != "closed"]
        if request.to_phase is not None:
            if request.to_phase not in WORKSTREAM_PHASES:
                _fail("phase", "ledger append", "requested target phase is not recognised")
            if request.to_phase == current:
                if request.role != owner:
                    _fail("phase-owner", "ledger append", "only the current phase owner may add a note", expected=owner)
                from_phase = to_phase = current
            elif WORKSTREAM_TRANSITIONS.get((current, request.to_phase)) != request.role or request.to_phase == "closed":
                _fail("transition", "ledger append", "requested transition is not permitted")
            else:
                from_phase, to_phase = current, request.to_phase
        elif len(transitions) == 1:
            from_phase, to_phase = current, transitions[0][0]
        elif not transitions and request.role == owner:
            from_phase = to_phase = current
        elif len(transitions) > 1:
            _fail("transition", "ledger append", "role has multiple possible transitions; choose to_phase explicitly")
        else:
            _fail("phase-owner", "ledger append", "role cannot append to this chain phase", expected=owner)
        identifier = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, created_at, pre_ledger_digest)
    if any(dependency.workstream_id == ledger.header.workstream_id for dependency in dependencies):
        _fail("dependency", "ledger append", "a workstream cannot depend on itself")
    for dependency in dependencies:
        resolve_workstream_dependency(
            dependency, source_workstream_id=ledger.header.workstream_id, active_ledgers=active_ledgers,
            durable_receipts=durable_receipts, receipt_verifier=receipt_verifier,
        )
    draft = WorkstreamRecord(identifier, created_at, request.role, from_phase, to_phase, None, chain, parents,
                             request.relationship, request.no_related_thread, dependencies, request.source, decisions,
                             request.confidence, pre_ledger_digest, "sha256:" + "0" * 64, request.conclusion, request.reasoning,
                             request.assumptions, request.alternatives, request.evidence, request.next_step)
    detail = _detail_digest_for_record(draft)
    return WorkstreamRecord(**{**draft.__dict__, "detail_digest": detail})


def plan_workstream_append(ledger: WorkstreamLedger, request: WorkstreamAppendRequest, *, expected_head: str,
                           actual_head: str, pre_ledger_digest: str, branch: str,
                           clock: Callable[[], datetime] | None = None,
                           active_ledgers: Iterable[WorkstreamLedger] = (),
                           durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                           receipt_verifier: WorkstreamReceiptVerifier | None = None) -> WorkstreamLedger:
    """Return the next ledger after all compare-and-swap and phase checks.

    This pure primitive does not write.  Surface adapters must obtain both the
    Git tip and digest immediately before invoking it, then atomically write the
    exact rendered result.
    """
    if expected_head != actual_head:
        _fail("stale_head", "ledger append", "branch tip changed; reload and re-judge", expected=expected_head, actual=actual_head)
    actual_digest = _append_pre_digest(ledger)
    if pre_ledger_digest != actual_digest:
        _fail("stale_ledger_digest", "ledger append", "ledger bytes changed; reload and re-judge", expected=pre_ledger_digest, actual=actual_digest)
    created_at = _clock_timestamp(clock)
    record = _append_record(ledger, request, created_at=created_at, pre_ledger_digest=actual_digest, branch=branch,
                            active_ledgers=active_ledgers, durable_receipts=durable_receipts,
                            receipt_verifier=receipt_verifier)
    result = WorkstreamLedger(ledger.header, ledger.entries + (record,))
    validate_workstream_ledger(result)
    return result


@dataclass(frozen=True)
class WorkstreamReceipt:
    """A compact durable session receipt used after temporary blocks expire."""

    workstream_id: str
    chain_id: str
    record_id: str
    detail_digest: str
    session_path: str
    entry_id: str
    decision_id: str
    receipt_id: str
    receipt_digest: str
    disposition: str

    def dependency_locator(self) -> WorkstreamDependencyReceipt:
        return WorkstreamDependencyReceipt(self.session_path, self.entry_id, self.decision_id, self.receipt_id, self.receipt_digest)


@dataclass(frozen=True)
class AdmittedWorkstreamReceipt:
    """A receipt reloaded from an immutable committed session blob."""

    receipt: WorkstreamReceipt
    commit: str
    blob: str


class WorkstreamReceiptVerifier:
    """Session/Git adapter; raw receipt dataclasses are never coverage authority."""

    def verify(self, admitted: AdmittedWorkstreamReceipt) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class EarlyExpiryApproval:
    """Durable live-user approval/disposition locator for one unpromoted chain."""

    workstream_id: str
    chain_id: str
    session_path: str
    entry_id: str
    decision_id: str
    commit: str
    blob: str
    disposition: str


class EarlyExpiryApprovalVerifier:
    """Host/Git verifier for a live-user early-expiry approval."""

    def verify(self, approval: EarlyExpiryApproval) -> bool:
        raise NotImplementedError


def _validate_early_expiry_approval(approval: EarlyExpiryApproval, path: str = "early expiry approval") -> None:
    _id(approval.workstream_id, "rwl_", path, "workstream_id")
    _id(approval.chain_id, "rlc_", path, "chain_id")
    _session_path(approval.session_path, path, "session_path")
    if not SESSION_ENTRY_ID_RE.fullmatch(approval.entry_id) or not SESSION_DECISION_ID_RE.fullmatch(approval.decision_id):
        _fail("early-expiry", path, "approval session entry or decision locator is invalid")
    _git_sha(approval.commit, path, "commit")
    _git_sha(approval.blob, path, "blob")
    _text(approval.disposition, path, "disposition")


def _validate_workstream_receipt(receipt: WorkstreamReceipt, path: str = "receipt") -> None:
    _id(receipt.workstream_id, "rwl_", path, "workstream_id")
    _id(receipt.chain_id, "rlc_", path, "chain_id")
    _id(receipt.record_id, "rlr_", path, "record_id")
    _digest(receipt.detail_digest, path, "detail_digest")
    _dependency_receipt_from_dict(receipt.dependency_locator().as_dict(), path)
    _text(receipt.disposition, path, "disposition")


def _validate_admitted_receipt(value: AdmittedWorkstreamReceipt, verifier: WorkstreamReceiptVerifier,
                                path: str = "receipt") -> WorkstreamReceipt:
    if not isinstance(value, AdmittedWorkstreamReceipt):
        _fail("receipt", path, "receipt coverage requires a Git/session-admitted receipt")
    _validate_workstream_receipt(value.receipt, path)
    _git_sha(value.commit, path, "commit")
    _git_sha(value.blob, path, "blob")
    if not verifier.verify(value):
        _fail("receipt", path, "receipt was not admitted from its committed session blob")
    return value.receipt


@dataclass(frozen=True)
class DependencyResolution:
    dependency: WorkstreamDependency
    source: str  # active-ledger or durable-receipt
    receipt: WorkstreamReceipt | None = None


def resolve_workstream_dependency(dependency: WorkstreamDependency, *, source_workstream_id: str,
                                  active_ledgers: Iterable[WorkstreamLedger] = (),
                                  durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                  receipt_verifier: WorkstreamReceiptVerifier | None = None) -> DependencyResolution:
    """Resolve by active exact record first, otherwise by an exact durable receipt."""
    if dependency.workstream_id == source_workstream_id:
        _fail("dependency", "dependency", "a workstream cannot depend on itself")
    active = [ledger for ledger in active_ledgers if ledger.header.workstream_id == dependency.workstream_id]
    if len(active) > 1:
        _fail("dependency", "dependency", "dependency workstream is ambiguously active")
    if active:
        matches = [record for record in active[0].records if record.record_id == dependency.record_id]
        if matches:
            if matches[0].detail_digest != dependency.record_digest:
                _fail("dependency", "dependency", "active dependency record digest changed")
            return DependencyResolution(dependency, "active-ledger")
        # A live ledger that claims the target, but lacks the cited record, is a
        # changed/missing target rather than a licence to silently switch proof.
        _fail("dependency", "dependency", "active dependency target is missing; a fallback is legal only after expiry")
    if dependency.receipt is None:
        _fail("dependency", "dependency", "expired dependency requires a durable receipt fallback")
    if receipt_verifier is None:
        _fail("dependency", "dependency", "expired dependency requires a session/Git receipt verifier")
    candidates: list[WorkstreamReceipt] = []
    locator = dependency.receipt
    for receipt in durable_receipts:
        durable = _validate_admitted_receipt(receipt, receipt_verifier, "dependency receipt")
        if (durable.workstream_id == dependency.workstream_id and durable.record_id == dependency.record_id
                and durable.detail_digest == dependency.record_digest and durable.dependency_locator() == locator):
            candidates.append(durable)
    if len(candidates) != 1:
        _fail("dependency", "dependency", "dependency fallback does not resolve to one exact durable receipt", matches=len(candidates))
    return DependencyResolution(dependency, "durable-receipt", candidates[0])


@dataclass(frozen=True)
class WorkstreamBoardItem:
    path: str
    status: str  # valid, malformed, unsupported
    raw_digest: str | None
    workstream_id: str | None
    working_branch: str | None
    effective_branch: str | None
    diagnostic: ReflectionDiagnostic | None = None
    ledger: WorkstreamLedger | None = None


@dataclass(frozen=True)
class WorkstreamBoardView:
    items: tuple[WorkstreamBoardItem, ...]

    @property
    def valid_ledgers(self) -> tuple[WorkstreamLedger, ...]:
        return tuple(item.ledger for item in self.items if item.status == "valid" and item.ledger is not None)

    @property
    def exit_code(self) -> int:
        return 0 if all(item.status == "valid" for item in self.items) else 1


def _recover_v2_header(raw: bytes, path: str) -> tuple[str | None, str | None, str | None]:
    """Best-effort information for diagnostics; never turns malformed bytes valid."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, None, None
    if not text.startswith("---\n"):
        return None, None, None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None, None
    try:
        header = _parse_yaml_mapping(text[4:end], path)
    except ReflectionValidationError:
        return None, None, None
    return header.get("workstream_id") if isinstance(header.get("workstream_id"), str) else None, \
        header.get("working_branch") if isinstance(header.get("working_branch"), str) else None, \
        header.get("schema") if isinstance(header.get("schema"), str) else None


def workstream_board_view(cwd: Path | str = ".", *, active_root: str = REFLECTION_ROOT) -> WorkstreamBoardView:
    """Read-only, complete projection of every immediate active-ledger candidate."""
    root = Path(cwd).resolve()
    active = root / Path(active_root)
    if not active.exists():
        return WorkstreamBoardView(())
    items: list[WorkstreamBoardItem] = []
    for candidate in sorted((item for item in active.iterdir() if item.is_dir()), key=lambda item: item.name):
        ledger_path = candidate / WORKSTREAM_LEDGER_NAME
        relative = (PurePosixPath(active_root) / candidate.name / WORKSTREAM_LEDGER_NAME).as_posix()
        if not ledger_path.is_file():
            items.append(WorkstreamBoardItem(relative, "malformed", None, None, None, None,
                                              ReflectionDiagnostic("missing-ledger", relative, "active candidate has no ledger.md", {})))
            continue
        raw = ledger_path.read_bytes()
        raw_digest = "sha256:" + sha256(raw).hexdigest()
        workstream, branch, schema = _recover_v2_header(raw, relative)
        try:
            ledger = parse_workstream_ledger(raw, relative)
        except ReflectionValidationError as exc:
            status = "unsupported" if schema is not None and schema != WORKSTREAM_LEDGER_SCHEMA else "malformed"
            items.append(WorkstreamBoardItem(relative, status, raw_digest, workstream, branch, None, exc.diagnostic))
            continue
        if candidate.name != ledger.header.workstream_id:
            items.append(WorkstreamBoardItem(relative, "malformed", raw_digest, ledger.header.workstream_id,
                                              ledger.header.working_branch, ledger.effective_branch,
                                              ReflectionDiagnostic("path", relative, "ledger directory must equal workstream_id", {})))
            continue
        if (candidate / MANIFEST_NAME).exists():
            items.append(WorkstreamBoardItem(relative, "malformed", raw_digest, ledger.header.workstream_id,
                                              ledger.header.working_branch, ledger.effective_branch,
                                              ReflectionDiagnostic("mixed-family", relative, "v2 ledger directory cannot contain manifest.yaml", {})))
            continue
        items.append(WorkstreamBoardItem(relative, "valid", raw_digest, ledger.header.workstream_id,
                                         ledger.header.working_branch, ledger.effective_branch, None, ledger))
    owners: dict[str, list[int]] = {}
    for index, item in enumerate(items):
        if item.status == "valid" and item.effective_branch is not None:
            owners.setdefault(item.effective_branch, []).append(index)
    for branch, indexes in owners.items():
        if len(indexes) < 2:
            continue
        for index in indexes:
            item = items[index]
            items[index] = WorkstreamBoardItem(
                item.path, "malformed", item.raw_digest, item.workstream_id, item.working_branch, item.effective_branch,
                ReflectionDiagnostic("branch-collision", item.path, "multiple active v2 ledgers claim one effective branch", {"branch": branch}),
            )
    return WorkstreamBoardView(tuple(items))


def validate_workstream_init_collisions(cwd: Path | str, *, working_branch: str, workstream_id: str,
                                        active_root: str = REFLECTION_ROOT) -> None:
    """Fail closed on every active candidate, including a malformed ownerless one."""
    board = workstream_board_view(cwd, active_root=active_root)
    for item in board.items:
        if item.status != "valid":
            _fail("branch-collision", item.path, "malformed or unsupported active candidate blocks init", status=item.status)
        if item.workstream_id == workstream_id:
            _fail("workstream-collision", item.path, "workstream ID is already active")
        if item.effective_branch == working_branch:
            _fail("branch-collision", item.path, "an active ledger already owns this branch", branch=working_branch)


def validate_workstream_branch_owner(cwd: Path | str, ledger: WorkstreamLedger, *, active_root: str = REFLECTION_ROOT) -> None:
    """Require exactly one healthy active candidate for every guarded mutation."""
    board = workstream_board_view(cwd, active_root=active_root)
    relative = workstream_ledger_path(ledger.header.workstream_id)
    matches = [item for item in board.items if item.path == relative and item.status == "valid"]
    if len(matches) != 1:
        _fail("branch-collision", relative, "active ledger is missing, malformed, or ambiguously owned")
    for item in board.items:
        if item.status != "valid":
            _fail("branch-collision", item.path, "malformed or ambiguous active ledger blocks guarded mutation")
        if item.path != relative and item.effective_branch == ledger.effective_branch:
            _fail("branch-collision", item.path, "another ledger claims this effective branch", branch=ledger.effective_branch)


@dataclass(frozen=True)
class TrustedRebindToken:
    """Opaque integration coordinator capability; callers cannot choose a target branch."""

    token: str
    workstream_id: str
    source_branch: str
    source_tip: str
    target_branch: str
    target_pre_merge_tip: str
    pre_ledger_digest: str


class TrustedRebindVerifier:
    """Host adapter for the opaque token and the durable integration witness."""

    def verify(self, token: TrustedRebindToken, *, integration_commit: str, current_target_tip: str) -> bool:
        raise NotImplementedError

    def admit_witness(self, token: TrustedRebindToken, rebind: TrustedRebind, *, integration_commit: str) -> "TrustedIntegrationWitness":
        raise NotImplementedError

    def verify_witness(self, witness: "TrustedIntegrationWitness") -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class TrustedIntegrationWitness:
    """Verifier-issued evidence that binds a rebind record to real integration."""

    workstream_id: str
    rebind_record_id: str
    source_branch: str
    target_branch: str
    source_tip: str
    target_pre_merge_tip: str
    integration_commit: str
    pre_ledger_digest: str


@dataclass(frozen=True)
class TrustedRebindResult:
    ledger: WorkstreamLedger
    witness: TrustedIntegrationWitness


def preview_trusted_rebind(ledger: WorkstreamLedger, *, source_tip: str, target_branch: str,
                           target_pre_merge_tip: str, token_factory: Callable[[], str]) -> TrustedRebindToken:
    validate_workstream_ledger(ledger)
    return TrustedRebindToken(_text(token_factory(), "rebind preview", "token"), ledger.header.workstream_id,
                              ledger.effective_branch, _git_sha(source_tip, "rebind preview", "source_tip"),
                              _text(target_branch, "rebind preview", "target_branch"),
                              _git_sha(target_pre_merge_tip, "rebind preview", "target_pre_merge_tip"),
                              _append_pre_digest(ledger))


def apply_trusted_rebind(ledger: WorkstreamLedger, token: TrustedRebindToken, *, integration_commit: str,
                         current_target_tip: str, verifier: TrustedRebindVerifier,
                         reason: str, clock: Callable[[], datetime] | None = None) -> TrustedRebindResult:
    """Append the only v2 ownership transfer record after verified integration."""
    validate_workstream_ledger(ledger)
    pre_digest = _append_pre_digest(ledger)
    if token.workstream_id != ledger.header.workstream_id or token.source_branch != ledger.effective_branch or token.pre_ledger_digest != pre_digest:
        _fail("rebind", "ledger rebind", "token is not bound to this current ledger state")
    integration_commit = _git_sha(integration_commit, "ledger rebind", "integration_commit")
    if current_target_tip != integration_commit:
        _fail("stale_head", "ledger rebind", "integration target is not at the verified integration commit", expected=integration_commit, actual=current_target_tip)
    if not verifier.verify(token, integration_commit=integration_commit, current_target_tip=current_target_tip):
        _fail("rebind", "ledger rebind", "host did not verify the trusted integration token")
    created = _clock_timestamp(clock)
    identifier = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, created, pre_digest)
    draft = TrustedRebind(identifier, created, token.source_branch, token.target_branch, token.source_tip,
                          token.target_pre_merge_tip, integration_commit, pre_digest, "sha256:" + "0" * 64, reason)
    rebind = TrustedRebind(**{**draft.__dict__, "detail_digest": _detail_digest_for_rebind(draft)})
    result = WorkstreamLedger(ledger.header, ledger.entries + (rebind,))
    validate_workstream_ledger(result)
    witness = verifier.admit_witness(token, rebind, integration_commit=integration_commit)
    if not isinstance(witness, TrustedIntegrationWitness) or not verifier.verify_witness(witness):
        _fail("rebind", "ledger rebind", "integration verifier did not issue an admitted witness")
    _validate_integration_witness(result, witness, verifier)
    return TrustedRebindResult(result, witness)


def _validate_integration_witness(ledger: WorkstreamLedger, witness: TrustedIntegrationWitness,
                                  verifier: TrustedRebindVerifier) -> TrustedRebind:
    """Refuse structural rebind bytes unless a verifier admits the exact witness."""
    if not verifier.verify_witness(witness):
        _fail("close-authority", "integration witness", "integration witness is not admitted by its verifier")
    matches = [item for item in ledger.rebinds if item.record_id == witness.rebind_record_id]
    if len(matches) != 1:
        _fail("close-authority", "integration witness", "witness rebind record is absent or ambiguous")
    rebind = matches[0]
    expected = (ledger.header.workstream_id, rebind.record_id, rebind.from_branch, rebind.to_branch, rebind.source_tip,
                rebind.target_pre_merge_tip, rebind.integration_commit, rebind.pre_ledger_digest)
    actual = (witness.workstream_id, witness.rebind_record_id, witness.source_branch, witness.target_branch,
              witness.source_tip, witness.target_pre_merge_tip, witness.integration_commit, witness.pre_ledger_digest)
    if actual != expected:
        _fail("close-authority", "integration witness", "witness does not exactly bind the rendered rebind record")
    if rebind != ledger.rebinds[-1]:
        _fail("close-authority", "integration witness", "only the current effective rebind can authorise closeout")
    return rebind


def _receipt_coverage(ledger: WorkstreamLedger, receipts: Iterable[AdmittedWorkstreamReceipt], chain_id: str,
                      verifier: WorkstreamReceiptVerifier) -> dict[str, WorkstreamReceipt]:
    records = _records_by_chain(ledger).get(chain_id, [])
    expected = {record.record_id: record for record in records}
    covered: dict[str, WorkstreamReceipt] = {}
    for admitted in receipts:
        receipt = _validate_admitted_receipt(admitted, verifier, "chain receipt")
        if receipt.workstream_id != ledger.header.workstream_id or receipt.chain_id != chain_id:
            continue
        target = expected.get(receipt.record_id)
        if target is None or target.detail_digest != receipt.detail_digest:
            _fail("receipt", "chain close", "receipt does not identify an exact chain member", record_id=receipt.record_id)
        expected_receipt_id = workstream_receipt_id(ledger.header.id_salt, ledger.header.workstream_id, chain_id, target.detail_digest)
        if receipt.receipt_id != expected_receipt_id:
            _fail("receipt", "chain close", "receipt ID does not match its frozen workstream preimage", record_id=receipt.record_id)
        old = covered.get(receipt.record_id)
        if old is not None and old != receipt:
            _fail("receipt", "chain close", "conflicting duplicate receipt coverage", record_id=receipt.record_id)
        covered[receipt.record_id] = receipt
    return covered


def plan_workstream_chain_close(ledger: WorkstreamLedger, *, chain_id: str, receipts: Iterable[AdmittedWorkstreamReceipt],
                                receipt_verifier: WorkstreamReceiptVerifier,
                                integration_witness: TrustedIntegrationWitness,
                                integration_verifier: TrustedRebindVerifier,
                                expected_head: str, actual_head: str, pre_ledger_digest: str, branch: str,
                                conclusion: str, reasoning: str, source: str, confidence: str,
                                clock: Callable[[], datetime] | None = None) -> WorkstreamLedger:
    """Create the post-integration orchestrator close record for exactly one chain."""
    if branch != ledger.effective_branch:
        _fail("close-authority", "chain close", "close requires a trusted rebind on its integration branch")
    _validate_integration_witness(ledger, integration_witness, integration_verifier)
    if expected_head != actual_head:
        _fail("stale_head", "chain close", "branch tip changed; reload and re-judge", expected=expected_head, actual=actual_head)
    actual_digest = _append_pre_digest(ledger)
    if pre_ledger_digest != actual_digest:
        _fail("stale_ledger_digest", "chain close", "ledger bytes changed; reload and re-judge", expected=pre_ledger_digest, actual=actual_digest)
    if workstream_chain_phase(ledger, chain_id) != "orchestrate":
        _fail("close", "chain close", "only an orchestrate-phase chain can close")
    coverage = _receipt_coverage(ledger, receipts, chain_id, receipt_verifier)
    expected_members = {record.record_id for record in _records_by_chain(ledger)[chain_id]}
    if set(coverage) != expected_members:
        _fail("receipt", "chain close", "every existing chain member needs one durable receipt", missing=sorted(expected_members - set(coverage)))
    heads = workstream_chain_heads(ledger, chain_id)
    created = _clock_timestamp(clock)
    identifier = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, created, actual_digest)
    draft = WorkstreamRecord(identifier, created, "orchestrator", "orchestrate", "closed", created, chain_id, heads,
                             "combines" if len(heads) > 1 else "responds", False, (), source, (), confidence,
                             actual_digest, "sha256:" + "0" * 64, conclusion, reasoning)
    close = WorkstreamRecord(**{**draft.__dict__, "detail_digest": _detail_digest_for_record(draft)})
    result = WorkstreamLedger(ledger.header, ledger.entries + (close,))
    validate_workstream_ledger(result)
    return result


@dataclass(frozen=True)
class WorkstreamExpiryPreview:
    expected_head: str
    pre_ledger_digest: str
    removed_chain_ids: tuple[str, ...]
    removed_record_ids: tuple[str, ...]
    post_ledger_digest: str
    post_ledger: WorkstreamLedger
    git_blobs_remain: bool = True
    privacy_grade_erasure: bool = False


def _chain_closed_at(ledger: WorkstreamLedger, chain_id: str) -> str:
    records = _records_by_chain(ledger).get(chain_id, [])
    if not records or records[-1].to_phase != "closed" or records[-1].closed_at is None:
        _fail("expiry", "ledger expiry", "chain is not closed", chain_id=chain_id)
    return records[-1].closed_at


def _validate_expiry_dependencies(ledger: WorkstreamLedger, removed_chain_ids: set[str]) -> None:
    removed_records = {record.record_id for chain in removed_chain_ids for record in _records_by_chain(ledger).get(chain, [])}
    for record in ledger.records:
        if record.chain_id in removed_chain_ids:
            continue
        if record.to_phase == "closed":
            continue
        for dependency in record.depends_on:
            if dependency.workstream_id == ledger.header.workstream_id and dependency.record_id in removed_records and dependency.receipt is None:
                _fail("dependency", "ledger expiry", "open dependent lacks a durable fallback for removed target", record_id=record.record_id)


def preview_workstream_expiry(ledger: WorkstreamLedger, *, expected_head: str, chain_ids: Iterable[str], now: datetime,
                               receipts: Iterable[AdmittedWorkstreamReceipt], receipt_verifier: WorkstreamReceiptVerifier,
                               integration_witness: TrustedIntegrationWitness,
                               integration_verifier: TrustedRebindVerifier,
                               early_approval: EarlyExpiryApproval | None = None,
                               early_approval_verifier: EarlyExpiryApprovalVerifier | None = None) -> WorkstreamExpiryPreview:
    validate_workstream_ledger(ledger)
    _validate_integration_witness(ledger, integration_witness, integration_verifier)
    early = early_approval is not None
    selected = tuple(sorted(set(chain_ids)))
    if not selected:
        _fail("expiry", "ledger expiry", "expiry must select at least one complete chain")
    for chain in selected:
        _id(chain, "rlc_", "ledger expiry", "chain_id")
        closed_at = _chain_closed_at(ledger, chain)
        coverage = _receipt_coverage(ledger, receipts, chain, receipt_verifier)
        members = _records_by_chain(ledger)[chain]
        if set(coverage) != {record.record_id for record in members}:
            _fail("receipt", "ledger expiry", "expired chain lacks complete receipt coverage", chain_id=chain)
        if early:
            if any(receipt.disposition == "promoted" for receipt in coverage.values()):
                _fail("early-expiry", "ledger expiry", "a promoted chain can never use early expiry", chain_id=chain)
            if early_approval is None or early_approval_verifier is None:
                _fail("early-expiry", "ledger expiry", "early cleanup needs a durable live-user approval/disposition")
            _validate_early_expiry_approval(early_approval)
            if (early_approval.workstream_id != ledger.header.workstream_id or early_approval.chain_id != chain
                    or not early_approval.disposition or not early_approval_verifier.verify(early_approval)):
                _fail("early-expiry", "ledger expiry", "early cleanup approval is not a verified durable chain disposition", chain_id=chain)
        elif now.astimezone(timezone.utc) < _as_utc(closed_at) + timedelta(days=ledger.header.reflection_retention_days):
            _fail("expiry", "ledger expiry", "chain retention window has not elapsed", chain_id=chain)
    _validate_expiry_dependencies(ledger, set(selected))
    retained = tuple(entry for entry in ledger.entries if not (isinstance(entry, WorkstreamRecord) and entry.chain_id in set(selected)))
    post = WorkstreamLedger(ledger.header, retained)
    # Compaction deliberately removes historical blocks without rewriting the
    # surviving immutable record IDs/preimages.  Normal parser/append paths
    # always recompute predecessor digests; this one-shot post-image has just
    # been derived from a verified pre-image and is checked structurally here.
    validate_workstream_ledger(post, verify_predecessors=False)
    removed = tuple(sorted(record.record_id for record in ledger.records if record.chain_id in set(selected)))
    return WorkstreamExpiryPreview(expected_head, _append_pre_digest(ledger), selected, removed, _append_pre_digest(post), post)


def apply_workstream_expiry(ledger: WorkstreamLedger, preview: WorkstreamExpiryPreview, *, actual_head: str,
                            integration_witness: TrustedIntegrationWitness,
                            integration_verifier: TrustedRebindVerifier,
                            actual_ledger_digest: str | None = None) -> WorkstreamLedger:
    _validate_integration_witness(ledger, integration_witness, integration_verifier)
    if actual_head != preview.expected_head:
        _fail("stale_head", "ledger expiry", "branch tip changed after expiry preview", expected=preview.expected_head, actual=actual_head)
    actual_digest = actual_ledger_digest or _append_pre_digest(ledger)
    if actual_digest != preview.pre_ledger_digest:
        _fail("stale_ledger_digest", "ledger expiry", "ledger bytes changed after expiry preview", expected=preview.pre_ledger_digest, actual=actual_digest)
    if _append_pre_digest(preview.post_ledger) != preview.post_ledger_digest:
        _fail("expiry", "ledger expiry", "expiry preview post bytes no longer match their digest")
    return preview.post_ledger


RETENTION_PREFLIGHT_FIELDS = (
    "schema", "version", "key_id", "id_domain", "id_kind", "workstream_id", "working_branch", "base_sha",
    "id_salt", "created_at", "retention_days", "scope", "chain_id", "nonce", "approved_at", "expires_at",
    "reason", "session_path", "entry_id",
)
RETENTION_APPROVAL_FIELDS = RETENTION_PREFLIGHT_FIELDS + ("commit", "blob", "signature")


def _retention_preflight_mapping(preflight: RetentionPreflight) -> dict[str, Any]:
    return {
        "schema": "memory-seed/reflection-retention-preflight", "version": 2, "key_id": preflight.key_id,
        "id_domain": "memory-seed/reflection-workstream-ledger/v2", "id_kind": "workstream",
        "workstream_id": preflight.workstream_id, "working_branch": preflight.working_branch, "base_sha": preflight.base_sha,
        "id_salt": preflight.id_salt, "created_at": preflight.created_at, "retention_days": preflight.retention_days,
        "scope": "ledger", "chain_id": None, "nonce": preflight.nonce, "approved_at": preflight.approved_at,
        "expires_at": preflight.expires_at, "reason": preflight.reason, "session_path": preflight.session_path,
        "entry_id": preflight.entry_id,
    }


def render_retention_preflight(preflight: RetentionPreflight) -> str:
    _validate_retention_preflight(preflight)
    values = _retention_preflight_mapping(preflight)
    return _v2_yaml_mapping([(name, values[name]) for name in RETENTION_PREFLIGHT_FIELDS])


def retention_preflight_from_dict(value: Mapping[str, Any], path: str = "retention-preflight.yaml") -> RetentionPreflight:
    _required(value, RETENTION_PREFLIGHT_FIELDS, path)
    _only(value, RETENTION_PREFLIGHT_FIELDS, path)
    if value["schema"] != "memory-seed/reflection-retention-preflight" or value["version"] != 2 or value["id_domain"] != "memory-seed/reflection-workstream-ledger/v2" or value["id_kind"] != "workstream" or value["scope"] != "ledger" or value["chain_id"] is not None:
        _fail("retention-approval", path, "retention preflight discriminator or scope is invalid")
    result = RetentionPreflight(_text(value["key_id"], path, "key_id"), _text(value["workstream_id"], path, "workstream_id"),
                                _text(value["working_branch"], path, "working_branch"), _text(value["base_sha"], path, "base_sha"),
                                _text(value["id_salt"], path, "id_salt"), _text(value["created_at"], path, "created_at"),
                                value["retention_days"], _text(value["nonce"], path, "nonce"),
                                _text(value["approved_at"], path, "approved_at"), _text(value["expires_at"], path, "expires_at"),
                                _text(value["reason"], path, "reason"), _session_path(value["session_path"], path, "session_path"),
                                _text(value["entry_id"], path, "entry_id"))
    _validate_retention_preflight(result, path)
    return result


def parse_retention_preflight(raw: bytes | str, path: str = "retention-preflight.yaml") -> RetentionPreflight:
    text = _canonical_text(raw, path)
    result = retention_preflight_from_dict(_parse_yaml_mapping(text, path), path)
    if render_retention_preflight(result) != text:
        _fail("canonical-bytes", path, "retention preflight is not canonical")
    return result


def _retention_approval_mapping(approval: RetentionApproval, *, include_signature: bool) -> dict[str, Any]:
    result = _retention_preflight_mapping(approval.preflight)
    result["schema"] = "memory-seed/reflection-retention-approval"
    result["commit"] = approval.commit
    result["blob"] = approval.blob
    if include_signature:
        result["signature"] = approval.signature
    return result


def render_retention_approval(approval: RetentionApproval) -> str:
    _validate_retention_preflight(approval.preflight, "retention approval")
    if not re.fullmatch(r"ed25519:[0-9a-f]{128}", approval.signature):
        _fail("retention-approval", "retention approval", "approval signature is invalid")
    values = _retention_approval_mapping(approval, include_signature=True)
    return _v2_yaml_mapping([(name, values[name]) for name in RETENTION_APPROVAL_FIELDS])


def retention_approval_payload(approval: RetentionApproval) -> bytes:
    values = _retention_approval_mapping(approval, include_signature=False)
    return _v2_yaml_mapping([(name, values[name]) for name in RETENTION_APPROVAL_FIELDS[:-1]]).encode("utf-8")


def retention_approval_from_dict(value: Mapping[str, Any], path: str = "retention-approval.yaml") -> RetentionApproval:
    _required(value, RETENTION_APPROVAL_FIELDS, path)
    _only(value, RETENTION_APPROVAL_FIELDS, path)
    if value["schema"] != "memory-seed/reflection-retention-approval":
        _fail("retention-approval", path, "retention approval schema is invalid")
    preflight_fields = {name: value[name] for name in RETENTION_PREFLIGHT_FIELDS}
    preflight_fields["schema"] = "memory-seed/reflection-retention-preflight"
    preflight = retention_preflight_from_dict(preflight_fields, path)
    result = RetentionApproval(preflight, _git_sha(value["commit"], path, "commit"), _git_sha(value["blob"], path, "blob"),
                               _text(value["signature"], path, "signature"))
    if not re.fullmatch(r"ed25519:[0-9a-f]{128}", result.signature):
        _fail("retention-approval", path, "retention approval signature is invalid")
    return result


def parse_retention_approval(raw: bytes | str, path: str = "retention-approval.yaml") -> RetentionApproval:
    text = _canonical_text(raw, path)
    result = retention_approval_from_dict(_parse_yaml_mapping(text, path), path)
    if render_retention_approval(result) != text:
        _fail("canonical-bytes", path, "retention approval is not canonical")
    return result


@dataclass(frozen=True)
class RetentionApprovalTrust:
    key_id: str
    public_key: str


def validate_retention_approval_admission(header: WorkstreamLedgerHeader, approval: RetentionApproval, *,
                                          trust: RetentionApprovalTrust, now: datetime,
                                          session_contains_preflight: Callable[[RetentionPreflight, str, str], bool],
                                          commit_is_reachable: Callable[[str], bool],
                                          object_at: Callable[[str, str], str | None],
                                          admitted_headers: Iterable[WorkstreamLedgerHeader] = ()) -> None:
    """Validate all host/Git supplied facts without accepting caller candidate fields.

    The callbacks deliberately expose facts, not arbitrary policy: adapters own
    Git traversal and session parsing, while this kernel owns every exact
    identity, signature, binding, expiry, and replay comparison.
    """
    _header_from_dict(header.as_dict(), "ledger header")
    _validate_retention_preflight(approval.preflight, "retention approval")
    if header.reflection_retention_days not in {14, 30} or header.retention_extension_receipt is None:
        _fail("retention-approval", "ledger header", "only extended headers can admit an approval")
    if trust.key_id != header.retention_approval_key_id or trust.key_id != approval.preflight.key_id:
        _fail("retention-approval", "ledger header", "trust key ID does not bind the header and approval")
    if not re.fullmatch(r"ed25519:[0-9a-f]{64}", trust.public_key):
        _fail("retention-approval", "trust anchor", "trusted public key is not canonical")
    preflight = approval.preflight
    common = ("workstream_id", "working_branch", "base_sha", "id_salt", "created_at", "retention_days", "nonce",
              "session_path", "entry_id")
    expected = {"workstream_id": header.workstream_id, "working_branch": header.working_branch, "base_sha": header.base_sha,
                "id_salt": header.id_salt, "created_at": header.created_at, "retention_days": header.reflection_retention_days,
                "nonce": header.retention_extension_receipt.nonce, "session_path": header.retention_extension_receipt.session_path,
                "entry_id": header.retention_extension_receipt.entry_id}
    for name in common:
        if getattr(preflight, name) != expected[name]:
            _fail("retention-approval", "ledger header", "approval preflight does not exactly bind header", field=name)
    receipt = header.retention_extension_receipt
    if receipt.commit != approval.commit or receipt.blob != approval.blob or receipt.signature != approval.signature:
        _fail("retention-approval", "ledger header", "header locator does not exactly equal signed approval")
    if now.astimezone(timezone.utc) >= _as_utc(preflight.expires_at):
        _fail("retention-approval", "retention approval", "retention approval has expired")
    if not commit_is_reachable(approval.commit) or object_at(approval.commit, preflight.session_path) != approval.blob:
        _fail("retention-approval", "retention approval", "approval locator is not Git-admitted")
    if not session_contains_preflight(preflight, approval.commit, approval.blob):
        _fail("retention-approval", "retention approval", "committed session does not contain exact preflight")
    if not ed25519_verify(bytes.fromhex(trust.public_key[len("ed25519:"):]), retention_approval_payload(approval), bytes.fromhex(approval.signature[len("ed25519:"):])):
        _fail("retention-approval", "retention approval", "approval signature does not verify under the admitted key")
    nonce_identity = ("memory-seed/reflection-retention-approval", 2, preflight.key_id, preflight.nonce)
    locator_identity = (preflight.session_path, preflight.entry_id, approval.commit, approval.blob)
    for other in admitted_headers:
        if other.workstream_id == header.workstream_id or other.retention_extension_receipt is None:
            continue
        other_nonce = ("memory-seed/reflection-retention-approval", 2, other.retention_approval_key_id, other.retention_extension_receipt.nonce)
        other_locator = (other.retention_extension_receipt.session_path, other.retention_extension_receipt.entry_id,
                         other.retention_extension_receipt.commit, other.retention_extension_receipt.blob)
        if nonce_identity == other_nonce or locator_identity == other_locator:
            _fail("retention-approval", "ledger header", "approval nonce or locator was already consumed")


def _atomic_write_new(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        _fail("overwrite", path.as_posix(), "guarded init refuses to overwrite an existing file")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = path.with_name(path.name + ".tmp")
    if descriptor.exists() or descriptor.is_symlink():
        _fail("overwrite", descriptor.as_posix(), "temporary guarded writer path is occupied")
    try:
        descriptor.write_bytes(raw)
        os.replace(descriptor, path)
    finally:
        descriptor.unlink(missing_ok=True)


def _atomic_replace_existing(path: Path, old: bytes, new: bytes) -> None:
    if not path.is_file() or path.read_bytes() != old:
        _fail("stale_ledger_digest", path.as_posix(), "ledger changed before guarded write")
    descriptor = path.with_name(path.name + ".tmp")
    if descriptor.exists() or descriptor.is_symlink():
        _fail("overwrite", descriptor.as_posix(), "temporary guarded writer path is occupied")
    try:
        descriptor.write_bytes(new)
        # Re-check immediately before replacement so a direct overwrite loses
        # rather than being silently replaced by stale author intent.
        if path.read_bytes() != old:
            _fail("stale_ledger_digest", path.as_posix(), "ledger changed during guarded write")
        os.replace(descriptor, path)
    finally:
        descriptor.unlink(missing_ok=True)


def guarded_init_workstream_ledger(cwd: Path | str, *, expected_head: str, actual_head: str, working_branch: str,
                                   base_sha: str, retention_days: int = 7, clock: Callable[[], datetime] | None = None,
                                   entropy: Callable[[int], bytes] = os.urandom,
                                   retention_preflight_handle: object | None = None,
                                   retention_verifier: RetentionPreflightVerifier | None = None) -> tuple[str, WorkstreamLedger]:
    if expected_head != actual_head:
        _fail("stale_head", "ledger init", "branch tip changed before init", expected=expected_head, actual=actual_head)
    ledger = initialize_workstream_ledger(working_branch=working_branch, base_sha=base_sha, retention_days=retention_days,
                                          clock=clock, entropy=entropy, retention_preflight_handle=retention_preflight_handle,
                                          retention_verifier=retention_verifier)
    root = Path(cwd).resolve()
    validate_workstream_init_collisions(root, working_branch=working_branch, workstream_id=ledger.header.workstream_id)
    relative = workstream_ledger_path(ledger.header.workstream_id)
    _atomic_write_new(root / Path(relative), render_workstream_ledger(ledger).encode("utf-8"))
    return relative, ledger


def guarded_append_workstream_ledger(cwd: Path | str, *, workstream_id: str, request: WorkstreamAppendRequest,
                                     expected_head: str, actual_head: str, pre_ledger_digest: str, branch: str,
                                     clock: Callable[[], datetime] | None = None,
                                     active_ledgers: Iterable[WorkstreamLedger] = (),
                                     durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                     receipt_verifier: WorkstreamReceiptVerifier | None = None) -> WorkstreamLedger:
    root = Path(cwd).resolve()
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v2 ledger does not exist")
    raw = path.read_bytes()
    ledger = parse_workstream_ledger(raw, relative)
    if ledger.header.workstream_id != workstream_id:
        _fail("path", relative, "ledger path and header workstream ID differ")
    validate_workstream_branch_owner(root, ledger)
    result = plan_workstream_append(ledger, request, expected_head=expected_head, actual_head=actual_head,
                                    pre_ledger_digest=pre_ledger_digest, branch=branch, clock=clock,
                                    active_ledgers=active_ledgers, durable_receipts=durable_receipts,
                                    receipt_verifier=receipt_verifier)
    _atomic_replace_existing(path, raw, render_workstream_ledger(result).encode("utf-8"))
    return result


def guarded_apply_trusted_rebind(cwd: Path | str, *, workstream_id: str, token: TrustedRebindToken,
                                 integration_commit: str, current_target_tip: str, verifier: TrustedRebindVerifier,
                                 reason: str, clock: Callable[[], datetime] | None = None) -> TrustedRebindResult:
    """CAS write primitive which rejects occupied/malformed target-branch boards."""
    root = Path(cwd).resolve()
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v2 ledger does not exist")
    raw = path.read_bytes()
    ledger = parse_workstream_ledger(raw, relative)
    validate_workstream_branch_owner(root, ledger)
    board = workstream_board_view(root)
    for item in board.items:
        if item.status != "valid":
            _fail("branch-collision", item.path, "malformed active candidate blocks trusted rebind")
        if item.path != relative and item.effective_branch == token.target_branch:
            _fail("branch-collision", item.path, "target branch is already owned by another ledger", branch=token.target_branch)
    result = apply_trusted_rebind(ledger, token, integration_commit=integration_commit, current_target_tip=current_target_tip,
                                  verifier=verifier, reason=reason, clock=clock)
    _atomic_replace_existing(path, raw, render_workstream_ledger(result.ledger).encode("utf-8"))
    return result


def guarded_apply_workstream_expiry(cwd: Path | str, *, workstream_id: str, preview: WorkstreamExpiryPreview,
                                    actual_head: str, integration_witness: TrustedIntegrationWitness,
                                    integration_verifier: TrustedRebindVerifier) -> WorkstreamLedger:
    root = Path(cwd).resolve()
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v2 ledger does not exist")
    raw = path.read_bytes()
    ledger = parse_workstream_ledger(raw, relative)
    validate_workstream_branch_owner(root, ledger)
    result = apply_workstream_expiry(ledger, preview, actual_head=actual_head,
                                     integration_witness=integration_witness, integration_verifier=integration_verifier)
    _atomic_replace_existing(path, raw, render_workstream_ledger(result).encode("utf-8"))
    return result
