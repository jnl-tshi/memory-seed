import assert from "node:assert/strict";
import { test } from "node:test";

import { overviewCounts, overviewExhausted } from "./graphOverview.ts";

test("no graph yet is not exhausted", () => {
  assert.equal(overviewExhausted(null, null, 60), false);
});

test("first fetch under the limit on both axes is exhausted", () => {
  assert.equal(overviewExhausted({ nodes: 40, edges: 38 }, null, 60), true);
});

test("first fetch that filled the limit is not exhausted", () => {
  assert.equal(overviewExhausted({ nodes: 60, edges: 60 }, null, 60), false);
});

test("saturated nodes with a still-truncated edge list keeps paging", () => {
  // The measured regression: at limit=600 this corpus returns 555 nodes (the
  // node count has saturated) but a full 600 edges, and 70 more entries still
  // render at higher limits. Judging on nodes alone retired "Show more" here.
  assert.equal(overviewExhausted({ nodes: 555, edges: 600 }, { nodes: 540, edges: 540 }, 600), false);
});

test("a bigger ask that returned nothing new on either axis is exhausted", () => {
  // Terminates against the server's hard 1000 cap, where raising the limit
  // returns the identical payload forever.
  assert.equal(overviewExhausted({ nodes: 555, edges: 1000 }, { nodes: 555, edges: 1000 }, 1060), true);
});

test("growth on the edge axis alone still counts as growth", () => {
  assert.equal(overviewExhausted({ nodes: 555, edges: 800 }, { nodes: 555, edges: 660 }, 800), false);
});

test("growth on the node axis alone still counts as growth", () => {
  assert.equal(overviewExhausted({ nodes: 555, edges: 660 }, { nodes: 540, edges: 660 }, 660), false);
});

test("counts read straight off a graph payload", () => {
  assert.deepEqual(overviewCounts({ nodes: [1, 2, 3], edges: [1] }), { nodes: 3, edges: 1 });
});
