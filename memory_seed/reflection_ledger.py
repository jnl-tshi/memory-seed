"""Reflection Board v1: one strict sequential ledger per workstream.

Temporary coordination state uses its own canonical format and trusted Git
history. Durable receipt evidence is read from ordinary append-only sessions.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from functools import lru_cache, wraps
from hashlib import sha256, sha512
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence
import json
import os
import posixpath
import re
import secrets
import stat
import subprocess
import unicodedata


REFLECTION_ROOT = ".memory-seed/reflections/active"
RETENTION_TRUST_PATH = ".memory-seed/reflections/trust/retention-approval.yaml"
RETENTION_TRUST_SCHEMA = "memory-seed/reflection-retention-trust"
EXPIRY_DISCLOSURE = (
    "Working-tree disappearance is not cryptographic erasure. "
    "Historical and unreachable Git objects may remain until Git garbage collection."
)
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


def _ed25519_sign(seed: bytes, message: bytes) -> tuple[bytes, bytes]:
    """RFC 8032 deterministic signing for a local, offline host.

    Like the existing verifier, this uses only the standard library. Python
    big integers are not constant-time; this is not a hardware key boundary.
    """
    if len(seed) != 32:
        _fail("retention-trust", "private key", "Ed25519 seed must contain exactly 32 bytes")

    def add(p, q):
        a, b = (p[1] - p[0]) * (q[1] - q[0]), (p[1] + p[0]) * (q[1] + q[0])
        c, d = 2 * ED25519_D * p[3] * q[3], 2 * p[2] * q[2]
        e, f, g, h = b - a, d - c, d + c, b + a
        return tuple(v % ED25519_P for v in (e * f, g * h, f * g, e * h))

    def encode_multiple(scalar):
        y = ED25519_BASE_Y
        xx = (y * y - 1) * pow(ED25519_D * y * y + 1, ED25519_P - 2, ED25519_P) % ED25519_P
        x = pow(xx, (ED25519_P + 3) // 8, ED25519_P)
        if x & 1:
            x = ED25519_P - x
        current, total = (x, y, 1, x * y % ED25519_P), (0, 1, 1, 0)
        while scalar:
            if scalar & 1:
                total = add(total, current)
            current, scalar = add(current, current), scalar >> 1
        inverse = pow(total[2], ED25519_P - 2, ED25519_P)
        x, y = total[0] * inverse % ED25519_P, total[1] * inverse % ED25519_P
        return (y | ((x & 1) << 255)).to_bytes(32, "little")

    hashed = sha512(seed).digest()
    scalar = (int.from_bytes(hashed[:32], "little") & ((1 << 254) - 8)) | (1 << 254)
    public = encode_multiple(scalar)
    nonce = int.from_bytes(sha512(hashed[32:] + message).digest(), "little") % ED25519_L
    encoded_r = encode_multiple(nonce)
    challenge = int.from_bytes(sha512(encoded_r + public + message).digest(), "little") % ED25519_L
    return public, encoded_r + ((nonce + challenge * scalar) % ED25519_L).to_bytes(32, "little")


@dataclass(frozen=True)
class GitBlob:
    path: str
    oid: str
    mode: str
    content: bytes


def _git(root: Path, *args: str, binary: bool = False, input: bytes | None = None) -> tuple[int, bytes | str]:
    result = subprocess.run(["git", "-C", str(root), *args], input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
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


def is_reserved_reflection_path(path: str) -> bool:
    """Recognize the reserved family, including Windows component aliases.

    Alias recognition never grants authority: scope admission rejects ambiguous
    components and committed inventory still requires canonical ledger paths.
    """
    parts = PurePosixPath(posixpath.normpath(path.replace("\\", "/"))).parts
    folded = tuple(part.rstrip(" .").casefold() for part in parts)
    return any(folded[index:index + 2] == (".memory-seed", "reflections")
               for index in range(len(folded) - 1))


def validate_reflection_capability(execution: Mapping[str, Any]) -> dict[str, Any] | None:
    """Pure writer-scope admission, reusable by compiler and artifact consumers.

    A capability only narrows access; the operation still owes the ledger's
    role, phase, expected-identity, integration and approval checks.
    """
    allowed = execution.get("allowed_files", ())
    absent = execution.get("expected_absent", ())
    if not isinstance(allowed, (list, tuple)) or not isinstance(absent, (list, tuple)):
        _fail("reflection-capability-scope", "execution", "file scopes must be exact path lists")
    if any(not isinstance(path, str) for path in (*allowed, *absent)):
        _fail("reflection-capability-scope", "execution", "file scopes must contain strings")
    reserved = [path for path in allowed if is_reserved_reflection_path(path)]
    reserved_absent = [path for path in absent if is_reserved_reflection_path(path)]
    for path in (*reserved, *reserved_absent):
        if any(part not in {".", ".."} and part.endswith((".", " "))
               for part in path.replace("\\", "/").split("/")):
            _fail("reflection-capability-scope", path, "Windows trailing-dot/space component aliases are forbidden")
    capability = execution.get("reflection")
    if capability is None:
        if execution.get("write_intent") == "writing" and (reserved or reserved_absent):
            _fail("reflection-capability-required", "execution.reflection", "reserved reflection writes require workstream-v1")
        return None
    if not isinstance(capability, Mapping) or set(capability) != {"format", "workstream_id", "ledger_path", "operations"}:
        _fail("reflection-capability-scope", "execution.reflection", "requires exactly format, workstream_id, ledger_path and operations")
    if capability["format"] != "workstream-v1":
        _fail("unsupported-reflection-format", "execution.reflection.format", "only workstream-v1 is supported")
    workstream = _id(capability["workstream_id"], "rwl_", "execution.reflection", "workstream_id")
    path = workstream_ledger_path(workstream)
    operations = capability["operations"]
    if (not isinstance(operations, list) or not operations or any(not isinstance(op, str) for op in operations)
            or len(set(operations)) != len(operations) or not set(operations) <= {"append", "close", "expire", "rebind"}):
        _fail("reflection-capability-scope", "execution.reflection.operations", "requires nonempty unique append/close/expire/rebind operations")
    identity = lambda value: PurePosixPath(value.replace("\\", "/")).as_posix().casefold()
    if (capability["ledger_path"] != path or len(reserved) != 1 or identity(reserved[0]) != path
            or reserved_absent):
        _fail("reflection-capability-scope", path, "the initialized canonical ledger must be the sole reflection write path")
    return {"format": "workstream-v1", "workstream_id": workstream, "ledger_path": path,
            "operations": sorted(operations)}


def measure_reflection_capability(cwd: Path | str, execution: Mapping[str, Any], *,
                                  working_branch: str, expected: Mapping[str, Any] | None = None) -> dict[str, str] | None:
    """Bind a pure capability to committed state, never to caller-supplied proof."""
    capability = validate_reflection_capability(execution)
    if capability is None:
        if expected is not None:
            _fail("reflection-capability-scope", "runtime_binding.reflection", "binding has no capability")
        return None
    root = Path(cwd).resolve()
    branch_code, branch = _git(root, "branch", "--show-current")
    if branch_code or str(branch).strip() != working_branch:
        _fail("reflection-binding-stale", str(root), "capability branch is not the measured checked-out branch")
    ref = "refs/heads/" + working_branch
    loaded = load_trusted_workstream_ledger(root, trusted_ref=ref, ledger_path=capability["ledger_path"])
    _check_reflection_worktree(root, _reflection_tree_inventory(root, loaded.head))
    code, changed = _git(root, "diff", "--cached", "--name-only", "-z")
    if code or any(is_reserved_reflection_path(path) for path in str(changed).split("\0") if path):
        _fail("reflection-binding-stale", loaded.ledger_path, "index contains unadmitted reserved changes")
    if loaded.ledger.effective_branch != working_branch:
        _fail("reflection-binding-stale", loaded.ledger_path, "ledger is owned by another effective branch")
    measured = {"trusted_ref": ref, "head": loaded.head, "ledger_blob": loaded.ledger_blob,
                "ledger_digest": workstream_ledger_digest(loaded.raw), "history_fingerprint": loaded.history_fingerprint}
    if expected is not None and dict(expected) != measured:
        _fail("reflection-binding-stale", loaded.ledger_path, "measured ledger binding changed; compile a fresh packet")
    return measured


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
    if type(retention) is not int or retention not in {7, 14, 30}:
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
            if path == active_root.rstrip("/"):
                return WorkstreamBoardView((
                    WorkstreamBoardItem(path, "malformed", None, None, None, None,
                                        ReflectionDiagnostic("unsupported-reflection-format", path,
                                                             "committed active board root must be a directory", {})),
                ))
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
    _git_sha(current_target_tip, "ledger rebind", "current_target_tip")
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
    "closure_receipts", "member_receipts", "reason", "git_blobs_remain", "privacy_grade_erasure", "elapsed_attestation",
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
    # Canonical JSON keeps the immutable receipt hashable during history scans.
    elapsed_attestation: str | None = None

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
            "elapsed_attestation": json.loads(self.elapsed_attestation) if self.elapsed_attestation is not None else None,
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
        _canonical_elapsed_attestation(value["elapsed_attestation"], path),
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
                   _cached_git_changed_tree_paths, _cached_git_tree_paths, _cached_git_commit_message, _retention_anchor):
        cached.cache_clear()


def _render_retention_trust(trust: RetentionApprovalTrust) -> str:
    return _workstream_yaml_mapping(tuple(dict(schema=RETENTION_TRUST_SCHEMA, version=1,
        key_id=trust.key_id, public_key=trust.public_key).items()))


def _parse_retention_trust(raw: bytes, path: str = RETENTION_TRUST_PATH) -> RetentionApprovalTrust:
    text = _canonical_text(raw, path)
    value = _parse_yaml_mapping(text, path)
    _required(value, ("schema", "version", "key_id", "public_key"), path)
    _only(value, ("schema", "version", "key_id", "public_key"), path)
    if value["schema"] != RETENTION_TRUST_SCHEMA or type(value["version"]) is not int or value["version"] != 1:
        _fail("retention-trust", path, "unsupported canonical trust schema/version")
    public = value["public_key"]
    if not isinstance(public, str) or not re.fullmatch(r"ed25519:[0-9a-f]{64}", public):
        _fail("retention-trust", path, "anchor requires one canonical Ed25519 public key")
    if value["key_id"] != "sha256:" + sha256(bytes.fromhex(public[8:])).hexdigest():
        _fail("retention-trust", path, "anchor key ID does not bind its public key")
    trust = RetentionApprovalTrust(value["key_id"], public)
    if _render_retention_trust(trust) != text:
        _fail("retention-trust", path, "trust anchor bytes are not canonical")
    return trust


@lru_cache(maxsize=32768)
def _retention_anchor(root: Path, head: str, *, required: bool = True) -> GitBlob | None:
    _git_oid_40(head, RETENTION_TRUST_PATH, "trust head")
    code, paths = _git(root, "ls-tree", "-r", "-z", "--name-only", head, binary=True)
    if code or not isinstance(paths, bytes):
        _fail("retention-trust", RETENTION_TRUST_PATH, "cannot inventory trust aliases")
    for path in paths.decode("utf-8").split("\0"):
        if (is_reserved_reflection_path(path) and path != RETENTION_TRUST_PATH
                and not re.fullmatch(r"\.memory-seed/reflections/active/rwl_[0-9abcdefghjkmnpqrstvwxyz]{20}/ledger\.md", path)):
            _fail("retention-trust", path, "trust aliases and unknown reserved paths are forbidden")
    blob = _tree_blob(root, head, RETENTION_TRUST_PATH)
    if blob is None:
        if required:
            _fail("retention-trust", RETENTION_TRUST_PATH, "trust init must precede the ledger base")
        return None
    if blob.mode != CANONICAL_MODE:
        _fail("retention-trust", RETENTION_TRUST_PATH, "trust anchor must be a regular 100644 blob")
    _parse_retention_trust(blob.content)
    # Follow every parent, including deleted/restored periods. No rotation or
    # divergent trust history can be laundered by returning to today's bytes.
    code, output = _git(root, "rev-list", "--full-history",
        f"--max-count={MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS + 1}", head, "--", RETENTION_TRUST_PATH)
    history = output.splitlines() if code == 0 and isinstance(output, str) else []
    if not history or len(history) > MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS:
        _fail("retention-trust", RETENTION_TRUST_PATH, "trust history is missing or exceeds its bound")
    for commit in history:
        current = _tree_blob(root, commit, RETENTION_TRUST_PATH)
        parents = _git_commit_parents(root, commit)
        prior = [_tree_blob(root, parent, RETENTION_TRUST_PATH) for parent in parents]
        if (current is None or current.mode != CANONICAL_MODE or current.content != blob.content
                or any(item is not None and (item.mode != CANONICAL_MODE or item.content != blob.content) for item in prior)):
            _fail("retention-trust", RETENTION_TRUST_PATH, "anchor rotation, removal or divergence is forbidden")
        if not any(prior):
            if len(parents) != 1 or _git_changed_tree_paths(root, parents[0], commit) != (RETENTION_TRUST_PATH,):
                _fail("retention-trust", RETENTION_TRUST_PATH, "bootstrap must introduce only the canonical anchor")
            trust = _parse_retention_trust(blob.content)
            match = re.fullmatch(r"reflection: trust init\n\nReflection-Trust-Proof: ed25519:([0-9a-f]{128})", _git_commit_message(root, commit))
            if match is None or not ed25519_verify(bytes.fromhex(trust.public_key[8:]),
                    _trust_bootstrap_payload(parents[0], blob.content), bytes.fromhex(match.group(1))):
                _fail("retention-trust", RETENTION_TRUST_PATH, "bootstrap lacks its exact key-pair proof")
    return blob


def _trust_bootstrap_payload(parent: str, raw: bytes) -> bytes:
    return b"memory-seed/reflection-trust-bootstrap/v1\0" + parent.encode("ascii") + b"\0" + raw


def _retention_key_path(root: Path) -> Path:
    common = _rebind_common_directory(root)
    path = common / "memory-seed-retention" / "ed25519.seed"
    for candidate in (path.parent, path):
        if candidate.is_symlink() or candidate.resolve() != candidate:
            _fail("retention-trust", str(candidate), "private key paths cannot contain links or junctions")
    return path


def _read_retention_key(root: Path, trust: RetentionApprovalTrust | None = None) -> bytes:
    path = _retention_key_path(root)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        _fail("retention-trust", str(path), "local private key is unavailable; replacement is not supported")
    if os.name != "nt" and path.stat().st_mode & 0o077:
        _fail("retention-trust", str(path), "private key permissions must exclude group and other users")
    seed = path.read_bytes()
    challenge = b"memory-seed/reflection-key-pair/v1"
    public, signature = _ed25519_sign(seed, challenge)
    if (not ed25519_verify(public, challenge, signature)
            or (trust is not None and trust.public_key != "ed25519:" + public.hex())):
        _fail("retention-trust", RETENTION_TRUST_PATH, "private key and public anchor do not match")
    return seed


def _create_retention_key(root: Path) -> None:
    path = _retention_key_path(root)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    if os.name == "nt":
        identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=False)
        match = re.search(r"S-1-[0-9-]+", identity.stdout)
        if identity.returncode or match is None:
            _fail("retention-trust", str(path.parent), "cannot determine a restrictive local key ACL")
        reset = subprocess.run(["icacls", str(path.parent), "/reset"], capture_output=True, check=False)
        if reset.returncode:
            _fail("retention-trust", str(path.parent), "cannot remove pre-existing private-directory ACL grants")
        secured = subprocess.run(["icacls", str(path.parent), "/inheritance:r", "/grant:r",
            f"*{match.group(0)}:(OI)(CI)F"], capture_output=True, check=False)
        if secured.returncode:
            _fail("retention-trust", str(path.parent), "cannot restrict the local private-key directory ACL")
    else:
        path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(secrets.token_bytes(32))
        stream.flush()
        os.fsync(stream.fileno())


def _reflection_tree_layout(root: Path, commit: str) -> tuple[tuple[str, str, str], ...]:
    """Validate and inventory reserved tree shape without loading ledger history."""
    context = _REFLECTION_VERIFICATION_CONTEXT.get()
    # Only complete object identities are immutable; never memoize a ref name.
    cacheable = context is not None and re.fullmatch(r"[0-9a-f]{40}", commit)
    key = (str(root.resolve()), commit)
    if cacheable and key in context.layouts:
        return context.layouts[key]
    result = _read_reflection_tree_layout(root, commit)
    if cacheable and len(context.layouts) < 32768:
        context.layouts[key] = result
    return result


def _read_reflection_tree_layout(root: Path, commit: str) -> tuple[tuple[str, str, str], ...]:
    """Read the complete tree, retaining alias and trust-anchor validation."""
    code, raw = _git(root, "ls-tree", "-rz", "--full-tree", commit, binary=True)
    if code or not isinstance(raw, bytes):
        _fail("reflection-integration-tree", commit, "could not inventory the exact Git tree")
    entries: list[tuple[str, str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, path_raw = item.split(b"\t", 1)
        path = path_raw.decode("utf-8", errors="strict")
        if not is_reserved_reflection_path(path):
            continue
        mode, kind, oid = metadata.decode("ascii").split()
        if path == RETENTION_TRUST_PATH and mode == CANONICAL_MODE and kind == "blob":
            _retention_anchor(root, commit)
            entries.append((path, mode, oid))
            continue
        match = re.fullmatch(r"\.memory-seed/reflections/active/(rwl_[0-9abcdefghjkmnpqrstvwxyz]{20})/ledger\.md", path)
        if match is None or mode != CANONICAL_MODE or kind != "blob":
            _fail("unsupported-reflection-format", path, "reserved tree permits only canonical regular v1 ledgers", mode=mode)
        entries.append((path, mode, oid))
    return tuple(sorted(entries))


def _reflection_tree_inventory(root: Path, commit: str) -> tuple[tuple[str, str, str], ...]:
    """Inventory every valid reserved blob, including trusted ledger owners."""
    entries = _reflection_tree_layout(root, commit)
    owners: dict[str, str] = {}
    for path, mode, oid in entries:
        if path == RETENTION_TRUST_PATH:
            continue
        match = re.fullmatch(r"\.memory-seed/reflections/active/(rwl_[0-9abcdefghjkmnpqrstvwxyz]{20})/ledger\.md", path)
        assert match is not None
        loaded = load_trusted_workstream_ledger(root, trusted_ref=commit, ledger_path=path)
        if loaded.ledger.header.workstream_id != match.group(1):
            _fail("reflection-integration-tree", path, "directory does not bind its ledger identity")
        owner = loaded.ledger.effective_branch
        if owner in owners:
            _fail("branch-collision", path, "committed board contains duplicate effective owners", other=owners[owner])
        owners[owner] = path
    return entries


def _inherited_identical_reflection_family(root: Path, *, base_commit: str, source_commit: str,
                                           merge_base: str, merged_commit: str | None = None) -> bool:
    """Whether a normal descendant carries an untouched complete Reflection family.

    This adds the normal-descendant topology constraint to the complete-identity
    proof used for a two-parent carrier. ``merged_commit`` binds the same
    family to the actual no-FF merge index.
    """
    return (
        merge_base == base_commit
        and _git_is_ancestor(root, base_commit, source_commit)
        and _identical_reflection_family(
            root,
            base_commit=base_commit,
            source_commit=source_commit,
            merge_base=merge_base,
            merged_commit=merged_commit,
        )
    )


def _identical_reflection_family(root: Path, *, base_commit: str, source_commit: str,
                                 merge_base: str, merged_commit: str | None = None) -> bool:
    """Whether both parents inherit one byte-identical complete Reflection family.

    An ordinary no-FF merge can be an identity carrier even when unrelated
    work advanced on both branches. This admits that narrow topology only when
    every reserved path (including the trust anchor) is identical at the sole
    merge base and both parents. It never combines ledger histories, and the
    optional merged tree recheck prevents an index-side substitution.
    """
    if base_commit == source_commit:
        return False
    base = _reflection_tree_layout(root, base_commit)
    if not base:
        return False
    if _reflection_tree_layout(root, source_commit) != base or _reflection_tree_layout(root, merge_base) != base:
        return False
    return merged_commit is None or _reflection_tree_layout(root, merged_commit) == base


def _check_reflection_worktree(root: Path, expected: tuple[tuple[str, str, str], ...]) -> None:
    """Inventory ignored/untracked families within this checkout, without writes.

    Only Git metadata and other registered worktrees are traversal boundaries.
    Dependency/generated folder names are not exclusions: they can own runtimes.
    Directory links (including Windows junctions) are never followed.
    """
    code, worktrees = _git(root, "worktree", "list", "--porcelain", "-z", binary=True)
    if code or not isinstance(worktrees, bytes):
        _fail("reflection-integration-tree", str(root), "could not establish checkout traversal boundaries")
    nested_worktrees = set()
    for field in worktrees.split(b"\0"):
        if field.startswith(b"worktree "):
            checkout = Path(field[len(b"worktree "):].decode("utf-8", errors="strict")).resolve()
            if checkout != root and checkout.is_relative_to(root):
                nested_worktrees.add(checkout)
    actual: dict[str, bytes] = {}
    expected_paths = {path for path, _mode, _oid in expected}
    allowed_dirs = {".memory-seed/reflections", REFLECTION_ROOT} | {
        str(PurePosixPath(path).parent) for path in expected_paths
    }
    if RETENTION_TRUST_PATH in expected_paths:
        allowed_dirs.add(".memory-seed/reflections/trust")

    def scan_error(error: OSError) -> None:
        _fail("reflection-integration-tree", str(error.filename), "could not inventory checkout directories")

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=scan_error):
        descend = []
        directory_names = set(dirs)
        for name in dirs + files:
            path = Path(directory) / name
            folded = name.rstrip(" .").casefold()
            relative = path.relative_to(root).as_posix()
            reserved = is_reserved_reflection_path(relative)
            if folded == ".git" or path in nested_worktrees:
                if reserved:
                    _fail("unsupported-reflection-format", relative, "checkout boundaries cannot hide reserved state")
                continue
            metadata = path.lstat()
            linked = (stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_reparse_tag", None)
                      == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003))
            if folded == ".memory-seed" and (
                name.endswith((".", " ")) or linked or not stat.S_ISDIR(metadata.st_mode)
            ):
                _fail("unsupported-reflection-format", str(path), "runtime is not a regular directory")
            if reserved:
                if linked:
                    _fail("unsupported-reflection-format", relative, "directory links and symlinks are forbidden in reserved state")
                if stat.S_ISDIR(metadata.st_mode):
                    if relative not in allowed_dirs:
                        _fail("unsupported-reflection-format", relative, "unknown or nested reserved directory is not admitted")
                elif relative not in expected_paths or not stat.S_ISREG(metadata.st_mode):
                    _fail("unsupported-reflection-format", relative, "unknown reserved file is not admitted")
                else:
                    actual[relative] = path.read_bytes()
            if name in directory_names and not linked:
                descend.append(name)
        dirs[:] = descend
    if set(actual) != expected_paths:
        _fail("reflection-binding-stale", str(root), "working-tree reserved paths differ from the admitted tree")
    for path, _mode, oid in expected:
        code, raw = _git(root, "cat-file", "blob", oid, binary=True)
        if code or raw != actual[path]:
            _fail("reflection-binding-stale", path, "working-tree ledger differs from the admitted blob")


@dataclass(frozen=True)
class ReflectionIntegrationPreview:
    source_ref: str
    base_ref: str
    source_commit: str
    base_commit: str
    merge_base: str
    worktree_head: str
    source: tuple[tuple[str, str, str], ...]
    base: tuple[tuple[str, str, str], ...]
    ancestor: tuple[tuple[str, str, str], ...]
    proposed: tuple[tuple[str, str, str], ...]
    inherited_identical_family: bool


def reflection_verification_operation(function):
    """Share bounded immutable-history proofs only within one synchronous operation.

    Nested preview/recheck calls reuse classifications, not mutable ref, index,
    worktree, or admission results. Exceptions also discard the outer context.
    Nothing is persisted or accepted as caller-supplied verification evidence.
    """
    @wraps(function)
    def wrapped(*args, **kwargs):
        if _REFLECTION_VERIFICATION_CONTEXT.get() is not None:
            return function(*args, **kwargs)
        token = _REFLECTION_VERIFICATION_CONTEXT.set(_ReflectionVerificationContext())
        try:
            return function(*args, **kwargs)
        finally:
            _REFLECTION_VERIFICATION_CONTEXT.reset(token)
    return wrapped


@reflection_verification_operation
def preview_reflection_integration(cwd: Path | str, *, source_ref: str, base_ref: str) -> ReflectionIntegrationPreview:
    """Read exact parents and the determinable reserved result without writes.

    A ledger may enter a new merge through exactly one parent. A normal
    descendant may also carry a complete untouched Reflection family through
    both parents. General Git content merges cannot combine or rewrite
    reflection histories.
    """
    root = Path(cwd).resolve()
    source_commit, base_commit = _commit(root, source_ref), _commit(root, base_ref)
    if source_commit is None or base_commit is None:
        _fail("reflection-integration-tree", str(root), "integration refs must resolve to exact commits")
    code, ancestors = _git(root, "merge-base", "--all", source_commit, base_commit)
    bases = str(ancestors).split()
    if code or len(bases) != 1:
        _fail("reflection-integration-topology", str(root), "integration requires one unambiguous merge-base")
    source = _reflection_tree_inventory(root, source_commit)
    base = _reflection_tree_inventory(root, base_commit)
    ancestor = _reflection_tree_inventory(root, bases[0])
    left, right = {item[0]: item for item in base}, {item[0]: item for item in source}
    for path, _mode, _oid in ancestor:
        if path not in left or path not in right:
            _fail("reflection-integration-topology", path, "raw ledger removal is not admitted integration")
    inherited_identical_family = _identical_reflection_family(
        root, base_commit=base_commit, source_commit=source_commit, merge_base=bases[0],
    )
    if _git_is_ancestor(root, source_commit, base_commit):
        proposed = base
    elif inherited_identical_family:
        proposed = base
    else:
        common = left.keys() & right.keys()
        if RETENTION_TRUST_PATH in common and left[RETENTION_TRUST_PATH] != right[RETENTION_TRUST_PATH]:
            _fail("retention-trust", RETENTION_TRUST_PATH, "integration parents have divergent public anchors")
        ledger_common = common - {RETENTION_TRUST_PATH}
        if ledger_common:
            _fail("reflection-integration-topology", sorted(ledger_common)[0],
                  "merge would have two ledger-bearing parents; use admitted sequential topology")
        proposed = tuple(sorted(set((*base, *source))))
    owners: dict[str, str] = {}
    for path, _mode, _oid in proposed:
        if path == RETENTION_TRUST_PATH:
            continue
        commit = base_commit if path in left else source_commit
        owner = load_trusted_workstream_ledger(root, trusted_ref=commit, ledger_path=path).ledger.effective_branch
        if owner in owners:
            _fail("branch-collision", path, "proposed result has duplicate effective ledger owners", other=owners[owner])
        owners[owner] = path
    head = _commit(root, "HEAD")
    if head is None:
        _fail("reflection-integration-tree", str(root), "worktree HEAD must resolve")
    return ReflectionIntegrationPreview(
        source_ref, base_ref, source_commit, base_commit, bases[0], head,
        source, base, ancestor, proposed, inherited_identical_family,
    )


@reflection_verification_operation
def recheck_reflection_integration(cwd: Path | str, preview: ReflectionIntegrationPreview, *, merged: bool = False) -> None:
    """Recheck preview bindings and actual reserved files before mutation."""
    root = Path(cwd).resolve()
    if not isinstance(preview, ReflectionIntegrationPreview):
        _fail("reflection-binding-stale", str(root), "requires the original immutable integration preview")
    measured = preview_reflection_integration(root, source_ref=preview.source_ref, base_ref=preview.base_ref)
    if measured != preview:
        _fail("reflection-binding-stale", str(root), "integration refs or proposed reserved result changed after preview")
    if merged:
        expected = preview.proposed
        code, raw = _git(root, "ls-files", "--stage", "-z", binary=True)
        if code or not isinstance(raw, bytes):
            _fail("reflection-integration-tree", str(root), "could not inspect proposed index")
        staged: list[tuple[str, str, str]] = []
        for item in raw.split(b"\0"):
            if not item:
                continue
            metadata, path_raw = item.split(b"\t", 1)
            path = path_raw.decode("utf-8", errors="strict")
            if is_reserved_reflection_path(path):
                mode, oid, stage = metadata.decode("ascii").split()
                if stage != "0":
                    _fail("reflection-integration-topology", path, "reserved merge conflict is not admitted")
                staged.append((path, mode, oid))
        if tuple(sorted(staged)) != expected:
            _fail("reflection-binding-stale", str(root), "proposed index differs from preview")
    else:
        expected = _reflection_tree_inventory(root, preview.worktree_head)
    _check_reflection_worktree(root, expected)


@reflection_verification_operation
def reflection_commit_admission(cwd: Path | str, *, candidate: str | None = None,
                                plan: WorkstreamCommitPreview | None = None) -> dict[str, Any]:
    """Shared reserved-family gate for kernel transactions and commit hooks.

    The hook supplies only cwd. Commit messages, environment switches and
    caller-provided tokens never confer kernel admission.
    """
    root = Path(cwd).resolve()
    if plan is not None:
        stored = _WORKSTREAM_COMMIT_PLANS.get(plan.token)
        if stored is None or stored.preview != plan or stored.repository != str(root) or candidate is None:
            _fail("reflection-hook", str(root), "kernel admission requires its live transaction plan")
        changed = tuple(path for path in _git_changed_tree_paths(root, plan.expected_head, candidate)
                        if is_reserved_reflection_path(path))
        if changed != (plan.ledger_path,):
            _fail("reflection-hook", str(root), "kernel transaction changed another reserved path")
        blob = _tree_blob(root, candidate, plan.ledger_path)
        if blob is None or blob.content != stored.post_raw or blob.mode != CANONICAL_MODE:
            _fail("reflection-hook", plan.ledger_path, "kernel candidate differs from its exact planned bytes")
        _check_reflection_worktree(root, _reflection_tree_inventory(root, candidate))
        return {"admission": "trust-bootstrap" if plan.operation == "trust_init" else "kernel", "paths": list(changed)}
    if candidate is not None:
        _fail("reflection-hook", str(root), "candidate admission requires a kernel plan")
    head = _commit(root, "HEAD")
    code, staged = _git(root, "diff", "--cached", "--name-only", "-z", *(('HEAD',) if head else ()), binary=True)
    if code or not isinstance(staged, bytes):
        _fail("reflection-hook", str(root), "could not inspect reserved staged changes")
    paths = tuple(path for path in staged.decode("utf-8").split("\0") if path and is_reserved_reflection_path(path))
    code, merge_path = _git(root, "rev-parse", "--git-path", "MERGE_HEAD")
    merge_file = root / str(merge_path)
    if code == 0 and merge_file.is_file():
        heads = merge_file.read_text(encoding="ascii").split()
        if len(heads) != 1 or not re.fullmatch(r"[0-9a-f]{40}", heads[0]) or head is None:
            _fail("reflection-hook", str(root), "only exact two-parent integration carriers are admitted")
        preview = preview_reflection_integration(root, source_ref=heads[0], base_ref=head)
        recheck_reflection_integration(root, preview, merged=True)
        return {"admission": "merge-carrier", "paths": list(paths)}
    if paths:
        _fail("reflection-hook", paths[0], "manual staged reflection paths are forbidden; use the reflection kernel")
    return {"admission": "ordinary", "paths": []}


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
    """Replay the host signature against the immutable base and exact history.

    Git dates never enter this decision. The signature is the local host's
    clock observation; its five-minute issue window is not a Git timestamp.
    """
    if receipt.elapsed_attestation is None:
        _fail("compaction-proof-retention", receipt.ledger_path, "unsigned cleanup remains disabled: no trusted elapsed-time attestation")
    value = json.loads(receipt.elapsed_attestation)
    _canonical_elapsed_attestation(value, receipt.ledger_path)
    current = load_trusted_workstream_ledger(root, trusted_ref=receipt.pre_tip, ledger_path=receipt.ledger_path)
    if current.ledger != pre_ledger:
        _fail("compaction-proof-retention", receipt.ledger_path, "pre-cleanup history does not match the signed ledger")
    observed = _as_utc(value["observed_at"])
    expected = _elapsed_payload(current, receipt, observed)
    supplied = {key: item for key, item in value.items() if key != "signature"}
    trust = _parse_retention_trust(_retention_anchor(root, pre_ledger.header.base_sha).content)
    if supplied != expected or not ed25519_verify(bytes.fromhex(trust.public_key[8:]),
            _elapsed_signing_bytes(expected), bytes.fromhex(value["signature"][8:])):
        _fail("compaction-proof-retention", receipt.ledger_path, "elapsed-time signature or exact history binding does not verify")


_ELAPSED_FIELDS = ("schema", "version", "key_id", "trust_anchor_blob", "ledger_base", "integration_commit",
    "integration_record_id", "integration_branch", "retention_days", "observed_at", "expires_at",
    "close_commits", "binding_digest", "signature")


def _canonical_elapsed_attestation(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        _fail("compaction-proof-retention", path, "elapsed attestation must be an exact mapping")
    _required(value, _ELAPSED_FIELDS, path)
    _only(value, _ELAPSED_FIELDS, path)
    if (value["schema"] != "memory-seed/reflection-elapsed-retention" or type(value["version"]) is not int
            or value["version"] != 1 or type(value["retention_days"]) is not int
            or value["retention_days"] not in {7, 14, 30}
            or not isinstance(value["signature"], str) or not re.fullmatch(r"ed25519:[0-9a-f]{128}", value["signature"])):
        _fail("compaction-proof-retention", path, "unsupported elapsed attestation schema, interval or signature")
    for name in ("observed_at", "expires_at"):
        _timestamp(value[name], path, name)
    if _as_utc(value["expires_at"]) != _as_utc(value["observed_at"]) + timedelta(minutes=5):
        _fail("compaction-proof-retention", path, "elapsed attestation issue window must be exactly five minutes")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _elapsed_signing_bytes(value: Mapping[str, Any]) -> bytes:
    return b"memory-seed/reflection-elapsed-retention/v1\0" + json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _close_time_signing_bytes(value: Mapping[str, Any]) -> bytes:
    return b"memory-seed/reflection-close-time/v1\0" + json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _close_time_payload(loaded: TrustedWorkstreamLedger, close: WorkstreamRecord,
                        post_blob: str, observed: datetime) -> dict[str, Any]:
    """Bind an apply-time host observation, never a caller-authored timestamp."""
    root = Path(loaded.repository)
    anchor = _retention_anchor(root, loaded.ledger.header.base_sha)
    if _retention_anchor(root, loaded.head).oid != anchor.oid:
        _fail("close-time-proof", loaded.ledger_path, "close anchor differs from its immutable base")
    trust = _parse_retention_trust(anchor.content)
    witness = GitWorkstreamIntegrationVerifier(loaded).witness()
    if close.closed_at is None or observed < _as_utc(close.closed_at):
        _fail("close-time-proof", loaded.ledger_path, "host observation cannot precede the close record")
    post_raw = loaded.raw + b"\n" + render_workstream_record(close).encode("utf-8")
    return dict(schema="memory-seed/reflection-close-time", version=1, key_id=trust.key_id,
        trust_anchor_blob=anchor.oid, ledger_base=loaded.ledger.header.base_sha,
        workstream_id=loaded.ledger.header.workstream_id, ledger_path=loaded.ledger_path,
        parent=loaded.head, pre_blob=loaded.ledger_blob, post_blob=post_blob,
        pre_ledger_digest=workstream_ledger_digest(loaded.raw), post_ledger_digest=workstream_ledger_digest(post_raw),
        chain_id=close.chain_id, close_record_id=close.record_id, close_record_digest=close.detail_digest,
        closed_at=close.closed_at, integration_commit=witness.integration_commit,
        integration_record_id=witness.rebind_record_id, integration_branch=witness.target_branch,
        observed_at=_clock_timestamp(lambda: observed),
        expires_at=_clock_timestamp(lambda: observed + timedelta(minutes=5)))


def _verified_close_time(root: Path, close: WorkstreamRecord, transition: _LedgerTransition) -> dict[str, Any]:
    """Require the original exact close transition's authenticated host time.

    Legacy/raw close records stay readable but confer no expiry authority.
    A proof copied to another parent, ledger image, or integration cannot verify.
    """
    path = transition.blob.path
    if (_git_commit_parents(root, transition.commit) != (transition.parent,)
            or _git_changed_tree_paths(root, transition.parent, transition.commit) != (path,)):
        _fail("close-time-proof", path, "close proof requires an exact ledger-only sole-parent introduction")
    matches = re.findall(r"^Reflection-Close-Time: (.+)$", _git_commit_message(root, transition.commit), re.MULTILINE)
    if len(matches) != 1:
        _fail("close-time-proof", path, "close has no unique authenticated host-time proof; legacy close cannot expire")
    try:
        value = json.loads(matches[0])
    except (ValueError, TypeError):
        _fail("close-time-proof", path, "close-time proof is not canonical JSON")
    if (not isinstance(value, dict) or json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) != matches[0]
            or type(value.get("version")) is not int
            or not isinstance(value.get("signature"), str)
            or not re.fullmatch(r"ed25519:[0-9a-f]{128}", value["signature"])):
        _fail("close-time-proof", path, "close-time proof is not a canonical signed mapping")
    observed = _as_utc(_timestamp(value.get("observed_at"), path, "observed_at"))
    loaded = load_trusted_workstream_ledger(root, trusted_ref=transition.parent, ledger_path=path)
    if transition.blob.content != loaded.raw + b"\n" + render_workstream_record(close).encode("utf-8"):
        _fail("close-time-proof", path, "close proof does not introduce exactly this record")
    expected = _close_time_payload(loaded, close, transition.blob.oid, observed)
    anchor = _retention_anchor(root, loaded.ledger.header.base_sha)
    trust = _parse_retention_trust(anchor.content)
    if ({key: item for key, item in value.items() if key != "signature"} != expected
            or not ed25519_verify(bytes.fromhex(trust.public_key[8:]), _close_time_signing_bytes(expected),
                                  bytes.fromhex(value["signature"][8:]))):
        _fail("close-time-proof", path, "close-time signature or exact history binding does not verify")
    return value


def _require_mapping_origin(root: Path, mapping: Mapping[str, str], commit: str, *, after: str) -> None:
    """A later snapshot, merge, or delete/restore cannot reset evidence origin."""
    path = mapping["session_path"]
    code, output = _git(root, "rev-list", "--full-history",
        f"--max-count={MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS + 1}", commit, "--", path)
    commits = output.splitlines() if code == 0 and isinstance(output, str) else []
    if not commits or len(commits) > MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS:
        _fail("receipt-history-missing", path, "could not inspect bounded receipt provenance")
    for candidate in dict.fromkeys((commit, *commits)):
        blob = _tree_blob(root, candidate, path)
        if (blob is not None and _session_has_exact_yaml_mapping(blob.content, path, mapping,
                entry_id=mapping["entry_id"], decision_id=mapping["decision_id"])
                and (candidate == after or not _git_is_ancestor(root, after, candidate))):
            _fail("receipt-integration", path, "receipt must originate after its admitted integration or close")


def _elapsed_payload(loaded: TrustedWorkstreamLedger, receipt: WorkstreamCompactionReceipt, observed: datetime) -> dict[str, Any]:
    root, ledger = Path(loaded.repository), loaded.ledger
    anchor = _retention_anchor(root, ledger.header.base_sha)
    if _retention_anchor(root, loaded.head).content != anchor.content:
        _fail("retention-trust", RETENTION_TRUST_PATH, "current anchor differs from the ledger base")
    trust = _parse_retention_trust(anchor.content)
    witness = GitWorkstreamIntegrationVerifier(loaded).witness()
    if ledger.effective_branch != witness.target_branch:
        _fail("compaction-proof-retention", loaded.ledger_path, "cleanup is not owned by the integrated branch")
    _initial, _blob, transitions = _ledger_lineage(root, loaded.head, loaded.ledger_path)
    closings = []
    for closure in receipt.closure_receipts:
        close = next((item for item in ledger.records if item.record_id == closure.closed_record_id), None)
        if close is None or close.closed_at is None:
            _fail("compaction-proof-retention", loaded.ledger_path, "closing record is absent")
        introduced = [item for item in transitions if item.blob.content == item.parent_blob.content
                      + b"\n" + render_workstream_record(close).encode("utf-8")]
        if len(introduced) != 1 or not _git_is_ancestor(root, witness.integration_commit, introduced[0].commit):
            _fail("compaction-proof-retention", loaded.ledger_path, "close has no exact post-integration introduction")
        close_time = _verified_close_time(root, close, introduced[0])
        if observed < _as_utc(close_time["observed_at"]) + timedelta(days=ledger.header.reflection_retention_days):
            _fail("compaction-proof-retention", loaded.ledger_path, "chain retention window has not elapsed")
        _require_mapping_origin(root, _closure_session_mapping(closure), closure.commit, after=introduced[0].commit)
        closings.append(dict(chain_id=close.chain_id, record_id=close.record_id,
            closed_at=close.closed_at, commit=introduced[0].commit, observed_at=close_time["observed_at"],
            close_time_proof_digest="sha256:" + sha256(_close_time_signing_bytes(close_time)).hexdigest()))
        for member in receipt.member_receipts:
            if member.chain_id == close.chain_id:
                _require_mapping_origin(root, _member_session_mapping(receipt.workstream_id, member), member.commit,
                    after=introduced[0].commit if member.record_id == close.record_id else witness.integration_commit)
    bound = receipt.as_dict()
    bound.pop("elapsed_attestation")
    return dict(schema="memory-seed/reflection-elapsed-retention", version=1, key_id=trust.key_id,
        trust_anchor_blob=anchor.oid, ledger_base=ledger.header.base_sha,
        integration_commit=witness.integration_commit, integration_record_id=witness.rebind_record_id,
        integration_branch=witness.target_branch, retention_days=ledger.header.reflection_retention_days,
        observed_at=_clock_timestamp(lambda: observed), expires_at=_clock_timestamp(lambda: observed + timedelta(minutes=5)),
        close_commits=closings, binding_digest="sha256:" + sha256(_elapsed_signing_bytes(bound)).hexdigest())


def _trusted_active_ledgers_at_commit(root: Path, commit: str) -> tuple[tuple[str, WorkstreamLedger], ...]:
    """Build the entire v1 board from one immutable Git tree, fail closed."""
    prefix = REFLECTION_ROOT + "/"
    candidates: dict[str, set[str]] = {}
    for path in _git_tree_paths(root, commit):
        if path == REFLECTION_ROOT:
            _fail("unsupported-reflection-format", path, "committed active board root must be a directory")
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
            if len(ledger_parents) == 1:
                parent, parent_blob = ledger_parents[0]
            elif len(parents) == 2 and len(ledger_parents) == 2:
                code, raw_bases = _git(root, "merge-base", "--all", parents[0], parents[1])
                merge_bases = str(raw_bases).split()
                if (code == 0 and len(merge_bases) == 1 and _identical_reflection_family(
                        root, base_commit=parents[0], source_commit=parents[1],
                        merge_base=merge_bases[0], merged_commit=current,
                )):
                    # A guarded no-FF identity carrier may retain one untouched
                    # complete Reflection family through both parents.
                    # First-parent traversal is deterministic and skips no
                    # ledger transition.
                    parent, parent_blob = ledger_parents[0]
                else:
                    _fail("compaction-proof-history-ambiguous", ledger_path,
                          "merge must have exactly one ledger-bearing parent or an identical family", commit=current)
            else:
                _fail("compaction-proof-history-ambiguous", ledger_path,
                      "merge must have exactly one ledger-bearing parent or an identical family", commit=current)
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


@dataclass
class _ReflectionVerificationContext:
    """Bounded result reuse, separate from each dependency graph's safety budget."""

    completed: dict[tuple[str, str, str, str], TrustedWorkstreamLedger] = field(default_factory=dict)
    layouts: dict[tuple[str, str], tuple[tuple[str, str, str], ...]] = field(default_factory=dict)


