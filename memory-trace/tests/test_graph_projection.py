"""B0a conformance tests for renderer-neutral graph benchmark fixtures."""
from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_trace.service import TraceCache, TraceService
from memory_trace.graph_projection import (
    FIXTURE_SCHEMA_VERSION,
    GraphProjectionContractError,
    load_graph_fixture,
    project_trace_graph,
    renderer_input,
)


FIXTURE = Path(__file__).parent / "fixtures" / "graph-renderer" / "bounded-neighbourhood.v1.json"


class GraphProjectionFixtureTests(unittest.TestCase):
    def test_bounded_fixture_is_renderer_neutral_and_benchmark_ready(self):
        fixture = load_graph_fixture(FIXTURE)

        self.assertEqual(fixture["schema_version"], FIXTURE_SCHEMA_VERSION)
        self.assertEqual({node["node_type"] for node in fixture["nodes"]}, {"memory_entry"})
        self.assertTrue({"related", "supersedes", "evolves", "branch", "topic"}.issubset(
            {edge["edge_type"] for edge in fixture["edges"]}
        ))
        self.assertEqual(fixture["selection"]["selected_node_id"], "memory:entry:mse_b0a_shell")
        self.assertEqual(
            {case["layout"] for case in fixture["benchmark_cases"]},
            {"topology", "temporal_topology", "evolution_hierarchy"},
        )

    def test_renderer_input_detaches_but_preserves_semantics(self):
        fixture = load_graph_fixture(FIXTURE)
        adapter_input = renderer_input(fixture)

        self.assertEqual(adapter_input, fixture)
        self.assertIsNot(adapter_input, fixture)
        adapter_input["nodes"][0]["label"] = "renderer-local change"
        self.assertNotEqual(adapter_input["nodes"][0]["label"], fixture["nodes"][0]["label"])

    def test_renderer_owned_coordinates_are_rejected(self):
        fixture = load_graph_fixture(FIXTURE)
        invalid = copy.deepcopy(fixture)
        invalid["nodes"][0]["x"] = 120

        with self.assertRaisesRegex(GraphProjectionContractError, "renderer-owned"):
            renderer_input(invalid)

    def test_noncanonical_edge_kind_is_rejected(self):
        fixture = load_graph_fixture(FIXTURE)
        invalid = copy.deepcopy(fixture)
        invalid["edges"][0]["edge_type"] = "provider_call_graph"

        with self.assertRaisesRegex(GraphProjectionContractError, "canonical graph edge"):
            renderer_input(invalid)

    def test_live_trace_graph_adapts_without_renderer_state(self):
        projection = project_trace_graph(
            {
                "nodes": [
                    {
                        "id": "mse_one",
                        "entry_id": "mse_one",
                        "title": "First entry",
                        "date": "2026-07-16",
                        "datetime": "2026-07-16T09:00:00+00:00",
                        "connectivity": 2,
                        "importance_score": 1.5,
                        "provenance_class": "authored_memory",
                    },
                    {
                        "id": "mse_two",
                        "entry_id": "mse_two",
                        "title": "Second entry",
                        "date": "2026-07-16",
                        "datetime": None,
                        "connectivity": 1,
                        "importance_score": 0.0,
                    },
                ],
                "edges": [{"source": "mse_two", "target": "mse_one", "type": "evolves"}],
            }
        )

        self.assertEqual(projection["nodes"][0]["temporal"]["source"], "authored_timestamp")
        self.assertEqual(projection["nodes"][1]["temporal"], {"value": "2026-07-16", "source": "authored_timestamp", "precision": "date"})
        self.assertEqual(projection["edges"][0]["evidence_refs"], ["mse_two", "mse_one"])
        self.assertNotIn("position", projection["nodes"][0])
        self.assertEqual(projection["nodes"][0]["community"]["id"], "community:unassigned")

    def test_adapter_consumes_a_real_trace_service_graph(self):
        project = Path(tempfile.mkdtemp(prefix="memory-trace-projection-"))
        cache_root = Path(tempfile.mkdtemp(prefix="memory-trace-projection-cache-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(cache_root, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-07-16.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            "## 2026-07-16 09:00 - First graph entry\n\n"
            "```yaml\nentry_id: mse_projection_one\nuser_initials: TS\nagent_type: codex\nproject_path: .\nsubproject_path: null\n```\n\n"
            "### Decision\n\n- D: Establish the projection fixture.\n- R: Renderer evidence needs one shared input.\n\n"
            "## 2026-07-16 09:10 - Second graph entry\n\n"
            "```yaml\nentry_id: mse_projection_two\nuser_initials: TS\nagent_type: codex\nproject_path: .\nsubproject_path: null\nrelated_entries:\n  - mse_projection_one\n```\n\n"
            "### Decision\n\n- D: Link the second entry to the first.\n- R: The live graph needs a canonical edge.\n",
            encoding="utf-8",
        )
        cache = TraceCache(project, cache_root=cache_root)
        cache.rebuild()

        projection = project_trace_graph(TraceService(cache).graph(edge_types=("related",), limit=10))

        self.assertEqual(len(projection["nodes"]), 2)
        self.assertEqual(projection["edges"][0]["edge_type"], "related")
        self.assertEqual(projection["nodes"][0]["temporal"]["precision"], "timestamp")


if __name__ == "__main__":
    unittest.main()
