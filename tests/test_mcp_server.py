import json
import shutil
import tempfile
import unittest
from datetime import date
from io import StringIO
from pathlib import Path

from memory_seed.mcp_server import (
    call_tool,
    format_search_results,
    handle_jsonrpc_message,
    serve_stdio,
)
from memory_seed.semantic_cache import rank_session_memory


class MemoryMcpServerTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-mcp-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".AGENTS" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / filename).write_text(content, encoding="utf-8")

    def make_memory_fixture(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Bootstrap mode check fix\n\n"
            "Updated AGENTS.md and agent-rules.md to require checking for initialized memory files before operating mode.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## Semble integration into control plane\n\n"
            "Added Semble guidance for code search and #code-search routing.\n",
        )
        self.write_session(
            cwd,
            "2026-05-19.md",
            "## Compact command agent routine\n\n"
            "Added #compact behavior for agents to run memory-seed compact and report key facts.\n",
        )
        return cwd

    def test_human_validatable_search_output_identifies_expected_memory(self):
        cwd = self.make_memory_fixture()
        ranked = rank_session_memory(
            "bootstrap mode check",
            cwd,
            today=date(2026, 5, 19),
        )

        formatted = format_search_results("bootstrap mode check", ranked, top_k=3)

        self.assertEqual(formatted["query"], "bootstrap mode check")
        self.assertEqual(formatted["results"][0]["source"], ".AGENTS/sessions/2026-05-17.md")
        self.assertEqual(formatted["results"][0]["heading_path"], ["2026-05-17 09:15 - Bootstrap mode check fix"])
        self.assertEqual(formatted["results"][0]["entry_datetime"], "2026-05-17T09:15:00")
        self.assertIn("Updated AGENTS.md", formatted["results"][0]["excerpt"])
        self.assertIn("heading_path", formatted["results"][0]["matched_fields"])
        self.assertIsInstance(formatted["results"][0]["score"], float)
        self.assertEqual(len(formatted["human_report"].splitlines()), 5)

    def test_call_tool_memory_search_returns_structured_results(self):
        cwd = self.make_memory_fixture()

        payload = call_tool(
            "memory_search",
            {
                "query": "#compact",
                "cwd": str(cwd),
                "top_k": 2,
                "today": "2026-05-19",
            },
        )

        self.assertEqual(payload["results"][0]["source"], ".AGENTS/sessions/2026-05-19.md")
        self.assertIn("tags", payload["results"][0]["matched_fields"])
        self.assertIn("text", payload["results"][0]["matched_fields"])
        self.assertIn("Compact command agent routine", payload["human_report"])

    def test_call_tool_memory_get_chunk_returns_exact_chunk_by_id(self):
        cwd = self.make_memory_fixture()
        search = call_tool(
            "memory_search",
            {
                "query": "Semble code search",
                "cwd": str(cwd),
                "top_k": 1,
                "today": "2026-05-19",
            },
        )
        chunk_id = search["results"][0]["chunk_id"]

        payload = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": chunk_id})

        self.assertEqual(payload["chunk"]["chunk_id"], chunk_id)
        self.assertIsNone(payload["chunk"]["entry_datetime"])
        self.assertIn("Semble guidance", payload["chunk"]["text"])

    def test_jsonrpc_tools_list_and_call(self):
        cwd = self.make_memory_fixture()
        listed = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        called = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "memory_search",
                    "arguments": {
                        "query": "compact behavior",
                        "cwd": str(cwd),
                        "today": "2026-05-19",
                    },
                },
            }
        )

        self.assertEqual(listed["id"], 1)
        self.assertIn("memory_search", [tool["name"] for tool in listed["result"]["tools"]])
        self.assertEqual(called["id"], 2)
        content = called["result"]["content"][0]
        self.assertEqual(content["type"], "text")
        parsed = json.loads(content["text"])
        self.assertEqual(parsed["results"][0]["source"], ".AGENTS/sessions/2026-05-19.md")

    def test_unknown_jsonrpc_method_returns_error(self):
        response = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 9, "method": "missing"})

        self.assertEqual(response["id"], 9)
        self.assertEqual(response["error"]["code"], -32601)

    def test_stdio_server_handles_newline_delimited_jsonrpc(self):
        input_stream = StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
        output_stream = StringIO()

        exit_code = serve_stdio(input_stream=input_stream, output_stream=output_stream)

        self.assertEqual(exit_code, 0)
        response = json.loads(output_stream.getvalue())
        self.assertEqual(response["id"], 1)
        self.assertIn("memory_search", [tool["name"] for tool in response["result"]["tools"]])


if __name__ == "__main__":
    unittest.main()
