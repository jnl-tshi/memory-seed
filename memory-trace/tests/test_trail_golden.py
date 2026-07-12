import json
import unittest
from pathlib import Path

GOLDEN = Path(__file__).parent / "fixtures" / "trail-golden-48.json"


class TrailGoldenFixtureTests(unittest.TestCase):
    """Phase 0 golden fixture: the vanilla Trail's lane/edge model, captured
    from the live app over the deterministic 48-entry synthetic corpus.

    This is the parity target for the React Trail (roadmap Phase 4): a
    re-implementation must reproduce laneOf/spans/linkRows/items for the same
    corpus. Regenerate after any trailModel change with the browserless
    harness (requires node; deterministic - two runs are byte-identical):

        PYTHONPATH=".;memory-trace" python memory-trace/tests/fixtures/regen_trail_golden.py

    It evaluates the real app.js in a node vm and calls the same
    window.memoryTraceDebug.trailModel hook the original browser capture
    procedure (docs/4_Reference/memory-trace-phase0-baseline.md) used.

    The assertions below check internal consistency, so a hand-edited or
    corrupted fixture fails loudly even without a browser.
    """

    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_shape_and_counts(self):
        golden = self.golden
        self.assertEqual(golden["node_count"], 48)
        self.assertEqual(golden["total"], 48)
        node_items = [item for item in golden["items"] if item["kind"] == "node"]
        self.assertEqual(len(node_items), 48)
        day_items = [item for item in golden["items"] if item["kind"] == "day"]
        self.assertEqual(len(day_items), len(golden["items"]) - 48)
        self.assertGreaterEqual(golden["laneCount"], 3)

    def test_main_owns_lane_zero_exclusively(self):
        lane_of = self.golden["laneOf"]
        self.assertEqual(lane_of["main"], 0)
        others = {branch: lane for branch, lane in lane_of.items() if branch != "main"}
        self.assertTrue(all(lane != 0 for lane in others.values()),
                        f"trunk column shared by a feature branch: {others}")

    def test_lane_occupancy_intervals_never_overlap(self):
        # Occupancy runs fork-to-merge (the same extension trailModel applies);
        # two branches on one lane may touch at a shared junction row
        # (daisy-chaining) but never overlap.
        golden = self.golden
        occupancy = {}
        for branch, span in golden["spans"].items():
            if branch == "main":
                occupancy[branch] = (span["first"], span["last"])
                continue
            link = golden["linkRows"].get(branch, {})
            first = span["first"] if link.get("mergeRow") is None else min(span["first"], link["mergeRow"])
            last = span["last"] if link.get("forkRow") is None else max(span["last"], link["forkRow"])
            occupancy[branch] = (first, last)
        by_lane: dict[int, list[tuple[int, int]]] = {}
        for branch, lane in golden["laneOf"].items():
            by_lane.setdefault(lane, []).append(occupancy[branch])
        for lane, intervals in by_lane.items():
            intervals.sort()
            for (a_first, a_last), (b_first, b_last) in zip(intervals, intervals[1:]):
                self.assertLessEqual(a_last, b_first,
                                     f"lane {lane}: intervals overlap beyond a shared junction")

    def test_items_are_newest_first(self):
        node_ids = [item["id"] for item in self.golden["items"] if item["kind"] == "node"]
        self.assertEqual(node_ids, sorted(node_ids, reverse=True))

    def test_lifecycle_edges_are_forward_only_and_resolvable(self):
        known = {item["id"] for item in self.golden["items"] if item["kind"] == "node"}
        types = set()
        for edge in self.golden["lifecycle"]:
            types.add(edge["type"])
            self.assertIn(edge["source"], known)
            self.assertIn(edge["target"], known)
            # Synthetic ids are counter-ordered: newer entries reference older.
            self.assertGreater(edge["source"], edge["target"])
        self.assertEqual(types, {"related", "supersedes", "evolves"})


if __name__ == "__main__":
    unittest.main()
