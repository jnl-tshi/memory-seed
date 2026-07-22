import assert from "node:assert/strict";
import { test } from "node:test";

import {
  connectedIds,
  haloPositions,
  initialPositions,
  layoutIterations,
  nodeSetSignature,
  seedPositions,
  type Point,
} from "./graphLayout.ts";
import type { RendererGraphNode } from "./api.ts";

function node(id: string): RendererGraphNode {
  return {
    id,
    label: id,
    community: { id: "c1", label: "c1", fingerprint: "f" },
    connectivity: 1,
    importance_score: 0,
    node_type: "entry",
    authority_class: "authored",
    provenance_class: "authored_memory",
    provider: null,
    revision: null,
    stale: false,
    temporal: { precision: "minute", source: "authored", value: "2026-06-01T09:00:00" },
    source: { chunk_id: id, entry_id: id, agent: "claude", topics: [] },
  } as unknown as RendererGraphNode;
}

const nodes = (n: number) => Array.from({ length: n }, (_, i) => node(`n${i}`));

test("an exact node-set match restores every settled position", () => {
  // The regression: this is the case that SKIPS the simulation, so if the
  // settled positions are not applied the nodes are stranded on the raw
  // seeding circle - which past ~100 nodes lands them outside the viewport
  // and leaves only edge chords crossing an empty canvas.
  const set = nodes(200);
  const settledPositions = new Map<string, Point>(set.map((item, i) => [item.id, { x: i * 3, y: i * 7 }]));
  const { positions, settled, warmSeeded } = seedPositions(set, [], settledPositions, nodeSetSignature(set));
  assert.equal(settled, true, "identical node set must be recognised as settled");
  assert.equal(warmSeeded, true);
  for (const [id, expected] of settledPositions) {
    assert.deepEqual(positions.get(id), expected, `${id} must keep its settled position`);
  }
});

test("a grown node set keeps known positions and seeds newcomers beside their neighbours", () => {
  const previous = nodes(3);
  const grown = nodes(6);
  const settledPositions = new Map<string, Point>(previous.map((item, i) => [item.id, { x: 1000 + i, y: 2000 + i }]));
  // n3 attaches to n0; the rest arrive unattached.
  const edges = [{ source: "n3", target: "n0" }];
  const { positions, settled, warmSeeded } = seedPositions(grown, edges, settledPositions, nodeSetSignature(previous));
  assert.equal(settled, false, "a different node set still needs a layout");
  assert.equal(warmSeeded, true, "the overlap must be warm-seeded");
  for (const [id, expected] of settledPositions) assert.deepEqual(positions.get(id), expected);
  // The newcomer with a settled neighbour lands NEAR it, not out on the spiral.
  const anchored = positions.get("n3")!;
  assert.ok(
    Math.hypot(anchored.x - 1000, anchored.y - 2000) <= 80,
    `n3 should seed within jitter range of n0, got ${JSON.stringify(anchored)}`,
  );
  // An unattached newcomer keeps its spiral slot.
  assert.deepEqual(positions.get("n4"), initialPositions(grown).get("n4"));
});

test("with no cached positions every node starts on the deterministic spiral", () => {
  const set = nodes(8);
  const { positions, settled, warmSeeded } = seedPositions(set, [], new Map(), "");
  assert.equal(settled, false);
  assert.equal(warmSeeded, false);
  assert.deepEqual([...positions.entries()].sort(), [...initialPositions(set).entries()].sort());
  // Deterministic: same input, same output.
  assert.deepEqual([...initialPositions(set).entries()], [...initialPositions(set).entries()]);
});

test("the spiral grows with the square root, not linearly", () => {
  // The regression that made large graphs unfittable: a ring of radius
  // nodeCount*14 put 462 nodes ~6,500px out, past what the reduced iteration
  // budget could close and past what fit could reach.
  const radiusOf = (count: number) =>
    Math.max(...[...initialPositions(nodes(count)).values()].map((p) => Math.hypot(p.x, p.y)));
  assert.ok(radiusOf(462) < 1600, `462 nodes must seed compactly, got ${radiusOf(462)}`);
  // Quadrupling the node count should roughly double the radius.
  const ratio = radiusOf(400) / radiusOf(100);
  assert.ok(ratio > 1.6 && ratio < 2.4, `expected ~2x for 4x nodes, got ${ratio}`);
});

test("connectedIds finds every edge endpoint and nothing else", () => {
  const ids = connectedIds([{ source: "a", target: "b" }, { source: "b", target: "c" }]);
  assert.deepEqual([...ids].sort(), ["a", "b", "c"]);
  assert.equal(connectedIds([]).size, 0);
});

test("the halo places every isolate outside the connected core's BOX", () => {
  // Asserted against the rectangle, not a circular proxy. The first version of
  // this test checked distance against max(w,h)/2 and passed while the live
  // graph put 82 of 107 isolates inside the core: a ring at that radius clears
  // the box's edges but cuts straight through its corners.
  const bounds = { x1: -500, y1: -400, x2: 500, y2: 400 };
  const isolates = nodes(40);
  const halo = haloPositions(isolates, bounds);
  assert.equal(halo.size, 40, "every isolate must be placed");
  for (const [id, point] of halo) {
    const outside =
      point.x < bounds.x1 || point.x > bounds.x2 || point.y < bounds.y1 || point.y > bounds.y2;
    assert.ok(outside, `${id} at ${JSON.stringify(point)} must sit outside the core box`);
  }
  assert.deepEqual([...haloPositions(isolates, bounds).entries()], [...halo.entries()], "must be deterministic");
});

test("the halo clears a very oblong core at every angle", () => {
  // The corner case in the literal sense: a wide, flat core is where a circular
  // radius is most wrong.
  const bounds = { x1: -2000, y1: -100, x2: 2000, y2: 100 };
  for (const [id, point] of haloPositions(nodes(60), bounds)) {
    const outside =
      point.x < bounds.x1 || point.x > bounds.x2 || point.y < bounds.y1 || point.y > bounds.y2;
    assert.ok(outside, `${id} at ${JSON.stringify(point)} must clear an oblong core`);
  }
});

test("the halo spills onto further rings rather than crowding one", () => {
  const bounds = { x1: -100, y1: -100, x2: 100, y2: 100 };
  const halo = haloPositions(nodes(200), bounds);
  const radii = new Set([...halo.values()].map((p) => Math.round(Math.hypot(p.x, p.y) / 10)));
  assert.ok(radii.size > 1, "200 isolates cannot fit on a single ring at readable spacing");
});

test("an empty halo and a missing bounding box are both handled", () => {
  assert.equal(haloPositions([], { x1: 0, y1: 0, x2: 1, y2: 1 }).size, 0);
  assert.equal(haloPositions(nodes(3), null).size, 3, "no connected core still places isolates");
});

test("layout iterations stay full at default size and scale down past it", () => {
  assert.equal(layoutIterations(60, false), 900);
  assert.equal(layoutIterations(150, false), 900);
  assert.ok(layoutIterations(500, false) < 900);
  assert.ok(layoutIterations(1000, false) < layoutIterations(500, false));
  assert.ok(layoutIterations(500, true) < layoutIterations(500, false), "warm-seeded sets need less work");
  assert.ok(layoutIterations(5000, true) >= 80, "never drops to zero work");
});
