"""Coordinated Area/Activity filtering is decision-granular, not a topic union."""

from datetime import date, datetime
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from memory_seed.semantic_cache import MemoryChunk
from memory_trace.service import TraceService, _contextual_ontology_counts, _filter_chunks


class OntologyFacetTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-trace-ontology-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        memory = self.cwd / ".memory-seed"
        memory.mkdir()
        (memory / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: area-root
    axis: area
  - slug: area-empty
    parent: area-root
  - slug: area-parent
    parent: area-root
  - slug: area-a
    parent: area-parent
  - slug: area-b
    parent: area-root
  - slug: activity-root
    axis: activity
  - slug: activity-empty
    parent: activity-root
  - slug: activity-x
    parent: activity-root
  - slug: activity-y
    parent: activity-root
  - slug: activity-empty-root
    axis: activity
""",
            encoding="utf-8",
        )

    @staticmethod
    def entry(entry_id, pairs):
        return MemoryChunk(
            chunk_id=entry_id,
            granularity="entry",
            entry_id=entry_id,
            source_path="session.md",
            source_file="session.md",
            session_date=date(2026, 7, 31),
            entry_datetime=datetime(2026, 7, 31, 9, 0),
            heading_path=(),
            heading_level=2,
            title=entry_id,
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=1,
            text="body",
            inferred_topics=tuple(slug for _, slug in pairs),
            inferred_decision_topics=tuple(pairs),
        )

    def test_combined_filter_requires_one_decision_to_carry_both_axes(self):
        paired = self.entry("mse_paired", [("d1", "area-a"), ("d1", "activity-y")])
        split = self.entry("mse_split", [("d1", "area-a"), ("d2", "activity-y")])

        result = _filter_chunks([paired, split], area="area-a", activity="activity-y", cwd=self.cwd)

        self.assertEqual([chunk.entry_id for chunk in result], ["mse_paired"])

    def test_each_axis_offers_options_constrained_by_the_other_axis_only(self):
        entries = [
            self.entry("mse_ax", [("d1", "area-a"), ("d1", "activity-x")]),
            self.entry("mse_ay", [("d1", "area-a"), ("d1", "activity-y")]),
            self.entry("mse_by", [("d1", "area-b"), ("d1", "activity-y")]),
            self.entry("mse_split", [("d1", "area-a"), ("d2", "activity-y")]),
        ]

        counts = _contextual_ontology_counts(entries, cwd=self.cwd, area="area-a", activity="activity-y")

        # Activity choices are calculated within Area A, so X remains offered;
        # Area choices are calculated within Activity Y, so B remains offered.
        self.assertEqual(counts["activity-x"], 1)
        self.assertEqual(counts["activity-y"], 1)
        self.assertEqual(counts["area-a"], 1)
        self.assertEqual(counts["area-b"], 1)

    def test_contextual_ontology_prunes_empty_branches_but_keeps_populated_ancestors(self):
        service = TraceService(SimpleNamespace(cwd=self.cwd))
        entries = [self.entry("mse_populated", [("d1", "area-a"), ("d1", "activity-x")])]

        ontology = service.contextual_ontology(entries)

        area_root = ontology["area"][0]
        self.assertEqual(area_root["id"], "area-root")
        self.assertEqual(area_root["count"], 0)
        self.assertEqual(area_root["total"], 1)
        self.assertEqual([node["id"] for node in area_root["children"]], ["area-parent"])
        self.assertEqual(area_root["children"][0]["children"][0]["id"], "area-a")
        self.assertEqual([node["id"] for node in ontology["activity"]], ["activity-root"])
        self.assertEqual([node["id"] for node in ontology["activity"][0]["children"]], ["activity-x"])

    def test_contextual_ontology_keeps_known_axes_when_every_branch_is_empty(self):
        service = TraceService(SimpleNamespace(cwd=self.cwd))

        ontology = service.contextual_ontology([self.entry("mse_unattributed", [])])

        # An empty contextual response is still loaded data, not an absent
        # response: the client distinguishes this from the full corpus tree.
        self.assertEqual(ontology, {"area": [], "activity": []})


if __name__ == "__main__":
    unittest.main()
