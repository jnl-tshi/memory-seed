import assert from "node:assert/strict";
import { test } from "node:test";

import { connectedIds, initialPositions, nodeSetSignature, seedPositions, type Point } from "./graphLayout.ts";
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