_REFLECTION_VERIFICATION_CONTEXT: ContextVar[_ReflectionVerificationContext | None] = ContextVar(
    "reflection_verification_context", default=None,
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
    operation = _REFLECTION_VERIFICATION_CONTEXT.get()
    key = (str(root), trusted_ref, head, ledger_path)
    # Reuse only whole, independently verified root graphs. Nested loads retain
    # the original cycle/depth/work budget; warm child proofs cannot bypass it.
    root_load = context is None
    if root_load and operation is not None and key in operation.completed:
        return operation.completed[key]
    token = None
    if context is None:
        context = _TrustedLedgerClassificationContext()
        token = _TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.set(context)
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
            if root_load and operation is not None and len(operation.completed) < MAX_TRUSTED_LEDGER_CLASSIFICATIONS:
                operation.completed[key] = result
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
class WorkstreamCommitPreview:
    """Inspectable receipt for a kernel-owned, single-use transaction plan."""

    token: str
    trusted_ref: str
    expected_head: str
    ledger_path: str
    expected_ledger_blob: str | None
    pre_ledger_digest: str
    history_fingerprint: str
    suffix_bytes: bytes
    record_id: str | None
    post_ledger_digest: str
    operation: str = "append"


@dataclass(frozen=True)
class WorkstreamAppendCommitPreview(WorkstreamCommitPreview):
    """Normal append preview; shares the canonical transaction implementation."""


@dataclass(frozen=True)
class WorkstreamCommitResult:
    new_head: str
    new_ledger_blob: str
    post_ledger_digest: str
    history_fingerprint: str
    record_id: str | None
    ledger: WorkstreamLedger | None
    integration_witness: TrustedIntegrationWitness | None = None


@dataclass(frozen=True)
class WorkstreamAppendCommitResult(WorkstreamCommitResult):
    """Result of the normal append entry point."""


@dataclass(frozen=True)
class _StoredWorkstreamCommitPlan:
    preview: WorkstreamCommitPreview
    repository: str
    post_raw: bytes
    revalidate: Callable[[], tuple[WorkstreamLedger | RetentionApprovalTrust, TrustedIntegrationWitness | None]]
    verify_refs: tuple[tuple[str, str], ...]
    compaction_factory: Callable[[str, str], WorkstreamCompactionReceipt] | None = None


_WORKSTREAM_COMMIT_PLANS: dict[str, _StoredWorkstreamCommitPlan] = {}


def _transaction_context(root: Path, full_ref: str) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    code, top = _git(root, "rev-parse", "--show-toplevel")
    if code or not isinstance(top, str) or Path(top).resolve() != root:
        _fail("transaction-worktree", str(root), "transaction requires the exact Git worktree root")
    _require_clean_append_worktree(root)
    code, attached = _git(root, "symbolic-ref", "--quiet", "HEAD")
    if code or not attached:
        _fail("append-detached-head", str(root), "transaction requires attached HEAD")
    if attached != full_ref:
        _fail("append-wrong-branch", str(root), "HEAD is not attached to the transaction branch")
    head = _commit(root, full_ref)
    if head is None:
        _fail("stale_head", str(root), "transaction branch does not resolve to a commit")
    inventory = _reflection_tree_inventory(root, head)
    _check_reflection_worktree(root, inventory)
    return head, inventory


def _store_workstream_commit(root: Path, full_ref: str, head: str, operation: str,
                             loaded: TrustedWorkstreamLedger | None,
                             revalidate: Callable[[], tuple[WorkstreamLedger, TrustedIntegrationWitness | None]], *,
                             verify_refs: tuple[tuple[str, str], ...] = ()) -> WorkstreamCommitPreview:
    post, _witness = revalidate()
    post_raw = render_workstream_ledger(post).encode("utf-8")
    relative = workstream_ledger_path(post.header.workstream_id)
    pre_raw = loaded.raw if loaded is not None else b""
    if loaded is not None and operation != "expiry" and not post_raw.startswith(pre_raw):
        _fail("append-commit-failed", relative, "planned transaction is not an exact canonical suffix")
    preview_type = WorkstreamAppendCommitPreview if operation == "append" else WorkstreamCommitPreview
    preview = preview_type(
        secrets.token_urlsafe(32), full_ref, head, relative, loaded.ledger_blob if loaded else None,
        workstream_ledger_digest(pre_raw) if loaded else "", loaded.history_fingerprint if loaded else "",
        post_raw if operation == "expiry" else post_raw[len(pre_raw):], post.entries[-1].record_id if post.entries else None,
        workstream_ledger_digest(post_raw), operation,
    )
    # Keep a distinct copy: even object.__setattr__ on a frozen public receipt
    # must not mutate the authority copy used by apply.
    _WORKSTREAM_COMMIT_PLANS[preview.token] = _StoredWorkstreamCommitPlan(
        deepcopy(preview), str(root), post_raw, revalidate, verify_refs,
    )
    return preview


def _require_unretired_workstream_owner(root: Path, loaded: TrustedWorkstreamLedger) -> None:
    """A surviving source checkout cannot resume writing after a local rebind."""
    code, tips = _git(root, "for-each-ref", "--format=%(objectname)", "refs/heads/")
    if code or not isinstance(tips, str):
        _fail("branch-owner", loaded.ledger_path, "could not inspect local ownership transfers")
    for tip in set(tips.splitlines()) - {loaded.head}:
        blob = _tree_blob(root, tip, loaded.ledger_path)
        if blob is None or blob.content == loaded.raw:
            continue
        other = load_trusted_workstream_ledger(root, trusted_ref=tip, ledger_path=loaded.ledger_path)
        known = {entry.record_id for entry in loaded.ledger.entries}
        for rebind in other.ledger.rebinds:
            if (rebind.record_id not in known and rebind.from_branch == loaded.ledger.effective_branch
                    and rebind.to_branch != rebind.from_branch):
                _fail("branch-owner", loaded.ledger_path, "source branch was retired by a committed ownership transfer")


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
    head, _inventory = _transaction_context(root, full_ref)
    relative = workstream_ledger_path(workstream_id)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=relative)
    if loaded.ledger.header.workstream_id != workstream_id:
        _fail("path", relative, "trusted ledger path and workstream ID differ")
    if full_ref[len("refs/heads/"):] != loaded.ledger.effective_branch:
        _fail("append-wrong-branch", relative, "trusted ref is not the effective ledger owner branch")
    request = deepcopy(request)
    durable_receipts = deepcopy(tuple(durable_receipts))
    active_ledgers = deepcopy(tuple(active_ledgers))
    created = _as_utc(_clock_timestamp(clock))

    def revalidate():
        current = _reload_trusted_workstream_ledger(loaded)
        _require_unretired_workstream_owner(root, current)
        # Active dependency facts come from Git; caller data can only narrow
        # that context, never substitute a fabricated active ledger.
        board = dict(_trusted_active_ledgers_at_commit(root, current.head))
        if any(board.get(workstream_ledger_path(item.header.workstream_id)) != item for item in active_ledgers):
            _fail("dependency-context", relative, "supplied active ledger differs from trusted Git")
        return _plan_trusted_workstream_append(
            current, request, clock=lambda: created, active_ledgers=board.values(),
            durable_receipts=durable_receipts, receipt_verifier=receipt_verifier,
        ), None

    return _store_workstream_commit(root, full_ref, head, "append", loaded, revalidate)


