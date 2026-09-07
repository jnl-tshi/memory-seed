"""Reflection Board v1: one strict sequential ledger per workstream.

Temporary coordination state uses its own canonical format and trusted Git
history. Durable receipt evidence is read from ordinary append-only sessions.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256, sha512
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence
import json
import os
import re
import secrets
import subprocess
import unicodedata


REFLECTION_ROOT = ".memory-seed/reflections/active"
CANONICAL_MODE = "100644"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
ID_SUFFIX_RE = re.compile(r"^[0-9abcdefghjkmnpqrstvwxyz]{20}$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./:+@=-]+$")


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


def _session_entry_scope(raw: bytes, path: str, entry_id: str) -> str:
    """Return the one immutable normal-session entry named by ``entry_id``."""
    _session_path(path, path, "session_path")
    if not SESSION_ENTRY_ID_RE.fullmatch(entry_id):
        _fail("session-locator", path, "receipt entry_id must be a canonical session entry ID", entry_id=entry_id)
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
    return text[entry.end():entry_end]


def _session_decision_scope(scope: str, path: str, entry_id: str, decision_id: str) -> str:
    """Return exactly one DRAFT decision body inside an already-scoped entry."""
    if not SESSION_DECISION_ID_RE.fullmatch(decision_id):
        _fail("session-locator", path, "receipt decision_id must be a canonical decision locator", decision_id=decision_id)
    decision_matches = list(re.finditer(rf"^#### {re.escape(decision_id)}(?:\s|-|$)[^\n]*\n", scope, re.MULTILINE))
    if len(decision_matches) != 1:
        _fail("session-locator", path, "receipt evidence must resolve exactly one decision in its session entry", entry_id=entry_id, decision_id=decision_id)
    decision = decision_matches[0]
    following = re.search(r"^#### D[1-9][0-9]*(?:\s|-|$)[^\n]*\n", scope[decision.end():], re.MULTILINE)
    decision_end = decision.end() + following.start() if following is not None else len(scope)
    return scope[decision.start():decision_end]


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


@dataclass(frozen=True)
class GitBlob:
    path: str
    oid: str
    mode: str
    content: bytes


def _git(root: Path, *args: str, binary: bool = False) -> tuple[int, bytes | str]:
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if binary:
        return result.returncode, result.stdout
    return result.returncode, result.stdout.decode("utf-8", errors="replace").strip()


def _commit(root: Path, ref: str) -> str | None:
    code, output = _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return output if code == 0 and isinstance(output, str) and re.fullmatch(r"[0-9a-f]{40}", output) else None


@lru_cache(maxsize=32768)
def _cached_tree_blob(repository: str, commit: str, path: str) -> GitBlob | None:
    """Read immutable Git tree evidence; cache is derived-only and bounded."""
    root = Path(repository)
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
    return GitBlob(path, match.group("oid"), match.group("mode"), content)


def _tree_blob(root: Path, commit: str, path: str) -> GitBlob | None:
    return _cached_tree_blob(str(root.resolve()), commit, path)


# ---------------------------------------------------------------------------
# Reflection workstream ledger v1
# ---------------------------------------------------------------------------

WORKSTREAM_LEDGER_SCHEMA = "memory-seed/reflection-workstream-ledger"
WORKSTREAM_LEDGER_VERSION = 1
WORKSTREAM_LEDGER_NAME = "ledger.md"
WORKSTREAM_LEDGER_DOMAIN = b"memory-seed/reflection-workstream-ledger/v1/ledger\0"
WORKSTREAM_DETAIL_DOMAIN = b"memory-seed/reflection-workstream-ledger/v1/detail\0"
WORKSTREAM_ID_DOMAIN = b"memory-seed/reflection-workstream-ledger/v1\0"
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


def _workstream_digest(domain: bytes, raw: bytes) -> str:
    return "sha256:" + sha256(domain + raw).hexdigest()


def _workstream_yaml_inline(value: Any) -> str:
    """The v1 renderer preserves all-digit IDs/nonces as strings."""
    if isinstance(value, list):
        return "[" + ", ".join(_workstream_yaml_inline(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{key}: {_workstream_yaml_inline(item)}" for key, item in value.items()) + "}"
    if isinstance(value, str) and re.fullmatch(r"0|[1-9]\d*", value):
        return json.dumps(value, ensure_ascii=False)
    return _quote(value)


def _workstream_yaml_mapping(items: Sequence[tuple[str, Any]]) -> str:
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
                    lines.append(f"  - {first_key}: {_workstream_yaml_inline(first_value)}")
                    for nested_key, nested_value in member_items[1:]:
                        lines.append(f"    {nested_key}: {_workstream_yaml_inline(nested_value)}")
                else:
                    lines.append(f"  - {_workstream_yaml_inline(member)}")
        else:
            lines.append(f"{key}: {_workstream_yaml_inline(value)}")
    return "\n".join(lines) + "\n"


def workstream_ledger_digest(raw: bytes | str) -> str:
    """Return the domain-separated digest of canonical ledger bytes."""
    text = _canonical_text(raw, "ledger.md")
    return _workstream_digest(WORKSTREAM_LEDGER_DOMAIN, text.encode("utf-8"))


def workstream_detail_digest(raw: bytes | str) -> str:
    """Return the domain-separated digest of one canonical record/rebind block."""
    text = _canonical_text(raw, "record")
    return _workstream_digest(WORKSTREAM_DETAIL_DOMAIN, text.encode("utf-8"))


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


def _workstream_id(prefix: str, id_salt: str, *components: str) -> str:
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
    return _workstream_id("rwl_", id_salt, "workstream", working_branch, base_sha, created_at)


def workstream_record_id(id_salt: str, workstream: str, created_at: str, pre_ledger_digest: str) -> str:
    return _workstream_id("rlr_", id_salt, "record", workstream, created_at, pre_ledger_digest)


def workstream_chain_id(id_salt: str, workstream: str, first_record_id: str) -> str:
    return _workstream_id("rlc_", id_salt, "chain", workstream, first_record_id)


def workstream_receipt_id(id_salt: str, workstream: str, chain_id: str, detail_digest: str) -> str:
    return _workstream_id("rrc_", id_salt, "receipt", workstream, chain_id, detail_digest)


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
    """The six immutable locator fields copied into a v1 ledger header."""

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
    if (value.get("schema") != WORKSTREAM_LEDGER_SCHEMA
            or type(value.get("version")) is not int
            or value["version"] != WORKSTREAM_LEDGER_VERSION):
        _fail("unsupported-reflection-format", path, "unsupported or mixed reflection ledger discriminator")
    _required(value, WORKSTREAM_HEADER_FIELDS, path)
    _only(value, WORKSTREAM_HEADER_FIELDS, path)
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
    """Recognize only the exact supported workstream schema and version."""
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
    if schema == WORKSTREAM_LEDGER_SCHEMA and type(version) is int and version == WORKSTREAM_LEDGER_VERSION:
        _only(mapping, WORKSTREAM_HEADER_FIELDS, path)
        return "workstream-v1"
    _fail("unsupported-reflection-format", path, "unsupported, absent, duplicate, or mixed reflection ledger family")


def render_workstream_header(header: WorkstreamLedgerHeader) -> str:
    # Parse the rendered mapping as a final renderer guard, including field order.
    rendered = _workstream_yaml_mapping([(name, header.as_dict()[name]) for name in WORKSTREAM_HEADER_FIELDS])
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


def _record_from_workstream_dict(value: Mapping[str, Any], sections: Mapping[str, str], path: str) -> WorkstreamRecord:
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


def _rebind_from_workstream_dict(value: Mapping[str, Any], path: str) -> TrustedRebind:
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


def _render_workstream_sections(record: WorkstreamRecord) -> str:
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
    metadata = _workstream_yaml_mapping([(name, record.metadata(zero_detail_digest=zero_detail_digest)[name]) for name in WORKSTREAM_RECORD_FIELDS])
    return f"## Record {record.record_id}\n\n```yaml\n{metadata}```\n\n{_render_workstream_sections(record)}"


def render_trusted_rebind(rebind: TrustedRebind, *, zero_detail_digest: bool = False) -> str:
    metadata = _workstream_yaml_mapping([(name, rebind.metadata(zero_detail_digest=zero_detail_digest)[name]) for name in WORKSTREAM_REBIND_FIELDS])
    return f"## Rebind {rebind.record_id}\n\n```yaml\n{metadata}```\n"


def _parse_workstream_sections(raw: str, path: str) -> dict[str, str]:
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


def _parse_workstream_entry(raw: str, path: str) -> WorkstreamEntry:
    if raw.startswith("## Record "):
        match = re.fullmatch(r"## Record ([^\n]+)\n\n```yaml\n(.*?)```\n\n(.*)", raw, re.DOTALL)
        if not match:
            _fail("record", path, "record block is malformed")
        metadata = _parse_yaml_mapping(match.group(2), path)
        if metadata.get("record_id") != match.group(1):
            _fail("record", path, "record heading and metadata ID differ")
        return _record_from_workstream_dict(metadata, _parse_workstream_sections(match.group(3), path), path)
    if raw.startswith("## Rebind "):
        # Ledger blocks are joined by exactly one separator LF.  Rebind blocks
        # already end in their YAML LF, so an intermediate rebind consequently
        # owns two trailing LFs; the final rebind owns one.  Accept precisely
        # those renderer-produced forms and let the full-ledger byte equality
        # check reject every other separator.
        match = re.fullmatch(r"## Rebind ([^\n]+)\n\n```yaml\n(.*?)```\n(?:\n)?", raw, re.DOTALL)
        if not match:
            _fail("rebind", path, "rebind block is malformed")
        metadata = _parse_yaml_mapping(match.group(2), path)
        if metadata.get("record_id") != match.group(1):
            _fail("rebind", path, "rebind heading and metadata ID differ")
        return _rebind_from_workstream_dict(metadata, path)
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
        reflection_ledger_family(text, path)
        _fail("discriminator", path, "v1 ledger requires canonical front matter")
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
    entries = tuple(_parse_workstream_entry(block, path) for block in blocks)
    ledger = WorkstreamLedger(header, entries)
    validate_workstream_ledger(ledger, path)
    if render_workstream_ledger(ledger) != text:
        _fail("canonical-bytes", path, "ledger does not use the canonical v1 renderer")
    return ledger


def _parse_compacted_workstream_ledger(raw: bytes | str, path: str) -> WorkstreamLedger:
    """Parse canonical v1 bytes after, and only after, a trusted removal proof.

    This deliberately has no public switch or caller-provided proof.  The
    history loader invokes it only after binding the post-image to an admitted
    cleanup pair and a byte-for-byte raw-block derivation.
    """
    header_value, blocks, text = _split_workstream_ledger(raw, path)
    header = _header_from_dict(header_value, path)
    entries = tuple(_parse_workstream_entry(block, path) for block in blocks)
    ledger = WorkstreamLedger(header, entries)
    _validate_compacted_workstream_ledger(ledger, path)
    if render_workstream_ledger(ledger) != text:
        _fail("canonical-bytes", path, "ledger does not use the canonical v1 renderer")
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


def _validate_workstream_ledger(ledger: WorkstreamLedger, path: str, *, verify_predecessors: bool) -> None:
    """Internal structural validator; only trusted history admission may skip predecessors."""
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
            _rebind_from_workstream_dict(entry.metadata(), entry_path)
            if entry.from_branch != effective_branch:
                _fail("rebind", entry_path, "rebind source is not the effective owning branch", expected=effective_branch)
            expected_id = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, entry.created_at, entry.pre_ledger_digest)
            if entry.record_id != expected_id:
                _fail("id", entry_path, "rebind ID does not match its frozen preimage")
            if entry.detail_digest != _detail_digest_for_rebind(entry):
                _fail("detail-digest", entry_path, "rebind detail digest is invalid")
            effective_branch = entry.to_branch
            continue
        _record_from_workstream_dict(entry.metadata(), {
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


def validate_workstream_ledger(ledger: WorkstreamLedger, path: str = "ledger.md") -> None:
    """Strict standalone v1 validation, including every predecessor digest."""
    _validate_workstream_ledger(ledger, path, verify_predecessors=True)


def _validate_compacted_workstream_ledger(ledger: WorkstreamLedger, path: str) -> None:
    """Private post-proof structural check; never a public parser escape hatch."""
    _validate_workstream_ledger(ledger, path, verify_predecessors=False)


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
                   receipt_verifier: WorkstreamReceiptVerifier | None,
                   trusted_compacted: bool = False) -> WorkstreamRecord:
    if trusted_compacted:
        _validate_compacted_workstream_ledger(ledger, "trusted ledger append")
    else:
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


def _plan_trusted_workstream_append(loaded: "TrustedWorkstreamLedger", request: WorkstreamAppendRequest, *,
                                    clock: Callable[[], datetime] | None = None,
                                    active_ledgers: Iterable[WorkstreamLedger] = (),
                                    durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                    receipt_verifier: WorkstreamReceiptVerifier | None = None) -> WorkstreamLedger:
    """Private planner for a ledger already admitted by trusted Git history."""
    ledger = loaded.ledger
    actual_digest = workstream_ledger_digest(loaded.raw)
    created_at = _clock_timestamp(clock)
    record = _append_record(ledger, request, created_at=created_at, pre_ledger_digest=actual_digest,
                            branch=ledger.effective_branch, active_ledgers=active_ledgers,
                            durable_receipts=durable_receipts, receipt_verifier=receipt_verifier,
                            trusted_compacted=isinstance(loaded, AdmittedCompactedLedger))
    result = WorkstreamLedger(ledger.header, ledger.entries + (record,))
    if isinstance(loaded, AdmittedCompactedLedger):
        _validate_compacted_workstream_ledger(result, "trusted ledger append")
    else:
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


# These are v1 receipt values, not free-form prose.  The two decision-backed
# dispositions deliberately share the promoted classification: a chain already
# covered by a decision is no less promoted than one newly promoted to it.
WORKSTREAM_RECEIPT_DISPOSITIONS = frozenset({
    "promoted-to-decision",
    "already-covered-by-decision",
    "expired-unpromoted",
    "early-expired-unpromoted",
})
WORKSTREAM_PROMOTED_RECEIPT_DISPOSITIONS = frozenset({
    "promoted-to-decision",
    "already-covered-by-decision",
})


def _workstream_receipt_is_promoted(receipt: WorkstreamReceipt) -> bool:
    return receipt.disposition in WORKSTREAM_PROMOTED_RECEIPT_DISPOSITIONS


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
    """Untrusted early-expiry input; v1 early-cleanup admission is disabled."""

    workstream_id: str
    chain_id: str
    session_path: str
    entry_id: str
    decision_id: str
    commit: str
    blob: str
    disposition: str


class EarlyExpiryApprovalVerifier:
    """Caller verifier interface; cannot authorize v1 early cleanup."""

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
    disposition = _text(receipt.disposition, path, "disposition")
    if disposition not in WORKSTREAM_RECEIPT_DISPOSITIONS:
        _fail("receipt", path, "receipt disposition is not a canonical v1 disposition", disposition=disposition)


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


def _recover_workstream_header(raw: bytes, path: str) -> tuple[str | None, str | None, str | None]:
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


def workstream_board_view(cwd: Path | str = ".", *, active_root: str = REFLECTION_ROOT,
                          trusted_ref: str | None = None) -> WorkstreamBoardView:
    """Read every active candidate, admitting compacted images only from a trusted ref.

    Without ``trusted_ref`` the projection remains predecessor-strict and
    therefore marks a compacted image malformed rather than treating an
    arbitrary structural rewrite as valid.  A supplied ref never trusts the
    worktree bytes: they must match the freshly classified committed blob.
    """
    root = Path(cwd).resolve()
    active = root / Path(active_root)
    candidates: dict[str, set[str]] = {}
    trusted_paths: dict[str, set[str]] = {}
    if active.is_symlink() or (active.exists() and not active.is_dir()):
        return WorkstreamBoardView((
            WorkstreamBoardItem(active_root, "malformed", None, None, None, None,
                                ReflectionDiagnostic("path", active_root, "active board root must be a regular directory", {})),
        ))
    if active.is_dir():
        for item in active.iterdir():
            candidates.setdefault(item.name, set()).add("worktree")
    if trusted_ref is not None:
        head = _commit(root, trusted_ref)
        if head is None:
            return WorkstreamBoardView((
                WorkstreamBoardItem(active_root, "malformed", None, None, None, None,
                                    ReflectionDiagnostic("git-ref", active_root, "trusted board ref does not resolve to a commit", {})),
            ))
        prefix = active_root.rstrip("/") + "/"
        for path in _git_tree_paths(root, head):
            if path.startswith(prefix):
                parts = PurePosixPath(path[len(prefix):]).parts
                if parts:
                    candidates.setdefault(parts[0], set()).add("trusted")
                    trusted_paths.setdefault(parts[0], set()).add(path)
    items: list[WorkstreamBoardItem] = []
    for name in sorted(candidates):
        candidate = active / name
        ledger_path = candidate / WORKSTREAM_LEDGER_NAME
        relative = (PurePosixPath(active_root) / name / WORKSTREAM_LEDGER_NAME).as_posix()
        if candidate.is_symlink() or ledger_path.is_symlink() or (candidate.exists() and not candidate.is_dir()):
            items.append(WorkstreamBoardItem(relative, "malformed", None, None, None, None,
                                              ReflectionDiagnostic("path", relative,
                                                                   "active candidate must be a regular ledger directory", {})))
            continue
        unexpected = sorted(
            {path.name for path in candidate.iterdir() if path.name != WORKSTREAM_LEDGER_NAME}
            if candidate.is_dir() else set()
        )
        extra_trusted_paths = sorted(trusted_paths.get(name, set()) - {relative})
        if unexpected or extra_trusted_paths:
            items.append(WorkstreamBoardItem(relative, "malformed", None, None, None, None,
                                              ReflectionDiagnostic("unsupported-reflection-format", relative,
                                                                   "active candidate permits only ledger.md",
                                                                   {"unexpected": unexpected, "trusted_paths": extra_trusted_paths})))
            continue
        if not ledger_path.is_file():
            items.append(WorkstreamBoardItem(relative, "malformed", None, None, None, None,
                                              ReflectionDiagnostic("missing-ledger", relative,
                                                                   "active candidate has no working-tree ledger.md", {})))
            continue
        raw = ledger_path.read_bytes()
        raw_digest = "sha256:" + sha256(raw).hexdigest()
        workstream, branch, schema = _recover_workstream_header(raw, relative)
        try:
            # A Git-backed board is a projection of classified committed
            # history, not a fast-path for predecessor-strict working bytes.
            # In particular, a strict-valid tail deletion must still traverse
            # the history classifier before it can become a valid board item.
            if trusted_ref is not None and schema == WORKSTREAM_LEDGER_SCHEMA and workstream is not None:
                trusted = load_trusted_workstream_ledger(root, trusted_ref=trusted_ref, ledger_path=relative)
                if trusted.raw != raw:
                    _fail("stale_ledger_digest", relative, "working-tree board bytes differ from trusted ref")
                ledger = trusted.ledger
            else:
                ledger = parse_workstream_ledger(raw, relative)
        except ReflectionValidationError as exc:
            status = "unsupported" if exc.diagnostic.code == "unsupported-reflection-format" else "malformed"
            items.append(WorkstreamBoardItem(relative, status, raw_digest, workstream, branch, None, exc.diagnostic))
            continue
        if candidate.name != ledger.header.workstream_id:
            items.append(WorkstreamBoardItem(relative, "malformed", raw_digest, ledger.header.workstream_id,
                                              ledger.header.working_branch, ledger.effective_branch,
                                              ReflectionDiagnostic("path", relative, "ledger directory must equal workstream_id", {})))
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
                ReflectionDiagnostic("branch-collision", item.path, "multiple active v1 ledgers claim one effective branch", {"branch": branch}),
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
    """Append the only v1 ownership transfer record after verified integration."""
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


def _plan_workstream_chain_close(ledger: WorkstreamLedger, *, chain_id: str, receipts: Iterable[AdmittedWorkstreamReceipt],
                                 receipt_verifier: WorkstreamReceiptVerifier,
                                 integration_witness: TrustedIntegrationWitness,
                                 integration_verifier: TrustedRebindVerifier,
                                 expected_head: str, actual_head: str, pre_ledger_digest: str, branch: str,
                                 conclusion: str, reasoning: str, source: str, confidence: str,
                                 clock: Callable[[], datetime] | None = None,
                                 verify_predecessors: bool = True) -> WorkstreamLedger:
    """Internal close planner; predecessor relaxation is loader-owned only."""
    _validate_workstream_ledger(ledger, "chain close", verify_predecessors=verify_predecessors)
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
    _validate_workstream_ledger(result, "chain close", verify_predecessors=verify_predecessors)
    return result


def plan_workstream_chain_close(ledger: WorkstreamLedger, *, chain_id: str, receipts: Iterable[AdmittedWorkstreamReceipt],
                                receipt_verifier: WorkstreamReceiptVerifier,
                                integration_witness: TrustedIntegrationWitness,
                                integration_verifier: TrustedRebindVerifier,
                                expected_head: str, actual_head: str, pre_ledger_digest: str, branch: str,
                                conclusion: str, reasoning: str, source: str, confidence: str,
                                clock: Callable[[], datetime] | None = None) -> WorkstreamLedger:
    """Create the post-integration orchestrator close record for a strict v1 ledger."""
    return _plan_workstream_chain_close(
        ledger, chain_id=chain_id, receipts=receipts, receipt_verifier=receipt_verifier,
        integration_witness=integration_witness, integration_verifier=integration_verifier,
        expected_head=expected_head, actual_head=actual_head, pre_ledger_digest=pre_ledger_digest, branch=branch,
        conclusion=conclusion, reasoning=reasoning, source=source, confidence=confidence, clock=clock,
    )


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


def _preview_workstream_expiry(ledger: WorkstreamLedger, *, expected_head: str, chain_ids: Iterable[str], now: datetime,
                                receipts: Iterable[AdmittedWorkstreamReceipt], receipt_verifier: WorkstreamReceiptVerifier,
                                integration_witness: TrustedIntegrationWitness,
                                integration_verifier: TrustedRebindVerifier,
                                early_approval: EarlyExpiryApproval | None = None,
                                early_approval_verifier: EarlyExpiryApprovalVerifier | None = None,
                                verify_predecessors: bool = True) -> WorkstreamExpiryPreview:
    _validate_workstream_ledger(ledger, "ledger expiry", verify_predecessors=verify_predecessors)
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
            if any(_workstream_receipt_is_promoted(receipt) for receipt in coverage.values()):
                _fail("early-expiry", "ledger expiry", "a promoted chain can never use early expiry", chain_id=chain)
            # The locator-only v1 approval and caller verifier cannot establish
            # host authority, complete-member binding, freshness, or replay.
            _fail("early-expiry", "ledger expiry",
                  "v1 early cleanup is disabled until canonical Git-admitted host-signed authorization is defined",
                  chain_id=chain)
        elif now.astimezone(timezone.utc) < _as_utc(closed_at) + timedelta(days=ledger.header.reflection_retention_days):
            _fail("expiry", "ledger expiry", "chain retention window has not elapsed", chain_id=chain)
    _validate_expiry_dependencies(ledger, set(selected))
    retained = tuple(entry for entry in ledger.entries if not (isinstance(entry, WorkstreamRecord) and entry.chain_id in set(selected)))
    post = WorkstreamLedger(ledger.header, retained)
    # The resulting image can only become readable through the trusted-history
    # admission proof.  Public parsing and validation remain predecessor-strict.
    _validate_compacted_workstream_ledger(post, "ledger expiry post-image")
    removed = tuple(sorted(record.record_id for record in ledger.records if record.chain_id in set(selected)))
    return WorkstreamExpiryPreview(expected_head, _append_pre_digest(ledger), selected, removed, _append_pre_digest(post), post)


def preview_workstream_expiry(ledger: WorkstreamLedger, *, expected_head: str, chain_ids: Iterable[str], now: datetime,
                               receipts: Iterable[AdmittedWorkstreamReceipt], receipt_verifier: WorkstreamReceiptVerifier,
                               integration_witness: TrustedIntegrationWitness,
                               integration_verifier: TrustedRebindVerifier,
                               early_approval: EarlyExpiryApproval | None = None,
                               early_approval_verifier: EarlyExpiryApprovalVerifier | None = None) -> WorkstreamExpiryPreview:
    """Preview expiry for a predecessor-strict v1 ledger image."""
    return _preview_workstream_expiry(
        ledger, expected_head=expected_head, chain_ids=chain_ids, now=now, receipts=receipts,
        receipt_verifier=receipt_verifier, integration_witness=integration_witness,
        integration_verifier=integration_verifier, early_approval=early_approval,
        early_approval_verifier=early_approval_verifier,
    )


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


# --- Trusted v1 compaction history ----------------------------------------
#
# A compacted image is intentionally not a second ledger format.  These types
# describe Git/session evidence for a single, already-rendered v1 image; all
# authority remains in the committed tree and ordinary session entry.

MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS = 4096
MAX_TRUSTED_LEDGER_CLASSIFICATIONS = 4096
MAX_TRUSTED_LEDGER_CLASSIFICATION_DEPTH = 32
TRUSTED_LEDGER_HISTORY_PAGE_SIZE = 128
TRUSTED_LEDGER_HISTORY_VERSION = 1
WORKSTREAM_COMPACTION_SCHEMA = "memory-seed/reflection-workstream-compaction"
WORKSTREAM_COMPACTION_FIELDS = (
    "schema", "version", "workstream_id", "ledger_path", "pre_ledger_digest", "post_ledger_digest",
    "pre_tip", "pre_blob", "cleanup_commit", "post_blob", "removed_chain_ids", "removed_record_ids",
    "closure_receipts", "member_receipts", "reason", "git_blobs_remain", "privacy_grade_erasure",
)
WORKSTREAM_COMPACTION_CLOSURE_FIELDS = (
    "chain_id", "closed_record_id", "closed_record_digest", "session_path", "entry_id", "decision_id",
    "commit", "blob", "receipt_digest",
)
WORKSTREAM_COMPACTION_MEMBER_FIELDS = (
    "chain_id", "record_id", "detail_digest", "session_path", "entry_id", "decision_id", "receipt_id",
    "receipt_digest", "commit", "blob", "disposition",
)


def _git_oid_40(value: Any, path: str, field_name: str) -> str:
    value = _text(value, path, field_name)
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        _fail("git-oid", path, "field must be a 40-character lowercase Git object ID", field=field_name, value=value)
    return value


def _compaction_entry_id(value: Any, path: str) -> str:
    value = _text(value, path, "entry_id")
    if not SESSION_ENTRY_ID_RE.fullmatch(value):
        _fail("compaction-proof", path, "entry_id is not a canonical session entry ID")
    return value


def _compaction_decision_id(value: Any, path: str) -> str:
    value = _text(value, path, "decision_id")
    if not SESSION_DECISION_ID_RE.fullmatch(value):
        _fail("compaction-proof", path, "decision_id is not a canonical session decision locator")
    return value


def _compaction_ledger_path(value: Any, path: str) -> str:
    value = _text(value, path, "ledger_path")
    candidate = PurePosixPath(value)
    if (candidate.is_absolute() or ".." in candidate.parts or "\\" in value or value != candidate.as_posix()
            or not value.startswith(f"{REFLECTION_ROOT}/") or not value.endswith(f"/{WORKSTREAM_LEDGER_NAME}")):
        _fail("compaction-proof", path, "ledger_path is not the canonical active v1 ledger path")
    return value


@dataclass(frozen=True)
class WorkstreamCompactionClosureReceipt:
    chain_id: str
    closed_record_id: str
    closed_record_digest: str
    session_path: str
    entry_id: str
    decision_id: str
    commit: str
    blob: str
    receipt_digest: str

    def as_dict(self) -> dict[str, str]:
        return {
            "chain_id": self.chain_id, "closed_record_id": self.closed_record_id,
            "closed_record_digest": self.closed_record_digest, "session_path": self.session_path,
            "entry_id": self.entry_id, "decision_id": self.decision_id, "commit": self.commit,
            "blob": self.blob, "receipt_digest": self.receipt_digest,
        }


@dataclass(frozen=True)
class WorkstreamCompactionMemberReceipt:
    chain_id: str
    record_id: str
    detail_digest: str
    session_path: str
    entry_id: str
    decision_id: str
    receipt_id: str
    receipt_digest: str
    commit: str
    blob: str
    disposition: str

    def as_dict(self) -> dict[str, str]:
        return {
            "chain_id": self.chain_id, "record_id": self.record_id, "detail_digest": self.detail_digest,
            "session_path": self.session_path, "entry_id": self.entry_id, "decision_id": self.decision_id,
            "receipt_id": self.receipt_id, "receipt_digest": self.receipt_digest, "commit": self.commit,
            "blob": self.blob, "disposition": self.disposition,
        }


@dataclass(frozen=True)
class WorkstreamCompactionReceipt:
    workstream_id: str
    ledger_path: str
    pre_ledger_digest: str
    post_ledger_digest: str
    pre_tip: str
    pre_blob: str
    cleanup_commit: str
    post_blob: str
    removed_chain_ids: tuple[str, ...]
    removed_record_ids: tuple[str, ...]
    closure_receipts: tuple[WorkstreamCompactionClosureReceipt, ...]
    member_receipts: tuple[WorkstreamCompactionMemberReceipt, ...]
    reason: str
    git_blobs_remain: bool = True
    privacy_grade_erasure: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": WORKSTREAM_COMPACTION_SCHEMA, "version": 1, "workstream_id": self.workstream_id,
            "ledger_path": self.ledger_path, "pre_ledger_digest": self.pre_ledger_digest,
            "post_ledger_digest": self.post_ledger_digest, "pre_tip": self.pre_tip, "pre_blob": self.pre_blob,
            "cleanup_commit": self.cleanup_commit, "post_blob": self.post_blob,
            "removed_chain_ids": list(self.removed_chain_ids), "removed_record_ids": list(self.removed_record_ids),
            "closure_receipts": [item.as_dict() for item in self.closure_receipts],
            "member_receipts": [item.as_dict() for item in self.member_receipts], "reason": self.reason,
            "git_blobs_remain": self.git_blobs_remain, "privacy_grade_erasure": self.privacy_grade_erasure,
        }


def _compaction_closure_from_dict(value: Any, path: str) -> WorkstreamCompactionClosureReceipt:
    if not isinstance(value, Mapping):
        _fail("compaction-proof", path, "closure receipt must be a mapping")
    _required(value, WORKSTREAM_COMPACTION_CLOSURE_FIELDS, path)
    _only(value, WORKSTREAM_COMPACTION_CLOSURE_FIELDS, path)
    return WorkstreamCompactionClosureReceipt(
        _id(value["chain_id"], "rlc_", path, "chain_id"), _id(value["closed_record_id"], "rlr_", path, "closed_record_id"),
        _digest(value["closed_record_digest"], path, "closed_record_digest"),
        _session_path(value["session_path"], path, "session_path"), _compaction_entry_id(value["entry_id"], path),
        _compaction_decision_id(value["decision_id"], path), _git_oid_40(value["commit"], path, "commit"),
        _git_oid_40(value["blob"], path, "blob"), _digest(value["receipt_digest"], path, "receipt_digest"),
    )


def _compaction_member_from_dict(value: Any, path: str) -> WorkstreamCompactionMemberReceipt:
    if not isinstance(value, Mapping):
        _fail("compaction-proof", path, "member receipt must be a mapping")
    _required(value, WORKSTREAM_COMPACTION_MEMBER_FIELDS, path)
    _only(value, WORKSTREAM_COMPACTION_MEMBER_FIELDS, path)
    disposition = _text(value["disposition"], path, "disposition")
    if disposition not in WORKSTREAM_RECEIPT_DISPOSITIONS:
        _fail("compaction-proof", path, "member receipt disposition is not canonical", disposition=disposition)
    return WorkstreamCompactionMemberReceipt(
        _id(value["chain_id"], "rlc_", path, "chain_id"), _id(value["record_id"], "rlr_", path, "record_id"),
        _digest(value["detail_digest"], path, "detail_digest"), _session_path(value["session_path"], path, "session_path"),
        _compaction_entry_id(value["entry_id"], path), _compaction_decision_id(value["decision_id"], path),
        _id(value["receipt_id"], "rrc_", path, "receipt_id"), _digest(value["receipt_digest"], path, "receipt_digest"),
        _git_oid_40(value["commit"], path, "commit"), _git_oid_40(value["blob"], path, "blob"), disposition,
    )


def _sorted_compaction(values: Iterable[Any], key: Callable[[Any], Any], path: str, field_name: str) -> tuple[Any, ...]:
    result = tuple(values)
    keys = tuple(key(item) for item in result)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        _fail("canonical-order", path, "receipt collection must be sorted and unique", field=field_name)
    return result


def workstream_compaction_receipt_from_dict(value: Mapping[str, Any], path: str = "compaction.yaml") -> WorkstreamCompactionReceipt:
    _required(value, WORKSTREAM_COMPACTION_FIELDS, path)
    _only(value, WORKSTREAM_COMPACTION_FIELDS, path)
    if value["schema"] != WORKSTREAM_COMPACTION_SCHEMA or value["version"] != 1:
        _fail("compaction-proof", path, "unsupported compaction receipt schema/version")
    chains_value, records_value = value["removed_chain_ids"], value["removed_record_ids"]
    if not isinstance(chains_value, list) or not isinstance(records_value, list):
        _fail("compaction-proof", path, "removed IDs must be canonical lists")
    chains = _sorted_unique([_id(item, "rlc_", path, "removed_chain_ids") for item in chains_value], path, "removed_chain_ids")
    records = _sorted_unique([_id(item, "rlr_", path, "removed_record_ids") for item in records_value], path, "removed_record_ids")
    closures_value, members_value = value["closure_receipts"], value["member_receipts"]
    if not isinstance(closures_value, list) or not isinstance(members_value, list) or not closures_value or not members_value:
        _fail("compaction-proof", path, "compaction receipt requires closure and member receipt coverage")
    closures = _sorted_compaction((_compaction_closure_from_dict(item, path) for item in closures_value),
                                  lambda item: item.chain_id, path, "closure_receipts")
    members = _sorted_compaction((_compaction_member_from_dict(item, path) for item in members_value),
                                 lambda item: (item.chain_id, item.record_id), path, "member_receipts")
    if value["git_blobs_remain"] is not True or value["privacy_grade_erasure"] is not False:
        _fail("compaction-proof", path, "compaction disclosure must state Git blob retention and no privacy erasure")
    return WorkstreamCompactionReceipt(
        _id(value["workstream_id"], "rwl_", path, "workstream_id"), _compaction_ledger_path(value["ledger_path"], path),
        _digest(value["pre_ledger_digest"], path, "pre_ledger_digest"), _digest(value["post_ledger_digest"], path, "post_ledger_digest"),
        _git_oid_40(value["pre_tip"], path, "pre_tip"), _git_oid_40(value["pre_blob"], path, "pre_blob"),
        _git_oid_40(value["cleanup_commit"], path, "cleanup_commit"), _git_oid_40(value["post_blob"], path, "post_blob"),
        chains, records, closures, members, _text(value["reason"], path, "reason"), True, False,
    )


def render_workstream_compaction_receipt(receipt: WorkstreamCompactionReceipt) -> str:
    parsed = workstream_compaction_receipt_from_dict(receipt.as_dict())
    values = parsed.as_dict()
    return _workstream_yaml_mapping([(name, values[name]) for name in WORKSTREAM_COMPACTION_FIELDS])


def parse_workstream_compaction_receipt(raw: bytes | str, path: str = "compaction.yaml") -> WorkstreamCompactionReceipt:
    text = _canonical_text(raw, path)
    receipt = workstream_compaction_receipt_from_dict(_parse_yaml_mapping(text, path), path)
    if render_workstream_compaction_receipt(receipt) != text:
        _fail("canonical-bytes", path, "compaction receipt is not canonical")
    return receipt


def _raw_workstream_blocks(raw: bytes, path: str) -> tuple[bytes, tuple[bytes, ...]]:
    """Return raw immutable header/block spans without re-rendering them."""
    text = _canonical_text(raw, path)
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        _fail("compaction-proof", path, "ledger has no canonical header span")
    prefix = text[:end + 5].encode("utf-8")
    body = text[end + 5:]
    if not body:
        return prefix, ()
    if not body.startswith("\n"):
        _fail("compaction-proof", path, "ledger blocks lack canonical header separator")
    body = body[1:]
    starts = list(re.finditer(r"^## (?:Record|Rebind) [^\n]+\n", body, re.MULTILINE))
    if not starts or starts[0].start() != 0:
        _fail("compaction-proof", path, "ledger block scanner found noncanonical body")
    blocks: list[bytes] = []
    for index, match in enumerate(starts):
        stop = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        part = body[match.start():stop]
        if index + 1 < len(starts):
            if not part.endswith("\n\n"):
                _fail("compaction-proof", path, "intermediate block separator is not canonical")
            part = part[:-1]
        if not part.endswith("\n"):
            _fail("compaction-proof", path, "block has no final LF")
        blocks.append(part.encode("utf-8"))
    return prefix, tuple(blocks)


def _derive_compaction_post_bytes(pre_raw: bytes, pre_ledger: WorkstreamLedger, removed_chain_ids: Iterable[str], path: str) -> bytes:
    """Remove whole record-chain spans while preserving every survivor byte."""
    selected = set(removed_chain_ids)
    prefix, blocks = _raw_workstream_blocks(pre_raw, path)
    if len(blocks) != len(pre_ledger.entries):
        _fail("compaction-proof", path, "raw block scanner and parsed ledger disagree")
    retained: list[bytes] = []
    for entry, block in zip(pre_ledger.entries, blocks):
        if isinstance(entry, TrustedRebind):
            retained.append(block)
        elif entry.chain_id not in selected:
            retained.append(block)
    if not retained:
        return prefix
    return prefix + b"\n" + b"\n".join(retained)


@dataclass(frozen=True)
class WorkstreamCompactionProof:
    receipt: WorkstreamCompactionReceipt
    receipt_commit: str
    receipt_session_path: str
    receipt_blob: str
    entry_id: str


@dataclass(frozen=True)
class NormalTrustedLedger:
    repository: str
    trusted_ref: str
    head: str
    ledger_path: str
    ledger_blob: str
    raw: bytes
    ledger: WorkstreamLedger
    history_fingerprint: str
    validation: str = "normal"


@dataclass(frozen=True)
class AdmittedCompactedLedger:
    repository: str
    trusted_ref: str
    head: str
    ledger_path: str
    ledger_blob: str
    raw: bytes
    ledger: WorkstreamLedger
    history_fingerprint: str
    proofs: tuple[WorkstreamCompactionProof, ...]
    suffix_record_ids: tuple[str, ...]
    validation: str = "admitted-compaction"


TrustedWorkstreamLedger = NormalTrustedLedger | AdmittedCompactedLedger


@dataclass(frozen=True)
class _LedgerTransition:
    commit: str
    parent: str
    parent_blob: GitBlob
    blob: GitBlob


@lru_cache(maxsize=32768)
def _cached_git_commit_parents(repository: str, commit: str) -> tuple[str, ...]:
    root = Path(repository)
    code, output = _git(root, "rev-list", "--parents", "-n", "1", commit)
    fields = output.split() if code == 0 and isinstance(output, str) else []
    if not fields or fields[0] != commit or any(not re.fullmatch(r"[0-9a-f]{40}", field) for field in fields):
        _fail("compaction-proof-history-missing", str(root), "could not resolve Git commit parents", commit=commit)
    return tuple(fields[1:])


def _git_commit_parents(root: Path, commit: str) -> tuple[str, ...]:
    return _cached_git_commit_parents(str(root.resolve()), commit)


@lru_cache(maxsize=32768)
def _cached_git_is_ancestor(repository: str, ancestor: str, descendant: str) -> bool:
    root = Path(repository)
    code, _output = _git(root, "merge-base", "--is-ancestor", ancestor, descendant)
    return code == 0


def _git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return _cached_git_is_ancestor(str(root.resolve()), ancestor, descendant)


@lru_cache(maxsize=32768)
def _cached_git_changed_tree_paths(repository: str, parent: str, child: str) -> tuple[str, ...]:
    root = Path(repository)
    code, output = _git(root, "diff-tree", "--no-commit-id", "-r", "--name-only", "-z", parent, child, binary=True)
    if code or not isinstance(output, bytes):
        _fail("compaction-proof-tree", str(root), "could not inspect restricted Git tree diff")
    fields = tuple(item for item in output.decode("utf-8", errors="strict").split("\0") if item)
    return fields


def _git_changed_tree_paths(root: Path, parent: str, child: str) -> tuple[str, ...]:
    return _cached_git_changed_tree_paths(str(root.resolve()), parent, child)


@lru_cache(maxsize=32768)
def _cached_git_tree_paths(repository: str, commit: str) -> tuple[str, ...]:
    root = Path(repository)
    code, output = _git(root, "ls-tree", "-r", "-z", "--name-only", commit, "--", REFLECTION_ROOT, binary=True)
    if code or not isinstance(output, bytes):
        _fail("dependency-context", str(root), "could not enumerate the trusted active-ledger board", commit=commit)
    return tuple(item for item in output.decode("utf-8", errors="strict").split("\0") if item)


def _git_tree_paths(root: Path, commit: str) -> tuple[str, ...]:
    return _cached_git_tree_paths(str(root.resolve()), commit)


@lru_cache(maxsize=32768)
def _cached_git_commit_message(repository: str, commit: str) -> str:
    root = Path(repository)
    code, output = _git(root, "show", "-s", "--format=%B", commit)
    if code or not isinstance(output, str):
        _fail("compaction-proof-session", str(root), "could not read receipt commit message", commit=commit)
    return output


def _git_commit_message(root: Path, commit: str) -> str:
    return _cached_git_commit_message(str(root.resolve()), commit)


def clear_trusted_workstream_history_cache() -> None:
    """Discard derived Git-object caches; never touches authoritative files."""
    for cached in (_cached_tree_blob, _cached_git_commit_parents, _cached_git_is_ancestor,
                   _cached_git_changed_tree_paths, _cached_git_tree_paths, _cached_git_commit_message):
        cached.cache_clear()


def _require_memory_entry_trailer(root: Path, commit: str, entry_id: str) -> None:
    message = _git_commit_message(root, commit).rstrip()
    trailers = re.findall(r"(?m)^Memory-Entry: ([^\n]+)$", message)
    if trailers != [entry_id] or not message.endswith(f"Memory-Entry: {entry_id}"):
        _fail("compaction-proof-session", "commit message", "receipt commit needs one final matching Memory-Entry trailer",
              commit=commit, entry_id=entry_id)


def _session_compaction_entries(raw: bytes, path: str) -> tuple[tuple[str, WorkstreamCompactionReceipt], ...]:
    """Find canonical receipt fences within individually identified session entries."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("compaction-proof-session", path, "session receipt is not UTF-8", reason=str(exc))
    if "\r" in text or unicodedata.normalize("NFC", text) != text:
        _fail("compaction-proof-session", path, "session receipt must use NFC UTF-8 and LF")
    starts = list(re.finditer(r"^## [^\n]+\n\n```yaml\n(?P<meta>.*?)```\n", text, re.MULTILINE | re.DOTALL))
    result: list[tuple[str, WorkstreamCompactionReceipt]] = []
    for index, start in enumerate(starts):
        stop = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        try:
            metadata = _parse_yaml_mapping(start.group("meta"), path)
        except ReflectionValidationError:
            continue
        entry_id = metadata.get("entry_id")
        if not isinstance(entry_id, str) or not SESSION_ENTRY_ID_RE.fullmatch(entry_id):
            continue
        # Re-resolve through the same exact locator path used by member and
        # closure evidence.  A duplicate entry ID or malformed session cannot
        # smuggle a cleanup proof through this broader scanner.
        entry = _session_entry_scope(raw, path, entry_id)
        fences = list(re.finditer(r"^### Reflection workstream compaction\n\n```yaml\n(?P<body>.*?)```\n",
                                entry, re.MULTILINE | re.DOTALL))
        if len(fences) > 1:
            _fail("compaction-proof-session", path, "session entry has multiple compaction receipts", entry_id=entry_id)
        if not fences:
            continue
        body = fences[0].group("body")
        receipt = parse_workstream_compaction_receipt(body, path)
        result.append((entry_id, receipt))
    return tuple(result)


