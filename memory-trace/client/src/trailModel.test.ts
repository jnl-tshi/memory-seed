import assert from "node:assert/strict";
import { test } from "node:test";

import { buildTrailModel, compareTrailNodes, decisionEndpointLabel, entryIdOfRowId, inDecisionGroup, isDecisionEdge, isDecisionRow, lifecycleEdgeClass, pastelOf, trailWindowEntryIds, trunkRowRange } from "./trailModel.ts";
import type { TrailEvent, TrailResponse } from "./api.ts";

const PALETTE = [
  "#6f7cff", "#3fa66a", "#d9941a",
  "#d94b63", "#22b8cf", "#7cb342",
  "#8f63e8", "#e8590c", "#18a999",
  "#db2777", "#3b82f6", "#16a34a",
];

function node(overrides: Partial<TrailEvent>): TrailEvent {
  return {
    id: "mse_x",
    chunk_id: "mse_x",
    entry_id: "mse_x",
    title: "2026-06-01 09:00 - entry",
    date: "2026-06-01",
    datetime: "2026-06-01T09:00:00",
    branch: "main",
    branch_inferred: false,
    agent: "claude",
    topics: [],
    granularity: "entry",
    continuity: [],
    connectivity: 0,
    importance_score: 0,
    provenance_class: "authored_memory",
    has_diagram: false,
    decision_ordinal: null,
    decision_count: 0,
    ...overrides,
  } as TrailEvent;
}

