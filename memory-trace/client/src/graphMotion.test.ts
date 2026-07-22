import assert from "node:assert/strict";
import test from "node:test";

import { buildAdjacency, LIVE_MOTION_MAX, reheatNeighbourhood } from "./graphMotion.ts";

const edge = (source: string, target: string) => ({ source, target });

test("adjacency is undirected", () => {
  const adjacency = buildAdjacency([edge("a", "b")]);
  assert.deepEqual(adjacency.get("a"), ["b"]);
  assert.deepEqual(adjacency.get("b"), ["a"]);
});

test("a drag disturbs two hops", () => {
  // a - b - c - d: dragging a should reach c and stop.
  const adjacency = buildAdjacency([edge("a", "b"), edge("b", "c"), edge("c", "d")]);
  const { simIds, pinnedIds } = reheatNeighbourhood("a", adjacency);
  assert.deepEqual(simIds.sort(), ["a", "b", "c"]);
  // d borders the sim set, so it is held fixed rather than left to drift.
  assert.deepEqual(pinnedIds, ["d"]);
});

test("the pinned ring is what stops forces travelling further", () => {
  const adjacency = buildAdjacency([edge("a", "b"), edge("b", "c"), edge("c", "d"), edge("d", "e")]);
  const { simIds, pinnedIds } = reheatNeighbourhood("a", adjacency);
  assert.ok(!simIds.includes("d"), "d is outside the two-hop region");
  assert.ok(pinnedIds.includes("d"), "d must be pinned, not ignored");
  assert.ok(!pinnedIds.includes("e"), "the ring is one node deep");
});

test("a hub falls back to one hop rather than dragging the component", () => {
  // A star of 200 leaves around `hub`, each leaf carrying its own leaf: two
  // hops would be 400+ nodes, far past the live budget.
  const edges = [];
  for (let i = 0; i < 200; i += 1) {
    edges.push(edge("hub", `leaf${i}`));
    edges.push(edge(`leaf${i}`, `twig${i}`));
  }
  const { simIds } = reheatNeighbourhood("hub", buildAdjacency(edges), 150);
  assert.ok(simIds.length <= 150, `must respect the cap, got ${simIds.length}`);
  assert.ok(simIds.includes("hub"));
  // Fell back to one hop then truncated: no twig (two hops away) survives.
  assert.ok(!simIds.some((id) => id.startsWith("twig")), "two-hop nodes must be dropped wholesale");
});

test("truncation still happens when even one hop is too wide", () => {
  const edges = Array.from({ length: 400 }, (_, i) => edge("hub", `leaf${i}`));
  const { simIds } = reheatNeighbourhood("hub", buildAdjacency(edges), 150);
  assert.equal(simIds.length, 150);
  assert.equal(simIds[0], "hub", "the dragged node always survives truncation");
});

test("the same drag disturbs the same nodes every time", () => {
  const edges = [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("c", "d"), edge("d", "e")];
  const adjacency = buildAdjacency(edges);
  const first = reheatNeighbourhood("a", adjacency);
  const second = reheatNeighbourhood("a", adjacency);
  assert.deepEqual(first, second);
});

test("an isolate drags alone", () => {
  // No edges: nothing to transfer force to, and nothing to pin.
  const { simIds, pinnedIds } = reheatNeighbourhood("lonely", buildAdjacency([]));
  assert.deepEqual(simIds, ["lonely"]);
  assert.deepEqual(pinnedIds, []);
});

test("the live-motion cap matches the measured layout budget", () => {
  // Tied to the e2e-scale measurement (1177ms warm at 467 nodes); raising it
  // without re-measuring is what this pin is here to prevent.
  assert.equal(LIVE_MOTION_MAX, 150);
});