def _session_has_exact_yaml_mapping(raw: bytes, path: str, expected: Mapping[str, Any], *,
                                    entry_id: str, decision_id: str) -> bool:
    """Match one exact evidence mapping only inside its cited normal decision.

    Session blobs are append-only evidence containers, not an unscoped YAML
    database.  A lookalike mapping elsewhere in the file cannot authorise a
    member or closure locator.
    """
    try:
        text = _session_decision_scope(_session_entry_scope(raw, path, entry_id), path, entry_id, decision_id)
    except ReflectionValidationError:
        return False
    for fence in re.finditer(r"```yaml\n(?P<body>.*?)```", text, re.DOTALL):
        try:
            value = _parse_yaml_mapping(fence.group("body"), path)
        except ReflectionValidationError:
            continue
        if value == dict(expected):
            return True
    return False


def _member_session_mapping(workstream_id_value: str, receipt: WorkstreamCompactionMemberReceipt) -> dict[str, str]:
    return {
        "workstream_id": workstream_id_value, "chain_id": receipt.chain_id, "record_id": receipt.record_id,
        "detail_digest": receipt.detail_digest, "session_path": receipt.session_path, "entry_id": receipt.entry_id,
        "decision_id": receipt.decision_id, "receipt_id": receipt.receipt_id, "receipt_digest": receipt.receipt_digest,
        "disposition": receipt.disposition,
    }


