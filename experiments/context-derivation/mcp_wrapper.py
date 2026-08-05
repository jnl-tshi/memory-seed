"""Read-only, experiment-local MCP facade for context-derivation fixtures.

The production server deliberately contains write tools.  This process is a narrow
stdio facade, rather than a modified production server, so an experiment cannot
accidentally advertise those tools to a subject.
"""
from __future__ import annotations

import argparse
import copy
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
APPROVAL_SMOKE_TOOLS = frozenset({"memory_adrs_list"})
ARM_TOOLS = {
    "search-mcp": SEARCH_TOOLS,
    "adr-mcp-workflow": WORKFLOW_TOOLS,
    "approval-smoke": APPROVAL_SMOKE_TOOLS,
}


def allowed_names(arm: str) -> frozenset[str]:
    try:
        return ARM_TOOLS[arm]
    except KeyError as exc:
        raise ValueError(f"MCP is not available for arm {arm!r}") from exc


def filtered_tools(arm: str) -> list[dict[str, Any]]:
    allowed = allowed_names(arm)
    tools = [copy.deepcopy(tool) for tool in mcp_server.TOOLS if tool["name"] in allowed]
    for tool in tools:
        if tool["name"] == "memory_search":
            semantic = tool["inputSchema"]["properties"]["semantic_enabled"]
            semantic.update({
                "default": False,
                "const": False,
                "description": "Disabled in the deterministic experiment fixture facade.",
            })
    return tools


def rpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _validated_arguments(name: str, arguments: Any, fixture_cwd: Path) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")
    tool = next(item for item in filtered_tools("adr-mcp-workflow") if item["name"] == name)
    properties = set((tool.get("inputSchema") or {}).get("properties") or {})
    unsupported = sorted(set(arguments) - properties)
    if unsupported:
        raise ValueError("unsupported tool arguments")
    if name == "memory_search" and arguments.get("semantic_enabled") not in (None, False):
        raise ValueError("semantic search is disabled")
    if name == "memory_adr_show":
        from memory_seed.adr import ADR_ID_RE
        from memory_seed.core import resolve_runtime

        adr_id = arguments.get("adr_id")
        if not isinstance(adr_id, str) or not ADR_ID_RE.fullmatch(adr_id):
            raise ValueError("invalid ADR ID")
        decisions = (resolve_runtime(fixture_cwd).memory_dir / "decisions").resolve()
        candidate = (decisions / f"{adr_id}.md").resolve()
        try:
            candidate.relative_to(decisions)
        except ValueError as exc:
            raise ValueError("ADR path escaped fixture") from exc
    # Never honour a model-provided cwd. The isolated copy is the only corpus.
    validated = {**arguments, "cwd": str(fixture_cwd)}
    if name == "memory_search":
        validated["semantic_enabled"] = False
    return validated


def _sanitize_payload(value: Any, fixture_cwd: Path, *, key: str | None = None) -> Any:
    """Keep evidence references while removing host filesystem disclosure."""
    fixture = fixture_cwd.resolve()
    if isinstance(value, dict):
        return {name: _sanitize_payload(item, fixture, key=name) for name, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item, fixture) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item, fixture) for item in value]
    if not isinstance(value, str):
        return value
    if key == "path" and Path(value).is_absolute():
        try:
            relative = Path(value).resolve().relative_to(fixture)
        except ValueError:
            return "<redacted-path>"
        return f"<fixture>/{relative.as_posix()}"
    return value.replace(str(fixture), "<fixture>").replace(fixture.as_posix(), "<fixture>")


def handle_message(message: dict[str, Any], *, arm: str, fixture_cwd: Path) -> dict[str, Any] | None:
    """Handle exactly the MCP methods needed by a subject, pinning every tool cwd."""
    message_id, method = message.get("id"), message.get("method")
    if message.get("jsonrpc", "2.0") != "2.0" or not isinstance(method, str):
        return None if message_id is None else rpc_error(message_id, -32600, "invalid JSON-RPC request")
    # MCP calls are requests, never fire-and-forget capabilities. Unknown or
    # call-shaped notifications must neither execute nor receive a response.
    if message_id is None and method != "notifications/initialized":
        return None
    if method == "initialize":
        params = message.get("params") or {}
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        version = requested if requested in {
            "2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25",
        } else "2024-11-05"
        return _result(message_id, {"protocolVersion": version, "serverInfo": {
            "name": "context-derivation-readonly", "version": "1"},
            "capabilities": {"tools": {"listChanged": False}}})
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _result(message_id, {})
    if method == "tools/list":
        return _result(message_id, {"tools": filtered_tools(arm)})
    if method != "tools/call":
        return None if message_id is None else rpc_error(message_id, -32601, "method not found")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return rpc_error(message_id, -32602, "invalid tool parameters")
    name = params.get("name")
    if name not in allowed_names(arm):
        return rpc_error(message_id, -32602, "tool is not allowlisted")
    try:
        arguments = params.get("arguments", {})
        if arguments is None:
            arguments = {}
        arguments = _validated_arguments(name, arguments, fixture_cwd)
        payload = _sanitize_payload(mcp_server.call_tool(name, arguments), fixture_cwd)
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        return _result(message_id, {"content": [{"type": "text", "text": text}], "isError": False})
    except ValueError:
        return rpc_error(message_id, -32602, "invalid tool arguments")
    except Exception:
        # Do not expose fixture paths, exception strings, or implementation details.
        return _result(message_id, {"content": [{"type": "text", "text": "tool execution failed"}], "isError": True})


def serve(arm: str, fixture_cwd: Path, input_stream=None, output_stream=None) -> int:
    input_stream, output_stream = input_stream or sys.stdin, output_stream or sys.stdout
    fixture_cwd = fixture_cwd.resolve()
    for line in input_stream:
        if not line.strip():
            continue
        try:
            response = handle_message(json.loads(line), arm=arm, fixture_cwd=fixture_cwd)
        except Exception:
            response = rpc_error(None, -32700, "invalid JSON")
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