def preview_workstream_init_commit(cwd: Path | str, *, trusted_ref: str, retention_days: int = 7,
                                   retention_preflight_handle: object | None = None,
                                   retention_verifier: RetentionPreflightVerifier | None = None,
                                   clock: Callable[[], datetime] | None = None) -> WorkstreamCommitPreview:
    """Mint initialization from the attached branch and its measured current base.

    Identity, entropy, base SHA, bytes and commit metadata are kernel-owned.
    Extended retention retains the existing host-issued approval requirement.
    """
    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, trusted_ref)
    head, _inventory = _transaction_context(root, full_ref)
    branch = full_ref[len("refs/heads/"):]
    ledger = initialize_workstream_ledger(
        working_branch=branch, base_sha=head, retention_days=retention_days, clock=clock,
        retention_preflight_handle=retention_preflight_handle, retention_verifier=retention_verifier,
    )
    frozen_raw = render_workstream_ledger(ledger)

    def revalidate():
        post = parse_workstream_ledger(frozen_raw)
        if retention_days != 7:
            renewed = initialize_workstream_ledger(
                working_branch=branch, base_sha=head, retention_days=retention_days,
                retention_preflight_handle=retention_preflight_handle, retention_verifier=retention_verifier,
            )
            if renewed != post:
                _fail("retention-approval", "ledger init", "approval changed after initialization planning")
        validate_workstream_init_collisions(root, working_branch=branch, workstream_id=post.header.workstream_id)
        return post, None

    return _store_workstream_commit(root, full_ref, head, "init", None, revalidate)


