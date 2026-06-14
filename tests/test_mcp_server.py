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
from memory_seed.semantic_cache import Model2VecEmbeddingProvider, rank_session_memory


class FailingModel2VecEmbeddingProvider:
    name = "model2vec:minishlab/potion-base-8M"

    def __init__(self, reason):
        self.reason = reason

    def embed(self, texts):
        raise RuntimeError(self.reason)


class StaticEmbeddingProvider:
    name = "model2vec:minishlab/potion-base-8M"

    def embed(self, texts):
        return [(1.0, 0.0) for _ in texts]


class MemoryMcpServerTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-mcp-test-"))
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
            "Updated AGENTS.md and agent-rules.md to require checking for initialized memory files before operating mode.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## Semble integration into control plane\n\n"
            "```yaml\n"
            "entry_id: ms-semble\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Added Semble guidance for code search and #code-search routing.\n",
        )
        self.write_session(
            cwd,
            "2026-05-19.md",
            "## Compact command agent routine\n\n"
            "```yaml\n"
            "entry_id: ms-compact\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
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
        self.assertEqual(formatted["results"][0]["source"], ".memory-seed/sessions/2026-05-17.md")
        self.assertEqual(formatted["results"][0]["heading_path"], ["2026-05-17 09:15 - Bootstrap mode check fix"])
        self.assertEqual(formatted["results"][0]["entry_datetime"], "2026-05-17T09:15:00")
        self.assertEqual(formatted["results"][0]["chunk_id"], "ms-bootstrap")
        self.assertEqual(formatted["results"][0]["entry_id"], "ms-bootstrap")
        self.assertEqual(formatted["results"][0]["granularity"], "entry")
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
                "_embedding_provider": StaticEmbeddingProvider(),
            },
            today=date(2026, 5, 19),
        )

        self.assertEqual(payload["results"][0]["source"], ".memory-seed/sessions/2026-05-19.md")
        self.assertEqual(payload["results"][0]["chunk_id"], "ms-compact")
        self.assertTrue(payload["semantic_enabled"])
        self.assertEqual(payload["semantic_provider"], "model2vec:minishlab/potion-base-8M")
        self.assertIsNotNone(payload["results"][0]["semantic_score"])
        self.assertIn("tags", payload["results"][0]["matched_fields"])
        self.assertIn("text", payload["results"][0]["matched_fields"])
        self.assertIn("Compact command agent routine", payload["human_report"])

    def test_memory_search_schema_has_no_today_override(self):
        from memory_seed.mcp_server import TOOLS

        search_tool = next(t for t in TOOLS if t["name"] == "memory_search")
        self.assertNotIn("today", search_tool["inputSchema"]["properties"])

    def test_call_tool_ignores_caller_supplied_today_in_arguments(self):
        cwd = self.make_memory_fixture()

        base_args = {
            "query": "#compact",
            "cwd": str(cwd),
            "top_k": 2,
            "semantic_enabled": False,
        }
        without = call_tool("memory_search", dict(base_args))
        with_bogus = call_tool("memory_search", {**base_args, "today": "1999-01-01"})

        # A caller-supplied "today" must be ignored; recency is anchored to the
        # system clock at call time, so both queries rank identically.
        self.assertEqual(
            [r["chunk_id"] for r in without["results"]],
            [r["chunk_id"] for r in with_bogus["results"]],
        )
        self.assertEqual(
            [r["recency_multiplier"] for r in without["results"]],
            [r["recency_multiplier"] for r in with_bogus["results"]],
        )

    def test_call_tool_memory_search_can_disable_semantic_scoring(self):
        cwd = self.make_memory_fixture()

        payload = call_tool(
            "memory_search",
            {
                "query": "#compact",
                "cwd": str(cwd),
                "top_k": 2,
                "semantic_enabled": False,
            },
            today=date(2026, 5, 19),
        )

        self.assertFalse(payload["semantic_enabled"])
        self.assertIsNone(payload["semantic_provider"])
        self.assertIsNone(payload["results"][0]["semantic_score"])

    def test_call_tool_memory_search_reports_semantic_fallback(self):
        cwd = self.make_memory_fixture()

        payload = call_tool(
            "memory_search",
            {
                "query": "#compact",
                "cwd": str(cwd),
                "top_k": 2,
                "_embedding_provider": FailingModel2VecEmbeddingProvider("model unavailable"),
            },
            today=date(2026, 5, 19),
        )

        self.assertFalse(payload["semantic_enabled"])
        self.assertEqual(payload["semantic_provider"], "model2vec:minishlab/potion-base-8M")
        self.assertIn("model unavailable", payload["semantic_fallback_reason"])
        self.assertIsNone(payload["results"][0]["semantic_score"])

    def test_model2vec_provider_wraps_static_model_encode(self):
        class StaticModel:
            def encode(self, texts):
                return [(1.0, 0.0) if "query" in text else (0.0, 1.0) for text in texts]

        provider = Model2VecEmbeddingProvider(
            model_name="example/model",
            model_loader=lambda model_name: StaticModel(),
        )

        self.assertEqual(provider.name, "model2vec:example/model")
        self.assertEqual(provider.embed(["query text", "memory text"]), [(1.0, 0.0), (0.0, 1.0)])

    def test_call_tool_memory_get_chunk_returns_exact_chunk_by_id(self):
        cwd = self.make_memory_fixture()
        search = call_tool(
            "memory_search",
            {
                "query": "Semble code search",
                "cwd": str(cwd),
                "top_k": 1,
            },
            today=date(2026, 5, 19),
        )
        chunk_id = search["results"][0]["chunk_id"]

        payload = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": chunk_id})

        self.assertEqual(payload["chunk"]["chunk_id"], chunk_id)
        self.assertEqual(payload["chunk"]["entry_id"], "ms-semble")
        self.assertIsNone(payload["chunk"]["entry_datetime"])
        self.assertIn("Semble guidance", payload["chunk"]["text"])

    def test_call_tool_memory_get_chunk_returns_per_user_chunk(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-21/jean.md",
            "## 2026-06-21 10:00 - Dual-read MCP\n\n"
            "```yaml\n"
            "entry_id: ms-jean-mcp\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Per-user search text.\n",
        )

        payload = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-jean-mcp"})

        self.assertEqual(payload["chunk"]["chunk_id"], "ms-jean-mcp")
        self.assertEqual(payload["chunk"]["date"], "2026-06-21")
        self.assertEqual(payload["chunk"]["source"], ".memory-seed/sessions/2026-06-21/jean.md")
        self.assertIn("Per-user search text.", payload["chunk"]["text"])

    def test_call_tool_memory_search_supports_section_granularity(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-20.md",
            "## 2026-05-20 11:00 - Entry granularity work\n\n"
            "```yaml\n"
            "entry_id: ms-granular\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "### Decisions\n\n"
            "#### D1 - Use entry chunks\n\n"
            "Entry chunks preserve rationale.\n",
        )

        payload = call_tool(
            "memory_search",
            {
                "query": "preserve rationale",
                "cwd": str(cwd),
                "top_k": 3,
                "granularity": "section",
            },
            today=date(2026, 5, 20),
        )

        self.assertIn("ms-granular#decisions/d1-use-entry-chunks", [result["chunk_id"] for result in payload["results"]])
        self.assertTrue(all(result["entry_id"] == "ms-granular" for result in payload["results"]))
        fetched = call_tool(
            "memory_get_chunk",
            {
                "cwd": str(cwd),
                "chunk_id": "ms-granular#decisions/d1-use-entry-chunks",
            },
        )
        self.assertEqual(fetched["chunk"]["entry_id"], "ms-granular")
        self.assertEqual(fetched["chunk"]["granularity"], "section")

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
                        "recency_enabled": False,
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
        self.assertEqual(parsed["results"][0]["source"], ".memory-seed/sessions/2026-05-19.md")

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