def _closure_session_mapping(receipt: WorkstreamCompactionClosureReceipt) -> dict[str, str]:
    return {
        "chain_id": receipt.chain_id, "closed_record_id": receipt.closed_record_id,
        "closed_record_digest": receipt.closed_record_digest, "session_path": receipt.session_path,
        "entry_id": receipt.entry_id, "decision_id": receipt.decision_id, "receipt_digest": receipt.receipt_digest,
    }


def _read_session_blob(root: Path, commit: str, session_path: str, blob: str, *, before: str) -> bytes:
    if not _git_is_ancestor(root, commit, before):
        _fail("compaction-proof-reachability", session_path, "receipt session commit is not reachable before cleanup", commit=commit)
    item = _tree_blob(root, commit, session_path)
    if item is None or item.mode != CANONICAL_MODE or item.oid != blob:
        _fail("compaction-proof-session", session_path, "receipt session locator does not bind its committed blob")
    return item.content


def _validate_compaction_coverage(root: Path, receipt: WorkstreamCompactionReceipt, pre_ledger: WorkstreamLedger,
                                  cleanup_commit: str) -> None:
    records_by_id = {record.record_id: record for record in pre_ledger.records}
    chains = _records_by_chain(pre_ledger)
    selected = set(receipt.removed_chain_ids)
    expected_ids = tuple(sorted(record.record_id for chain in selected for record in chains.get(chain, ())))
    if not selected or tuple(receipt.removed_record_ids) != expected_ids:
        _fail("compaction-proof-coverage", receipt.ledger_path, "removed record IDs are not exactly the selected complete chains")
    if any(chain not in chains for chain in selected):
        _fail("compaction-proof-coverage", receipt.ledger_path, "receipt names an unknown removed chain")
    expected_closures: dict[str, WorkstreamRecord] = {}
    for chain in selected:
        chain_records = chains[chain]
        close = chain_records[-1]
        if close.to_phase != "closed" or close.closed_at is None:
            _fail("compaction-proof-coverage", receipt.ledger_path, "removed chain is not closed", chain_id=chain)
        expected_closures[chain] = close
    if {item.chain_id for item in receipt.closure_receipts} != selected:
        _fail("compaction-proof-coverage", receipt.ledger_path, "closure receipts do not cover every removed chain")
    if {(item.chain_id, item.record_id) for item in receipt.member_receipts} != {
        (record.chain_id, record.record_id) for record in records_by_id.values() if record.chain_id in selected
    }:
        _fail("compaction-proof-coverage", receipt.ledger_path, "member receipts do not cover every removed record")
    for closure in receipt.closure_receipts:
        close = expected_closures[closure.chain_id]
        if closure.closed_record_id != close.record_id or closure.closed_record_digest != close.detail_digest:
            _fail("compaction-proof-coverage", receipt.ledger_path, "closure receipt does not bind the closed chain head")
        raw = _read_session_blob(root, closure.commit, closure.session_path, closure.blob, before=cleanup_commit)
        if not _session_has_exact_yaml_mapping(raw, closure.session_path, _closure_session_mapping(closure),
                                               entry_id=closure.entry_id, decision_id=closure.decision_id):
            _fail("compaction-proof-session", closure.session_path, "committed session lacks exact closure receipt")
    for member in receipt.member_receipts:
        record = records_by_id.get(member.record_id)
        if record is None or record.chain_id != member.chain_id or record.detail_digest != member.detail_digest:
            _fail("compaction-proof-coverage", receipt.ledger_path, "member receipt does not bind a removed record")
        raw = _read_session_blob(root, member.commit, member.session_path, member.blob, before=cleanup_commit)
        if not _session_has_exact_yaml_mapping(raw, member.session_path, _member_session_mapping(receipt.workstream_id, member),
                                               entry_id=member.entry_id, decision_id=member.decision_id):
            _fail("compaction-proof-session", member.session_path, "committed session lacks exact member receipt")


