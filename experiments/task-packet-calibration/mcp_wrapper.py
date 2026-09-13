"""Experiment-only, read-only Memory Seed MCP facade with call auditing."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed import mcp_server

try:  # Package import under pytest; direct-script fallback for the CLI.
    from .contracts import READ_ONLY_TOOLS
except ImportError:  # pragma: no cover - exercised by live direct-script runs
    from contracts import READ_ONLY_TOOLS


def filtered_tools() -> list[dict[str, Any]]:
    return [
        {**tool, "annotations": {"readOnlyHint": True}}
        for tool in mcp_server.TOOLS
        if tool["name"] in READ_ONLY_TOOLS
    ]


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _evidence_ids(value: Any) -> list[str]:
    found: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {"id", "adr_id", "entry_id", "chunk_id"} and isinstance(child, str):
                    found.add(child)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return sorted(found)


def _append_audit(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def handle_message(
    message: dict[str, Any], *, fixture_cwd: Path, audit_log: Path
) -> dict[str, Any] | None:
    message_id, method = message.get("id"), message.get("method")
    if method == "initialize":
        return _result(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "task-packet-calibration", "version": "1"},
                "capabilities": {"tools": {}},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(message_id, {"tools": filtered_tools()})
    if method != "tools/call":
        return _error(message_id, -32601, f"Method not found: {method}")

    params = message.get("params") or {}
    name = params.get("name")
    if name not in READ_ONLY_TOOLS:
        return _error(message_id, -32602, f"Tool is not allowlisted: {name}")
    supplied = params.get("arguments") or {}
    if not isinstance(supplied, dict):
        return _error(message_id, -32602, "tool arguments must be an object")
    effective = {**supplied, "cwd": str(fixture_cwd.resolve())}
    try:
        payload = mcp_server.call_tool(str(name), effective)
        rendered = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        _append_audit(
            audit_log,
            {
                "sequence": sum(1 for _ in audit_log.open(encoding="utf-8")) + 1
                if audit_log.exists()
                else 1,
                "tool": name,
                "model_arguments": supplied,
                "effective_cwd": str(fixture_cwd.resolve()),
                "result_chars": len(rendered),
                "result_digest": "sha256:" + hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                "evidence_ids": _evidence_ids(payload),
            },
        )
        return _result(message_id, {"content": [{"type": "text", "text": rendered}]})
    except Exception as exc:  # mirrors the production MCP error boundary
        _append_audit(
            audit_log,
            {"tool": name, "model_arguments": supplied, "error": f"{type(exc).__name__}: {exc}"},
        )
        return _error(message_id, -32603, str(exc))


def serve(fixture_cwd: Path, audit_log: Path, input_stream=None, output_stream=None) -> int:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for line in input_stream:
        if not line.strip():
            continue
        try:
            response = handle_message(
                json.loads(line), fixture_cwd=fixture_cwd, audit_log=audit_log
            )
        except Exception as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            output_stream.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--audit-log", required=True, type=Path)
    args = parser.parse_args(argv)
    return serve(args.fixture, args.audit_log)


if __name__ == "__main__":
    raise SystemExit(main())
