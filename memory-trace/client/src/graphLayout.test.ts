import assert from "node:assert/strict";
import { test } from "node:test";

import { initialPositions, layoutIterations, nodeSetSignature, seedPositions, type Point } from "./graphLayout.ts";
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
  const { positions, settled, warmSeeded } = seedPositions(set, settledPositions, nodeSetSignature(set));
  assert.equal(settled, true, "identical node set must be recognised as settled");
  assert.equal(warmSeeded, true);
  for (const [id, expected] of settledPositions) {
    assert.deepEqual(positions.get(id), expected, `${id} must keep its settled position`);
  }
  // Not the deterministic circle: every point on that ring is equidistant.
  const radii = [...positions.values()].map((p) => Math.hypot(p.x, p.y));
  assert.ok(Math.max(...radii) - Math.min(...radii) > 1, "positions must not collapse onto the seeding circle");
});

test("a grown node set keeps known positions and places only the new nodes on the circle", () => {
  const previous = nodes(3);
  const grown = nodes(6);
  const settledPositions = new Map<string, Point>(previous.map((item, i) => [item.id, { x: 1000 + i, y: 2000 + i }]));
  const { positions, settled, warmSeeded } = seedPositions(grown, settledPositions, nodeSetSignature(previous));
  assert.equal(settled, false, "a different node set still needs a layout");
  assert.equal(warmSeeded, true, "the overlap must be warm-seeded");
  for (const [id, expected] of settledPositions) assert.deepEqual(positions.get(id), expected);
  const circle = initialPositions(grown);
  for (const item of grown.slice(3)) assert.deepEqual(positions.get(item.id), circle.get(item.id));
});

test("with no cached positions every node starts on the deterministic circle", () => {
  const set = nodes(8);
  const { positions, settled, warmSeeded } = seedPositions(set, new Map(), "");
  assert.equal(settled, false);
  assert.equal(warmSeeded, false);
  assert.deepEqual([...positions.entries()].sort(), [...initialPositions(set).entries()].sort());
  // Deterministic: same input, same output.
  assert.deepEqual([...initialPositions(set).entries()], [...initialPositions(set).entries()]);
});

test("layout iterations stay full at default size and scale down past it", () => {
  assert.equal(layoutIterations(60, false), 900);
  assert.equal(layoutIterations(150, false), 900);
  assert.ok(layoutIterations(500, false) < 900);
  assert.ok(layoutIterations(1000, false) < layoutIterations(500, false));
  assert.ok(layoutIterations(500, true) < layoutIterations(500, false), "warm-seeded sets need less work");
  assert.ok(layoutIterations(5000, true) >= 80, "never drops to zero work");
});