def _transaction_active_ledgers(root: Path, full_ref: str, head: str) -> tuple[TrustedWorkstreamLedger, ...]:
    return tuple(load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=path)
                 for path, _mode, _oid in _reflection_tree_inventory(root, head) if path != RETENTION_TRUST_PATH)


def preview_reflection_trust_init(cwd: Path | str) -> tuple[WorkstreamCommitPreview | None, RetentionApprovalTrust | None]:
    """One-time CLI bootstrap, on the locally resolved integration/default branch."""
    from .core import _resolve_pr_base_branch

    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, "HEAD")
    target, _ref, _tip, error = _resolve_pr_base_branch(root, None, source_branch="")
    if error or full_ref != "refs/heads/" + str(target):
        _fail("retention-trust", RETENTION_TRUST_PATH, error or "trust init requires the integration/default branch")
    head, _inventory = _transaction_context(root, full_ref)
    anchor = _retention_anchor(root, head, required=False)
    if anchor is not None:
        trust = _parse_retention_trust(anchor.content)
        _read_retention_key(root, trust)
        return None, trust
    # Preview creates no private material. Generation is an apply-only step.
    key_path = _retention_key_path(root)
    if key_path.exists():
        _read_retention_key(root)
    return WorkstreamCommitPreview("", full_ref, head, RETENTION_TRUST_PATH, None, "", "", b"", None, "", "trust_init"), None


