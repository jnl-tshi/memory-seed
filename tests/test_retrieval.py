import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from memory_seed.mcp_server import call_tool
from memory_seed.retrieval import get_chunk, search_memory


class RetrievalServiceParityTests(unittest.TestCase):
    """Distribution-plan Phase 1 gate: the MCP tools and the public retrieval
    service must return identical answers for the same corpus and arguments -
    the extraction is a refactor, not a behavior change."""

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_memory_fixture(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Bootstrap mode check fix\n\n"
            "```yaml\n"
            "entry_id: ms-bootstrap\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Updated AGENTS.md and agent-rules.md to require checking for initialized memory files.\n\n"
            "### Decision\n\n"
            "- D: Require the bootstrap mode check before operating mode.\n\n"
            "### Follow-up\n\n"
            "- Watch for bootstrap regressions in agent-rules.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:00 - Semble integration\n\n"
            "```yaml\n"
            "entry_id: ms-semble\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "related_entries:\n"
            "  - ms-bootstrap\n"
            "```\n\n"
            "Added Semble guidance for code search routing.\n",
        )
        return cwd

    def test_search_parity_with_mcp_tool(self):
        cwd = self.make_memory_fixture()
        for kwargs in (
            {},
            {"granularity": "section"},
            {"top_k": 1},
            {"recency_enabled": False},
        ):
            with self.subTest(kwargs=kwargs):
                tool_result = call_tool(
                    "memory_search",
                    {"query": "bootstrap mode check", "cwd": str(cwd), "semantic_enabled": False, **kwargs},
                    today=date(2026, 5, 20),
                )
                service_result = search_memory(
                    "bootstrap mode check",
                    str(cwd),
                    semantic_enabled=False,
                    today=date(2026, 5, 20),
                    **kwargs,
                )
                self.assertEqual(tool_result, service_result)
                self.assertTrue(service_result["results"])

    def test_get_chunk_parity_with_mcp_tool(self):
        cwd = self.make_memory_fixture()
        tool_result = call_tool("memory_get_chunk", {"chunk_id": "ms-bootstrap", "cwd": str(cwd)})
        service_result = get_chunk("ms-bootstrap", str(cwd))
        self.assertEqual(tool_result, {"chunk": service_result})
        # Graph metrics from the edge contract ride along identically.
        self.assertEqual(service_result["inbound_relation_count"], 1)
        self.assertIn("importance_score", service_result)
        self.assertIn("superseded_by", service_result)
        self.assertIn("commit_reference_count", service_result)

    def test_get_chunk_unknown_id_raises(self):
        cwd = self.make_memory_fixture()
        with self.assertRaises(ValueError):
            get_chunk("ms-nonexistent", str(cwd))

    def test_service_is_mcp_independent(self):
        # The service must not import the MCP layer: the dependency points
        # from mcp_server to retrieval, never back (distribution-plan gate).
        import ast

        import memory_seed.retrieval as retrieval_module

        tree = ast.parse(Path(retrieval_module.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse([name for name in imported if "mcp_server" in name], imported)


if __name__ == "__main__":
    unittest.main()
