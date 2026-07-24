"""Structural checks on the committed v1 OpenAPI contract fixture.

Asserts shape (paths present, key models/enum values expose the right
fields), not byte-equality - a FastAPI/Pydantic version bump reformats the
raw schema and would fail a byte-diff test for no real reason. Also checks
the fixture hasn't drifted from what the live app currently produces, using
the same filtering the export script applies, so route/model changes are
caught without demanding exact fixture regeneration on every dependency bump.
"""

import json
import sys
import unittest
from pathlib import Path

CONTRACT_DIR = Path(__file__).parent / "contract"
FIXTURE = CONTRACT_DIR / "openapi.v1.json"

sys.path.insert(0, str(CONTRACT_DIR))
from export_openapi import filtered_v1_schema  # noqa: E402

from memory_trace.service import create_app  # noqa: E402


class OpenApiContractFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_v1_paths_present(self):
        expected = {
            "/api/v1/worktrees",
            "/api/v1/runtime",
            "/api/v1/facets",
            "/api/v1/search",
            "/api/v1/chunks/{chunk_id}",
            "/api/v1/graph",
            "/api/v1/graph/projection",
            "/api/v1/trail",
        }
        self.assertEqual(set(self.fixture["paths"]), expected)

    def test_no_legacy_paths_leaked_in(self):
        for path in self.fixture["paths"]:
            self.assertTrue(path.startswith("/api/v1"), path)

    def test_provenance_class_is_the_full_seven_value_enum(self):
        schema = self.fixture["components"]["schemas"]["ProvenanceClass"]
        self.assertEqual(
            set(schema["enum"]),
            {
                "authored_memory",
                "source_control",
                "pr_review",
                "automation_ci",
                "annotation",
                "release",
                "generated_artefact",
            },
        )

    def test_edge_type_covers_every_kind_graph_edges_produces(self):
        schema = self.fixture["components"]["schemas"]["EdgeType"]
        self.assertEqual(
            set(schema["enum"]),
            {"related", "replaces", "evolves", "branch", "topic", "agent", "day"},
        )

    def test_graph_node_and_trail_event_both_carry_provenance_class(self):
        schemas = self.fixture["components"]["schemas"]
        for name in ("GraphNode", "TrailEvent"):
            self.assertIn("provenance_class", schemas[name]["properties"], name)

    def test_continuity_schema_uses_ordered_kind_from_to_shape(self):
        schemas = self.fixture["components"]["schemas"]
        continuity = schemas["ContinuityItem"]
        self.assertEqual(set(continuity["required"]), {"kind", "from"})
        self.assertIn("to", continuity["properties"])
        self.assertEqual(
            set(continuity["properties"]),
            {"kind", "from", "to"},
        )
        for name in ("ChunkResponse", "GraphNode", "TrailEvent", "SearchResult"):
            self.assertIn("continuity", schemas[name]["properties"], name)

    def test_fixture_matches_live_app_filtering(self):
        import os
        import shutil
        import tempfile

        fixtures_dir = Path(__file__).parent / "fixtures"
        sys.path.insert(0, str(fixtures_dir))
        from generate_synthetic import generate  # noqa: E402

        corpus_dir = Path(tempfile.mkdtemp(prefix="memory-trace-openapi-fixture-check-"))
        cache_dir = Path(tempfile.mkdtemp(prefix="memory-trace-openapi-fixture-check-cache-"))
        try:
            generate(48, corpus_dir)
            os.environ["MEMORY_SEED_LENSE_CACHE_ROOT"] = str(cache_dir)
            live = filtered_v1_schema(create_app(corpus_dir, rebuild_cache=True).openapi())
            self.assertEqual(set(live["paths"]), set(self.fixture["paths"]))
            self.assertEqual(set(live["components"]["schemas"]), set(self.fixture["components"]["schemas"]))
        finally:
            shutil.rmtree(corpus_dir, ignore_errors=True)
            shutil.rmtree(cache_dir, ignore_errors=True)
            os.environ.pop("MEMORY_SEED_LENSE_CACHE_ROOT", None)


if __name__ == "__main__":
    unittest.main()