def _validate_historical_compaction_retention(root: Path, receipt: WorkstreamCompactionReceipt,
                                              pre_ledger: WorkstreamLedger, receipt_commit: str,
                                              cleanup_commit: str) -> None:
    """Fail closed until elapsed time or early-cleanup authority is replayable.

    Git author/committer dates are caller-controlled, even in immutable commits.
    Session mappings likewise prove recorded bytes, never live-user authority.
    The frozen v1 contract defines no external elapsed-time anchor or canonical
    host-signed early-cleanup authorization. Neither can be invented here.

    A future authorization must bind the workstream, chain, complete member IDs
    and detail digests, close record, scoped session entry/decision, short-lived
    host timestamp, immutable trust anchor, and replay identity, and must be
    reloaded from admitted Git evidence. Until then every historical cleanup,
    including apparently old or promoted cleanup, remains inadmissible.
    """
    _fail("compaction-proof-retention", receipt.ledger_path,
          "v1 historical cleanup is disabled: no trusted elapsed-time anchor or replay-verified host authorization",
          cleanup_commit=cleanup_commit, receipt_commit=receipt_commit)


def _trusted_active_ledgers_at_commit(root: Path, commit: str) -> tuple[tuple[str, WorkstreamLedger], ...]:
    """Build the entire v1 board from one immutable Git tree, fail closed."""
    prefix = REFLECTION_ROOT + "/"
    candidates: dict[str, set[str]] = {}
    for path in _git_tree_paths(root, commit):
        if not path.startswith(prefix):
            continue
        suffix = path[len(prefix):]
        parts = PurePosixPath(suffix).parts
        if not parts:
            continue
        candidates.setdefault(parts[0], set()).add(path)
    if len(candidates) > MAX_TRUSTED_LEDGER_CLASSIFICATIONS:
        _fail("dependency-context-limit", str(root), "trusted active board exceeds its bounded candidate limit")
    ledgers: list[tuple[str, WorkstreamLedger]] = []
    branches: dict[str, str] = {}
    for directory, paths in sorted(candidates.items()):
        ledger_path = (PurePosixPath(REFLECTION_ROOT) / directory / WORKSTREAM_LEDGER_NAME).as_posix()
        if paths != {ledger_path}:
            _fail("unsupported-reflection-format", ledger_path, "trusted active candidate permits only ledger.md",
                  paths=sorted(paths))
        blob = _tree_blob(root, commit, ledger_path)
        if blob is None or blob.mode != CANONICAL_MODE:
            _fail("dependency-context", ledger_path, "trusted active board ledger is not a regular blob")
        workstream_id, _branch, schema = _recover_workstream_header(blob.content, ledger_path)
        if schema != WORKSTREAM_LEDGER_SCHEMA or workstream_id is None:
            _fail("dependency-context", ledger_path, "trusted active board has an unsupported or malformed v1 ledger")
        # Strict-valid bytes can still hide a raw tail/sole-chain deletion.
        # Every candidate, including the cleanup target's pre-image, must pass
        # lineage classification at this exact pre-cleanup commit.
        ledger = load_trusted_workstream_ledger(root, trusted_ref=commit, ledger_path=ledger_path).ledger
        if directory != ledger.header.workstream_id:
            _fail("dependency-context", ledger_path, "trusted board ledger directory and workstream ID differ")
        owner = branches.get(ledger.effective_branch)
        if owner is not None:
            _fail("dependency-context", ledger_path, "trusted active board has multiple effective owners", branch=ledger.effective_branch)
        branches[ledger.effective_branch] = ledger_path
        ledgers.append((ledger_path, ledger))
    return tuple(ledgers)