def reflection_trust_init(cwd: Path | str, *, apply: bool = False,
                          fault_injector: Callable[[str], None] | None = None) -> dict[str, Any]:
    if type(apply) is not bool:
        _fail("retention-trust", RETENTION_TRUST_PATH, "apply must be a boolean")
    root = Path(cwd).resolve()
    preview, existing = preview_reflection_trust_init(root)
    if preview is None or not apply:
        return dict(operation="trust_init", applied=False, initialized=existing is not None,
            head=_commit(root, "HEAD"), public_anchor=RETENTION_TRUST_PATH,
            key_id=existing.key_id if existing else None)
    if not _retention_key_path(root).exists():
        _create_retention_key(root)
    seed = _read_retention_key(root)
    public, _signature = _ed25519_sign(seed, b"")
    trust = RetentionApprovalTrust("sha256:" + sha256(public).hexdigest(), "ed25519:" + public.hex())
    raw = _render_retention_trust(trust).encode("utf-8")

    def revalidate():
        current, _existing = preview_reflection_trust_init(root)
        if current != preview:
            _fail("retention-trust", RETENTION_TRUST_PATH, "bootstrap context changed after preview")
        _read_retention_key(root, trust)
        return trust, None

    planned = replace(preview, token=secrets.token_urlsafe(32), suffix_bytes=raw,
        post_ledger_digest=workstream_ledger_digest(raw))
    _WORKSTREAM_COMMIT_PLANS[planned.token] = _StoredWorkstreamCommitPlan(deepcopy(planned), str(root), raw, revalidate, ())
    result = apply_workstream_commit(root, planned, fault_injector=fault_injector)
    return dict(operation="trust_init", applied=True, initialized=True, head=result.new_head,
        public_anchor=RETENTION_TRUST_PATH, key_id=trust.key_id)


def preview_workstream_rebind_commit(cwd: Path | str, *, trusted_ref: str, workstream_id: str,
                                     token: TrustedRebindToken, verifier: TrustedRebindVerifier,
                                     reason: str, clock: Callable[[], datetime] | None = None,
                                     integration_commit: str | None = None) -> WorkstreamCommitPreview:
    """Persist a host-admitted integration token through the shared transaction.

    The host supplies its existing integration capability, not a post-ledger,
    rebind record ID, witness, current tip or commit plan.
    """
    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, trusted_ref)
    head, _inventory = _transaction_context(root, full_ref)
    relative = workstream_ledger_path(workstream_id)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=relative)
    if not isinstance(token, TrustedRebindToken):
        _fail("rebind", relative, "rebind requires the host's integration token")
    token = deepcopy(token)
    source_ref = _full_local_branch_ref(root, "refs/heads/" + token.source_branch)
    merge_event = _git_sha(integration_commit or head, relative, "integration_commit")
    created = _as_utc(_clock_timestamp(clock))

    def revalidate():
        current = _reload_trusted_workstream_ledger(loaded)
        _require_unretired_workstream_owner(root, current)
        if token.target_branch != full_ref[len("refs/heads/"):]:
            _fail("rebind", relative, "integration target differs from the attached transaction branch")
        if (_commit(root, "refs/heads/" + token.source_branch) != token.source_tip
                or not _git_is_ancestor(root, token.source_tip, current.head)
                or not _git_is_ancestor(root, token.target_pre_merge_tip, current.head)):
            _fail("rebind", relative, "integration token does not bind reachable current branch facts")
        source_blob = _tree_blob(root, token.source_tip, relative)
        if source_blob is None or source_blob.mode != CANONICAL_MODE or source_blob.content != current.raw:
            _fail("rebind", relative, "integrated ledger differs from the token's source tip")
        for item in _transaction_active_ledgers(root, full_ref, current.head):
            if item.ledger_path != relative and item.ledger.effective_branch == token.target_branch:
                _fail("branch-collision", relative, "rebind target branch already has a ledger")
        result = apply_trusted_rebind(
            current.ledger, token, integration_commit=merge_event, current_target_tip=current.head,
            verifier=verifier, reason=reason, clock=lambda: created,
        )
        return result.ledger, result.witness

    return _store_workstream_commit(root, full_ref, head, "rebind", loaded, revalidate,
                                    verify_refs=((source_ref, token.source_tip),))


def _rebind_source_ref(root: Path, source: str) -> str:
    """Accept only a live same-repository local branch locator, never a rev expression."""
    ref = source if source.startswith("refs/heads/") else "refs/heads/" + source
    if (source.startswith("refs/") and not source.startswith("refs/heads/")
            or re.fullmatch(r"[0-9a-fA-F]{40,64}", source)
            or _git(root, "check-ref-format", ref)[0]):
        _fail("rebind", source, "source must be a local branch name or refs/heads locator")
    code, actual = _git(root, "show-ref", "--verify", "--hash", ref)
    if code or actual != _commit(root, ref):
        _fail("rebind", ref, "source branch must still be live in this repository")
    code, _ = _git(root, "symbolic-ref", "--quiet", ref)
    if code == 0:
        _fail("rebind", ref, "symbolic source aliases are not supported")
    return ref


def _unchanged_rebind_ancestry(root: Path, base: str, tip: str, relative: str) -> None:
    """Every first-parent advancement preserves the exact ledger, including absence."""
    if not _git_is_ancestor(root, base, tip):
        _fail("rebind", relative, "target is not descended from the prepared merge identity")
    expected = _tree_blob(root, base, relative)
    current = tip
    while current != base:
        if _tree_blob(root, current, relative) != expected:
            _fail("stale_ledger_digest", relative, "target advancement changed the prepared ledger")
        parents = _git_commit_parents(root, current)
        if not parents:
            _fail("rebind", relative, "target is not a first-parent descendant of the prepared merge identity")
        current = parents[0]


def _rebind_common_directory(root: Path) -> Path:
    code, common = _git(root, "rev-parse", "--git-common-dir")
    if code or not common:
        _fail("rebind-handoff", str(root), "cannot resolve the repository Git common directory")
    return (root / common).resolve()


def _rebind_handoff_path(root: Path, workstream_id: str, source_ref: str, source_tip: str) -> Path:
    workstream_ledger_path(workstream_id)
    directory = _rebind_common_directory(root) / "memory-seed-reflection-handoffs"
    if directory.is_symlink() or directory.resolve() != directory:
        _fail("rebind-handoff", str(directory), "handoff directory must not be a symlink or junction")
    identity = sha256((workstream_id + "\n" + source_ref + "\n" + source_tip).encode("utf-8")).hexdigest()
    return directory / (identity + ".json")


def _rebind_handoff_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def prepare_workstream_rebind(cwd: Path | str, *, workstream_id: str, apply: bool = False) -> dict[str, Any]:
    """Capture the final clean source state in an untracked, non-secret local PR handoff."""
    from .core import _resolve_pr_base_branch, read_integration_mode

    root = Path(cwd).resolve()
    if type(apply) is not bool:
        _fail("rebind-handoff", str(root), "apply must be a boolean")
    if read_integration_mode(root) != "pr":
        _fail("rebind-handoff", str(root), "PR prepare requires integration_mode: pr")
    source_ref = _full_local_branch_ref(root, "HEAD")
    source_tip, _ = _transaction_context(root, source_ref)
    relative = workstream_ledger_path(workstream_id)
    source = load_trusted_workstream_ledger(root, trusted_ref=source_ref, ledger_path=relative)
    if source.ledger.effective_branch != source_ref.removeprefix("refs/heads/"):
        _fail("rebind", relative, "prepare must run on the effective source branch")
    _require_unretired_workstream_owner(root, source)
    target, _, _, error = _resolve_pr_base_branch(root, None, source_branch=source.ledger.effective_branch)
    if error or not target:
        _fail("rebind-handoff", relative, error or "cannot derive the target branch")
    target_ref = _rebind_source_ref(root, target)
    target_tip = _commit(root, target_ref)
    code, merge_head = _git(root, "rev-parse", "--git-path", "MERGE_HEAD")
    if code or (root / merge_head).exists() or not _git_is_ancestor(root, target_tip, source_tip):
        _fail("rebind-handoff", relative, "finish source preparation against the current target before preparing the handoff")
    if _tree_blob(root, target_tip, relative) is not None:
        _fail("rebind-handoff", relative, "prepare must precede integration of the source ledger")
    evidence = dict(schema="memory-seed/reflection-rebind-handoff", version=1,
        repository=str(_rebind_common_directory(root)), workstream_id=workstream_id,
        source_ref=source_ref, source_tip=source_tip, target_ref=target_ref,
        target_tip=target_tip, ledger_blob=source.ledger_blob,
        pre_ledger_digest=workstream_ledger_digest(source.raw))
    path = _rebind_handoff_path(root, workstream_id, source_ref, source_tip)
    if path.exists() or path.is_symlink() or path.with_suffix(".consumed").exists():
        _fail("rebind-handoff", relative, "this final source tip already has a single-use handoff")
    if apply:
        # All source preparation must be complete before capture. Remeasure
        # after planning so no preparation or target movement can be hidden.
        if _transaction_context(root, source_ref)[0] != source_tip or _commit(root, target_ref) != target_tip:
            _fail("stale_head", relative, "source or target changed during preparation")
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            stream.write(_rebind_handoff_bytes(evidence))
    return {"operation": "prepare", "applied": apply, "workstream_id": workstream_id,
        "head": source_tip, "source": source_ref, "target_branch": target,
        "pre_ledger_digest": evidence["pre_ledger_digest"], "status": "prepared" if apply else "ready_to_prepare"}


class _GitRebindVerifier(TrustedRebindVerifier):
    """Internal verifier for one measured exact merge event and a later CAS head."""

    def __init__(self, root: Path, loaded: TrustedWorkstreamLedger, token: TrustedRebindToken,
                 merge_event: str, prepared_target: str | None = None):
        self.root, self.loaded, self.token = root, loaded, token
        self.merge_event, self.prepared_target = merge_event, prepared_target
        self.witnesses: list[TrustedIntegrationWitness] = []

    def verify(self, token, *, integration_commit, current_target_tip):
        if token != self.token or integration_commit != self.merge_event or current_target_tip != self.loaded.head:
            return False
        root, relative = self.root, self.loaded.ledger_path
        if _git_commit_parents(root, integration_commit) != (token.target_pre_merge_tip, token.source_tip):
            return False
        source_ref = _rebind_source_ref(root, token.source_branch)
        if _commit(root, source_ref) != token.source_tip:
            return False
        source = load_trusted_workstream_ledger(root, trusted_ref=source_ref, ledger_path=relative)
        if (source.raw != self.loaded.raw or source.ledger.effective_branch != token.source_branch
                or workstream_ledger_digest(source.raw) != token.pre_ledger_digest
                or _tree_blob(root, token.target_pre_merge_tip, relative) is not None):
            return False
        if source.ledger.rebinds:
            GitWorkstreamIntegrationVerifier(source).witness()
        integrated = _tree_blob(root, integration_commit, relative)
        if integrated is None or integrated.mode != CANONICAL_MODE or integrated.content != source.raw:
            return False
        _unchanged_rebind_ancestry(root, integration_commit, current_target_tip, relative)
        if self.prepared_target:
            _unchanged_rebind_ancestry(root, self.prepared_target, token.target_pre_merge_tip, relative)
        return True

    def admit_witness(self, token, rebind, *, integration_commit):
        witness = TrustedIntegrationWitness(token.workstream_id, rebind.record_id, token.source_branch,
            token.target_branch, token.source_tip, token.target_pre_merge_tip, integration_commit, token.pre_ledger_digest)
        self.witnesses.append(witness)
        return witness

    def verify_witness(self, witness):
        # Admission follows verify() in the kernel. Apply invokes that complete
        # verification again, then checks source and target refs atomically;
        # membership here must not duplicate the same Git history scan.
        return witness in self.witnesses


def preview_integrated_workstream_rebind(cwd: Path | str, *, workstream_id: str,
        source: str, reason: str, pr: bool = False) -> tuple[WorkstreamCommitPreview, str, Path | None, bytes | None]:
    """Derive all authority from Git and, for PRs, the exact local prepared handoff."""
    from .core import read_integration_mode

    root = Path(cwd).resolve()
    if (read_integration_mode(root) == "pr") != pr:
        _fail("rebind", str(root), "use the rebind operation matching the project's integration mode")
    target_ref = _full_local_branch_ref(root, "HEAD")
    head, _ = _transaction_context(root, target_ref)
    relative = workstream_ledger_path(workstream_id)
    source_ref = _rebind_source_ref(root, source)
    source_tip = _commit(root, source_ref)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=target_ref, ledger_path=relative)
    if (loaded.ledger.effective_branch != source_ref.removeprefix("refs/heads/") or source_ref == target_ref):
        _fail("rebind", relative, "source locator must identify the ledger's current owner")
    path, raw, evidence = None, None, None
    if pr:
        path = _rebind_handoff_path(root, workstream_id, source_ref, source_tip)
        if path.is_symlink() or not path.is_file() or path.with_suffix(".consumed").exists():
            _fail("rebind-handoff", relative, "prepared handoff is absent, invalid or already consumed")
        raw = path.read_bytes()
        try:
            evidence = json.loads(raw)
        except (ValueError, UnicodeError):
            _fail("rebind-handoff", relative, "handoff is not canonical JSON")
        expected = dict(schema="memory-seed/reflection-rebind-handoff", version=1,
            repository=str(_rebind_common_directory(root)), workstream_id=workstream_id,
            source_ref=source_ref, source_tip=source_tip, target_ref=target_ref,
            target_tip=evidence.get("target_tip") if isinstance(evidence, dict) else None,
            ledger_blob=loaded.ledger_blob, pre_ledger_digest=workstream_ledger_digest(loaded.raw))
        if evidence != expected or raw != _rebind_handoff_bytes(expected):
            _fail("rebind-handoff", relative, "handoff does not bind this repository, source, target and ledger preimage")
        _git_sha(evidence["target_tip"], relative, "prepared target tip")
    merge_event, current = None, head
    while current:
        parents = _git_commit_parents(root, current)
        if len(parents) == 2 and parents[1] == source_tip:
            merge_event = current
            break
        current = parents[0] if parents else None
    if merge_event is None:
        _fail("rebind", relative, "no exact two-parent target/source merge event on the target's first-parent history")
    token = preview_trusted_rebind(loaded.ledger, source_tip=source_tip,
        target_branch=target_ref.removeprefix("refs/heads/"),
        target_pre_merge_tip=_git_commit_parents(root, merge_event)[0], token_factory=lambda: secrets.token_urlsafe(32))
    verifier = _GitRebindVerifier(root, loaded, token, merge_event, evidence["target_tip"] if evidence else None)
    if not verifier.verify(token, integration_commit=merge_event, current_target_tip=head):
        _fail("rebind", relative, "merge event does not preserve the exact live source ledger")
    preview = preview_workstream_rebind_commit(root, trusted_ref=target_ref, workstream_id=workstream_id,
        token=token, verifier=verifier, reason=reason, integration_commit=merge_event)
    return preview, merge_event, path, raw


