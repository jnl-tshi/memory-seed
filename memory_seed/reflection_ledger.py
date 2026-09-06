"""Strict, temporary reflection-ledger kernel.

This module deliberately has no dependency on the session readers.  A
reflection board is coordination state, rather than a second source of durable
memory, so its format, discovery, and fuse are all kept separate from
``memory_seed.core``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence
import json
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
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in value or value.startswith("."):
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
              "orchestrator", "participants")
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
        ("participants_seal", manifest.participants_seal), ("orchestrator", dict(manifest.orchestrator)),
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


def live_heads(fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest | None = None) -> dict[str, tuple[ReflectionRecord, ...]]:
    fragments = tuple(fragments)
    if manifest is not None:
        validate_relationships(fragments, manifest)
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


def common_view(fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest | None = None, *, plan_id: str | None = None,
                area: str | None = None, activity: str | None = None, topic: str | None = None,
                related_decision: str | None = None, chain: str | None = None, responds_to: str | None = None,
                transitive: bool = False) -> tuple[ReflectionRecord, ...]:
    fragments = tuple(fragments)
    if manifest is not None:
        validate_relationships(fragments, manifest)
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


def render_closeout(plan_id: str, closes: Iterable[ReflectionChainClose]) -> str:
    closes = tuple(closes)
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
        closes.append(ReflectionChainClose(
            _id(item["chain_id"], "rlc_", path, "chain_id"), _timestamp(item["closed_at"], path, "closed_at"), item["retention_days"],
            _timestamp(item["expires_at"], path, "expires_at"), tuple(item["implementer_record_ids"]), tuple(item["reviewer_record_ids"]),
            tuple(item["orchestrator_record_ids"]), _id(item["synthesis_record_id"], "rlr_", path, "synthesis_record_id"),
            tuple(item["resolved_head_ids"]), tuple(item["disposed_head_ids"]), _text(item["validation_receipt"], path, "validation_receipt"), tuple(item["receipt_ids"]), path,
        ))
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


def validate_chain_close(close: ReflectionChainClose, fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest,
                         receipts: Iterable[ReflectionReceipt]) -> None:
    fragments = tuple(fragments)
    validate_relationships(fragments, manifest)
    if close.retention_days < 1 or _as_utc(close.expires_at) != _as_utc(close.closed_at) + timedelta(days=close.retention_days):
        _fail("close", close.path, "expires_at must equal closed_at plus retention_days")
    index = _record_index(fragments)
    members = {identifier for identifier, (_fragment, record) in index.items() if record.chain_id == close.chain_id}
    if not members:
        _fail("close", close.path, "close record names an unknown chain")
    heads = {record.record_id for record in live_heads(fragments, manifest).get(close.chain_id, ())}
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
    synthesis = index.get(close.synthesis_record_id)
    if synthesis is None or synthesis[1].chain_id != close.chain_id or synthesis[1].kind not in {"resolution", "closeout", "promotion"}:
        _fail("close", close.path, "close needs an orchestrator synthesis record in its chain")
    receipts_by_id: dict[str, ReflectionReceipt] = {}
    for receipt in receipts:
        existing = receipts_by_id.get(receipt.receipt_id)
        if existing is not None and existing != receipt:
            _fail("receipt-collision", close.path, "conflicting duplicate durable receipt ID", receipt_id=receipt.receipt_id)
        receipts_by_id[receipt.receipt_id] = receipt
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


def validate_board_close(closes: Iterable[ReflectionChainClose], fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest,
                         receipts: Iterable[ReflectionReceipt]) -> None:
    fragments = tuple(fragments)
    chains = {record.chain_id for _fragment, record in _record_index(fragments).values()}
    by_chain: dict[str, ReflectionChainClose] = {}
    for close in closes:
        if close.chain_id in by_chain:
            _fail("close-collision", close.path, "multiple close records name one chain", chain=close.chain_id)
        by_chain[close.chain_id] = close
    if chains != set(by_chain):
        _fail("board-close", "closeout.md", "board cannot close until every admitted chain has a close record", missing=sorted(chains - set(by_chain)))
    for close in by_chain.values():
        validate_chain_close(close, fragments, manifest, receipts)


class LiveUserApproval:
    """Opaque approval capability intentionally not constructible by agents/API callers."""
    __slots__ = ("_seal", "chain_id", "member_ids", "approved_at", "reason")
    _SEAL = object()

    def __init__(self, seal: object, chain_id: str, member_ids: Sequence[str], approved_at: str, reason: str) -> None:
        if seal is not self._SEAL:
            raise TypeError("live user approvals are minted only by the interactive host")
        self._seal, self.chain_id, self.member_ids, self.approved_at, self.reason = seal, chain_id, tuple(member_ids), approved_at, reason


def _mint_live_user_approval(chain_id: str, member_ids: Sequence[str], approved_at: str, reason: str) -> LiveUserApproval:
    """Host-only seam; intentionally private so an agent cannot self-mint approval."""
    return LiveUserApproval(LiveUserApproval._SEAL, chain_id, member_ids, approved_at, reason)


def eligible_expiry_paths(closes: Iterable[ReflectionChainClose], fragments: Iterable[ReflectionFragment], manifest: ReflectionManifest,
                          receipts: Iterable[ReflectionReceipt], *, now: datetime, chain: str | None = None,
                          early: bool = False, approval: LiveUserApproval | None = None) -> tuple[str, ...]:
    if now.tzinfo is None:
        _fail("expiry", "closeout.md", "expiry comparison requires timezone-aware now")
    fragments = tuple(fragments)
    close_map = {close.chain_id: close for close in closes}
    if chain is None and early:
        _fail("expiry", "closeout.md", "early expiry requires one exact chain")
    candidates = [close_map[chain]] if chain is not None and chain in close_map else ([] if chain is not None else list(close_map.values()))
    if chain is not None and not candidates:
        _fail("expiry", "closeout.md", "requested chain has no close record", chain=chain)
    eligible: list[str] = []
    for close in candidates:
        if early:
            if approval is None or approval._seal is not LiveUserApproval._SEAL or approval.chain_id != close.chain_id:
                _fail("live-user-approval", close.path, "early deletion requires unforgeable live-user approval for this chain")
            member_ids = {record.record_id for _fragment, record in _record_index(fragments).values() if record.chain_id == close.chain_id}
            if set(approval.member_ids) != member_ids or _as_utc(approval.approved_at) > _as_utc(close.expires_at):
                _fail("live-user-approval", close.path, "approval does not bind the exact members before expiry")
            receipts_by_id = {item.receipt_id: item for item in receipts}
            if any(receipts_by_id[item].disposition == "promoted" for item in close.receipt_ids if item in receipts_by_id):
                _fail("early-expiry", close.path, "early deletion is limited to unpromoted chains")
        else:
            validate_chain_close(close, fragments, manifest, receipts)
            if now < _as_utc(close.expires_at):
                continue
        eligible.append(close.path)
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
    code, content = _git(root, "show", f"{commit}:{path}", binary=True)
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
        token_source = "\0".join([plan_id, branch, source_tip, base_tip, manifest_blob.oid] + sorted(blob.oid for blob in additions))
        token = sha256(token_source.encode("utf-8")).hexdigest()
        plan = _ReflectionFusePlan(plan_id, branch, source_tip, base_tip, manifest_blob.oid, manifest_blob.raw_sha256,
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