def _validate_compaction_incoming_dependencies(root: Path, receipt: WorkstreamCompactionReceipt,
                                                pre_ledger: WorkstreamLedger, cleanup_commit: str) -> None:
    """Refuse cleanup while a trusted open cross-workstream dependent is naked.

    The pre-cleanup tree is the mandatory active-ledger/board context.  A
    fallback is accepted only when its exact durable locator is one of the
    receipt members whose session evidence has already been admitted.
    """
    removed = {record.record_id for record in pre_ledger.records if record.chain_id in receipt.removed_chain_ids}
    members = tuple(receipt.member_receipts)
    for ledger_path, ledger in _trusted_active_ledgers_at_commit(root, cleanup_commit):
        if ledger_path == receipt.ledger_path:
            continue
        for record in ledger.records:
            if record.to_phase == "closed":
                continue
            for dependency in record.depends_on:
                if dependency.workstream_id != receipt.workstream_id or dependency.record_id not in removed:
                    continue
                if dependency.receipt is None:
                    _fail("dependency", receipt.ledger_path,
                          "open cross-workstream dependent lacks a verified fallback before cleanup",
                          dependent_workstream=ledger.header.workstream_id, record_id=record.record_id)
                candidates = [
                    member for member in members
                    if member.record_id == dependency.record_id and member.detail_digest == dependency.record_digest
                    and WorkstreamDependencyReceipt(member.session_path, member.entry_id, member.decision_id,
                                                   member.receipt_id, member.receipt_digest) == dependency.receipt
                ]
                if len(candidates) != 1:
                    _fail("dependency", receipt.ledger_path,
                          "open cross-workstream dependency fallback is not one admitted cleanup member receipt",
                          dependent_workstream=ledger.header.workstream_id, record_id=record.record_id)


def _session_compaction_candidates(root: Path, trusted_head: str, base_sha: str) -> tuple[tuple[WorkstreamCompactionReceipt, str, str, str], ...]:
    """Scan only committed ordinary-session changes reachable from the trusted head."""
    code, output = _git(root, "rev-list", "--reverse", f"{base_sha}..{trusted_head}")
    commits = output.splitlines() if code == 0 and isinstance(output, str) else []
    if len(commits) > MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS:
        _fail("compaction-proof-history-limit", str(root), "session proof scan exceeds the bounded history limit")
    result: list[tuple[WorkstreamCompactionReceipt, str, str, str]] = []
    for commit in commits:
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            _fail("compaction-proof-history-missing", str(root), "history scan returned an invalid commit")
        parents = _git_commit_parents(root, commit)
        if len(parents) != 1:
            continue
        for changed in _git_changed_tree_paths(root, parents[0], commit):
            if not changed.startswith(SESSION_ROOT):
                continue
            blob = _tree_blob(root, commit, changed)
            if blob is None or blob.mode != CANONICAL_MODE:
                continue
            parent_blob = _tree_blob(root, parents[0], changed)
            if parent_blob is not None and parent_blob.mode != CANONICAL_MODE:
                _fail("compaction-proof-session", changed, "prior ordinary-session entry is not a regular Git blob")
            prior = set(_session_compaction_entries(parent_blob.content, changed)) if parent_blob is not None else set()
            # A later edit to the same session file must not re-admit every
            # historic receipt it happens to carry.  Only the canonical receipt
            # entry introduced by this exact commit is a candidate proof.
            for entry_id, receipt in _session_compaction_entries(blob.content, changed):
                if (entry_id, receipt) in prior:
                    continue
                result.append((receipt, commit, changed, entry_id))
    return tuple(result)


def _ledger_lineage(root: Path, head: str, ledger_path: str) -> tuple[str, GitBlob, tuple[_LedgerTransition, ...]]:
    """Follow the one allowed ledger-bearing parent chain, newest to genesis."""
    current = head
    reverse: list[_LedgerTransition] = []
    seen: set[str] = set()
    while True:
        if current in seen:
            _fail("compaction-proof-history-ambiguous", ledger_path, "ledger Git lineage contains a cycle")
        seen.add(current)
        blob = _tree_blob(root, current, ledger_path)
        if blob is None:
            _fail("compaction-proof-history-missing", ledger_path, "trusted head lacks the active ledger path", head=current)
        if blob.mode != CANONICAL_MODE:
            _fail("mode", ledger_path, "trusted ledger must be a regular 100644 Git blob", mode=blob.mode)
        parents = _git_commit_parents(root, current)
        if not parents:
            return current, blob, tuple(reversed(reverse))
        parent_blobs = [(parent, _tree_blob(root, parent, ledger_path)) for parent in parents]
        ledger_parents = [(parent, item) for parent, item in parent_blobs if item is not None]
        if len(parents) > 1:
            if len(ledger_parents) != 1:
                _fail("compaction-proof-history-ambiguous", ledger_path,
                      "merge must have exactly one ledger-bearing parent", commit=current)
            parent, parent_blob = ledger_parents[0]
        else:
            parent, parent_blob = parent_blobs[0]
        if parent_blob is None:
            return current, blob, tuple(reversed(reverse))
        if parent_blob.mode != CANONICAL_MODE:
            _fail("mode", ledger_path, "ledger parent must be a regular 100644 Git blob", mode=parent_blob.mode)
        if parent_blob.oid != blob.oid:
            reverse.append(_LedgerTransition(current, parent, parent_blob, blob))
            if len(reverse) > MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS:
                _fail("compaction-proof-history-limit", ledger_path, "ledger history exceeds the bounded transition limit")
        current = parent


