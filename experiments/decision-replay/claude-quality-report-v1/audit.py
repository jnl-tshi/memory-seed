"""Audit a Claude JSONL transcript for exposure, uptake, timing, and validation breadth."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from prepare import RELEVANT_ENTRY_IDS

RECEIPT_RE = re.compile(r"^CONTEXT_RECEIPT:\s*(ctx_[a-f0-9]+)\s*$", re.MULTILINE)
MEMORY_REPORT_RE = re.compile(r"Memory evidence used:\s*([^\r\n]+)", re.IGNORECASE)
TEST_MARKERS = ("pytest", "unittest", "test_quality", "verify")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds(start: dt.datetime | None, end: dt.datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def audit_transcript(fixture: Path, transcript: Path) -> dict:
    context = (fixture / "EXPERIMENT_CONTEXT.md").read_text(encoding="utf-8")
    match = RECEIPT_RE.search(context)
    if not match:
        raise ValueError("fixture context has no valid CONTEXT_RECEIPT")
    receipt = match.group(1)

    events: list[dict] = []
    invalid_lines = 0
    with transcript.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if isinstance(value, dict):
                events.append(value)

    timestamps = [stamp for event in events if (stamp := _timestamp(event.get("timestamp")))]
    assistant_texts: list[tuple[dt.datetime | None, str, str | None]] = []
    context_strings: list[str] = []
    tool_calls: dict[str, dict] = {}
    assistant_messages: dict[str, dict] = {}
    models: set[str] = set()
    versions: set[str] = set()
    session_ids: set[str] = set()

    for event in events:
        stamp = _timestamp(event.get("timestamp"))
        if event.get("subtype") == "init":
            init_model = event.get("model")
            init_version = event.get("claude_code_version")
            if isinstance(init_model, str):
                models.add(init_model)
            if isinstance(init_version, str):
                versions.add(init_version)
        version = event.get("version")
        if isinstance(version, str):
            versions.add(version)
        session_id = event.get("sessionId") or event.get("session_id")
        if isinstance(session_id, str):
            session_ids.add(session_id)

        message = event.get("message")
        is_assistant = isinstance(message, dict) and message.get("role") == "assistant"
        if is_assistant:
            model = message.get("model")
            if isinstance(model, str):
                models.add(model)
            message_id = message.get("id") or event.get("uuid")
            if isinstance(message_id, str):
                assistant_messages[message_id] = message
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        assistant_texts.append((stamp, item["text"], message.get("stop_reason")))
                    if item.get("type") == "tool_use":
                        tool_id = item.get("id") or f"anonymous-{len(tool_calls)}"
                        tool_calls[str(tool_id)] = {
                            "timestamp": stamp,
                            "name": item.get("name"),
                            "input": item.get("input"),
                        }
        else:
            context_strings.extend(_strings(event))

    final_candidates = [item for item in assistant_texts if item[2] == "end_turn"]
    final_stamp, final_text, _ = (final_candidates or assistant_texts or [(None, "", None)])[-1]
    all_context = "\n".join(context_strings)
    memory_match = MEMORY_REPORT_RE.search(final_text)
    memory_report = memory_match.group(1).strip() if memory_match else None
    reported_ids = [entry_id for entry_id in RELEVANT_ENTRY_IDS if entry_id in (memory_report or "")]

    context_calls = [
        call
        for call in tool_calls.values()
        if "EXPERIMENT_CONTEXT.md" in json.dumps(call.get("input"), ensure_ascii=False)
    ]
    edit_stamps = [
        call["timestamp"]
        for call in tool_calls.values()
        if call.get("name") in EDIT_TOOLS and call.get("timestamp") is not None
    ]
    validation_commands = []
    for call in tool_calls.values():
        rendered = json.dumps(call.get("input"), ensure_ascii=False)
        if call.get("name") in {"Bash", "PowerShell"} and any(
            marker in rendered.lower() for marker in TEST_MARKERS
        ):
            validation_commands.append(rendered)

    start = min(timestamps) if timestamps else None
    end = final_stamp or (max(timestamps) if timestamps else None)
    last_edit = max(edit_stamps) if edit_stamps else None
    output_tokens = 0
    for message in assistant_messages.values():
        usage = message.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("output_tokens"), int):
            output_tokens += usage["output_tokens"]

    relevant_exposed = [entry_id for entry_id in RELEVANT_ENTRY_IDS if entry_id in all_context]
    packet_uptake = bool(context_calls) and receipt in all_context and receipt in final_text
    rationale_confirmed = bool(relevant_exposed) and bool(reported_ids)
    return {
        "schema_version": 1,
        "fixture": str(fixture.resolve()),
        "transcript": str(transcript.resolve()),
        "invalid_json_lines": invalid_lines,
        "models": sorted(models),
        "claude_versions": sorted(versions),
        "session_ids": sorted(session_ids),
        "timing": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "elapsed_seconds": _seconds(start, end),
            "last_structured_edit": last_edit.isoformat() if last_edit else None,
            "time_to_last_structured_edit_seconds": _seconds(start, last_edit),
            "post_structured_edit_tail_seconds": _seconds(last_edit, end),
        },
        "activity": {
            "unique_assistant_messages": len(assistant_messages),
            "tool_calls": len(tool_calls),
            "output_tokens": output_tokens,
            "validation_command_count": len(validation_commands),
            "validation_commands": validation_commands,
        },
        "manipulation_check": {
            "context_read_tool_call": bool(context_calls),
            "context_receipt_reached_tool_result": receipt in all_context,
            "context_receipt_reported_in_final": receipt in final_text,
            "context_packet_uptake_confirmed": packet_uptake,
            "memory_evidence_report": memory_report,
            "relevant_entry_ids_exposed": relevant_exposed,
            "relevant_entry_ids_reported_used": reported_ids,
            "relevant_rationale_uptake_confirmed": rationale_confirmed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_transcript(args.fixture.resolve(), args.transcript.resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
