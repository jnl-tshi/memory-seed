from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceCoordinate:
    rollout_id: str
    path: str
    source_ordinal: int
    byte_offset: int
    generation: int


@dataclass(frozen=True)
class ParserState:
    session_id: str | None = None
    cli_version: str | None = None
    cwd: str | None = None
    repository: dict[str, Any] = field(default_factory=dict)
    parent_rollout_id: str | None = None
    turn_id: str | None = None
    turn_index: int | None = None
    failed_closed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ParserState":
        return cls(**(value or {}))


@dataclass(frozen=True)
class CaptureEvent:
    schema_version: str
    event_id: str
    rollout_id: str
    session_id: str | None
    source_ordinal: int
    timestamp: str | None
    category: str
    raw_type: str
    raw_subtype: str | None
    actor: str
    attestation: str
    turn_id: str | None
    turn_index: int | None
    repository: dict[str, Any]
    source: dict[str, Any]
    full_payload: dict[str, Any]
    raw_sha256: str
    unavailable_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    detail: str
    raw_sha256: str
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCursor:
    source_key: str
    path: str
    generation: int
    file_identity: str
    head_sha256: str
    byte_offset: int
    source_ordinal: int
    parser_state: ParserState
    discard_until_newline: bool = False