test("pastelOf is deterministic, lighter, and keeps hues distinct", () => {
  const luminance = (hex: string) => {
    const value = hex.replace("#", "");
    return (
      parseInt(value.slice(0, 2), 16) * 0.2126 +
      parseInt(value.slice(2, 4), 16) * 0.7152 +
      parseInt(value.slice(4, 6), 16) * 0.0722
    );
  };
  const pastels = PALETTE.map((hex) => pastelOf(hex));
  pastels.forEach((pastel, index) => {
    assert.match(pastel, /^#[0-9a-f]{6}$/);
    assert.equal(pastel, pastelOf(PALETTE[index]), "same input must give same output");
    assert.ok(
      luminance(pastel) > luminance(PALETTE[index]),
      `${PALETTE[index]} -> ${pastel} must be lighter`,
    );
  });
  assert.equal(new Set(pastels).size, PALETTE.length, "distinct hues stay distinct");
});

test("trunkRowRange keeps the main spine visible between direct main work and a merged branch", () => {
  // Rows are newest-first. A direct main entry at row 2 followed by a merge at
  // row 7 must draw a spine through both; using row 2 as both bounds makes
  // main disappear except for its dot.
  assert.deepEqual(trunkRowRange([2], [7]), { first: 2, last: 7 });
  assert.deepEqual(trunkRowRange([2, 9], [7]), { first: 2, last: 9 });
  assert.equal(trunkRowRange([], []), null);
});

test("compareTrailNodes orders a group anchor < D1 < D2 < D10 at identical timestamps", () => {
  const anchor = node({ id: "mse_a", decision_count: 3 });
  const d1 = node({ id: "mse_a#decisions/d1-w", chunk_id: "mse_a#decisions/d1-w", decision_ordinal: "d1" });
  const d2 = node({ id: "mse_a#decisions/d2-x", chunk_id: "mse_a#decisions/d2-x", decision_ordinal: "d2" });
  const d10 = node({ id: "mse_a#decisions/d10-y", chunk_id: "mse_a#decisions/d10-y", decision_ordinal: "d10" });
  const shuffled = [d10, d1, anchor, d2].sort(compareTrailNodes);
  // The anchor has no ordinal, so it ranks 0 and heads its own group - the
  // entry title above its D1..DN subheadings.
  assert.deepEqual(shuffled.map((item) => item.decision_ordinal), [null, "d1", "d2", "d10"]);
  // Newest entries still lead regardless of ordinals.
  const newer = node({ id: "mse_b", entry_id: "mse_b", datetime: "2026-06-02T09:00:00" });
  assert.ok(compareTrailNodes(newer, anchor) < 0);
});

test("isDecisionRow and inDecisionGroup differ exactly on the group anchor", () => {
  const ordinary = node({ id: "mse_p" });
  const anchor = node({ id: "mse_a", decision_count: 3 });
  const d1 = node({ id: "mse_a#decisions/d1-w", decision_ordinal: "d1" });
  assert.deepEqual([ordinary, anchor, d1].map(isDecisionRow), [false, false, true]);
  assert.deepEqual([ordinary, anchor, d1].map(inDecisionGroup), [false, true, true]);
});

test("buildTrailModel keeps decision rows unique, grouped, and never bisected by the window", () => {
  const trail = {
    nodes: [
      node({ id: "mse_new", entry_id: "mse_new", chunk_id: "mse_new", datetime: "2026-06-03T09:00:00", date: "2026-06-03" }),
      node({ id: "mse_multi", entry_id: "mse_multi", chunk_id: "mse_multi", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_count: 3 }),
      node({ id: "mse_multi#decisions/d1-z", entry_id: "mse_multi", chunk_id: "mse_multi#decisions/d1-z", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_ordinal: "d1", title: "D1 - z" }),
      node({ id: "mse_multi#decisions/d2-a", entry_id: "mse_multi", chunk_id: "mse_multi#decisions/d2-a", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_ordinal: "d2", title: "D2 - a" }),
      node({ id: "mse_multi#decisions/d3-b", entry_id: "mse_multi", chunk_id: "mse_multi#decisions/d3-b", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_ordinal: "d3", title: "D3 - b" }),
      node({ id: "mse_old", entry_id: "mse_old", chunk_id: "mse_old", datetime: "2026-06-01T09:00:00", date: "2026-06-01" }),
    ],
    edges: [],
    branches: {},
    merges: [],
    edge_types: [],
    entry_id: null,
    granularity: "entry",
  } as unknown as TrailResponse;

  const model = buildTrailModel(trail, 10);
  const nodeItems = model.items.filter((item) => item.kind === "node");
  const ids = nodeItems.map((item) => (item.kind === "node" ? item.node.id : ""));
  assert.equal(new Set(ids).size, ids.length, "row ids must be unique");
  const multiRows = ids.filter((id) => id.startsWith("mse_multi"));
  assert.deepEqual(
    multiRows,
    ["mse_multi", "mse_multi#decisions/d1-z", "mse_multi#decisions/d2-a", "mse_multi#decisions/d3-b"],
    "anchor leads, then every decision, contiguous and ordered",
  );
  assert.equal(model.rowOf.size, nodeItems.length, "every row keyed once");
  // "N of M entries" counts entries, so the 4 rows of mse_multi count once.
  assert.equal(model.total, 3, "decision rows never inflate the entry count");

  // A window cut landing inside the group extends to the group's end: window
  // of 2 would slice after the anchor - the children must still be included.
  const clipped = buildTrailModel(trail, 2);
  const clippedIds = clipped.items.filter((item) => item.kind === "node").map((item) => (item.kind === "node" ? item.node.id : ""));
  assert.ok(clippedIds.includes("mse_multi#decisions/d3-b"), "window never bisects a decision group");
  assert.ok(!clippedIds.includes("mse_old"), "extension stops at the group end");
});

test("trailWindowEntryIds matches what the Trail renders, deduped to entries", () => {
  const trail = {
    nodes: [
      node({ id: "mse_new", entry_id: "mse_new", chunk_id: "mse_new", datetime: "2026-06-03T09:00:00", date: "2026-06-03" }),
      node({ id: "mse_multi", entry_id: "mse_multi", chunk_id: "mse_multi", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_count: 2 }),
      node({ id: "mse_multi#decisions/d1-z", entry_id: "mse_multi", chunk_id: "mse_multi#decisions/d1-z", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_ordinal: "d1", title: "D1 - z" }),
      node({ id: "mse_multi#decisions/d2-a", entry_id: "mse_multi", chunk_id: "mse_multi#decisions/d2-a", datetime: "2026-06-02T09:00:00", date: "2026-06-02", decision_ordinal: "d2", title: "D2 - a" }),
      node({ id: "mse_old", entry_id: "mse_old", chunk_id: "mse_old", datetime: "2026-06-01T09:00:00", date: "2026-06-01" }),
    ],
    edges: [], branches: {}, merges: [], edge_types: [], entry_id: null, granularity: "entry",
  } as unknown as TrailResponse;

  // The pin set is exactly the entries the Trail draws: four rows of two
  // entries collapse to two ids, and the unwindowed entry is absent.
  const clipped = trailWindowEntryIds(trail, 2);
  const rendered = new Set(
    buildTrailModel(trail, 2).items.flatMap((item) => (item.kind === "node" ? [item.node.entry_id] : [])),
  );
  assert.deepEqual([...clipped].sort(), [...rendered].sort());
  assert.deepEqual([...clipped].sort(), ["mse_multi", "mse_new"]);

  // Growing the window pins strictly more - "Load older" never drops a pin.
  const grown = trailWindowEntryIds(trail, 10);
  assert.deepEqual([...grown].sort(), ["mse_multi", "mse_new", "mse_old"]);
  assert.ok(clipped.every((id) => grown.includes(id)));

  assert.deepEqual(trailWindowEntryIds(null, 60), []);
});

test("isDecisionEdge reads granularity off the endpoint ids, either end", () => {
  // The row id IS the granularity: _decision_edges_for_rows terminates a
  // decision-level edge on a `#decisions/dN-` row and an entry-level one on
  // the bare id, so nothing can disagree with it.
  assert.equal(isDecisionEdge({ source: "mse_a", target: "mse_b" }), false);
  assert.equal(isDecisionEdge({ source: "mse_a#decisions/d2-x", target: "mse_b#decisions/d1-y" }), true);
  // Mixed granularity counts - "d3 of B evolves A" is precise on one end.
  assert.equal(isDecisionEdge({ source: "mse_a#decisions/d3-x", target: "mse_b" }), true);
  assert.equal(isDecisionEdge({ source: "mse_a", target: "mse_b#decisions/d1-y" }), true);
});

test("decisionEndpointLabel names the decision and the entry it belongs to", () => {
  const entry = node({ id: "mse_a", title: "Ship the parser" });
  const decision = node({
    id: "mse_a#decisions/d2-the-source-ordinal",
    entry_id: "mse_a",
    title: "D2 - The source ordinal rides on the item",
    decision_ordinal: "d2",
  });

  // An entry row is its own label.
  assert.equal(decisionEndpointLabel(entry), "Ship the parser");
  // With the anchor title, the reader learns WHICH session the decision is in -
  // the thing a raw "D2 - ..." heading cannot tell them.
  assert.equal(decisionEndpointLabel(decision, "Ship the parser"), "D2 of Ship the parser");
  // Anchor outside the window: fall back to the decision heading rather than
  // dropping the ordinal, which is the part that makes the edge precise.
  assert.equal(decisionEndpointLabel(decision), "D2 (D2 - The source ordinal rides on the item)");
});

test("entryIdOfRowId maps a decision row back to its entry", () => {
  // Selection is entry-scoped but a decision edge terminates on a ROW, so an
  // exact id comparison can never match one. That mismatch is what made
  // decision lineage unreachable in on-select mode and invisible when its own
  // entry was selected - both reported live on 2026-07-24.
  assert.equal(entryIdOfRowId("mse_a"), "mse_a");
  assert.equal(entryIdOfRowId("mse_a#decisions/d2-the-source-ordinal"), "mse_a");
  assert.equal(entryIdOfRowId("ms-f83a27d3#decisions/d1-rationale"), "ms-f83a27d3");
  // A legacy singular '#decision' anchor resolves the same way.
  assert.equal(entryIdOfRowId("mse_a#decision"), "mse_a");
});

test("lifecycleEdgeClass ranks edges 1/2/3 by how many ends name a decision", () => {
  // Ratified 2026-07-24: decision->decision is first class (most precise),
  // entry<->decision second, entry->entry third (history links, single-
  // decision entries). The Trail weights ink by this class.
  assert.equal(lifecycleEdgeClass({ source: "mse_a#decisions/d1-x", target: "mse_b#decisions/d2-y" }), 1);
  assert.equal(lifecycleEdgeClass({ source: "mse_a#decisions/d1-x", target: "mse_b" }), 2);
  assert.equal(lifecycleEdgeClass({ source: "mse_a", target: "mse_b#decisions/d2-y" }), 2);
  assert.equal(lifecycleEdgeClass({ source: "mse_a", target: "mse_b" }), 3);
  // isDecisionEdge stays the class<=2 predicate the styling short-hands.
  assert.equal(isDecisionEdge({ source: "mse_a", target: "mse_b" }), false);
  assert.equal(isDecisionEdge({ source: "mse_a#decisions/d1-x", target: "mse_b" }), true);
});
