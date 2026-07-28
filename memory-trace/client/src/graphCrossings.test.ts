import assert from "node:assert/strict";
import { test } from "node:test";

import { countCrossings, edgeCrossingForce, segmentsCross, type CrossPoint } from "./graphCrossings.ts";

// --- segmentsCross -----------------------------------------------------

test("an X shape crosses", () => {
  assert.equal(
    segmentsCross({ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }, { x: 10, y: 0 }),
    true,
  );
});

test("parallel segments do not cross", () => {
  assert.equal(
    segmentsCross({ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 0, y: 5 }, { x: 10, y: 5 }),
    false,
  );
});

test("segments that only meet at a shared endpoint do not cross", () => {
  assert.equal(
    segmentsCross({ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 10, y: 10 }, { x: 20, y: 0 }),
    false,
  );
});

test("segments whose boxes overlap but that never touch do not cross", () => {
  assert.equal(
    segmentsCross({ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 0, y: 5 }, { x: 5, y: 8 }),
    false,
  );
});

// --- countCrossings ------------------------------------------------------

const SQUARE = new Map<string, CrossPoint>([
  ["a", { x: 0, y: 0 }],
  ["b", { x: 10, y: 10 }],
  ["c", { x: 0, y: 10 }],
  ["d", { x: 10, y: 0 }],
]);

test("the two diagonals of a square cross once", () => {
  const edges = [{ source: "a", target: "b" }, { source: "c", target: "d" }];
  assert.equal(countCrossings(SQUARE, edges), 1);
});

test("the four sides of a square never cross", () => {
  const edges = [
    { source: "a", target: "c" },
    { source: "c", target: "b" },
    { source: "b", target: "d" },
    { source: "d", target: "a" },
  ];
  assert.equal(countCrossings(SQUARE, edges), 0);
});

test("two edges sharing a node are never counted, even if collinear", () => {
  const positions = new Map<string, CrossPoint>([
    ["a", { x: 0, y: 0 }],
    ["b", { x: 5, y: 5 }],
    ["c", { x: 10, y: 10 }],
  ]);
  assert.equal(countCrossings(positions, [{ source: "a", target: "b" }, { source: "b", target: "c" }]), 0);
});

// --- edgeCrossingForce -----------------------------------------------------

type Node = { id: string; x: number; y: number; vx?: number; vy?: number };

function crossingNodes(): Node[] {
  // A square's diagonals cross exactly at its centre, which gives both edges
  // the identical midpoint and no direction to push apart in — a genuine
  // degenerate case, but not the one worth testing. These four are crossing
  // but off-centre, so the two midpoints differ.
  return [
    { id: "a", x: 0, y: 0 },
    { id: "b", x: 10, y: 10 },
    { id: "c", x: 1, y: 9 },
    { id: "d", x: 9, y: 0 },
  ];
}

test("a real crossing pushes both edges apart, in opposite directions", () => {
  const nodes = crossingNodes();
  const edges = [{ source: "a", target: "b" }, { source: "c", target: "d" }];
  const force = edgeCrossingForce(() => edges, () => 6);
  force.initialize(nodes);
  force(1);
  for (const node of nodes) assert.notEqual(node.vx, undefined, `${node.id} was not pushed`);
  const a = nodes.find((n) => n.id === "a")!;
  const c = nodes.find((n) => n.id === "c")!;
  // a and c belong to the two different edges, which the force pushes apart
  // along the same axis but in opposite senses — the dot product of their
  // velocity nudges is negative.
  const dot = (a.vx ?? 0) * (c.vx ?? 0) + (a.vy ?? 0) * (c.vy ?? 0);
  assert.ok(dot < 0, `expected opposing pushes, got a=(${a.vx},${a.vy}) c=(${c.vx},${c.vy})`);
});

test("zero strength is a no-op", () => {
  const nodes = crossingNodes();
  const edges = [{ source: "a", target: "b" }, { source: "c", target: "d" }];
  const force = edgeCrossingForce(() => edges, () => 0);
  force.initialize(nodes);
  force(1);
  for (const node of nodes) assert.equal(node.vx, undefined);
});

test("edges sharing an endpoint are never pushed, even head-on", () => {
  const nodes: Node[] = [
    { id: "a", x: 0, y: 0 },
    { id: "b", x: 10, y: 0 },
    { id: "c", x: 20, y: 0 },
  ];
  const edges = [{ source: "a", target: "b" }, { source: "b", target: "c" }];
  const force = edgeCrossingForce(() => edges, () => 6);
  force.initialize(nodes);
  force(1);
  for (const node of nodes) assert.equal(node.vx, undefined);
});

test("non-crossing edges far apart are left alone", () => {
  const nodes: Node[] = [
    { id: "a", x: 0, y: 0 },
    { id: "b", x: 10, y: 0 },
    { id: "c", x: 1000, y: 1000 },
    { id: "d", x: 1010, y: 1000 },
  ];
  const edges = [{ source: "a", target: "b" }, { source: "c", target: "d" }];
  const force = edgeCrossingForce(() => edges, () => 6);
  force.initialize(nodes);
  force(1);
  for (const node of nodes) assert.equal(node.vx, undefined);
});

test("a maxChecks of zero finds nothing, rather than throwing", () => {
  const nodes = crossingNodes();
  const edges = [{ source: "a", target: "b" }, { source: "c", target: "d" }];
  const force = edgeCrossingForce(() => edges, () => 6, { maxChecks: 0 });
  force.initialize(nodes);
  assert.doesNotThrow(() => force(1));
  for (const node of nodes) assert.equal(node.vx, undefined);
});