def _parse_initial_trusted_ledger(raw: bytes, path: str) -> WorkstreamLedger:
    ledger = parse_workstream_ledger(raw, path)
    if ledger.entries:
        _fail("compaction-proof-history-missing", path, "the first committed v1 image must be the canonical header-only init")
    return ledger


def _append_transition_ledger(parent_raw: bytes, parent_ledger: WorkstreamLedger, child_raw: bytes, path: str,
                              *, admitted: bool) -> WorkstreamLedger | None:
    """Return a canonical one-block suffix result, never a structural rewrite."""
    if not child_raw.startswith(parent_raw):
        return None
    try:
        child = _parse_compacted_workstream_ledger(child_raw, path) if admitted else parse_workstream_ledger(child_raw, path)
    except ReflectionValidationError:
        return None
    if child.header != parent_ledger.header or len(child.entries) != len(parent_ledger.entries) + 1:
        return None
    if child.entries[:-1] != parent_ledger.entries:
        return None
    if child.entries[-1].pre_ledger_digest != workstream_ledger_digest(parent_raw):
        return None
    return child


def _history_fingerprint(init_commit: str, head: str, ledger_path: str,
                         facts: Iterable[tuple[str, str, str, str, str, str, str, str]]) -> str:
    payload = {
        "version": TRUSTED_LEDGER_HISTORY_VERSION, "init": init_commit, "head": head, "path": ledger_path,
        "transitions": list(facts),
    }
    return "sha256:" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_cleanup_pair(root: Path, transition: _LedgerTransition, receipt: WorkstreamCompactionReceipt,
                           receipt_commit: str, receipt_path: str, entry_id: str,
                           pre_ledger: WorkstreamLedger, post_raw: bytes) -> WorkstreamCompactionProof:
    ledger_path = transition.blob.path
    if receipt.ledger_path != ledger_path or receipt.workstream_id != pre_ledger.header.workstream_id:
        _fail("compaction-proof-binding", ledger_path, "receipt does not bind this ledger path and workstream")
    if receipt.pre_tip != transition.parent or receipt.cleanup_commit != transition.commit:
        _fail("compaction-proof-binding", ledger_path, "receipt pre_tip or cleanup_commit does not bind this lineage transition")
    if receipt.pre_blob != transition.parent_blob.oid or receipt.post_blob != transition.blob.oid:
        _fail("compaction-proof-binding", ledger_path, "receipt blob OIDs do not bind this lineage transition")
    if receipt.pre_ledger_digest != workstream_ledger_digest(transition.parent_blob.content):
        _fail("compaction-proof-binding", ledger_path, "receipt pre-image digest does not match the committed blob")
    if receipt.post_ledger_digest != workstream_ledger_digest(post_raw):
        _fail("compaction-proof-binding", ledger_path, "receipt post-image digest does not match the committed blob")
    if _git_commit_parents(root, transition.commit) != (transition.parent,):
        _fail("compaction-proof-tree", ledger_path, "cleanup commit must have the exact pre-tip as its sole parent")
    if _git_changed_tree_paths(root, transition.parent, transition.commit) != (ledger_path,):
        _fail("compaction-proof-tree", ledger_path, "cleanup commit must change only ledger.md")
    if _git_commit_parents(root, receipt_commit) != (transition.commit,):
        _fail("compaction-proof-tree", receipt_path, "receipt commit must be the sole direct child of cleanup")
    if _git_changed_tree_paths(root, transition.commit, receipt_commit) != (receipt_path,):
        _fail("compaction-proof-tree", receipt_path, "receipt commit must change only its ordinary session path")
    receipt_blob = _tree_blob(root, receipt_commit, receipt_path)
    if receipt_blob is None or receipt_blob.mode != CANONICAL_MODE:
        _fail("compaction-proof-session", receipt_path, "receipt commit lacks its regular session blob")
    _require_memory_entry_trailer(root, receipt_commit, entry_id)
    expected_post = _derive_compaction_post_bytes(transition.parent_blob.content, pre_ledger, receipt.removed_chain_ids, ledger_path)
    if expected_post != post_raw:
        _fail("compaction-proof-derivation", ledger_path, "committed post-image is not the exact canonical raw-block removal")
    _validate_compaction_coverage(root, receipt, pre_ledger, transition.commit)
    _validate_compaction_incoming_dependencies(root, receipt, pre_ledger, transition.parent)
    _validate_historical_compaction_retention(root, receipt, pre_ledger, receipt_commit, transition.commit)
    post_ledger = _parse_compacted_workstream_ledger(post_raw, ledger_path)
    if post_ledger.header != pre_ledger.header:
        _fail("compaction-proof-derivation", ledger_path, "compaction changed immutable header bytes")
    return WorkstreamCompactionProof(receipt, receipt_commit, receipt_path, receipt_blob.oid, entry_id)


def _admit_compaction_transition(root: Path, trusted_head: str, transition: _LedgerTransition,
                                 pre_ledger: WorkstreamLedger, candidates: Iterable[tuple[WorkstreamCompactionReceipt, str, str, str]],
                                 used: set[tuple[str, str, str]]) -> WorkstreamCompactionProof:
    matching = [candidate for candidate in candidates if candidate[0].pre_tip == transition.parent
                and candidate[0].cleanup_commit == transition.commit and candidate[0].ledger_path == transition.blob.path]
    if not matching:
        _fail("compaction-proof-missing", transition.blob.path, "non-monotonic ledger transition has no unique reachable cleanup receipt")
    if len(matching) != 1:
        _fail("compaction-proof-ambiguous", transition.blob.path, "non-monotonic ledger transition has conflicting cleanup receipts")
    receipt, receipt_commit, receipt_path, entry_id = matching[0]
    identity = (receipt_commit, receipt_path, entry_id)
    if identity in used:
        _fail("compaction-proof-replay", transition.blob.path, "a compaction receipt locator cannot authorise two transitions")
    if not _git_is_ancestor(root, receipt_commit, trusted_head):
        _fail("compaction-proof-reachability", receipt_path, "receipt commit is not reachable from trusted head")
    proof = _validate_cleanup_pair(root, transition, receipt, receipt_commit, receipt_path, entry_id,
                                   pre_ledger, transition.blob.content)
    used.add(identity)
    return proof


@dataclass
class _TrustedLedgerClassificationContext:
    """Operation-local memoization, never caller-provided trust evidence."""

    in_progress: set[tuple[str, str, str, str]] = field(default_factory=set)
    completed: dict[tuple[str, str, str, str], TrustedWorkstreamLedger] = field(default_factory=dict)
    classifications: int = 0


_TRUSTED_LEDGER_CLASSIFICATION_CONTEXT: ContextVar[_TrustedLedgerClassificationContext | None] = ContextVar(
    "trusted_ledger_classification_context", default=None,
)


def load_trusted_workstream_ledger(cwd: Path | str, *, trusted_ref: str, ledger_path: str) -> TrustedWorkstreamLedger:
    """Load only a committed, history-classified v1 ledger from a host-selected ref.

    The caller never supplies raw proof bytes or a predecessor-validation mode.
    A strict-valid deletion is deliberately *not* normal: all path transitions
    are classified before a result is returned.
    """
    root = Path(cwd).resolve()
    if not isinstance(trusted_ref, str) or not trusted_ref or not isinstance(ledger_path, str):
        _fail("compaction-proof-history-missing", str(root), "trusted ref and canonical ledger path are required")
    head = _commit(root, trusted_ref)
    if head is None:
        _fail("compaction-proof-history-missing", ledger_path, "trusted ledger ref does not resolve to a commit", trusted_ref=trusted_ref)
    context = _TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.get()
    token = None
    if context is None:
        context = _TrustedLedgerClassificationContext()
        token = _TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.set(context)
    key = (str(root), trusted_ref, head, ledger_path)
    try:
        if key in context.completed:
            return context.completed[key]
        if key in context.in_progress:
            _fail("dependency-context-cycle", ledger_path, "trusted board history classification contains a cycle", commit=head)
        if (len(context.in_progress) >= MAX_TRUSTED_LEDGER_CLASSIFICATION_DEPTH
                or context.classifications >= MAX_TRUSTED_LEDGER_CLASSIFICATIONS):
            _fail("dependency-context-limit", ledger_path, "trusted board history classification exceeds its bounded context")
        context.in_progress.add(key)
        context.classifications += 1
        try:
            result = _classify_trusted_workstream_ledger(root, trusted_ref, head, ledger_path)
            context.completed[key] = result
            return result
        finally:
            context.in_progress.remove(key)
    finally:
        if token is not None:
            _TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.reset(token)


def _classify_trusted_workstream_ledger(root: Path, trusted_ref: str, head: str,
                                       ledger_path: str) -> TrustedWorkstreamLedger:
    """Classify one immutable image within the loader's bounded board context."""
    initial_commit, initial_blob, transitions = _ledger_lineage(root, head, ledger_path)
    initial = _parse_initial_trusted_ledger(initial_blob.content, ledger_path)
    if ledger_path != workstream_ledger_path(initial.header.workstream_id):
        _fail("path", ledger_path, "trusted ledger path does not equal its immutable workstream ID")
    if not _git_is_ancestor(root, initial.header.base_sha, head):
        _fail("compaction-proof-history-missing", ledger_path, "ledger immutable base is not an ancestor of trusted head")
    candidates = _session_compaction_candidates(root, head, initial.header.base_sha)
    current_raw, current_ledger, admitted = initial_blob.content, initial, False
    proofs: list[WorkstreamCompactionProof] = []
    suffix_record_ids: list[str] = []
    facts: list[tuple[str, str, str, str, str, str, str, str]] = []
    used: set[tuple[str, str, str]] = set()
    for transition in transitions:
        if transition.parent_blob.content != current_raw:
            _fail("compaction-proof-history-ambiguous", ledger_path, "ledger transition is not continuous with its classified parent")
        appended = _append_transition_ledger(current_raw, current_ledger, transition.blob.content, ledger_path, admitted=admitted)
        if appended is not None:
            current_ledger, current_raw = appended, transition.blob.content
            suffix_record_ids.append(appended.entries[-1].record_id)
            kind = "append-rebind" if isinstance(appended.entries[-1], TrustedRebind) else "append"
        else:
            proof = _admit_compaction_transition(root, head, transition, current_ledger, candidates, used)
            current_ledger = _parse_compacted_workstream_ledger(transition.blob.content, ledger_path)
            current_raw = transition.blob.content
            proofs.append(proof)
            admitted = True
            kind = "admitted-compaction"
        facts.append((transition.commit, transition.parent, ledger_path, transition.parent_blob.mode,
                      transition.parent_blob.oid, transition.blob.mode, transition.blob.oid, kind))
    final_blob = _tree_blob(root, head, ledger_path)
    if final_blob is None or final_blob.content != current_raw:
        _fail("compaction-proof-history-ambiguous", ledger_path, "trusted head does not expose the classified final ledger bytes")
    fingerprint = _history_fingerprint(initial_commit, head, ledger_path, facts)
    common = (str(root), trusted_ref, head, ledger_path, final_blob.oid, current_raw, current_ledger, fingerprint)
    if not proofs:
        return NormalTrustedLedger(*common)
    return AdmittedCompactedLedger(*common, tuple(proofs), tuple(suffix_record_ids))


