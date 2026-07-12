"""Trace-source parity: Memory Trace must return the same answers as core MCP.

Distribution-plan Arc 1 gate. Memory Trace lives in its own source boundary,
even though it now ships through the root `memory-seed[trace]` extra. Whatever
it reads from `memory_seed` is still a public API with semver obligations.
These tests assert that the extracted UI, consuming `memory_seed.retrieval`
through its `LenseService`, agrees with the core MCP tools on the same corpus -
the "same answers as MCP, one canonical chunk model" rule, proven across the
source boundary rather than assumed.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.mcp_server import call_tool
from memory_trace.lense import LenseCache, LenseService


def _session(entry_id: str, title: str, body: str) -> str:
    return (
        "---\ntags:\n  - session-log\n---\n\n"
        f"## {title}\n\n"
        "```yaml\n"
        f"entry_id: {entry_id}\n"
        "user_initials: JN\n"
        "agent_type: codex\n"
        "project_path: .\n"
        "subproject_path: null\n"
        "```\n\n"
        f"{body}\n"
    )


class CrossPackageParityTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-trace-parity-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-trace-parity-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(
            _session("mse_bootstrap", "2026-06-01 09:00 - Bootstrap cache check",
                     "Fixed the bootstrap mode check before operating mode."),
            encoding="utf-8",
        )
        (sessions / "2026-06-02.md").write_text(
            _session("mse_graph", "2026-06-02 10:00 - Graph neighborhood",
                     "Graph neighborhood traversal for the review UI."),
            encoding="utf-8",
        )

    def service(self) -> LenseService:
        cache = LenseCache(self.cwd, cache_root=self.cache_root)
        cache.rebuild()
        return LenseService(cache)

    def test_search_top_entry_agrees_with_mcp(self):
        query = "bootstrap mode check"
        mcp = call_tool("memory_search", {"query": query, "cwd": str(self.cwd), "semantic_enabled": False})
        ui = self.service().search(q=query, limit=5)
        self.assertTrue(mcp["results"] and ui["results"])
        # Same winning entry, across the Trace source boundary.
        self.assertEqual(mcp["results"][0]["entry_id"], ui["results"][0]["entry_id"])
        self.assertEqual(ui["results"][0]["entry_id"], "mse_bootstrap")

    def test_chunk_fetch_core_fields_agree_with_mcp(self):
        mcp_chunk = call_tool("memory_get_chunk", {"chunk_id": "mse_bootstrap", "cwd": str(self.cwd)})["chunk"]
        ui_chunk = self.service().chunk("mse_bootstrap")
        # The UI presents a leaner view, but the identity/anchor fields it shares
        # with MCP must match exactly - deep links target the same records.
        self.assertEqual(ui_chunk["entry_id"], mcp_chunk["entry_id"])
        self.assertEqual(ui_chunk["chunk_id"], mcp_chunk["chunk_id"])
        self.assertEqual(ui_chunk["line_range"], mcp_chunk["line_range"])
        self.assertEqual(ui_chunk["source"], mcp_chunk["source"])
