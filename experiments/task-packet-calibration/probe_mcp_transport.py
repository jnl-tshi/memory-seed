"""Directly probe the experiment MCP server through Hermes' MCP SDK runtime."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _probe(command: Path, args: list[str]) -> None:
    parameters = StdioServerParameters(
        command=str(command),
        args=args,
        env=dict(os.environ),
        encoding_error_handler="replace",
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            print("\n".join(sorted(tool.name for tool in result.tools)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, type=Path)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()
    if sys.platform == "win32":
        policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        if policy is not None:
            asyncio.set_event_loop_policy(policy())
    anyio.run(_probe, parsed.command, parsed.args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