def apply_integrated_workstream_rebind(cwd: Path | str, preview: WorkstreamCommitPreview,
        *, handoff_path: Path | None = None, handoff_bytes: bytes | None = None) -> WorkstreamCommitResult:
    """Claim a PR handoff exactly once, then delegate to the existing ledger CAS writer."""
    if handoff_path is not None:
        if handoff_path.is_symlink() or handoff_path.read_bytes() != handoff_bytes:
            _fail("rebind-handoff", preview.ledger_path, "handoff changed after preview")
        try:
            with handoff_path.with_suffix(".consumed").open("xb") as stream:
                stream.write(sha256(handoff_bytes).hexdigest().encode("ascii") + b"\n")
        except FileExistsError:
            _fail("rebind-handoff", preview.ledger_path, "handoff was already consumed")
        # A failed transaction leaves the claim in place: it must never replay.
    return apply_workstream_commit(cwd, preview)


def plan_workstream_chain_receipts(loaded: TrustedWorkstreamLedger, *, chain_id: str, session_path: str,
                                    entry_id: str, decision_id: str, disposition: str) -> tuple[WorkstreamReceipt, ...]:
    """Draft exact member receipts for an ordinary session writer; grants no admission.

    The receipt digest uses the existing detail domain over the ordered member
    mapping with its own digest zeroed, just as record detail digests do.
    """
    current = _reload_trusted_workstream_ledger(loaded)
    records = _records_by_chain(current.ledger).get(chain_id)
    if not records:
        _fail("receipt", current.ledger_path, "receipt draft requires an existing chain")
    return tuple(_plan_workstream_record_receipt(current.ledger, record, session_path=session_path,
        entry_id=entry_id, decision_id=decision_id, disposition=disposition) for record in records)


def _plan_workstream_record_receipt(ledger: WorkstreamLedger, record: WorkstreamRecord, *,
        session_path: str, entry_id: str, decision_id: str, disposition: str) -> WorkstreamReceipt:
    """Derive one member mapping from an already classified operation-local ledger."""
    receipt = WorkstreamReceipt(
        ledger.header.workstream_id, record.chain_id, record.record_id, record.detail_digest,
        session_path, entry_id, decision_id,
        workstream_receipt_id(ledger.header.id_salt, ledger.header.workstream_id, record.chain_id, record.detail_digest),
        "sha256:" + "0" * 64, disposition,
    )
    _validate_workstream_receipt(receipt)
    mapping = _member_session_mapping(receipt.workstream_id, receipt)
    digest = workstream_detail_digest(_workstream_yaml_mapping(tuple(mapping.items())))
    return WorkstreamReceipt(**{**receipt.__dict__, "receipt_digest": digest})


def render_workstream_receipt(receipt: WorkstreamReceipt) -> str:
    """Render one member mapping for embedding in a normal decision YAML fence."""
    _validate_workstream_receipt(receipt)
    return _workstream_yaml_mapping(tuple(_member_session_mapping(receipt.workstream_id, receipt).items()))


class GitWorkstreamIntegrationVerifier(TrustedRebindVerifier):
    """Read-only admission of an existing rebind against its actual merge history.

    This does not issue tokens or authorize a new rebind. Every verification
    reloads the committed ledger and measures every ownership transfer's
    introduction, ordered merge parents, and unchanged source ledger.
    """

    def __init__(self, loaded: TrustedWorkstreamLedger):
        self.loaded = loaded

    def witness(self) -> TrustedIntegrationWitness:
        current = _reload_trusted_workstream_ledger(self.loaded)
        if not current.ledger.rebinds:
            _fail("close-authority", current.ledger_path, "close requires a committed integration rebind")
        root = Path(current.repository)
        _initial, _blob, transitions = _ledger_lineage(root, current.head, current.ledger_path)
        # A valid final merge cannot launder an unverified earlier ownership
        # transfer. Admit the complete predecessor chain before its last head.
        for rebind in current.ledger.rebinds:
            witness = self._admit_rebind(current, rebind, transitions)
        return witness

    def _admit_rebind(self, current: TrustedWorkstreamLedger, rebind: TrustedRebind,
                       transitions: tuple[_LedgerTransition, ...]) -> TrustedIntegrationWitness:
        root = Path(current.repository)
        matching = [item for item in transitions
                    if item.blob.content == item.parent_blob.content + b"\n" + render_trusted_rebind(rebind).encode("utf-8")]
        if len(matching) != 1:
            _fail("close-authority", current.ledger_path, "rebind has no exact committed introduction")
        introduction = matching[0]
        code, parents = _git(root, "rev-list", "--parents", "-n", "1", rebind.integration_commit)
        if code or parents.split()[1:] != [rebind.target_pre_merge_tip, rebind.source_tip]:
            _fail("close-authority", current.ledger_path, "integration must bind its ordered target and source merge parents")
        code, parents = _git(root, "rev-list", "--parents", "-n", "1", introduction.commit)
        if code or parents.split()[1:] != [introduction.parent]:
            _fail("close-authority", current.ledger_path, "rebind introduction must have one parent")
        _unchanged_rebind_ancestry(root, rebind.integration_commit, introduction.parent, current.ledger_path)
        source = load_trusted_workstream_ledger(root, trusted_ref=rebind.source_tip, ledger_path=current.ledger_path)
        integrated = _tree_blob(root, rebind.integration_commit, current.ledger_path)
        if (source.raw != introduction.parent_blob.content or source.ledger.effective_branch != rebind.from_branch
                or integrated is None or integrated.mode != CANONICAL_MODE or integrated.content != source.raw
                or workstream_ledger_digest(source.raw) != rebind.pre_ledger_digest):
            _fail("close-authority", current.ledger_path, "integration did not preserve the admitted source ledger")
        return TrustedIntegrationWitness(current.ledger.header.workstream_id, rebind.record_id,
            rebind.from_branch, rebind.to_branch, rebind.source_tip, rebind.target_pre_merge_tip,
            rebind.integration_commit, rebind.pre_ledger_digest)

    def verify_witness(self, witness: TrustedIntegrationWitness) -> bool:
        return witness == self.witness()


class GitWorkstreamReceiptVerifier(WorkstreamReceiptVerifier):
    """Recheck exact durable member mappings in reachable ordinary sessions."""

    def __init__(self, loaded: TrustedWorkstreamLedger, integration_commit: str):
        self.loaded, self.integration_commit = loaded, integration_commit

    def verify(self, admitted: AdmittedWorkstreamReceipt) -> bool:
        current = _reload_trusted_workstream_ledger(self.loaded)
        _check_transaction_receipts(Path(current.repository), current.head, (admitted,),
                                    integration_commit=self.integration_commit)
        return True


def workstream_receipt_mapping(receipt: WorkstreamReceipt) -> dict[str, str]:
    """Project a validated member receipt for the ordinary session writer."""
    _validate_workstream_receipt(receipt)
    return _member_session_mapping(receipt.workstream_id, receipt)


def committed_workstream_receipt(loaded: TrustedWorkstreamLedger, mapping: Mapping[str, str]) -> AdmittedWorkstreamReceipt | None:
    """Measure one exact public member mapping at the selected committed head."""
    receipt = WorkstreamReceipt(**mapping)
    _validate_workstream_receipt(receipt)
    root = Path(loaded.repository)
    blob = _tree_blob(root, loaded.head, receipt.session_path)
    if blob is None or blob.mode != CANONICAL_MODE or not _session_has_exact_yaml_mapping(
            blob.content, receipt.session_path, mapping, entry_id=receipt.entry_id, decision_id=receipt.decision_id):
        return None
    return AdmittedWorkstreamReceipt(receipt, loaded.head, blob.oid)


def workstream_closure_mapping(record: WorkstreamRecord, *, session_path: str, entry_id: str,
                               decision_id: str) -> dict[str, str]:
    """Draft the existing closure-outcome mapping, with a deterministic digest."""
    value = dict(chain_id=record.chain_id, closed_record_id=record.record_id,
                 closed_record_digest=record.detail_digest, session_path=session_path,
                 entry_id=entry_id, decision_id=decision_id, receipt_digest="sha256:" + "0" * 64)
    value["receipt_digest"] = workstream_detail_digest(_workstream_yaml_mapping(tuple(value.items())))
    return value


def _committed_session_mappings(loaded: TrustedWorkstreamLedger) -> list[dict[str, Any]]:
    """Read exact scoped mappings from ordinary committed session decisions."""
    root = Path(loaded.repository)
    code, paths = _git(root, "ls-tree", "-r", "-z", "--name-only", loaded.head, "--", SESSION_ROOT, binary=True)
    if code or not isinstance(paths, bytes):
        _fail("receipt", loaded.ledger_path, "could not inspect ordinary session receipt history")
    mappings = []
    for path in paths.decode("utf-8").split("\0"):
        if not path.startswith(".memory-seed/sessions/") or not path.endswith(".md"):
            continue
        blob = _tree_blob(root, loaded.head, path)
        if blob is None or blob.mode != CANONICAL_MODE:
            continue
        for fence in re.finditer(r"```yaml\n(?P<body>.*?)```", blob.content.decode("utf-8", errors="replace"), re.DOTALL):
            try:
                value = _parse_yaml_mapping(fence.group("body"), path)
            except ReflectionValidationError:
                continue
            if (value.get("session_path") == path and isinstance(value.get("entry_id"), str)
                    and isinstance(value.get("decision_id"), str)
                    and _session_has_exact_yaml_mapping(blob.content, path, value,
                        entry_id=value["entry_id"], decision_id=value["decision_id"])):
                mappings.append(value)
    return mappings


def workstream_closed_receipt_status(loaded: TrustedWorkstreamLedger) -> list[dict[str, Any]]:
    """Expose incomplete closed chains from committed ordinary session scopes."""
    if not any(record.to_phase == "closed" for record in loaded.ledger.records):
        return []
    mappings = _committed_session_mappings(loaded)
    by_record: dict[str, list[dict[str, Any]]] = {}
    by_close: dict[str, list[dict[str, Any]]] = {}
    for value in mappings:
        record_id = value.get("record_id")
        if isinstance(record_id, str):
            by_record.setdefault(record_id, []).append(value)
        closed_record_id = value.get("closed_record_id")
        if isinstance(closed_record_id, str):
            by_close.setdefault(closed_record_id, []).append(value)
    try:
        current = _reload_trusted_workstream_ledger(loaded)
    except ReflectionValidationError:
        # A failed member-receipt validation has always meant missing coverage
        # here. Reuse that outcome too, without reclassifying for each candidate.
        current = None
    results = []
    for chain, records in _records_by_chain(loaded.ledger).items():
        close = records[-1]
        if close.to_phase != "closed":
            continue
        missing = []
        for record in records:
            valid = False
            for value in by_record.get(record.record_id, ()) if current is not None else ():
                try:
                    receipt = WorkstreamReceipt(**value)
                    expected = _plan_workstream_record_receipt(current.ledger, record,
                        session_path=receipt.session_path, entry_id=receipt.entry_id,
                        decision_id=receipt.decision_id, disposition=receipt.disposition)
                    valid = workstream_receipt_mapping(expected) == value
                except (TypeError, ReflectionValidationError):
                    continue
                if valid:
                    break
            if not valid:
                missing.append({"kind": "member", "workstream_id": loaded.ledger.header.workstream_id,
                    "chain_id": chain, "record_id": record.record_id, "detail_digest": record.detail_digest,
                    "receipt_id": workstream_receipt_id(loaded.ledger.header.id_salt,
                        loaded.ledger.header.workstream_id, chain, record.detail_digest)})
        closure_found = any(value == workstream_closure_mapping(close, session_path=value["session_path"],
            entry_id=value["entry_id"], decision_id=value["decision_id"]) for value in by_close.get(close.record_id, ()))
        if not closure_found:
            missing.append({"kind": "closure", "chain_id": chain, "closed_record_id": close.record_id,
                            "closed_record_digest": close.detail_digest})
        results.append({"chain_id": chain, "status": "closed_receipts_pending" if missing else "closed",
                        "missing_receipts": missing})
    return results