def _reload_trusted_workstream_ledger(loaded: TrustedWorkstreamLedger) -> TrustedWorkstreamLedger:
    """Bind an operation to a freshly re-read, host-selected Git ledger image."""
    if not isinstance(loaded, (NormalTrustedLedger, AdmittedCompactedLedger)):
        _fail("compaction-proof-history-missing", "trusted ledger", "operation requires a loader-issued trusted ledger")
    current = load_trusted_workstream_ledger(
        loaded.repository, trusted_ref=loaded.trusted_ref, ledger_path=loaded.ledger_path,
    )
    expected = (loaded.head, loaded.ledger_blob, loaded.raw, loaded.history_fingerprint, loaded.ledger)
    actual = (current.head, current.ledger_blob, current.raw, current.history_fingerprint, current.ledger)
    if actual != expected:
        _fail("stale_ledger_history", loaded.ledger_path, "trusted ledger changed; reload before applying lifecycle action")
    return current


def _require_trusted_active_board(current: TrustedWorkstreamLedger,
                                  active_ledgers: Iterable[TrustedWorkstreamLedger] | None) -> tuple[TrustedWorkstreamLedger, ...]:
    """Reload and require the complete trusted board for a lifecycle action."""
    if active_ledgers is None:
        _fail("dependency-context", current.ledger_path,
              "Git-backed lifecycle actions require complete trusted active-ledger context")
    supplied = tuple(_reload_trusted_workstream_ledger(item) for item in active_ledgers)
    if any(item.repository != current.repository or item.trusted_ref != current.trusted_ref for item in supplied):
        _fail("dependency-context", current.ledger_path, "trusted active-ledger context must share repository and ref")
    by_path = {item.ledger_path: item for item in supplied}
    if len(by_path) != len(supplied):
        _fail("dependency-context", current.ledger_path, "trusted active-ledger context has duplicate ledger paths")
    if current.ledger_path not in by_path:
        _fail("dependency-context", current.ledger_path, "trusted active-ledger context omits the target ledger")
    board = workstream_board_view(current.repository, trusted_ref=current.trusted_ref)
    if board.exit_code != 0:
        _fail("dependency-context", current.ledger_path, "trusted active board is malformed or ambiguous")
    board_paths = {item.path for item in board.items}
    if set(by_path) != board_paths:
        _fail("dependency-context", current.ledger_path,
              "trusted active-ledger context must cover every trusted board ledger",
              expected=sorted(board_paths), actual=sorted(by_path))
    return tuple(by_path[path] for path in sorted(by_path))


def _validate_trusted_expiry_incoming_dependencies(current: TrustedWorkstreamLedger,
                                                    active_ledgers: Iterable[TrustedWorkstreamLedger],
                                                    preview: WorkstreamExpiryPreview,
                                                    receipts: Iterable[AdmittedWorkstreamReceipt],
                                                    receipt_verifier: WorkstreamReceiptVerifier) -> None:
    """Resolve each open dependent as if the selected source chains had expired."""
    active = tuple(active_ledgers)
    other_ledgers = tuple(item.ledger for item in active if item.ledger_path != current.ledger_path)
    removed = set(preview.removed_record_ids)
    for item in active:
        for record in item.ledger.records:
            if record.to_phase == "closed":
                continue
            for dependency in record.depends_on:
                if dependency.workstream_id != current.ledger.header.workstream_id or dependency.record_id not in removed:
                    continue
                resolve_workstream_dependency(
                    dependency, source_workstream_id=item.ledger.header.workstream_id,
                    active_ledgers=other_ledgers, durable_receipts=receipts, receipt_verifier=receipt_verifier,
                )


def plan_trusted_workstream_chain_close(loaded: TrustedWorkstreamLedger, *, chain_id: str,
                                        receipts: Iterable[AdmittedWorkstreamReceipt],
                                        receipt_verifier: WorkstreamReceiptVerifier,
                                        integration_witness: TrustedIntegrationWitness,
                                        integration_verifier: TrustedRebindVerifier,
                                        conclusion: str, reasoning: str, source: str, confidence: str,
                                        clock: Callable[[], datetime] | None = None,
                                        active_ledgers: Iterable[TrustedWorkstreamLedger] | None = None) -> WorkstreamLedger:
    """Plan closeout only from a freshly re-admitted Git/session history image."""
    current = _reload_trusted_workstream_ledger(loaded)
    _require_trusted_active_board(current, active_ledgers)
    return _plan_workstream_chain_close(
        current.ledger, chain_id=chain_id, receipts=receipts, receipt_verifier=receipt_verifier,
        integration_witness=integration_witness, integration_verifier=integration_verifier,
        expected_head=current.head, actual_head=current.head, pre_ledger_digest=workstream_ledger_digest(current.raw),
        branch=current.ledger.effective_branch, conclusion=conclusion, reasoning=reasoning, source=source,
        confidence=confidence, clock=clock, verify_predecessors=isinstance(current, NormalTrustedLedger),
    )


def preview_trusted_workstream_expiry(loaded: TrustedWorkstreamLedger, *, chain_ids: Iterable[str], now: datetime,
                                      receipts: Iterable[AdmittedWorkstreamReceipt],
                                      receipt_verifier: WorkstreamReceiptVerifier,
                                      integration_witness: TrustedIntegrationWitness,
                                      integration_verifier: TrustedRebindVerifier,
                                      early_approval: EarlyExpiryApproval | None = None,
                                      early_approval_verifier: EarlyExpiryApprovalVerifier | None = None,
                                      active_ledgers: Iterable[TrustedWorkstreamLedger] | None = None) -> WorkstreamExpiryPreview:
    """Preview compaction only from a freshly re-admitted Git/session history image."""
    current = _reload_trusted_workstream_ledger(loaded)
    trusted_active = _require_trusted_active_board(current, active_ledgers)
    durable_receipts = tuple(receipts)
    preview = _preview_workstream_expiry(
        current.ledger, expected_head=current.head, chain_ids=chain_ids, now=now, receipts=durable_receipts,
        receipt_verifier=receipt_verifier, integration_witness=integration_witness,
        integration_verifier=integration_verifier, early_approval=early_approval,
        early_approval_verifier=early_approval_verifier, verify_predecessors=isinstance(current, NormalTrustedLedger),
    )
    _validate_trusted_expiry_incoming_dependencies(current, trusted_active, preview, durable_receipts, receipt_verifier)
    return preview


def apply_trusted_workstream_expiry(loaded: TrustedWorkstreamLedger, preview: WorkstreamExpiryPreview, *,
                                    integration_witness: TrustedIntegrationWitness,
                                    integration_verifier: TrustedRebindVerifier,
                                    receipts: Iterable[AdmittedWorkstreamReceipt],
                                    receipt_verifier: WorkstreamReceiptVerifier,
                                    active_ledgers: Iterable[TrustedWorkstreamLedger] | None = None) -> WorkstreamLedger:
    """Apply a pre-admitted expiry preview only while the classified head remains exact."""
    current = _reload_trusted_workstream_ledger(loaded)
    trusted_active = _require_trusted_active_board(current, active_ledgers)
    durable_receipts = tuple(receipts)
    result = apply_workstream_expiry(
        current.ledger, preview, actual_head=current.head, integration_witness=integration_witness,
        integration_verifier=integration_verifier, actual_ledger_digest=workstream_ledger_digest(current.raw),
    )
    _validate_trusted_expiry_incoming_dependencies(current, trusted_active, preview, durable_receipts, receipt_verifier)
    _validate_workstream_ledger(result, "trusted ledger expiry", verify_predecessors=isinstance(current, NormalTrustedLedger))
    return result


def resolve_trusted_workstream_dependency(dependency: WorkstreamDependency, *, source_workstream_id: str,
                                          active_ledgers: Iterable[TrustedWorkstreamLedger] = (),
                                          durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                          receipt_verifier: WorkstreamReceiptVerifier | None = None) -> DependencyResolution:
    """Resolve active targets only after their histories are freshly admitted."""
    current = tuple(_reload_trusted_workstream_ledger(item) for item in active_ledgers)
    return resolve_workstream_dependency(
        dependency, source_workstream_id=source_workstream_id, active_ledgers=(item.ledger for item in current),
        durable_receipts=durable_receipts, receipt_verifier=receipt_verifier,
    )


@dataclass(frozen=True)
class WorkstreamAppendCommitPreview:
    """Opaque, host-owned normal-append transaction plan."""

    token: str
    trusted_ref: str
    expected_head: str
    ledger_path: str
    expected_ledger_blob: str
    pre_ledger_digest: str
    history_fingerprint: str
    suffix_bytes: bytes
    record_id: str
    post_ledger_digest: str


@dataclass(frozen=True)
class WorkstreamAppendCommitResult:
    new_head: str
    new_ledger_blob: str
    post_ledger_digest: str
    history_fingerprint: str
    record_id: str
    ledger: WorkstreamLedger


@dataclass(frozen=True)
class _StoredWorkstreamAppendPlan:
    preview: WorkstreamAppendCommitPreview
    post_ledger: WorkstreamLedger


_WORKSTREAM_APPEND_PLANS: dict[str, _StoredWorkstreamAppendPlan] = {}


def _full_local_branch_ref(root: Path, ref: str) -> str:
    code, output = _git(root, "rev-parse", "--symbolic-full-name", ref)
    if code or not isinstance(output, str) or not output.startswith("refs/heads/"):
        _fail("append-wrong-branch", str(root), "trusted append ref must be one local branch ref", trusted_ref=ref)
    return output


def _require_clean_append_worktree(root: Path) -> None:
    code, output = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if code or not isinstance(output, str) or output:
        _fail("append-worktree-not-clean", str(root), "append requires a clean worktree and index")
    for args in (("diff", "--quiet"), ("diff", "--cached", "--quiet", "HEAD")):
        code, _output = _git(root, *args)
        if code != 0:
            _fail("append-worktree-not-clean", str(root), "append requires an index equal to HEAD")


def preview_workstream_append_commit(cwd: Path | str, *, trusted_ref: str, workstream_id: str,
                                     request: WorkstreamAppendRequest, clock: Callable[[], datetime] | None = None,
                                     active_ledgers: Iterable[WorkstreamLedger] = (),
                                     durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                     receipt_verifier: WorkstreamReceiptVerifier | None = None) -> WorkstreamAppendCommitPreview:
    """Create the opaque plan for one later adapter-owned ledger-only commit."""
    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, trusted_ref)
    relative = workstream_ledger_path(workstream_id)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=relative)
    if loaded.ledger.header.workstream_id != workstream_id:
        _fail("path", relative, "trusted ledger path and workstream ID differ")
    if full_ref[len("refs/heads/"):] != loaded.ledger.effective_branch:
        _fail("append-wrong-branch", relative, "trusted ref is not the effective ledger owner branch")
    post = _plan_trusted_workstream_append(loaded, request, clock=clock, active_ledgers=active_ledgers,
                                           durable_receipts=durable_receipts, receipt_verifier=receipt_verifier)
    post_raw = render_workstream_ledger(post).encode("utf-8")
    if not post_raw.startswith(loaded.raw):
        _fail("append-commit-failed", relative, "planned append is not an exact canonical suffix")
    token = secrets.token_urlsafe(32)
    preview = WorkstreamAppendCommitPreview(
        token, full_ref, loaded.head, relative, loaded.ledger_blob, workstream_ledger_digest(loaded.raw),
        loaded.history_fingerprint, post_raw[len(loaded.raw):], post.records[-1].record_id,
        workstream_ledger_digest(post_raw),
    )
    _WORKSTREAM_APPEND_PLANS[token] = _StoredWorkstreamAppendPlan(preview, post)
    return preview


def _restore_append_worktree(root: Path, path: Path, raw: bytes, blob: GitBlob) -> bool:
    try:
        path.write_bytes(raw)
        code, _output = _git(root, "update-index", "--cacheinfo", f"{blob.mode},{blob.oid},{blob.path}")
        if code:
            return False
        code, index = _git(root, "ls-files", "-s", "--", blob.path)
        if code or not isinstance(index, str) or not re.fullmatch(rf"{blob.mode} {blob.oid} 0\t{re.escape(blob.path)}", index):
            return False
        return path.read_bytes() == raw
    except OSError:
        return False


