"""Console entry point for the ``memory-trace`` command.

Serves the local, read-only Memory Trace review UI over the current project's
Memory Seed session memory. Mirrors the arguments of the deprecated
``memory-seed lense`` subcommand so existing muscle memory keeps working.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from memory_seed import processes as process_tools

from . import __version__
from .service import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory-trace",
        description="Serve the local Memory Trace review UI for a Memory Seed project.",
    )
    parser.add_argument("--version", action="version", version=f"memory-trace {__version__}")
    parser.add_argument("--cwd", default=".", help="project/runtime path to inspect (default: current directory)")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="port to bind; 0 chooses a free port")
    browser_group = parser.add_mutually_exclusive_group()
    browser_group.add_argument("--no-open", action="store_true", help="do not open a browser")
    browser_group.add_argument(
        "--open-both",
        action="store_true",
        help="open the vanilla / and React /next views in browser tabs",
    )
    parser.add_argument("--rebuild-cache", action="store_true", help="rebuild the SQLite cache before serving")
    parser.add_argument(
        "--static-root",
        default=None,
        help="serve UI assets (index.html/app.js/styles.css) from this directory or checkout root "
        "instead of the installed package - verify a worktree's UI without copying files "
        "(also: MEMORY_TRACE_STATIC_ROOT)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if argv and argv[0] in process_tools.PACKAGE_COMMANDS:
        return process_tools.run_package_process_argv("memory-trace", argv, prog="memory-trace")
    args = build_parser().parse_args(argv)
    return run_server(args)


if __name__ == "__main__":
    sys.exit(main())
