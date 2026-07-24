import json
import shutil
import subprocess
import tempfile
import unittest
import pytest
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

    def git(self, cwd, *args):
        proc = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip()

    def init_git_project(self, cwd):
        self.git(cwd, "init", "-q")
        self.git(cwd, "config", "user.name", "Test User")
        self.git(cwd, "config", "user.email", "test@example.com")
        self.git(cwd, "config", "commit.gpgsign", "false")
        self.git(cwd, "branch", "-M", "main")

    def commit_all(self, cwd, message):
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-q", "-m", message)

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_topics_index(self, cwd):
        memory = cwd / ".memory-seed"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "topics.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "topics:",
                    "  - slug: retrieval",
                    "    label: Retrieval",
                    "    description: Search and ranking.",
                    "    status: active",
                    "    aliases: [search, ranking]",
                    "  - slug: old-theme",
                    "    label: Old Theme",
                    "    status: deprecated",
                    "    aliases: []",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def write_link_sidecar(self, cwd, file_date, source_entry, *, replaces=(), evolves=(), related_entries=()):
        links = cwd / ".memory-seed" / "sessions" / "links" / file_date[:7]
        links.mkdir(parents=True, exist_ok=True)
        lines = [f"## {file_date} 10:00 - sidecar links", "", "```yaml", f"entry_id: {source_entry}"]
        for key, refs in (
            ("related_entries", related_entries),
            ("replaces", replaces),
            ("evolves", evolves),
        ):
            if refs:
                lines.append(f"{key}:")
                lines.extend(f"  - {ref}" for ref in refs)
        lines += ["```", ""]
        (links / f"{file_date}.md").write_text("\n".join(lines), encoding="utf-8")

    def write_grouped_session(self, cwd, date_str, entry_id, *, branch):
        self.write_session(
            cwd,
            f"{date_str[:7]}/{date_str}.md",
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log",
                    "  - memory-seed",
                    f"session_date: {date_str}",
                    "---",
                    "",
                    f"## {date_str} 09:00 - Entry",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "user_initials: JN",
                    "agent_type: codex",
                    f"branch: {branch}",
                    "```",
                    "",
                    "- Body.",
                    "",
                ]
            ),
        )

    def write_legacy_diagram(self, cwd, date_str, entry_id):
        diagrams = cwd / ".memory-seed" / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        path = diagrams / f"{date_str}.md"
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    f"diagram_date: {date_str}",
                    "---",
                    "",
                    f"## {date_str} 09:00 - Entry",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "```",
                    "",
                    "```mermaid",
                    "graph TD",
                    "  A[Branch] --> B[Main]",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

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

    def _replaced_search_fixture(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Old cache decision\n\n"
            "```yaml\n"
            "entry_id: ms-oldcache0\n"
            "```\n\n"
            "The original cache key design.\n\n"
            "## 2026-05-17 10:00 - New cache decision\n\n"
            "```yaml\n"
            "entry_id: ms-newcache0\n"
            "replaces:\n"
            "  - ms-oldcache0\n"
            "```\n\n"
            "The revised cache key design.\n",
        )
        return cwd

    def test_memory_search_returns_replaced_entries_by_default(self):
        cwd = self._replaced_search_fixture()

        payload = call_tool(
            "memory_search",
            {"query": "cache design", "cwd": str(cwd), "top_k": 10, "semantic_enabled": False},
            today=date(2026, 5, 18),
        )
        ids = {r["entry_id"] for r in payload["results"]}

        # Default behavior is unchanged: the replaced entry is still returned.
        self.assertIn("ms-oldcache0", ids)
        self.assertIn("ms-newcache0", ids)

    def test_memory_search_exclude_replaced_drops_replaced_entries(self):
        cwd = self._replaced_search_fixture()

        payload = call_tool(
            "memory_search",
            {
                "query": "cache design",
                "cwd": str(cwd),
                "top_k": 10,
                "semantic_enabled": False,
                "exclude_replaced": True,
            },
            today=date(2026, 5, 18),
        )
        ids = {r["entry_id"] for r in payload["results"]}

        # Opt-in narrowing: the replaced entry is dropped, the current one kept.
        self.assertNotIn("ms-oldcache0", ids)
        self.assertIn("ms-newcache0", ids)

    def test_memory_search_results_carry_computed_lifecycle_status(self):
        # D7 (evolution-edges-plan.md): freshness at the moment of consumption.
        # Search results expose the computed inverses so a consumer sees
        # "retired" / "evolved" without a per-result get_chunk round trip.
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Old cache decision\n\n"
            "```yaml\n"
            "entry_id: ms-oldcache0\n"
            "```\n\n"
            "The original cache key design.\n\n"
            "## 2026-05-17 09:30 - Foundational cache decision\n\n"
            "```yaml\n"
            "entry_id: ms-basecache\n"
            "```\n\n"
            "The cache layering design.\n\n"
            "## 2026-05-17 10:00 - New cache decision\n\n"
            "```yaml\n"
            "entry_id: ms-newcache0\n"
            "replaces:\n"
            "  - ms-oldcache0\n"
            "evolves:\n"
            "  - ms-basecache\n"
            "```\n\n"
            "The revised cache key design.\n",
        )

        payload = call_tool(
            "memory_search",
            {"query": "cache design", "cwd": str(cwd), "top_k": 10, "semantic_enabled": False},
            today=date(2026, 5, 18),
        )
        by_id = {r["entry_id"]: r for r in payload["results"]}

        # The retired entry is still returned (never hidden) and labelled.
        self.assertEqual(by_id["ms-oldcache0"]["replaced_by"], ["ms-newcache0"])
        self.assertEqual(by_id["ms-oldcache0"]["evolved_by"], [])
        # The evolved entry is labelled fresh-but-extended, never retired.
        self.assertEqual(by_id["ms-basecache"]["evolved_by"], ["ms-newcache0"])
        self.assertEqual(by_id["ms-basecache"]["replaced_by"], [])
        # The successor entry carries its stored edges and clean status.
        self.assertEqual(by_id["ms-newcache0"]["replaces"], ["ms-oldcache0"])
        self.assertEqual(by_id["ms-newcache0"]["evolves"], ["ms-basecache"])
        self.assertEqual(by_id["ms-newcache0"]["replaced_by"], [])
        self.assertEqual(by_id["ms-newcache0"]["evolved_by"], [])

    def test_mcp_graph_surfaces_union_of_yaml_and_link_sidecar_edges(self):
        cwd = self.make_project()
        old_id = "mse_73acenc747vkk724"
        base_id = "mse_6f9qmrbdtq4esea8"
        new_id = "mse_3z3b625t90e185x4"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Old cache decision\n\n"
            "```yaml\n"
            f"entry_id: {old_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The original cache key design.\n\n"
            "## 2026-05-17 09:30 - Foundational cache decision\n\n"
            "```yaml\n"
            f"entry_id: {base_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The cache layering design.\n\n"
            "## 2026-05-17 10:00 - New cache decision\n\n"
            "```yaml\n"
            f"entry_id: {new_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The revised cache key design.\n",
        )
        self.write_link_sidecar(
            cwd,
            "2026-05-17",
            new_id,
            replaces=(old_id,),
            evolves=(base_id,),
        )

        search = call_tool(
            "memory_search",
            {"query": "cache design", "cwd": str(cwd), "top_k": 10, "semantic_enabled": False},
            today=date(2026, 5, 18),
        )
        by_id = {r["entry_id"]: r for r in search["results"]}
        old_chunk = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": old_id})["chunk"]
        base_chunk = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": base_id})["chunk"]
        new_chunk = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": new_id})["chunk"]
        old_node = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": old_id})
        base_node = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": base_id})
        new_node = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": new_id})

        self.assertEqual(by_id[old_id]["replaced_by"], [new_id])
        self.assertEqual(by_id[base_id]["evolved_by"], [new_id])
        self.assertEqual(by_id[new_id]["replaces"], [old_id])
        self.assertEqual(by_id[new_id]["evolves"], [base_id])
        self.assertEqual(old_chunk["replaced_by"], [new_id])
        self.assertEqual(base_chunk["evolved_by"], [new_id])
        self.assertEqual(new_chunk["replaces"], [old_id])
        self.assertEqual(new_chunk["evolves"], [base_id])
        self.assertEqual(old_node["replaced_by"], [new_id])
        self.assertEqual(base_node["evolved_by"], [new_id])
        self.assertEqual(new_node["replaces"], [old_id])
        self.assertEqual(new_node["evolves"], [base_id])

    def test_mcp_graph_yaml_only_lifecycle_edges_still_work_without_sidecars(self):
        cwd = self.make_project()
        original_id = "mse_ar1n3fe9phvv7dhd"
        replacement_id = "mse_zyp770zqesd85dpf"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Original decision\n\n"
            "```yaml\n"
            f"entry_id: {original_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The first take on the cache key.\n\n"
            "## 2026-05-17 10:00 - Replacement decision\n\n"
            "```yaml\n"
            f"entry_id: {replacement_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "replaces:\n"
            f"  - {original_id}\n"
            "```\n\n"
            "The corrected take on the cache key.\n",
        )

        search = call_tool(
            "memory_search",
            {"query": "cache key", "cwd": str(cwd), "top_k": 10, "semantic_enabled": False},
            today=date(2026, 5, 18),
        )
        by_id = {r["entry_id"]: r for r in search["results"]}
        original = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": original_id})["chunk"]
        replacement = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": replacement_id})

        self.assertEqual(by_id[original_id]["replaced_by"], [replacement_id])
        self.assertEqual(by_id[replacement_id]["replaces"], [original_id])
        self.assertEqual(original["replaced_by"], [replacement_id])
        self.assertEqual(replacement["replaces"], [original_id])

    def test_replacing_head_surfaces_terminal_replacement_across_search_chunk_and_graph(self):
        cwd = self.make_project()
        old_id = "mse_oldchain000000"
        mid_id = "mse_midchain000000"
        new_id = "mse_newchain000000"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Original cache policy\n\n"
            "```yaml\n"
            f"entry_id: {old_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The original cache ttl strategy.\n\n"
            "## 2026-05-17 10:00 - Intermediate cache policy\n\n"
            "```yaml\n"
            f"entry_id: {mid_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "replaces:\n"
            f"  - {old_id}\n"
            "```\n\n"
            "The second cache ttl strategy.\n\n"
            "## 2026-05-17 11:00 - Final cache policy\n\n"
            "```yaml\n"
            f"entry_id: {new_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The final cache ttl strategy.\n",
        )
        self.write_link_sidecar(cwd, "2026-05-17", new_id, replaces=(mid_id,))

        search = call_tool(
            "memory_search",
            {
                "query": "cache ttl strategy",
                "cwd": str(cwd),
                "top_k": 10,
                "semantic_enabled": False,
                "replacing_successor_boost": False,
            },
            today=date(2026, 5, 18),
        )
        by_id = {r["entry_id"]: r for r in search["results"]}
        old_chunk = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": old_id})["chunk"]
        old_node = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": old_id})

        self.assertEqual(by_id[old_id]["replacing_head"], [new_id])
        self.assertEqual(by_id[mid_id]["replacing_head"], [new_id])
        self.assertEqual(by_id[new_id]["replacing_head"], [])
        self.assertEqual(old_chunk["replacing_head"], [new_id])
        self.assertEqual(old_node["replacing_head"], [new_id])

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

    def test_memory_search_schema_exposes_replacing_successor_boost(self):
        from memory_seed.mcp_server import TOOLS

        search_tool = next(t for t in TOOLS if t["name"] == "memory_search")
        prop = search_tool["inputSchema"]["properties"].get("replacing_successor_boost")
        self.assertIsNotNone(prop)
        self.assertEqual(prop["type"], "boolean")
        self.assertTrue(prop["default"])

    def test_memory_search_defaults_successor_boost_on_and_allows_opt_out(self):
        cwd = self.make_project()
        old_id = "mse_oldboost000000"
        new_id = "mse_newboost000000"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Redis cache TTL invalidation strategy\n\n"
            "```yaml\n"
            f"entry_id: {old_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The original cache ttl invalidation strategy.\n\n"
            "## 2026-05-17 10:00 - Cache TTL rework\n\n"
            "```yaml\n"
            f"entry_id: {new_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "replaces:\n"
            f"  - {old_id}\n"
            "```\n\n"
            "A lighter cache ttl plan.\n",
        )

        default = call_tool(
            "memory_search",
            {"query": "redis cache ttl invalidation strategy", "cwd": str(cwd), "semantic_enabled": False},
            today=date(2026, 5, 18),
        )
        explicit_on = call_tool(
            "memory_search",
            {
                "query": "redis cache ttl invalidation strategy",
                "cwd": str(cwd),
                "semantic_enabled": False,
                "replacing_successor_boost": True,
            },
            today=date(2026, 5, 18),
        )
        explicit_off = call_tool(
            "memory_search",
            {
                "query": "redis cache ttl invalidation strategy",
                "cwd": str(cwd),
                "semantic_enabled": False,
                "replacing_successor_boost": False,
            },
            today=date(2026, 5, 18),
        )
        by_default = {r["entry_id"]: r for r in default["results"]}
        by_off = {r["entry_id"]: r for r in explicit_off["results"]}

        self.assertEqual(default["results"], explicit_on["results"])
        self.assertGreater(by_default[new_id]["score"], by_off[new_id]["score"])

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

    def test_call_tool_memory_get_chunk_exposes_replaces_and_replaced_by(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Original decision\n\n"
            "```yaml\n"
            "entry_id: ms-original\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "The first take on the cache key.\n\n"
            "## 2026-05-17 10:00 - Replacement decision\n\n"
            "```yaml\n"
            "entry_id: ms-replaces\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "replaces:\n"
            "  - ms-original\n"
            "```\n\n"
            "The corrected take on the cache key.\n",
        )

        replacing = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-replaces"})
        replaced = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-original"})

        self.assertEqual(replacing["chunk"]["replaces"], ["ms-original"])
        self.assertEqual(replacing["chunk"]["replaced_by"], [])
        self.assertEqual(replaced["chunk"]["replaces"], [])
        self.assertEqual(replaced["chunk"]["replaced_by"], ["ms-replaces"])

    def test_call_tool_memory_get_chunk_exposes_inbound_relation_count(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Cited decision\n\n"
            "```yaml\n"
            "entry_id: ms-cited0000\n"
            "```\n\n"
            "The decision two later entries cite.\n\n"
            "## 2026-05-17 10:00 - First citer\n\n"
            "```yaml\n"
            "entry_id: ms-citer0001\n"
            "related_entries:\n"
            "  - ms-cited0000\n"
            "```\n\n"
            "Cites the decision.\n\n"
            "## 2026-05-17 11:00 - Second citer\n\n"
            "```yaml\n"
            "entry_id: ms-citer0002\n"
            "related_entries:\n"
            "  - ms-cited0000\n"
            "```\n\n"
            "Also cites the decision.\n",
        )

        cited = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-cited0000"})
        citer = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-citer0001"})

        # Inbound backlinks only: citing others earns nothing; being cited does.
        self.assertEqual(cited["chunk"]["inbound_relation_count"], 2)
        self.assertEqual(citer["chunk"]["inbound_relation_count"], 0)
        # Not replaced: importance_score equals the raw inbound count.
        self.assertEqual(cited["chunk"]["importance_score"], 2.0)

    def test_call_tool_memory_get_chunk_exposes_commit_reference_count(self):
        cwd = self.make_project()  # no .git: field-only path
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Implemented decision\n\n"
            "```yaml\n"
            "entry_id: ms-withcommit\n"
            "commits:\n"
            "  - " + "a" * 40 + "\n"
            "```\n\n"
            "A decision with a linked commit.\n\n"
            "## 2026-05-17 10:00 - Plain decision\n\n"
            "```yaml\n"
            "entry_id: ms-nocommit0\n"
            "```\n\n"
            "No linked commit.\n",
        )

        linked = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-withcommit"})
        plain = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-nocommit0"})

        self.assertEqual(linked["chunk"]["commit_reference_count"], 1)
        self.assertEqual(plain["chunk"]["commit_reference_count"], 0)

    def test_call_tool_memory_get_chunk_dampens_importance_score_when_replaced(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Retired decision\n\n"
            "```yaml\n"
            "entry_id: ms-retired00\n"
            "```\n\n"
            "Cited but later replaced.\n\n"
            "## 2026-05-17 10:00 - Citer\n\n"
            "```yaml\n"
            "entry_id: ms-citer0001\n"
            "related_entries:\n"
            "  - ms-retired00\n"
            "```\n\n"
            "Cites the retired decision.\n\n"
            "## 2026-05-17 11:00 - Replacement\n\n"
            "```yaml\n"
            "entry_id: ms-replace00\n"
            "replaces:\n"
            "  - ms-retired00\n"
            "```\n\n"
            "Replaces it.\n",
        )

        retired = call_tool("memory_get_chunk", {"cwd": str(cwd), "chunk_id": "ms-retired00"})

        # Raw inbound count is 1, but the replaced dampener applies.
        self.assertEqual(retired["chunk"]["inbound_relation_count"], 1)
        self.assertEqual(retired["chunk"]["replaced_by"], ["ms-replace00"])
        self.assertLess(retired["chunk"]["importance_score"], 1.0)

    def test_call_tool_memory_get_chunk_returns_per_user_chunk(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-21/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-21\n"
            "hash_id: msm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "user: jean\n"
            "created_at: 2026-06-21T00:00:00Z\n"
            "---\n\n"
            "## 2026-06-21 10:00 - Dual-read MCP\n\n"
            "```yaml\n"
            "entry_id: ms-jean-mcp\n"
            "related_entries:\n"
            "  - ms-older-entry\n"
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
        self.assertEqual(payload["chunk"]["session_date"], "2026-06-21")
        self.assertEqual(payload["chunk"]["source"], ".memory-seed/sessions/2026-06-21/jean.md")
        self.assertEqual(payload["chunk"]["path"], ".memory-seed/sessions/2026-06-21/jean.md")
        self.assertEqual(payload["chunk"]["user"], "jean")
        self.assertEqual(payload["chunk"]["file_hash_id"], "msm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(payload["chunk"]["related_entries"], ["ms-older-entry"])
        self.assertIn("Per-user search text.", payload["chunk"]["text"])

    def test_memory_search_schema_accepts_user_and_date_filters(self):
        from memory_seed.mcp_server import TOOLS

        search_tool = next(t for t in TOOLS if t["name"] == "memory_search")
        properties = search_tool["inputSchema"]["properties"]

        self.assertIn("user", properties)
        self.assertIn("date_from", properties)
        self.assertIn("date_to", properties)

    def test_call_tool_memory_search_filters_by_user_and_date_before_ranking(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-20/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-20\n"
            "hash_id: msm_" + "a" * 32 + "\n"
            "user: jean\n"
            "---\n\n"
            "## 2026-06-20 09:00 - Shared topic\n\n"
            "```yaml\n"
            "entry_id: ms-jean-old\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "shared alpha topic.\n",
        )
        self.write_session(
            cwd,
            "2026-06-21/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-21\n"
            "hash_id: msm_" + "b" * 32 + "\n"
            "user: jean\n"
            "---\n\n"
            "## 2026-06-21 09:00 - Shared topic\n\n"
            "```yaml\n"
            "entry_id: ms-jean-new\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "shared alpha topic.\n",
        )
        self.write_session(
            cwd,
            "2026-06-21/amina.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-21\n"
            "hash_id: msm_" + "c" * 32 + "\n"
            "user: amina\n"
            "---\n\n"
            "## 2026-06-21 09:00 - Shared topic\n\n"
            "```yaml\n"
            "entry_id: ms-amina-new\n"
            "user_initials: AM\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "shared alpha topic.\n",
        )

        payload = call_tool(
            "memory_search",
            {
                "query": "shared alpha",
                "cwd": str(cwd),
                "top_k": 10,
                "semantic_enabled": False,
                "user": "jean",
                "date_from": "2026-06-21",
                "date_to": "2026-06-21",
            },
            today=date(2026, 6, 21),
        )

        self.assertEqual([result["chunk_id"] for result in payload["results"]], ["ms-jean-new"])
        self.assertEqual(payload["results"][0]["user"], "jean")
        self.assertEqual(payload["results"][0]["session_date"], "2026-06-21")
        self.assertEqual(payload["results"][0]["file_hash_id"], "msm_" + "b" * 32)

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

    @pytest.mark.integration
    def test_call_tool_memory_branch_status_reports_git_posture(self):
        cwd = self.make_project()
        (cwd / "README.md").write_text("# test\n", encoding="utf-8")
        self.init_git_project(cwd)
        self.commit_all(cwd, "base")

        payload = call_tool("memory_branch_status", {"cwd": str(cwd)})

        self.assertEqual(payload["status"]["branch"], "main")
        self.assertTrue(payload["status"]["is_git_repo"])
        self.assertTrue(payload["status"]["is_integration_branch"])
        self.assertIn("recommendation", payload["status"])

    @pytest.mark.integration
    def test_call_tool_memory_worktree_guard_reports_owned_namespace(self):
        cwd = self.make_project()
        (cwd / "README.md").write_text("# test\n", encoding="utf-8")
        self.init_git_project(cwd)
        self.commit_all(cwd, "base")
        worktree = cwd / ".codex" / "worktrees" / "mcp-task"
        worktree.parent.mkdir(parents=True)
        self.git(cwd, "worktree", "add", "-q", "-b", "codex/mcp-task", str(worktree))

        payload = call_tool(
            "memory_worktree_guard",
            {"cwd": str(worktree), "agent_type": "codex", "write_intent": True},
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["classification"], "owned-worktree")
        self.assertTrue(payload["safe_to_write"])
        self.assertEqual(payload["actual_namespace_owner"], "codex")

    @pytest.mark.integration
    def test_call_tool_memory_worktree_guard_blocks_foreign_namespace(self):
        cwd = self.make_project()
        (cwd / "README.md").write_text("# test\n", encoding="utf-8")
        self.init_git_project(cwd)
        self.commit_all(cwd, "base")
        worktree = cwd / ".claude" / "worktrees" / "mcp-task"
        worktree.parent.mkdir(parents=True)
        self.git(cwd, "worktree", "add", "-q", "-b", "claude/mcp-task", str(worktree))

        payload = call_tool(
            "memory_worktree_guard",
            {"cwd": str(worktree), "agent_type": "codex", "write_intent": True},
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["classification"], "foreign-worktree")
        self.assertFalse(payload["safe_to_write"])
        self.assertEqual(payload["severity"], "block")

    @pytest.mark.integration
    def test_call_tool_memory_session_fuse_preview_reports_parented_sidecar(self):
        cwd = self.make_project()
        self.write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self.init_git_project(cwd)
        self.commit_all(cwd, "base")
        self.git(cwd, "switch", "-c", "feature-fuse")
        self.write_legacy_diagram(cwd, "2026-07-10", "mse_0123456789abcdef")
        self.commit_all(cwd, "add sidecar")
        self.git(cwd, "switch", "main")

        payload = call_tool("memory_session_fuse_preview", {"cwd": str(cwd), "branch": "feature-fuse"})

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["issues"], [])
        self.assertEqual(payload["planned_entries"], [])
        self.assertEqual(
            payload["planned_sidecars"],
            ["mse_0123456789abcdef 2026-07-10 09:00 -> .memory-seed/sessions/diagrams/2026-07/2026-07-10.md"],
        )
        self.assertEqual(payload["write_surface"], "CLI-only; run apply during an in-progress git merge.")

    def test_call_tool_memory_link_suggest_ranks_older_lexical_candidates(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Cache key design\n\n"
            "```yaml\n"
            "entry_id: ms-cache0000\n"
            "```\n\n"
            "The original cache key sharding design.\n\n"
            "## 2026-05-17 10:00 - Unrelated hooks work\n\n"
            "```yaml\n"
            "entry_id: ms-hooks0000\n"
            "```\n\n"
            "Session start hook wiring, nothing about storage.\n\n"
            "## 2026-05-17 11:00 - Revisit cache key sharding\n\n"
            "```yaml\n"
            "entry_id: ms-newcache0\n"
            "```\n\n"
            "Revisit the cache key sharding design decided earlier.\n",
        )

        payload = call_tool("memory_link_suggest", {"cwd": str(cwd), "top_k": 5})

        # Defaults to the newest entry as the target the agent just wrote...
        self.assertEqual(payload["target"]["entry_id"], "ms-newcache0")
        # ...and the lexically-closest older entry ranks first for related_entries.
        self.assertEqual(payload["related_entries"][0], "ms-cache0000")
        # Forward-only: the target never suggests linking to itself.
        self.assertNotIn("ms-newcache0", payload["related_entries"])

    def test_call_tool_memory_link_suggest_honors_explicit_entry_id(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Oldest\n\n```yaml\nentry_id: ms-oldest000\n```\n\nAlpha topic.\n\n"
            "## 2026-05-17 10:00 - Middle\n\n```yaml\nentry_id: ms-middle000\n```\n\nAlpha topic again.\n\n"
            "## 2026-05-17 11:00 - Newest\n\n```yaml\nentry_id: ms-newest000\n```\n\nAlpha topic once more.\n",
        )

        payload = call_tool(
            "memory_link_suggest",
            {"cwd": str(cwd), "entry_id": "ms-middle000"},
        )

        # Target is the requested entry; only strictly-older entries are candidates.
        self.assertEqual(payload["target"]["entry_id"], "ms-middle000")
        self.assertEqual(payload["related_entries"], ["ms-oldest000"])

    def test_call_tool_memory_link_show_reports_graph_node(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Cited decision\n\n"
            "```yaml\n"
            "entry_id: ms-cited0000\n"
            "```\n\n"
            "The decision a later entry cites.\n\n"
            "## 2026-05-17 10:00 - Citer\n\n"
            "```yaml\n"
            "entry_id: ms-citer0001\n"
            "related_entries:\n"
            "  - ms-cited0000\n"
            "```\n\n"
            "Cites the decision.\n",
        )

        cited = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": "ms-cited0000"})
        citer = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": "ms-citer0001"})

        # Inbound backlinks are computed at read time; outbound is stored as declared.
        self.assertEqual(cited["inbound"], ["ms-citer0001"])
        self.assertEqual(cited["outbound"], [])
        self.assertEqual(cited["inbound_relation_count"], 1)
        self.assertEqual(cited["importance_score"], 1.0)
        # No .git in this fixture: commit reference scan degrades to the field-only set.
        self.assertEqual(cited["commit_reference_count"], 0)
        self.assertEqual(citer["outbound"], ["ms-cited0000"])
        self.assertEqual(citer["inbound"], [])

    def test_call_tool_memory_link_show_reports_lifecycle_and_continuity(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Base decision\n\n"
            "```yaml\n"
            "entry_id: ms-base00000\n"
            "```\n\n"
            "The foundational design.\n\n"
            "## 2026-05-17 10:00 - Refinement\n\n"
            "```yaml\n"
            "entry_id: ms-refine000\n"
            "evolves:\n"
            "  - ms-base00000\n"
            "continuity:\n"
            "  - kind: rename\n"
            "    from: old/name.py\n"
            "    to: new/name.py\n"
            "```\n\n"
            "Extends the foundational design and renames the module.\n",
        )

        base = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": "ms-base00000"})
        refine = call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": "ms-refine000"})

        self.assertEqual(base["evolved_by"], ["ms-refine000"])
        self.assertEqual(base["evolves"], [])
        # Evolution never dampens: base stays at its raw inbound count.
        self.assertEqual(base["importance_score"], 0.0)
        self.assertEqual(base["replaced_by"], [])
        self.assertEqual(refine["evolves"], ["ms-base00000"])
        self.assertEqual(refine["continuity"], [{"kind": "rename", "from": "old/name.py", "to": "new/name.py"}])

    def test_call_tool_memory_link_suggest_reports_shared_file_evidence(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 08:00 - Unrelated hooks work\n\n"
            "```yaml\n"
            "entry_id: ms-hooks0000\n"
            "```\n\n"
            "Hook wiring, nothing about scoring.\n\n"
            "- F: `hooks/check.py`.\n\n"
            "## 2026-05-17 09:00 - Ranker groundwork\n\n"
            "```yaml\n"
            "entry_id: ms-ground000\n"
            "```\n\n"
            "Scoring pipeline groundwork.\n\n"
            "- F: `src/ranker.py`.\n\n"
            "## 2026-05-17 11:00 - Ranker follow-up\n\n"
            "```yaml\n"
            "entry_id: ms-follow000\n"
            "```\n\n"
            "Scoring pipeline follow-up.\n\n"
            "- F: `src/ranker.py`.\n",
        )

        payload = call_tool("memory_link_suggest", {"cwd": str(cwd), "entry_id": "ms-follow000"})

        suggestion = payload["suggestions"][0]
        self.assertEqual(suggestion["entry_id"], "ms-ground000")
        self.assertEqual(suggestion["shared_files"], ["src/ranker.py"])
        self.assertGreater(suggestion["file_overlap_bonus"], 0.0)
        self.assertEqual(
            suggestion["adjusted_score"],
            round(suggestion["score"] + suggestion["file_overlap_bonus"], 6),
        )

    def test_memory_link_suggest_exposes_consulted_param(self):
        from memory_seed.mcp_server import TOOLS

        tool = next(t for t in TOOLS if t["name"] == "memory_link_suggest")
        prop = tool["inputSchema"]["properties"].get("consulted")
        self.assertIsNotNone(prop)
        self.assertEqual(prop["type"], "array")

    def test_call_tool_memory_link_suggest_consulted_flags_and_ranks_first(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 08:00 - Lineage parent, no shared file\n\n"
            "```yaml\n"
            "entry_id: ms-lineage00\n"
            "```\n\n"
            "A prior decision on the same concept, recorded against a different file.\n\n"
            "- F: `docs/design.md`.\n\n"
            "## 2026-05-17 09:00 - File sharer\n\n"
            "```yaml\n"
            "entry_id: ms-ground000\n"
            "```\n\n"
            "Scoring pipeline groundwork.\n\n"
            "- F: `src/ranker.py`.\n\n"
            "## 2026-05-17 11:00 - Ranker follow-up\n\n"
            "```yaml\n"
            "entry_id: ms-follow000\n"
            "```\n\n"
            "Scoring pipeline follow-up.\n\n"
            "- F: `src/ranker.py`.\n",
        )

        # Without consulted: the file-sharer leads, nothing flagged.
        plain = call_tool("memory_link_suggest", {"cwd": str(cwd), "entry_id": "ms-follow000"})
        self.assertEqual(plain["suggestions"][0]["entry_id"], "ms-ground000")
        self.assertFalse(any(s["consulted"] for s in plain["suggestions"]))

        # Naming the lineage parent consulted flags it and sorts it first, even
        # though it shares no file with the target - the axis file overlap misses.
        out = call_tool(
            "memory_link_suggest",
            {"cwd": str(cwd), "entry_id": "ms-follow000", "consulted": ["ms-lineage00"]},
        )
        self.assertEqual(out["suggestions"][0]["entry_id"], "ms-lineage00")
        self.assertTrue(out["suggestions"][0]["consulted"])
        self.assertEqual(out["related_entries"][0], "ms-lineage00")

    def test_call_tool_memory_link_show_raises_on_unknown_entry(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:00 - Only\n\n```yaml\nentry_id: ms-only0000\n```\n\nBody.\n",
        )

        with self.assertRaises(ValueError):
            call_tool("memory_link_show", {"cwd": str(cwd), "entry_id": "ms-missing00"})

    def test_call_tool_memory_topics_list_returns_vocabulary(self):
        cwd = self.make_project()
        self.write_topics_index(cwd)

        payload = call_tool("memory_topics_list", {"cwd": str(cwd)})

        self.assertTrue(payload["exists"])
        self.assertEqual(payload["schema_version"], "1")
        self.assertEqual([topic["slug"] for topic in payload["topics"]], ["retrieval", "old-theme"])
        self.assertEqual(payload["topics"][0]["aliases"], ["search", "ranking"])
        self.assertIn("Read-only", payload["write_surface"])

    def test_call_tool_memory_topic_inspect_resolves_alias_and_reports_usage(self):
        cwd = self.make_project()
        self.write_topics_index(cwd)
        self.write_session(
            cwd,
            "2026-07-01.md",
            "## 2026-07-01 09:00 - Retrieval work\n\n"
            "```yaml\n"
            "entry_id: ms-topic0000\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "topics:\n"
            "  - search\n"
            "```\n\n"
            "Improved ranking.\n",
        )

        payload = call_tool("memory_topic_inspect", {"cwd": str(cwd), "topic": "ranking"})

        self.assertTrue(payload["found"])
        self.assertEqual(payload["canonical"], "retrieval")
        self.assertEqual(payload["matching_names"], ["ranking", "retrieval", "search"])
        self.assertEqual(payload["usage_count"], 1)
        self.assertEqual(payload["entries"][0]["entry_id"], "ms-topic0000")
        self.assertEqual(payload["entries"][0]["topics"], ["search"])

    def test_call_tool_memory_topics_check_reports_validation_issues(self):
        cwd = self.make_project()
        self.write_topics_index(cwd)
        self.write_session(
            cwd,
            "2026-07-01.md",
            "## 2026-07-01 09:00 - Topic validation\n\n"
            "```yaml\n"
            "entry_id: ms-topicbad\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "topics:\n"
            "  - missing-topic\n"
            "```\n\n"
            "Bad topic.\n",
        )

        payload = call_tool("memory_topics_check", {"cwd": str(cwd)})

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["topics_defined"], 2)
        self.assertEqual(payload["entries_checked"], 1)
        self.assertIn("unknown-entry-topic", [issue["kind"] for issue in payload["issues"]])

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
        listed_names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertIn("memory_search", listed_names)
        self.assertIn("memory_branch_status", listed_names)
        self.assertIn("memory_worktree_guard", listed_names)
        self.assertIn("memory_session_fuse_preview", listed_names)
        self.assertIn("memory_link_suggest", listed_names)
        self.assertIn("memory_link_show", listed_names)
        self.assertIn("memory_session_append", listed_names)
        # The ungated authoring pair is gone: no tool hands out a bare id or
        # a write target for an agent to hand-write a session file with.
        self.assertNotIn("memory_session_target", listed_names)
        self.assertNotIn("memory_entry_id", listed_names)
        self.assertIn("memory_topics_list", listed_names)
        self.assertIn("memory_topic_inspect", listed_names)
        self.assertIn("memory_topics_check", listed_names)
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
