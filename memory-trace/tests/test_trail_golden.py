import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

GOLDEN = Path(__file__).parent / "fixtures" / "trail-golden-48.json"
APP_JS = Path(__file__).resolve().parents[1] / "memory_trace" / "static" / "app.js"


def _trail_model(graph: dict) -> dict:
    temp_dir = Path(tempfile.mkdtemp(prefix="trail-continuity-model-"))
    try:
        graph_path = temp_dir / "graph.json"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        script = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";

const [appPath, graphPath] = process.argv.slice(1);
const noop = () => {};
const stubElement = () => ({
  innerHTML: "",
  value: "",
  style: {},
  dataset: {},
  classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
  addEventListener: noop,
  removeEventListener: noop,
  querySelector: () => null,
  querySelectorAll: () => [],
  getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
  focus: noop,
  appendChild: noop,
  setAttribute: noop,
});
const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  document: {
    getElementById: stubElement,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: stubElement,
    addEventListener: noop,
    removeEventListener: noop,
    body: stubElement(),
    documentElement: stubElement(),
  },
  localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
  fetch: () => new Promise(noop),
  matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
  navigator: {},
  location: { search: "", hash: "" },
  history: { replaceState: noop, pushState: noop },
  requestAnimationFrame: (fn) => fn && undefined,
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(readFileSync(appPath, "utf-8"), sandbox, { filename: "app.js" });
const model = sandbox.window.memoryTraceDebug.trailModel(JSON.parse(readFileSync(graphPath, "utf-8")));
console.log(JSON.stringify({
  continuityLaneCount: model.continuityLaneCount,
  continuityChains: model.continuityChains,
  continuityEvents: model.continuityEvents,
}));
"""
        result = subprocess.run(
            ["node", "-e", script, str(APP_JS), str(graph_path)],
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(result.stdout)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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
        self.assertEqual(types, {"related", "replaces", "evolves"})

    def test_continuity_axis_groups_rename_chain_and_keeps_other_kinds_distinct(self):
        model = _trail_model(
            {
                "nodes": [
                    {
                        "id": "mse_4",
                        "chunk_id": "mse_4",
                        "entry_id": "mse_4",
                        "title": "2026-06-04 09:00 - Remove command",
                        "date": "2026-06-04",
                        "datetime": "2026-06-04T09:00:00",
                        "branch": "main",
                        "continuity": [{"kind": "removal", "from": "memory-seed lense command", "to": None}],
                    },
                    {
                        "id": "mse_3",
                        "chunk_id": "mse_3",
                        "entry_id": "mse_3",
                        "title": "2026-06-03 09:00 - Migrate runtime",
                        "date": "2026-06-03",
                        "datetime": "2026-06-03T09:00:00",
                        "branch": "main",
                        "continuity": [{"kind": "migration", "from": ".AGENTS/", "to": ".memory-seed/"}],
                    },
                    {
                        "id": "mse_2",
                        "chunk_id": "mse_2",
                        "entry_id": "mse_2",
                        "title": "2026-06-02 09:00 - Rename product",
                        "date": "2026-06-02",
                        "datetime": "2026-06-02T09:00:00",
                        "branch": "main",
                        "continuity": [{"kind": "rename", "from": "Memory Lense", "to": "Memory Trace"}],
                    },
                    {
                        "id": "mse_1",
                        "chunk_id": "mse_1",
                        "entry_id": "mse_1",
                        "title": "2026-06-01 09:00 - First rename",
                        "date": "2026-06-01",
                        "datetime": "2026-06-01T09:00:00",
                        "branch": "main",
                        "continuity": [{"kind": "rename", "from": "Explorer", "to": "Memory Lense"}],
                    },
                ],
                "edges": [],
                "merges": [],
                "branches": {},
            }
        )
        self.assertEqual(len(model["continuityEvents"]), 4)
        self.assertEqual({event["kind"] for event in model["continuityEvents"]}, {"rename", "migration", "removal"})
        rename_chains = [chain for chain in model["continuityChains"] if chain["kinds"] == ["rename"]]
        self.assertEqual(len(rename_chains), 1)
        self.assertEqual(
            [(event["from"], event["to"]) for event in rename_chains[0]["events"]],
            [("Memory Lense", "Memory Trace"), ("Explorer", "Memory Lense")],
        )
        singleton_kinds = sorted(
            chain["kinds"][0] for chain in model["continuityChains"] if len(chain["events"]) == 1
        )
        self.assertEqual(singleton_kinds, ["migration", "removal"])

    def test_continuity_axis_is_absent_when_nodes_have_no_continuity(self):
        model = _trail_model(
            {
                "nodes": [
                    {
                        "id": "mse_2",
                        "chunk_id": "mse_2",
                        "entry_id": "mse_2",
                        "title": "2026-06-02 09:00 - Newer",
                        "date": "2026-06-02",
                        "datetime": "2026-06-02T09:00:00",
                        "branch": "main",
                        "continuity": [],
                    },
                    {
                        "id": "mse_1",
                        "chunk_id": "mse_1",
                        "entry_id": "mse_1",
                        "title": "2026-06-01 09:00 - Older",
                        "date": "2026-06-01",
                        "datetime": "2026-06-01T09:00:00",
                        "branch": "main",
                        "continuity": [],
                    },
                ],
                "edges": [],
                "merges": [],
                "branches": {},
            }
        )
        self.assertEqual(model["continuityLaneCount"], 0)
        self.assertEqual(model["continuityChains"], [])
        self.assertEqual(model["continuityEvents"], [])


if __name__ == "__main__":
    unittest.main()
