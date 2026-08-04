"""Read-only, experiment-local MCP facade for context-derivation fixtures.

The production server deliberately contains write tools.  This process is a narrow
stdio facade, rather than a modified production server, so an experiment cannot
accidentally advertise those tools to a subject.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from memory_seed import mcp_server

SEARCH_TOOLS = frozenset({"memory_search", "memory_get_chunk"})
WORKFLOW_TOOLS = frozenset({
    *SEARCH_TOOLS,
    "memory_adrs_list", "memory_adr_show", "memory_adr_review", "memory_adrs_check",
    "memory_retrieval_spec_preview", "memory_retrieval_spec_resolve",
})
ARM_TOOLS = {"search-mcp": SEARCH_TOOLS, "adr-mcp-workflow": WORKFLOW_TOOLS}


def allowed_names(arm: str) -> frozenset[str]:
    try:
        return ARM_TOOLS[arm]
    except KeyError as exc:
        raise ValueError(f"MCP is not available for arm {arm!r}") from exc


def filtered_tools(arm: str) -> list[dict[str, Any]]:
    allowed = allowed_names(arm)
    return [tool for tool in mcp_server.TOOLS if tool["name"] in allowed]


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def handle_message(message: dict[str, Any], *, arm: str, fixture_cwd: Path) -> dict[str, Any] | None:
    """Handle exactly the MCP methods needed by a subject, pinning every tool cwd."""
    message_id, method = message.get("id"), message.get("method")
    if method == "initialize":
        return _result(message_id, {"protocolVersion": "2024-11-05", "serverInfo": {
            "name": "context-derivation-readonly", "version": "1"}, "capabilities": {"tools": {}}})
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(message_id, {"tools": filtered_tools(arm)})
    if method != "tools/call":
        return _error(message_id, -32601, f"Method not found: {method}")
    params = message.get("params") or {}
    name = params.get("name")
    if name not in allowed_names(arm):
        return _error(message_id, -32602, f"Tool is not allowlisted for {arm}: {name}")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _error(message_id, -32602, "tool arguments must be an object")
    # Do not honour a model-provided cwd.  The fixture is the only readable corpus.
    arguments = {**arguments, "cwd": str(fixture_cwd)}
    try:
        payload = mcp_server.call_tool(name, arguments)
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        return _result(message_id, {"content": [{"type": "text", "text": text}]})
    except Exception as exc:  # production server maps internal errors this way too
        return _error(message_id, -32603, str(exc))


def serve(arm: str, fixture_cwd: Path, input_stream=None, output_stream=None) -> int:
    input_stream, output_stream = input_stream or sys.stdin, output_stream or sys.stdout
    fixture_cwd = fixture_cwd.resolve()
    for line in input_stream:
        if not line.strip():
            continue
        try:
            response = handle_message(json.loads(line), arm=arm, fixture_cwd=fixture_cwd)
        except Exception as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            output_stream.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=sorted(ARM_TOOLS))
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args(argv)
    return serve(args.arm, Path(args.fixture))


if __name__ == "__main__":
    raise SystemExit(main())
