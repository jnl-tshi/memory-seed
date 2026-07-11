"""Contract tests for the versioned /api/v1/* surface (roadmap Phase 1).

Two things must hold: (1) v1 routes return response_model-validated data
matching what LenseService already returns, and (2) the legacy /api/*
routes are completely unaffected - the vanilla frontend's contract is
frozen, v1 is additive alongside it.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.lense import create_app


def _entry(title, entry_id, body, *, agent="codex", related=None, branch=None, supersedes=None, evolves=None, topics=None):
    lines = [
        f"## {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        f"agent_type: {agent}",
        "project_path: .",
        "subproject_path: null",
    ]
    if branch:
        lines.append(f"branch: {branch}")
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {topic}" for topic in topics)
    if related:
        lines.append("related_entries:")
        lines.extend(f"  - {ref}" for ref in related)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {ref}" for ref in supersedes)
    if evolves:
        lines.append("evolves:")
        lines.extend(f"  - {ref}" for ref in evolves)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class V1ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-v1-test-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-v1-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + "\n".join(
                [
                    _entry(
                        "2026-06-01 09:00 - Bootstrap cache",
                        "mse_bootstrap",
                        "Built #cache support for bootstrap runtime discovery.",
                        topics=["cache"],
                    ),
                    _entry(
                        "2026-06-01 12:00 - UI shell",
                        "mse_ui",
                        "Designed #ui filters and Memory Lense panes.",
                        related=["mse_bootstrap"],
                        branch="feature-ui",
                        topics=["ui"],
                    ),
                ]
            ),
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            self.app = create_app(self.cwd, rebuild_cache=True)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.app)

    def test_v1_runtime_facets_and_legacy_agree(self):
        client = self.client()

        legacy = client.get("/api/runtime").json()
        v1 = client.get("/api/v1/runtime").json()

        self.assertEqual(legacy, v1)
        self.assertEqual(v1["entry_count"], 2)

        facets = client.get("/api/v1/facets").json()
        self.assertEqual(facets["topics"], {"cache": 1, "ui": 1})
        self.assertIn("chunk_count", facets["runtime"])

    def test_v1_search_matches_legacy_and_covers_rollup_fields(self):
        client = self.client()

        legacy = client.get("/api/search", params={"q": "Memory Lense ui"}).json()
        v1 = client.get("/api/v1/search", params={"q": "Memory Lense ui"}).json()

        self.assertEqual(legacy["results"][0]["chunk_id"], v1["results"][0]["chunk_id"])
        result = v1["results"][0]
        self.assertIn("best_match_chunk_id", result)
        self.assertIn("matched_sections", result)

    def test_v1_chunk_matches_legacy_and_has_typed_metadata(self):
        client = self.client()

        legacy = client.get("/api/chunks/mse_ui").json()
        v1 = client.get("/api/v1/chunks/mse_ui").json()

        self.assertEqual(legacy["chunk_id"], v1["chunk_id"])
        self.assertEqual(v1["related_entries"], ["mse_bootstrap"])
        self.assertEqual(v1["backlinks"], [])
        self.assertIn("source", v1["metadata"])
        self.assertEqual(v1["suggestions"]["same_topic"], [])

    def test_v1_chunk_404_matches_legacy(self):
        client = self.client()

        self.assertEqual(client.get("/api/chunks/does-not-exist").status_code, 404)
        self.assertEqual(client.get("/api/v1/chunks/does-not-exist").status_code, 404)

    def test_v1_graph_node_has_default_authored_memory_provenance(self):
        client = self.client()

        v1 = client.get("/api/v1/graph", params={"granularity": "entry", "limit": 100}).json()
        self.assertTrue(v1["nodes"])
        for node in v1["nodes"]:
            self.assertEqual(node["provenance_class"], "authored_memory")
        for edge in v1["edges"]:
            self.assertIn(
                edge["type"],
                {"related", "supersedes", "evolves", "branch", "topic", "agent", "day"},
            )

    def test_v1_trail_fixes_edge_types_to_trail_set(self):
        client = self.client()

        v1 = client.get("/api/v1/trail", params={"limit": 100}).json()
        self.assertEqual(sorted(v1["edge_types"]), sorted(["branch", "evolves", "related", "supersedes"]))
        node_ids = {node["entry_id"] for node in v1["nodes"]}
        self.assertEqual(node_ids, {"mse_bootstrap", "mse_ui"})

    def test_v1_timeline_has_no_counterpart(self):
        client = self.client()

        self.assertEqual(client.get("/api/timeline").status_code, 200)
        self.assertEqual(client.get("/api/v1/timeline").status_code, 404)

    def test_legacy_routes_unaffected_by_v1_addition(self):
        client = self.client()

        for path in ("/api/runtime", "/api/facets", "/api/search", "/api/timeline", "/api/graph"):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_openapi_schema_exposes_named_v1_models(self):
        schema = self.app.openapi()

        for path in (
            "/api/v1/runtime",
            "/api/v1/facets",
            "/api/v1/search",
            "/api/v1/graph",
            "/api/v1/trail",
        ):
            self.assertIn(path, schema["paths"], path)

        schema_names = set(schema["components"]["schemas"])
        for name in ("RuntimeInfo", "Facets", "GraphNode", "TrailEvent", "ProvenanceClass", "EdgeType"):
            self.assertTrue(
                any(name in key for key in schema_names),
                f"{name} not found among component schemas: {sorted(schema_names)}",
            )


if __name__ == "__main__":
    unittest.main()
