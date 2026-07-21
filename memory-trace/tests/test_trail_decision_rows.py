"""Per-decision Trail rows (opt-in, /api/v1/trail only).

A multi-decision entry (>=2 ``#### Dn -`` decisions) expands into a heading
plus subheadings: the entry's own row anchors the group (ordinal None, count
N) and EVERY decision D1..DN appends a row with its section chunk_id as a
unique id, the parent's time/branch/agent/topics, and entry-scoped
affordances (continuity, diagram badge) deliberately stripped.
Singular-``### Decision`` and no-decision entries are untouched, as is every
non-trail surface.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from memory_trace.service import TraceCache, TraceService, create_app

MULTI = """## 2026-06-01 09:00 - multi decision entry

```yaml
entry_id: mse_multi
branch: claude/feature/example
```

### Summary

- One task, three calls.

### Decisions

#### D1 - First call

- D: one.
- R: because.

#### D2 - Second call

- D: two.
- R: because.

#### D3 - Third call

- D: three.
- R: because.

### Follow-up

- Later.

## 2026-06-01 10:00 - singular decision entry

```yaml
entry_id: mse_single
```

### Decision

- D: only.
- R: because.

## 2026-06-01 11:00 - no decision section

```yaml
entry_id: mse_none
```

Notes only.
"""


class TrailDecisionRowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cwd = Path(tempfile.mkdtemp(prefix="mtrace-decisions-"))
        cls.cache_root = Path(tempfile.mkdtemp(prefix="mtrace-decisions-cache-"))
        sessions = cls.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n" + MULTI, encoding="utf-8"
        )
        cls.cache = TraceCache(cls.cwd, cache_root=cls.cache_root)
        cls.cache.rebuild()
        cls.service = TraceService(cls.cache)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cwd, ignore_errors=True)
        shutil.rmtree(cls.cache_root, ignore_errors=True)

    def trail_nodes(self):
        return self.service.graph(
            edge_types=("branch", "supersedes", "evolves", "related"),
            limit=1000,
            include_decisions=True,
        )["nodes"]

    def test_multi_decision_entry_expands_to_anchor_plus_every_decision(self):
        # A heading and its subheadings: the entry row anchors the group and
        # EVERY decision gets a row, D1 included - a document does not skip
        # heading 1. Ordinal absent is what marks the anchor; decision_count
        # is what separates it from an ordinary single-decision entry.
        nodes = [node for node in self.trail_nodes() if node["entry_id"] == "mse_multi"]
        self.assertEqual([node.get("decision_ordinal") for node in nodes], [None, "d1", "d2", "d3"])
        self.assertEqual(len({node["id"] for node in nodes}), 4, "row ids must be unique")
        anchor, first, second, third = nodes
        self.assertEqual(anchor["decision_count"], 3)
        self.assertEqual(anchor["granularity"], "entry")
        self.assertEqual(anchor["id"], "mse_multi")
        self.assertEqual(first["id"], "mse_multi#decisions/d1-first-call")
        self.assertEqual(second["id"], "mse_multi#decisions/d2-second-call")
        self.assertEqual(second["chunk_id"], second["id"])
        self.assertEqual(second["title"], "D2 - Second call")
        self.assertEqual(second["granularity"], "section")
        self.assertEqual(second["decision_count"], 0)
        for child in (first, second, third):
            self.assertEqual(child["datetime"], anchor["datetime"])
            self.assertEqual(child["branch"], anchor["branch"])
            self.assertEqual(child["agent"], anchor["agent"])
            self.assertEqual(child["topics"], anchor["topics"])
            self.assertEqual(child["continuity"], [])
            self.assertFalse(child["has_diagram"])

    def test_non_decision_sections_do_not_expand(self):
        titles = [node["title"] for node in self.trail_nodes() if node["entry_id"] == "mse_multi"]
        self.assertNotIn("Follow-up", titles)
        self.assertNotIn("Summary", titles)

    def test_singular_and_no_decision_entries_stay_single_rows(self):
        nodes = self.trail_nodes()
        for entry_id in ("mse_single", "mse_none"):
            rows = [node for node in nodes if node["entry_id"] == entry_id]
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0].get("decision_ordinal"))
            self.assertFalse(rows[0].get("decision_count"))

    def test_default_graph_output_is_unchanged(self):
        plain = self.service.graph(
            edge_types=("branch", "supersedes", "evolves", "related"), limit=1000
        )["nodes"]
        self.assertEqual(len([node for node in plain if node["entry_id"] == "mse_multi"]), 1)
        self.assertNotIn("decision_ordinal", plain[0])

    def test_only_the_trail_endpoint_expands(self):
        client = TestClient(create_app(self.cwd, rebuild_cache=True))
        trail = client.get("/api/v1/trail", params={"limit": 100}).json()
        trail_multi = [node for node in trail["nodes"] if node["entry_id"] == "mse_multi"]
        self.assertEqual(len(trail_multi), 4)
        self.assertIsNone(trail_multi[0]["decision_ordinal"])
        self.assertEqual(trail_multi[0]["decision_count"], 3)

        graph = client.get("/api/v1/graph", params={"limit": 100}).json()
        graph_multi = [node for node in graph["nodes"] if node["entry_id"] == "mse_multi"]
        self.assertEqual(len(graph_multi), 1)
        self.assertIsNone(graph_multi[0]["decision_ordinal"])

        projection = client.get(
            "/api/v1/graph/projection",
            params={"limit": 100, "edge_types": "related,supersedes,evolves,topic"},
        ).json()
        projection_multi = [
            node for node in projection["nodes"] if node["source"]["entry_id"] == "mse_multi"
        ]
        self.assertLessEqual(len(projection_multi), 1)


if __name__ == "__main__":
    unittest.main()