def _append_commit_message(preview: WorkstreamAppendCommitPreview, workstream_id: str) -> str:
    return (
        f"reflection: append {preview.record_id}\n\n"
        f"Reflection-Workstream: {workstream_id}\n"
        f"Reflection-Record: {preview.record_id}\n"
        f"Reflection-Pre-Ledger-Digest: {preview.pre_ledger_digest}\n"
        f"Reflection-Post-Ledger-Digest: {preview.post_ledger_digest}"
    )


def apply_workstream_append_commit(cwd: Path | str, preview: WorkstreamAppendCommitPreview, *,
                                   fault_injector: Callable[[str], None] | None = None) -> WorkstreamAppendCommitResult:
    """Persist a preview as one ledger-only off-ref commit then branch CAS.

    ``fault_injector`` is test-only adapter instrumentation; it receives no
    authority fields and makes rollback paths observable without broadening the
    public plan surface.
    """
    if not isinstance(preview, WorkstreamAppendCommitPreview):
        _fail("append-commit-failed", "ledger append", "append apply requires a host-issued opaque preview")
    stored = _WORKSTREAM_APPEND_PLANS.get(preview.token)
    if stored is None or stored.preview != preview:
        _fail("append-commit-failed", "ledger append", "append preview is unknown, replaced, or expired")
    root = Path(cwd).resolve()
    _require_clean_append_worktree(root)
    code, attached = _git(root, "symbolic-ref", "--quiet", "HEAD")
    if code or not isinstance(attached, str) or not attached:
        _fail("append-detached-head", str(root), "append requires HEAD attached to the trusted branch")
    if attached != preview.trusted_ref:
        _fail("append-wrong-branch", str(root), "HEAD is not attached to the preview's trusted branch",
              expected=preview.trusted_ref, actual=attached)
    head = _commit(root, preview.trusted_ref)
    if head != preview.expected_head:
        _fail("stale_head", preview.ledger_path, "trusted ref changed after append preview",
              expected=preview.expected_head, actual=head)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=preview.trusted_ref, ledger_path=preview.ledger_path)
    if loaded.ledger_blob != preview.expected_ledger_blob or workstream_ledger_digest(loaded.raw) != preview.pre_ledger_digest:
        _fail("stale_ledger_digest", preview.ledger_path, "trusted ledger blob changed after append preview")
    if loaded.history_fingerprint != preview.history_fingerprint:
        _fail("stale_ledger_history", preview.ledger_path, "trusted ledger history changed after append preview")
    post_raw = loaded.raw + preview.suffix_bytes
    if workstream_ledger_digest(post_raw) != preview.post_ledger_digest:
        _fail("append-commit-failed", preview.ledger_path, "preview suffix no longer has its predicted canonical digest")
    if render_workstream_ledger(stored.post_ledger).encode("utf-8") != post_raw:
        _fail("append-commit-failed", preview.ledger_path, "preview suffix does not match its stored canonical post-image")
    path = root / Path(preview.ledger_path)
    if not path.is_file() or path.read_bytes() != loaded.raw:
        _fail("append-worktree-not-clean", preview.ledger_path, "working-tree ledger is not the trusted committed blob")
    expected_blob = _tree_blob(root, preview.expected_head, preview.ledger_path)
    if expected_blob is None:
        _fail("append-commit-failed", preview.ledger_path, "preview head no longer exposes its ledger blob")
    wrote_candidate = False
    try:
        path.write_bytes(post_raw)
        wrote_candidate = True
        code, _output = _git(root, "add", "--", preview.ledger_path)
        if code:
            raise RuntimeError("git add failed")
        code, tree = _git(root, "write-tree")
        if code or not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
            raise RuntimeError("git write-tree failed")
        message = _append_commit_message(preview, loaded.ledger.header.workstream_id)
        if fault_injector is not None:
            fault_injector("before-commit")
        code, candidate = _git(root, "commit-tree", tree, "-p", preview.expected_head, "-m", message)
        if code or not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate):
            raise RuntimeError("git commit-tree failed")
        candidate_blob = _tree_blob(root, candidate, preview.ledger_path)
        if (candidate_blob is None or candidate_blob.mode != CANONICAL_MODE or candidate_blob.content != post_raw
                or _git_commit_parents(root, candidate) != (preview.expected_head,)
                or _git_changed_tree_paths(root, preview.expected_head, candidate) != (preview.ledger_path,)
                or _git_commit_message(root, candidate) != message):
            raise RuntimeError("candidate append commit is not canonical")
        if fault_injector is not None:
            fault_injector("before-cas")
        code, _output = _git(root, "update-ref", preview.trusted_ref, candidate, preview.expected_head)
        if code:
            _fail("stale_ref", preview.ledger_path, "trusted ref changed during append compare-and-swap")
    except Exception as exc:
        if wrote_candidate and not _restore_append_worktree(root, path, loaded.raw, expected_blob):
            _fail("append-rollback-failed", preview.ledger_path, "append failure left an unsafe worktree", reason=str(exc))
        if isinstance(exc, ReflectionValidationError):
            raise
        _fail("append-commit-failed", preview.ledger_path, "could not construct canonical ledger-only append commit", reason=str(exc))
    _WORKSTREAM_APPEND_PLANS.pop(preview.token, None)
    final = load_trusted_workstream_ledger(root, trusted_ref=preview.trusted_ref, ledger_path=preview.ledger_path)
    if final.head != candidate or final.ledger_blob != candidate_blob.oid:
        _fail("append-commit-failed", preview.ledger_path, "successful CAS is not immediately visible to trusted readers")
    return WorkstreamAppendCommitResult(final.head, final.ledger_blob, workstream_ledger_digest(final.raw),
                                        final.history_fingerprint, preview.record_id, final.ledger)


RETENTION_PREFLIGHT_FIELDS = (
    "schema", "version", "key_id", "id_domain", "id_kind", "workstream_id", "working_branch", "base_sha",
    "id_salt", "created_at", "retention_days", "scope", "chain_id", "nonce", "approved_at", "expires_at",
    "reason", "session_path", "entry_id",
)
RETENTION_APPROVAL_FIELDS = RETENTION_PREFLIGHT_FIELDS + ("commit", "blob", "signature")


def _retention_preflight_mapping(preflight: RetentionPreflight) -> dict[str, Any]:
    return {
        "schema": "memory-seed/reflection-retention-preflight", "version": 1, "key_id": preflight.key_id,
        "id_domain": "memory-seed/reflection-workstream-ledger/v1", "id_kind": "workstream",
        "workstream_id": preflight.workstream_id, "working_branch": preflight.working_branch, "base_sha": preflight.base_sha,
        "id_salt": preflight.id_salt, "created_at": preflight.created_at, "retention_days": preflight.retention_days,
        "scope": "ledger", "chain_id": None, "nonce": preflight.nonce, "approved_at": preflight.approved_at,
        "expires_at": preflight.expires_at, "reason": preflight.reason, "session_path": preflight.session_path,
        "entry_id": preflight.entry_id,
    }


def render_retention_preflight(preflight: RetentionPreflight) -> str:
    _validate_retention_preflight(preflight)
    values = _retention_preflight_mapping(preflight)
    return _workstream_yaml_mapping([(name, values[name]) for name in RETENTION_PREFLIGHT_FIELDS])


def retention_preflight_from_dict(value: Mapping[str, Any], path: str = "retention-preflight.yaml") -> RetentionPreflight:
    _required(value, RETENTION_PREFLIGHT_FIELDS, path)
    _only(value, RETENTION_PREFLIGHT_FIELDS, path)
    if value["schema"] != "memory-seed/reflection-retention-preflight" or type(value["version"]) is not int or value["version"] != 1 or value["id_domain"] != "memory-seed/reflection-workstream-ledger/v1" or value["id_kind"] != "workstream" or value["scope"] != "ledger" or value["chain_id"] is not None:
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
    return _workstream_yaml_mapping([(name, values[name]) for name in RETENTION_APPROVAL_FIELDS])


def retention_approval_payload(approval: RetentionApproval) -> bytes:
    values = _retention_approval_mapping(approval, include_signature=False)
    return _workstream_yaml_mapping([(name, values[name]) for name in RETENTION_APPROVAL_FIELDS[:-1]]).encode("utf-8")


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


def _refuse_raw_git_backed_mutation(root: Path, trusted_ref: str | None, path: str) -> None:
    """Raw worktree CAS cannot preserve the Git/history admission invariant."""
    code, output = _git(root, "rev-parse", "--is-inside-work-tree")
    if trusted_ref is not None or (code == 0 and output == "true"):
        _fail("guarded-git-mutation", path,
              "Git-backed v1 mutation must use the trusted history/commit transaction route", trusted_ref=trusted_ref)


def guarded_init_workstream_ledger(cwd: Path | str, *, expected_head: str, actual_head: str, working_branch: str,
                                   base_sha: str, retention_days: int = 7, clock: Callable[[], datetime] | None = None,
                                   entropy: Callable[[int], bytes] = os.urandom,
                                   retention_preflight_handle: object | None = None,
                                   retention_verifier: RetentionPreflightVerifier | None = None,
                                   trusted_ref: str | None = None) -> tuple[str, WorkstreamLedger]:
    root = Path(cwd).resolve()
    _refuse_raw_git_backed_mutation(root, trusted_ref, "ledger init")
    if expected_head != actual_head:
        _fail("stale_head", "ledger init", "branch tip changed before init", expected=expected_head, actual=actual_head)
    ledger = initialize_workstream_ledger(working_branch=working_branch, base_sha=base_sha, retention_days=retention_days,
                                          clock=clock, entropy=entropy, retention_preflight_handle=retention_preflight_handle,
                                          retention_verifier=retention_verifier)
    validate_workstream_init_collisions(root, working_branch=working_branch, workstream_id=ledger.header.workstream_id)
    relative = workstream_ledger_path(ledger.header.workstream_id)
    _atomic_write_new(root / Path(relative), render_workstream_ledger(ledger).encode("utf-8"))
    return relative, ledger


def guarded_append_workstream_ledger(cwd: Path | str, *, workstream_id: str, request: WorkstreamAppendRequest,
                                     expected_head: str, actual_head: str, pre_ledger_digest: str, branch: str,
                                     clock: Callable[[], datetime] | None = None,
                                     active_ledgers: Iterable[WorkstreamLedger] = (),
                                     durable_receipts: Iterable[AdmittedWorkstreamReceipt] = (),
                                     receipt_verifier: WorkstreamReceiptVerifier | None = None,
                                     trusted_ref: str | None = None) -> WorkstreamLedger:
    root = Path(cwd).resolve()
    _refuse_raw_git_backed_mutation(root, trusted_ref, "ledger append")
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v1 ledger does not exist")
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
                                 reason: str, clock: Callable[[], datetime] | None = None,
                                 trusted_ref: str | None = None) -> TrustedRebindResult:
    """CAS write primitive which rejects occupied/malformed target-branch boards."""
    root = Path(cwd).resolve()
    _refuse_raw_git_backed_mutation(root, trusted_ref, "ledger rebind")
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v1 ledger does not exist")
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
                                    integration_verifier: TrustedRebindVerifier,
                                    trusted_ref: str | None = None) -> WorkstreamLedger:
    root = Path(cwd).resolve()
    _refuse_raw_git_backed_mutation(root, trusted_ref, "ledger expiry")
    relative = workstream_ledger_path(workstream_id)
    path = root / Path(relative)
    if not path.is_file():
        _fail("path", relative, "active v1 ledger does not exist")
    raw = path.read_bytes()
    ledger = parse_workstream_ledger(raw, relative)
    validate_workstream_branch_owner(root, ledger)
    result = apply_workstream_expiry(ledger, preview, actual_head=actual_head,
                                     integration_witness=integration_witness, integration_verifier=integration_verifier)
    _atomic_replace_existing(path, raw, render_workstream_ledger(result).encode("utf-8"))
    return result
