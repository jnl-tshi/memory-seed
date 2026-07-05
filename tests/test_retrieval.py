import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from memory_seed.mcp_server import call_tool
from memory_seed.retrieval import (
    get_chunk,
    rollup_entry_matches,
    rollup_entry_results,
    search_memory,
)
from memory_seed.semantic_cache import extract_memory_chunks, rank_memory_chunks


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

    def make_sectioned_fixture(self):
        """One entry with two distinct matching subsections + one unrelated entry."""
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-01.md",
            "## 2026-06-01 09:00 - Cache invalidation rework\n\n"
            "```yaml\n"
            "entry_id: ms-cache01\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Reworked the cache layer.\n\n"
            "### Decision\n\n"
            "- D: Use zanzibar tokens for cache keys.\n\n"
            "### Tests\n\n"
            "- T: Added zanzibar token round-trip coverage.\n",
        )
        self.write_session(
            cwd,
            "2026-06-02.md",
            "## 2026-06-02 10:00 - Unrelated docs pass\n\n"
            "```yaml\n"
            "entry_id: ms-docs02\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Refreshed the README wording.\n",
        )
        return cwd

    def test_rollup_collapses_section_matches_into_one_entry_result(self):
        cwd = self.make_sectioned_fixture()
        pool = [
            *extract_memory_chunks(str(cwd), granularity="entry"),
            *extract_memory_chunks(str(cwd), granularity="section"),
        ]
        ranked = rank_memory_chunks("zanzibar tokens", pool, top_k=len(pool), embedding_provider=None)
        # Multiple chunks from the same entry match ("Decision" + "Tests"
        # sections both mention zanzibar) ...
        matching_ids = {r.chunk.chunk_id for r in ranked if r.matched_fields}
        self.assertGreater(len({cid for cid in matching_ids if cid.startswith("ms-cache01")}), 1)
        # ... but they collapse into ONE visible entry-level record.
        records = rollup_entry_results(ranked, top_k=8)
        cache_records = [r for r in records if r["entry_id"] == "ms-cache01"]
        self.assertEqual(len(cache_records), 1)
        record = cache_records[0]
        # The visible record is the entry, not a section.
        self.assertEqual(record["chunk_id"], "ms-cache01")
        self.assertEqual(record["granularity"], "entry")
        # Best-match/highlight metadata is preserved.
        self.assertIn("best_match_chunk_id", record)
        self.assertIn(record["score_source"], {"entry", "section-rollup"})
        matched_headings = {
            tuple(section["heading_path"]) for section in record["matched_sections"]
        }
        self.assertTrue(matched_headings)
        for section in record["matched_sections"]:
            self.assertTrue(section["chunk_id"].startswith("ms-cache01#"))
            self.assertIn("excerpt", section)
            self.assertIn("line_range", section)

    def test_rollup_representative_prefers_entry_chunk(self):
        cwd = self.make_sectioned_fixture()
        pool = [
            *extract_memory_chunks(str(cwd), granularity="entry"),
            *extract_memory_chunks(str(cwd), granularity="section"),
        ]
        ranked = rank_memory_chunks("zanzibar tokens", pool, top_k=len(pool), embedding_provider=None)
        rollups = rollup_entry_matches(ranked)
        cache_rollup = next(r for r in rollups if r.entry_key == "ms-cache01")
        self.assertEqual(cache_rollup.representative.chunk.granularity, "entry")
        # Only genuinely-matching sections ride along as highlight metadata.
        for section in cache_rollup.sections:
            self.assertTrue(section.matched_fields)

    def test_mcp_section_granularity_is_unchanged_by_rollup(self):
        cwd = self.make_sectioned_fixture()
        result = call_tool(
            "memory_search",
            {
                "query": "zanzibar tokens",
                "cwd": str(cwd),
                "semantic_enabled": False,
                "granularity": "section",
            },
        )
        # Section granularity still returns raw section chunks - no rollup
        # fields leak into the MCP contract.
        section_results = [r for r in result["results"] if r["granularity"] == "section"]
        self.assertTrue(section_results)
        for record in result["results"]:
            self.assertNotIn("matched_sections", record)
            self.assertNotIn("best_match_chunk_id", record)
            self.assertNotIn("score_source", record)

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
