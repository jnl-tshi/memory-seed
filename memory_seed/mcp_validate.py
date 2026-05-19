from __future__ import annotations

import argparse
from pathlib import Path

from .mcp_server import call_tool


def build_validation_report(
    query: str,
    *,
    cwd: str | Path = ".",
    top_k: int = 5,
    today: str | None = None,
) -> str:
    args: dict[str, object] = {
        "query": query,
        "cwd": str(cwd),
        "top_k": top_k,
    }
    if today:
        args["today"] = today

    search = call_tool("memory_search", args)
    lines = [
        "# MCP Memory Validation",
        "",
        f"Query: {query}",
        "",
        "Search results:",
        search["human_report"],
    ]

    results = search["results"]
    if not results:
        return "\n".join(lines)

    top = results[0]
    fetched = call_tool(
        "memory_get_chunk",
        {
            "cwd": str(cwd),
            "chunk_id": top["chunk_id"],
        },
    )
    chunk = fetched["chunk"]
    heading = " > ".join(chunk["heading_path"]) or "(untitled)"
    lines.extend(
        [
            "",
            "Fetched top chunk:",
            f"Source: {chunk['source']}:{chunk['line_range'][0]}",
            f"Heading: {heading}",
            "",
            chunk["text"],
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memory-seed-mcp-validate")
    parser.add_argument("query", help="memory search query to validate")
    parser.add_argument("--cwd", default=".", help="project root to search")
    parser.add_argument("--top-k", type=int, default=5, help="number of search results to show")
    parser.add_argument("--today", default=None, help="optional YYYY-MM-DD date override")
    args = parser.parse_args(argv)
    print(
        build_validation_report(
            args.query,
            cwd=args.cwd,
            top_k=args.top_k,
            today=args.today,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
