"""A checkout may point .mcp.json at its own build, and an update must not revert it.

This repo dogfoods itself: its `.mcp.json` runs `uv run --no-sync python -m
memory_seed.mcp_server` so the MCP server under test is the working tree, not the
published wheel. That matters beyond convenience - the attention layer only
records through the local build, so a silent revert to `uvx --from memory-seed`
would stop the retrieval log accumulating with nothing to show it had stopped.

The preservation currently falls out of `_OWN_MCP_COMMANDS` not containing "uv".
That is load-bearing behaviour resting on the absence of a string, which is
exactly the kind of thing that gets "tidied up" later. These tests make the
revert loud.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_seed import core

LOCAL_BUILD_ENTRY = {
    "command": "uv",
    "args": ["run", "--no-sync", "python", "-m", "memory_seed.mcp_server", "--stdio"],
}

# Every project-scope upsert that writes our server key into a tool's config.
MERGERS = [
    ("claude", core._merge_claude_mcp, ".mcp.json", "mcpServers"),
    ("cursor", core._merge_cursor_mcp, ".cursor/mcp.json", "mcpServers"),
]


def _write(path: Path, container: str, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({container: {"memory-seed": entry}}, indent=2), encoding="utf-8")


def test_uv_is_not_an_owned_command():
    """The invariant, stated directly.

    If "uv" joins this set, the mergers below start overwriting a deliberate
    local-build entry. Adding it is a real decision, not a cleanup - this test
    is where that argument has to happen.
    """
    assert "uv" not in core._OWN_MCP_COMMANDS


@pytest.mark.parametrize("name,merger,rel,container", MERGERS, ids=[m[0] for m in MERGERS])
def test_local_build_entry_survives_merge(tmp_path, name, merger, rel, container):
    config = tmp_path / rel
    _write(config, container, LOCAL_BUILD_ENTRY)

    changed = merger(tmp_path)

    assert changed is False, f"{name} upsert rewrote a local-build entry"
    on_disk = json.loads(config.read_text(encoding="utf-8"))
    assert on_disk[container]["memory-seed"] == LOCAL_BUILD_ENTRY


def test_published_entry_is_still_upserted(tmp_path):
    """The preservation must not turn the upsert into a no-op for real configs."""
    config = tmp_path / ".mcp.json"
    _write(config, "mcpServers", {"command": "uvx", "args": ["--from", "memory-seed", "old"]})

    assert core._merge_claude_mcp(tmp_path) is True

    on_disk = json.loads(config.read_text(encoding="utf-8"))
    assert on_disk["mcpServers"]["memory-seed"]["command"] == core._MCP_SERVER_COMMAND
    assert on_disk["mcpServers"]["memory-seed"]["args"] == core._MCP_SERVER_ARGS


def test_repo_config_actually_points_at_the_local_build():
    """The dogfooding claim, checked against the file rather than asserted in prose."""
    repo_config = Path(__file__).resolve().parents[1] / ".mcp.json"
    entry = json.loads(repo_config.read_text(encoding="utf-8"))["mcpServers"]["memory-seed"]

    assert entry["command"] == "uv"
    assert "memory_seed.mcp_server" in entry["args"]
    assert "memory-seed" not in entry["args"], "points at the published package, not the working tree"
