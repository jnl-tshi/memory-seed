from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from .models import CaptureEvent, Diagnostic, ParserState, SourceCoordinate


SCHEMA_VERSION = "p0.2-codex-rollout-v1"
ALLOWED_CLI_VERSIONS = frozenset({"0.158.0-alpha.2.1"})
ALLOWED_TOP_LEVEL_TYPES = frozenset(
    {
        "session_meta",
        "event_msg",
        "response_item",
        "world_state",
        "turn_context",
        "token_usage_record",
        "inter_agent_communication_metadata",
        "realtime_item",
        "retained_context",
        "compacted",
    }
)
_HIDDEN_REASONING_KEYS = frozenset({"encrypted_content", "content", "raw_content"})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _diagnostic(code: str, detail: str, raw: bytes, coordinate: SourceCoordinate) -> Diagnostic:
    return Diagnostic(code, detail, _digest(raw), _source(coordinate))


def _source(coordinate: SourceCoordinate) -> dict[str, Any]:
    return {
        "path": coordinate.path,
        "source_ordinal": coordinate.source_ordinal,
        "byte_offset": coordinate.byte_offset,
        "generation": coordinate.generation,
    }


def _redacted_payload(row_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if row_type != "response_item" or payload.get("type") != "reasoning":
        return payload
    return {key: value for key, value in payload.items() if key not in _HIDDEN_REASONING_KEYS}


def _actor(row_type: str, subtype: str | None, payload: dict[str, Any]) -> tuple[str, str]:
    if row_type == "response_item" and subtype == "message":
        role = payload.get("role")
        if role == "user":
            return "user", "raw_role"
        if role in {"assistant", "agent"}:
            return "agent", "raw_role"
        if role in {"system", "developer"}:
            return "system", "raw_role"
    if row_type == "response_item" and subtype in {"custom_tool_call", "function_call", "function_call_output"}:
        return "tool", "raw_type"
    if row_type == "event_msg" and subtype == "user_message":
        return "unknown", "unattested_projection"
    if row_type == "event_msg" and subtype in {"agent_message", "agent_reasoning"}:
        return "agent", "raw_type"
    if row_type in {"session_meta", "turn_context", "world_state"}:
        return "system", "raw_type"
    return "unknown", "none"


def _category(row_type: str, subtype: str | None) -> str:
    if row_type == "session_meta":
        return "session"
    if row_type == "turn_context":
        return "turn"
    if row_type == "response_item" and subtype == "message":
        return "message"
    if row_type == "response_item" and subtype in {"custom_tool_call", "function_call", "function_call_output"}:
        return "tool"
    if row_type == "response_item" and subtype == "reasoning":
        return "reasoning_summary"
    return "event"


def parse_complete_line(
    state: ParserState,
    raw_line: bytes,
    coordinate: SourceCoordinate,
) -> tuple[ParserState, CaptureEvent | None, Diagnostic | None]:
    raw = raw_line.removesuffix(b"\r")
    try:
        row = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return state, None, _diagnostic("malformed_json", str(exc), raw, coordinate)
    if not isinstance(row, dict) or not isinstance(row.get("type"), str) or not isinstance(row.get("payload"), dict):
        return state, None, _diagnostic("unknown_shape", "row requires string type and object payload", raw, coordinate)

    row_type = row["type"]
    payload = row["payload"]
    subtype = payload.get("type") if isinstance(payload.get("type"), str) else None
    canonical = _canonical(row)
    raw_sha = _digest(canonical)

    if state.failed_closed:
        return state, None, _diagnostic("parser_failed_closed", "earlier schema/version validation failed", raw, coordinate)

    next_state = state
    if row_type == "session_meta":
        version = payload.get("cli_version")
        if version not in ALLOWED_CLI_VERSIONS:
            return replace(state, failed_closed=True), None, _diagnostic(
                "unsupported_cli_version", f"unsupported cli_version: {version!r}", raw, coordinate
            )
        parent = payload.get("parent_id") or payload.get("parent_rollout_id")
        next_state = replace(
            state,
            session_id=payload.get("id") if isinstance(payload.get("id"), str) else None,
            cli_version=version,
            cwd=payload.get("cwd") if isinstance(payload.get("cwd"), str) else None,
            repository=payload.get("git") if isinstance(payload.get("git"), dict) else {},
            parent_rollout_id=parent if isinstance(parent, str) else None,
        )
    elif state.cli_version not in ALLOWED_CLI_VERSIONS:
        return replace(state, failed_closed=True), None, _diagnostic(
            "missing_validated_session_meta", "event occurred before validated session_meta", raw, coordinate
        )
    elif row_type == "turn_context":
        turn_id = payload.get("turn_id") or payload.get("id")
        turn_index = payload.get("turn_index")
        next_state = replace(
            state,
            turn_id=turn_id if isinstance(turn_id, str) else state.turn_id,
            turn_index=turn_index if isinstance(turn_index, int) else state.turn_index,
        )

    unsupported = row_type not in ALLOWED_TOP_LEVEL_TYPES
    category = "unsupported" if unsupported else _category(row_type, subtype)
    actor, attestation = _actor(row_type, subtype, payload)
    safe_payload = _redacted_payload(row_type, payload)
    unavailable: list[str] = []
    if next_state.parent_rollout_id is None:
        unavailable.append("parent_rollout_id")
    if next_state.turn_id is None:
        unavailable.append("turn_id")
    if next_state.turn_index is None:
        unavailable.append("turn_index")
    event_id = _digest(
        f"{coordinate.rollout_id}:{coordinate.source_ordinal}:".encode("utf-8") + canonical
    )
    event = CaptureEvent(
        schema_version=SCHEMA_VERSION,
        event_id=event_id,
        rollout_id=coordinate.rollout_id,
        session_id=next_state.session_id,
        source_ordinal=coordinate.source_ordinal,
        timestamp=row.get("timestamp") if isinstance(row.get("timestamp"), str) else None,
        category=category,
        raw_type=row_type,
        raw_subtype=subtype,
        actor=actor,
        attestation=attestation,
        turn_id=next_state.turn_id,
        turn_index=next_state.turn_index,
        repository={"cwd": next_state.cwd, **next_state.repository},
        source=_source(coordinate),
        full_payload=safe_payload,
        raw_sha256=raw_sha,
        unavailable_fields=unavailable,
    )
    diagnostic = _diagnostic("unsupported_row", f"unsupported row type: {row_type}", raw, coordinate) if unsupported else None
    return next_state, event, diagnostic
