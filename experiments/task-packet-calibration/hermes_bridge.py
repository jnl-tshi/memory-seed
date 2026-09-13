"""Read a long prompt from disk and execute it through Hermes one-shot mode."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path


def _configure_windows_mcp_transport() -> str:
    """Use the MCP SDK's Popen fallback when overlapped pipes are unavailable."""
    if sys.platform != "win32":
        return "native"
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is None:
        return "native"
    asyncio.set_event_loop_policy(policy())
    return "selector-popen-fallback"


def _write_tool_diagnostics(path: Path, *, transport_mode: str) -> None:
    """Record the tools Hermes resolved after its bounded MCP discovery pass."""
    from hermes_cli.config import load_config
    from hermes_cli.mcp_startup import ensure_mcp_discovery_before_agent_build
    from model_tools import get_tool_definitions
    from toolsets import get_all_toolsets

    ensure_mcp_discovery_before_agent_build(
        logger=logging.getLogger(__name__),
        single_query=True,
        thread_name="calibration-mcp-discovery",
    )
    config = load_config()
    platform_toolsets = config.get("platform_toolsets") or {}
    requested = list(platform_toolsets.get("cli") or [])
    definitions = get_tool_definitions(
        enabled_toolsets=requested,
        quiet_mode=True,
    )
    record = {
        "configured_mcp_servers": sorted((config.get("mcp_servers") or {}).keys()),
        "registered_mcp_toolsets": sorted(
            name for name in get_all_toolsets() if str(name).startswith("mcp-")
        ),
        "requested_toolsets": requested,
        "windows_mcp_transport": transport_mode,
        "resolved_tools": sorted(
            item.get("function", {}).get("name", "") for item in definitions
        ),
    }
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-tree", required=True, type=Path)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--usage-file", required=True, type=Path)
    parser.add_argument("--diagnostics-file", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="lmstudio")
    args = parser.parse_args(argv)
    transport_mode = _configure_windows_mcp_transport()
    sys.path.insert(0, str(args.hermes_tree.resolve()))
    from hermes_cli.oneshot import run_oneshot

    _write_tool_diagnostics(args.diagnostics_file, transport_mode=transport_mode)
    prompt = args.prompt_file.read_text(encoding="utf-8")
    return run_oneshot(
        prompt,
        model=args.model,
        provider=args.provider,
        usage_file=str(args.usage_file),
    )


if __name__ == "__main__":
    raise SystemExit(main())