def preview_workstream_expiry_commit(cwd: Path | str, *, trusted_ref: str,
                                     workstream_id: str, chain_id: str) -> WorkstreamCommitPreview:
    """Derive elapsed-only cleanup authority internally from host/Git facts."""
    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, trusted_ref)
    head, _inventory = _transaction_context(root, full_ref)
    path = workstream_ledger_path(workstream_id)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=path)
    if loaded.ledger.effective_branch != full_ref.removeprefix("refs/heads/"):
        _fail("expiry", path, "only the effective integration owner can expire a chain")
    _id(chain_id, "rlc_", path, "chain_id")
    _chain_closed_at(loaded.ledger, chain_id)
    anchor = _retention_anchor(root, loaded.ledger.header.base_sha)
    _read_retention_key(root, _parse_retention_trust(anchor.content))
    mappings = sorted(_committed_session_mappings(loaded), key=lambda item: json.dumps(item, sort_keys=True))
    members = []
    for record in _records_by_chain(loaded.ledger)[chain_id]:
        admitted = None
        for mapping in mappings:
            if mapping.get("record_id") != record.record_id:
                continue
            try:
                drafts = plan_workstream_chain_receipts(loaded, chain_id=chain_id,
                    **{key: mapping[key] for key in ("session_path", "entry_id", "decision_id", "disposition")})
                if any(workstream_receipt_mapping(item) == mapping for item in drafts):
                    admitted = committed_workstream_receipt(loaded, mapping)
                    break
            except (KeyError, ReflectionValidationError):
                continue
        if admitted is None:
            _fail("receipt", path, "closed chain has missing durable member receipts", record_id=record.record_id)
        members.append(admitted)
    close = _records_by_chain(loaded.ledger)[chain_id][-1]
    closure_mapping = next((value for value in mappings if value == workstream_closure_mapping(close,
        session_path=value["session_path"], entry_id=value["entry_id"], decision_id=value["decision_id"])), None)
    if closure_mapping is None:
        _fail("receipt", path, "closed chain has no durable closure-outcome receipt")
    closure_blob = _tree_blob(root, head, closure_mapping["session_path"])
    closures = (WorkstreamCompactionClosureReceipt(**closure_mapping, commit=head, blob=closure_blob.oid),)
    member_proofs = tuple(sorted((WorkstreamCompactionMemberReceipt(
        **{key: value for key, value in workstream_receipt_mapping(member.receipt).items() if key != "workstream_id"},
        commit=member.commit, blob=member.blob) for member in members), key=lambda item: (item.chain_id, item.record_id)))
    integration = GitWorkstreamIntegrationVerifier(loaded)
    witness = integration.witness()
    verifier = GitWorkstreamReceiptVerifier(loaded, witness.integration_commit)

    def revalidate():
        current = _reload_trusted_workstream_ledger(loaded)
        _require_unretired_workstream_owner(root, current)
        _read_retention_key(root, _parse_retention_trust(anchor.content))
        preview = preview_trusted_workstream_expiry(current, chain_ids=(chain_id,),
            now=_as_utc(_clock_timestamp()), receipts=members, receipt_verifier=verifier,
            integration_witness=witness, integration_verifier=integration,
            active_ledgers=_transaction_active_ledgers(root, full_ref, current.head))
        return preview.post_ledger, None

    planned = _store_workstream_commit(root, full_ref, head, "expiry", loaded, revalidate)
    template = WorkstreamCompactionReceipt(workstream_id, path, planned.pre_ledger_digest,
        planned.post_ledger_digest, head, loaded.ledger_blob, "0" * 40, "0" * 40, (chain_id,),
        tuple(sorted(item.receipt.record_id for item in members)), closures, member_proofs, "elapsed retention")
    # Validate provenance during preview as well as the final history replay.
    _elapsed_payload(loaded, template, _as_utc(_clock_timestamp()))

    def receipt_factory(cleanup_commit, post_blob):
        receipt = replace(template, cleanup_commit=cleanup_commit, post_blob=post_blob)
        value = _elapsed_payload(loaded, receipt, _as_utc(_clock_timestamp()))
        seed = _read_retention_key(root, _parse_retention_trust(anchor.content))
        _public, signature = _ed25519_sign(seed, _elapsed_signing_bytes(value))
        value["signature"] = "ed25519:" + signature.hex()
        return replace(receipt, elapsed_attestation=_canonical_elapsed_attestation(value, path))

    _WORKSTREAM_COMMIT_PLANS[planned.token] = replace(_WORKSTREAM_COMMIT_PLANS[planned.token], compaction_factory=receipt_factory)
    return planned


def _require_post_integration_receipt(root: Path, admitted: AdmittedWorkstreamReceipt, integration_commit: str) -> None:
    """Every contributing receipt history must descend from this integration.

    Merely citing a newer commit containing an old receipt blob does not make
    that evidence post-integration. Full path history follows every merge
    parent and crosses periods of absence: deleting and restoring the exact
    mapping must not reset its origin. Unchanged snapshots need not be scanned
    because the earlier introduction of their mapping is retained in history.
    """
    receipt = admitted.receipt
    mapping = _member_session_mapping(receipt.workstream_id, receipt)
    code, output = _git(root, "rev-list", "--full-history",
                        f"--max-count={MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS + 1}",
                        admitted.commit, "--", receipt.session_path)
    commits = output.splitlines() if code == 0 and isinstance(output, str) else []
    if not commits or any(not re.fullmatch(r"[0-9a-f]{40}", commit) for commit in commits):
        _fail("receipt-history-missing", receipt.session_path, "could not resolve complete receipt path history")
    commits = tuple(dict.fromkeys((admitted.commit, *commits)))
    if len(commits) > MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS:
        _fail("receipt-history-limit", receipt.session_path, "receipt provenance exceeds the bounded history scan")
    for commit in commits:
        blob = _tree_blob(root, commit, receipt.session_path)
        if (blob is not None and blob.mode == CANONICAL_MODE
                and _session_has_exact_yaml_mapping(blob.content, receipt.session_path, mapping,
                                                   entry_id=receipt.entry_id, decision_id=receipt.decision_id)
                and (commit == integration_commit or not _git_is_ancestor(root, integration_commit, commit))):
            _fail("receipt-integration", receipt.session_path, "durable receipt evidence must originate after the validated integration")


def _validated_receipt_integration(current: TrustedWorkstreamLedger, witness: TrustedIntegrationWitness,
                                   verifier: TrustedRebindVerifier) -> str:
    if not isinstance(witness, TrustedIntegrationWitness):
        _fail("close-authority", current.ledger_path, "receipts require an admitted integration witness")
    rebind = _validate_integration_witness(current.ledger, witness, verifier)
    if not _git_is_ancestor(Path(current.repository), rebind.integration_commit, current.head):
        _fail("close-authority", current.ledger_path, "integration witness is not reachable from the receipt branch")
    return rebind.integration_commit


def _check_transaction_receipts(root: Path, head: str, receipts: Iterable[AdmittedWorkstreamReceipt], *,
                                 integration_commit: str) -> None:
    for admitted in receipts:
        if not isinstance(admitted, AdmittedWorkstreamReceipt):
            _fail("receipt", str(root), "close requires admitted session receipts")
        receipt = admitted.receipt
        _validate_workstream_receipt(receipt)
        raw = _read_session_blob(root, admitted.commit, receipt.session_path, admitted.blob, before=head)
        if not _session_has_exact_yaml_mapping(raw, receipt.session_path, _member_session_mapping(receipt.workstream_id, receipt),
                                               entry_id=receipt.entry_id, decision_id=receipt.decision_id):
            _fail("receipt", receipt.session_path, "committed decision lacks the exact member receipt")
        _require_post_integration_receipt(root, admitted, integration_commit)


def admit_workstream_chain_receipts(loaded: TrustedWorkstreamLedger, *, chain_id: str, session_path: str,
                                     entry_id: str, decision_id: str, disposition: str,
                                     session_ref: str, integration_witness: TrustedIntegrationWitness,
                                     integration_verifier: TrustedRebindVerifier) -> tuple[AdmittedWorkstreamReceipt, ...]:
    """Measure committed receipt locators, avoiding caller-built receipt internals."""
    current = _reload_trusted_workstream_ledger(loaded)
    integration_commit = _validated_receipt_integration(current, integration_witness, integration_verifier)
    root = Path(current.repository)
    commit = _commit(root, session_ref)
    blob = _tree_blob(root, commit, session_path) if commit else None
    if blob is None or blob.mode != CANONICAL_MODE:
        _fail("receipt", session_path, "session ref lacks a canonical receipt blob")
    receipts = tuple(AdmittedWorkstreamReceipt(receipt, commit, blob.oid) for receipt in plan_workstream_chain_receipts(
        current, chain_id=chain_id, session_path=session_path, entry_id=entry_id, decision_id=decision_id, disposition=disposition,
    ))
    _check_transaction_receipts(root, current.head, receipts, integration_commit=integration_commit)
    return receipts


def preview_workstream_close_commit(cwd: Path | str, *, trusted_ref: str, workstream_id: str, chain_id: str,
                                    receipts: Iterable[AdmittedWorkstreamReceipt], receipt_verifier: WorkstreamReceiptVerifier,
                                    integration_witness: TrustedIntegrationWitness, integration_verifier: TrustedRebindVerifier,
                                    conclusion: str, reasoning: str, source: str, confidence: str,
                                    clock: Callable[[], datetime] | None = None) -> WorkstreamCommitPreview:
    """Plan a trusted chain close, deriving complete board context from Git."""
    root = Path(cwd).resolve()
    full_ref = _full_local_branch_ref(root, trusted_ref)
    head, _inventory = _transaction_context(root, full_ref)
    relative = workstream_ledger_path(workstream_id)
    loaded = load_trusted_workstream_ledger(root, trusted_ref=full_ref, ledger_path=relative)
    if loaded.ledger.effective_branch != full_ref[len("refs/heads/"):]:
        _fail("close-authority", relative, "only the effective integration branch may close")
    receipts = deepcopy(tuple(receipts))
    integration_witness = deepcopy(integration_witness)
    created = _as_utc(_clock_timestamp(clock))

    def revalidate():
        current = _reload_trusted_workstream_ledger(loaded)
        _require_unretired_workstream_owner(root, current)
        integration_commit = _validated_receipt_integration(current, integration_witness, integration_verifier)
        _check_transaction_receipts(root, current.head, receipts, integration_commit=integration_commit)
        anchor = _retention_anchor(root, current.ledger.header.base_sha)
        _read_retention_key(root, _parse_retention_trust(anchor.content))
        if len(workstream_chain_heads(current.ledger, chain_id)) != 1:
            _fail("close", relative, "resolve or explicitly dispose divergent heads before close")
        return plan_trusted_workstream_chain_close(
            current, chain_id=chain_id, receipts=receipts, receipt_verifier=receipt_verifier,
            integration_witness=integration_witness, integration_verifier=integration_verifier,
            conclusion=conclusion, reasoning=reasoning, source=source, confidence=confidence, clock=lambda: created,
            active_ledgers=_transaction_active_ledgers(root, full_ref, current.head),
        ), None

    return _store_workstream_commit(root, full_ref, head, "close", loaded, revalidate)


def _index_path_state(root: Path, relative: str) -> str:
    code, state = _git(root, "ls-files", "-s", "--", relative)
    if code or not isinstance(state, str):
        _fail("append-worktree-not-clean", relative, "could not inspect transaction path index state")
    return state


def _blob_index_state(blob: GitBlob | None) -> str:
    return f"{blob.mode} {blob.oid} 0\t{blob.path}" if blob is not None else ""


def _owned_path_state(root: Path, path: Path, raw: bytes | None, index: str,
                      pre_blob: GitBlob | None, *, check_committed_preimage: bool = True) -> bool:
    """Check byte/index ownership, plus the committed preimage for sessions."""
    relative = path.relative_to(root).as_posix()
    if check_committed_preimage:
        head = _commit(root, "HEAD")
        committed = _tree_blob(root, head, relative) if head is not None else None
        if _blob_index_state(committed) != _blob_index_state(pre_blob):
            return False
    if _index_path_state(root, relative) != index:
        return False
    if path.is_symlink() or path.resolve() != path:
        return False
    return (path.is_file() and path.read_bytes() == raw) if raw is not None else not path.exists()


def _restore_workstream_worktree(root: Path, path: Path, raw: bytes, blob: GitBlob | None,
                                 created_directories: Sequence[Path], *, restore_path: bool,
                                 owned_raw: bytes | None, owned_index: str,
                                 check_committed_preimage: bool = True) -> bool:
    try:
        for candidate in (path, *path.parents):
            if candidate == root:
                break
            if not candidate.exists() and not candidate.is_symlink():
                continue
            metadata = candidate.lstat()
            if (stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_reparse_tag", None)
                    == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)):
                return False
        if not _owned_path_state(root, path, owned_raw, owned_index, blob,
                                 check_committed_preimage=check_committed_preimage):
            return False
        if blob is None:
            if restore_path:
                path.unlink(missing_ok=True)
            relative = path.relative_to(root).as_posix()
            code, _output = _git(root, "update-index", "--force-remove", "--", relative)
            if code:
                return False
            for directory in reversed(created_directories):
                directory.rmdir()
            code, index = _git(root, "ls-files", "-s", "--", relative)
            return code == 0 and not index and not path.exists()
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


def _workstream_commit_message(preview: WorkstreamCommitPreview, workstream_id: str) -> str:
    return (
        f"reflection: {preview.operation} {preview.record_id or workstream_id}\n\n"
        f"Reflection-Workstream: {workstream_id}\n"
        + (f"Reflection-Record: {preview.record_id}\n" if preview.record_id else "")
        +
        f"Reflection-Pre-Ledger-Digest: {preview.pre_ledger_digest or 'absent'}\n"
        f"Reflection-Post-Ledger-Digest: {preview.post_ledger_digest}"
    )


def apply_workstream_append_commit(cwd: Path | str, preview: WorkstreamAppendCommitPreview, *,
                                   fault_injector: Callable[[str], None] | None = None) -> WorkstreamAppendCommitResult:
    """Append entry point into the single kernel transaction writer."""
    if not isinstance(preview, WorkstreamAppendCommitPreview) or preview.operation != "append":
        _fail("append-commit-failed", "ledger append", "append apply requires a host-issued append preview")
    result = apply_workstream_commit(cwd, preview, fault_injector=fault_injector)
    return WorkstreamAppendCommitResult(**result.__dict__)


