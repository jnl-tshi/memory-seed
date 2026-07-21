import assert from "node:assert/strict";
import { test } from "node:test";

import { buildTrailModel, compareTrailNodes, inDecisionGroup, isDecisionRow, pastelOf } from "./trailModel.ts";
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