def apply_workstream_commit(cwd: Path | str, preview: WorkstreamCommitPreview, *,
                            fault_injector: Callable[[str], None] | None = None) -> WorkstreamCommitResult:
    """Persist every reflection operation through one transaction/ref-CAS.

    ``fault_injector`` is test-only adapter instrumentation; it receives no
    authority fields and makes rollback paths observable without broadening the
    public plan surface.
    """
    if not isinstance(preview, WorkstreamCommitPreview):
        _fail("append-commit-failed", "ledger transaction", "apply requires a kernel-issued opaque preview")
    stored = _WORKSTREAM_COMMIT_PLANS.get(preview.token)
    if stored is None or stored.preview != preview:
        _fail("append-commit-failed", "ledger append", "append preview is unknown, replaced, or expired")
    root = Path(cwd).resolve()
    if str(root) != stored.repository:
        _fail("transaction-worktree", str(root), "preview belongs to a different exact worktree")
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
    _transaction_context(root, preview.trusted_ref)
    loaded = (load_trusted_workstream_ledger(root, trusted_ref=preview.trusted_ref, ledger_path=preview.ledger_path)
              if preview.operation not in {"init", "trust_init"} else None)
    pre_raw = loaded.raw if loaded is not None else b""
    if ((loaded.ledger_blob if loaded else None) != preview.expected_ledger_blob
            or (workstream_ledger_digest(pre_raw) if loaded else "") != preview.pre_ledger_digest):
        _fail("stale_ledger_digest", preview.ledger_path, "trusted ledger blob changed after append preview")
    if (loaded.history_fingerprint if loaded else "") != preview.history_fingerprint:
        _fail("stale_ledger_history", preview.ledger_path, "trusted ledger history changed after append preview")
    post, witness = stored.revalidate()
    post_raw = preview.suffix_bytes if preview.operation == "expiry" else pre_raw + preview.suffix_bytes
    if workstream_ledger_digest(post_raw) != preview.post_ledger_digest:
        _fail("append-commit-failed", preview.ledger_path, "preview suffix no longer has its predicted canonical digest")
    rendered = _render_retention_trust(post) if preview.operation == "trust_init" else render_workstream_ledger(post)
    if stored.post_raw != post_raw or rendered.encode("utf-8") != post_raw:
        _fail("append-commit-failed", preview.ledger_path, "preview suffix does not match its stored canonical post-image")
    path = root / Path(preview.ledger_path)
    if loaded is not None and (not path.is_file() or path.read_bytes() != loaded.raw):
        _fail("append-worktree-not-clean", preview.ledger_path, "working-tree ledger is not the trusted committed blob")
    expected_blob = _tree_blob(root, preview.expected_head, preview.ledger_path)
    if (expected_blob is None) != (preview.operation in {"init", "trust_init"}):
        _fail("append-commit-failed", preview.ledger_path, "preview head no longer exposes its ledger blob")
    if loaded is None and (path.exists() or path.is_symlink()):
        _fail("workstream-collision", preview.ledger_path, "initialization path is already occupied")
    wrote_candidate = False
    created_directories: list[Path] = []
    session_path, session_blob, session_raw = None, None, b""
    session_directories: list[Path] = []
    session_owned_raw, session_owned_index = None, ""
    ledger_owned_index = _blob_index_state(expected_blob)
    elapsed_receipt, close_time = None, None
    try:
        if loaded is None:
            missing = []
            directory = path.parent
            while not directory.exists():
                missing.append(directory)
                directory = directory.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_directories.append(directory)
            with path.open("xb") as stream:
                wrote_candidate = True
                stream.write(post_raw)
        else:
            wrote_candidate = True
            path.write_bytes(post_raw)
        code, _output = _git(root, "add", "--", preview.ledger_path)
        if code:
            raise RuntimeError("git add failed")
        code, post_oid = _git(root, "hash-object", "--stdin", input=post_raw)
        if code or not isinstance(post_oid, str) or not re.fullmatch(r"[0-9a-f]{40}", post_oid):
            raise RuntimeError("could not identify transaction-owned ledger bytes")
        ledger_owned_index = f"{CANONICAL_MODE} {post_oid} 0\t{preview.ledger_path}"
        code, tree = _git(root, "write-tree")
        if code or not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
            raise RuntimeError("git write-tree failed")
        if preview.operation == "trust_init":
            _public, signature = _ed25519_sign(_read_retention_key(root, post), _trust_bootstrap_payload(preview.expected_head, post_raw))
            message = "reflection: trust init\n\nReflection-Trust-Proof: ed25519:" + signature.hex()
        else:
            message = _workstream_commit_message(preview, post.header.workstream_id)
            if preview.operation == "close":
                close_time = _close_time_payload(loaded, post.records[-1], post_oid, _as_utc(_clock_timestamp()))
                anchor = _retention_anchor(root, loaded.ledger.header.base_sha)
                seed = _read_retention_key(root, _parse_retention_trust(anchor.content))
                _public, signature = _ed25519_sign(seed, _close_time_signing_bytes(close_time))
                close_time["signature"] = "ed25519:" + signature.hex()
                message += "\nReflection-Close-Time: " + json.dumps(close_time, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
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
        if close_time is not None:
            _verified_close_time(root, post.records[-1], _LedgerTransition(candidate, preview.expected_head, expected_blob, candidate_blob))
        if preview.operation == "expiry":
            if stored.compaction_factory is None:
                _fail("expiry", preview.ledger_path, "expiry plan has no kernel receipt constructor")
            cleanup = candidate
            if fault_injector is not None:
                fault_injector("after-cleanup-commit")
            elapsed_receipt = stored.compaction_factory(cleanup, candidate_blob.oid)
            # The ordinary session author owns target resolution, chronology,
            # IDs, canonical entry structure and append-only persistence.
            from .core import session_append_entry
            session_args = dict(title=f"Reflection compaction {cleanup}", user_initials="MS", agent_type="memory-seed",
                body="### Summary\n\nExpired one closed reflection chain after signed elapsed retention. "
                    + EXPIRY_DISCLOSURE
                    + "\n\n### Records\n\n#### D1 - Documentation: Record reflection compaction\n\n"
                    + "- D: Recorded the signed elapsed-retention compaction receipt.\n"
                    + "  - Scope: The expired closed reflection chain and its ordinary session receipt.\n"
                    + "\n### Reflection workstream compaction\n\n```yaml\n"
                    + render_workstream_compaction_receipt(elapsed_receipt) + "```\n")
            session_preview = session_append_entry(root, **session_args, dry_run=True)
            if not session_preview.ok:
                _fail("expiry-session", preview.ledger_path, "ordinary session preview refused compaction", issues=session_preview.issues)
            selected_session = session_preview.path
            relative = selected_session.relative_to(root).as_posix()
            _session_path(relative, relative, "compaction session")
            for ancestor in (selected_session, *selected_session.parents):
                if ancestor == root:
                    break
                if ancestor.is_symlink() or ancestor.resolve() != ancestor:
                    _fail("expiry-session", relative, "session target cannot traverse a link or junction")
            session_blob = _tree_blob(root, preview.expected_head, relative)
            session_raw = session_blob.content if session_blob else b""
            if (selected_session.exists() and selected_session.read_bytes() != session_raw) or (session_blob and session_blob.mode != CANONICAL_MODE):
                _fail("expiry-session", relative, "session target differs from committed preimage")
            session_owned_index = _blob_index_state(session_blob)
            if _index_path_state(root, relative) != session_owned_index:
                _fail("expiry-session", relative, "session index differs from committed preimage")
            if session_preview.rendered is None or session_preview.sidecar_paths:
                _fail("expiry-session", relative, "ordinary session preview changed its exact single-path target")
            session_path = selected_session
            session_owned_raw = session_raw if session_blob is not None else None

            def authored(mutation):
                nonlocal session_owned_raw
                # Only the ordinary author knows a new per-user file's exact
                # generated frontmatter. Follow its creation/append receipts;
                # never adopt bytes read back after a potentially raced write.
                if (mutation.path != session_path or mutation.preimage != session_owned_raw
                        or mutation.created != (session_owned_raw is None)):
                    _fail("expiry-session", relative, "ordinary session mutation does not extend the owned preimage")
                session_owned_raw = mutation.postimage

            directory = session_path.parent
            while not directory.exists():
                session_directories.insert(0, directory)
                directory = directory.parent
            written = session_append_entry(root, **session_args, timestamp=session_preview.timestamp,
                                           _mutation_observer=authored)
            if not written.ok or written.entry_id != session_preview.entry_id or written.path != session_path:
                _fail("expiry-session", relative, "ordinary session author refused the exact compaction entry")
            if (session_owned_raw is None or session_path.read_bytes() != session_owned_raw
                    or not session_owned_raw.startswith(session_raw)):
                _fail("expiry-session", relative, "compaction session differs from its exact authored post-image")
            code, _output = _git(root, "add", "--", relative)
            if code:
                raise RuntimeError("could not stage ordinary compaction receipt")
            code, session_oid = _git(root, "hash-object", "--stdin", input=session_owned_raw)
            if code or not isinstance(session_oid, str) or not re.fullmatch(r"[0-9a-f]{40}", session_oid):
                raise RuntimeError("could not identify transaction-owned session bytes")
            session_owned_index = f"{CANONICAL_MODE} {session_oid} 0\t{relative}"
            code, tree = _git(root, "write-tree")
            if code:
                raise RuntimeError("could not construct compaction receipt tree")
            code, candidate = _git(root, "commit-tree", tree, "-p", cleanup, "-m",
                f"reflection: record compaction {post.header.workstream_id}\n\nMemory-Entry: {written.entry_id}")
            if code:
                raise RuntimeError("could not construct compaction receipt commit")
            if fault_injector is not None:
                fault_injector("after-receipt-commit")
            _validate_cleanup_pair(root, _LedgerTransition(cleanup, preview.expected_head, expected_blob, candidate_blob),
                elapsed_receipt, candidate, relative, written.entry_id, loaded.ledger, post_raw)
            load_trusted_workstream_ledger(root, trusted_ref=candidate, ledger_path=preview.ledger_path)
        reflection_commit_admission(root, candidate=candidate, plan=preview)
        if fault_injector is not None:
            fault_injector("before-cas")
        if elapsed_receipt is not None and _as_utc(_clock_timestamp()) > _as_utc(json.loads(elapsed_receipt.elapsed_attestation)["expires_at"]):
            _fail("compaction-proof-retention", preview.ledger_path, "host elapsed attestation expired before CAS")
        if close_time is not None and _as_utc(_clock_timestamp()) > _as_utc(close_time["expires_at"]):
            _fail("close-time-proof", preview.ledger_path, "host close-time observation expired before CAS")
        code, attached = _git(root, "symbolic-ref", "--quiet", "HEAD")
        if code or attached != preview.trusted_ref:
            _fail("append-wrong-branch", str(root), "HEAD attachment changed during transaction")
        # Detect index/worktree mutation after staging, including ignored
        # reserved paths and links. The branch itself is checked by ref CAS.
        _check_reflection_worktree(root, _reflection_tree_inventory(root, candidate))
        code, current_tree = _git(root, "write-tree")
        if code or current_tree != tree:
            _fail("append-worktree-not-clean", str(root), "index changed during transaction")
        if session_path is not None and not _owned_path_state(root, session_path, session_owned_raw, session_owned_index, session_blob):
            _fail("expiry-session", str(session_path), "compaction session changed during transaction")
        # Git holds all participating ref locks through prepare/commit. Rebind
        # verifies its source in the very transaction that advances the target;
        # an extra pre-CAS read would leave the same race window open.
        commands = ["start"]
        for ref, expected in stored.verify_refs:
            if ref != preview.trusted_ref:
                commands.append(f"verify {ref} {expected}")
            elif expected != preview.expected_head:
                _fail("stale_ref", preview.ledger_path, "source and target expectations disagree")
        commands.extend((f"update {preview.trusted_ref} {candidate} {preview.expected_head}", "prepare", "commit"))
        code, _output = _git(root, "update-ref", "--stdin", input=("\n".join(commands) + "\n").encode("utf-8"))
        if code:
            _fail("stale_ref", preview.ledger_path, "a bound source or target ref changed during transaction compare-and-swap")
    except Exception as exc:
        conflicts = []
        if session_path is not None and not _restore_workstream_worktree(
            root, session_path, session_raw, session_blob, session_directories, restore_path=True,
            owned_raw=session_owned_raw, owned_index=session_owned_index,
        ):
            conflicts.append(session_path.relative_to(root).as_posix())
        if (wrote_candidate or created_directories) and not _restore_workstream_worktree(
            root, path, pre_raw, expected_blob, created_directories, restore_path=wrote_candidate,
            owned_raw=post_raw if wrote_candidate else None, owned_index=ledger_owned_index,
            # Preserve the established ledger rollback contract after a raw
            # ref rewind, but never replace concurrent worktree/index bytes.
            check_committed_preimage=False,
        ):
            conflicts.append(preview.ledger_path)
        if conflicts:
            _fail("append-rollback-conflict", str(root), "concurrent or unowned content preserved; inspect transaction paths before retrying",
                  preserved_paths=conflicts, reason=str(exc))
        if isinstance(exc, ReflectionValidationError):
            raise
        _fail("append-commit-failed", preview.ledger_path, "could not construct canonical ledger-only append commit", reason=str(exc))
    _WORKSTREAM_COMMIT_PLANS.pop(preview.token, None)
    if preview.operation == "trust_init":
        _retention_anchor(root, candidate)
        return WorkstreamCommitResult(candidate, candidate_blob.oid, preview.post_ledger_digest, "", None, None)
    final = load_trusted_workstream_ledger(root, trusted_ref=preview.trusted_ref, ledger_path=preview.ledger_path)
    if final.head != candidate or final.ledger_blob != candidate_blob.oid:
        _fail("append-commit-failed", preview.ledger_path, "successful CAS is not immediately visible to trusted readers")
    return WorkstreamCommitResult(final.head, final.ledger_blob, workstream_ledger_digest(final.raw),
                                  final.history_fingerprint, preview.record_id, final.ledger, witness)


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
    nonce_identity = ("memory-seed/reflection-retention-approval", 1, preflight.key_id, preflight.nonce)
    locator_identity = (preflight.session_path, preflight.entry_id, approval.commit, approval.blob)
    for other in admitted_headers:
        if other.workstream_id == header.workstream_id or other.retention_extension_receipt is None:
            continue
        other_nonce = ("memory-seed/reflection-retention-approval", 1, other.retention_approval_key_id, other.retention_extension_receipt.nonce)
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
