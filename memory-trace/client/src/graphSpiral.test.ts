import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MIN_CHAIN_LENGTH,
  SPIRAL_INNER_RADIUS,
  SPIRAL_RADIUS_STEP,
  chainSpine,
  spiralAssignments,
  spiralChains,
} from "./graphSpiral.ts";

const node = (id: string, datetime: string) => ({ id, datetime });
const edge = (source: string, target: string, type = "evolves") => ({ source, target, type });

/** A path a-b-c-... with ascending timestamps. */
function chainFixture(length: number, prefix = "n") {
  const nodes = Array.from({ length }, (_, i) =>
    node(`${prefix}${i}`, `2026-06-${String(i + 1).padStart(2, "0")}T09:00`),
  );
  const edges = Array.from({ length: length - 1 }, (_, i) => edge(`${prefix}${i}`, `${prefix}${i + 1}`));
  return { nodes, edges };
}

test("a long path qualifies and comes back oldest first", () => {
  const { nodes, edges } = chainFixture(9);
  const chains = spiralChains(nodes, edges);
  assert.equal(chains.length, 1);
  assert.deepEqual(chains[0], ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"]);
});

test("a chain shorter than the floor is left alone", () => {
  const { nodes, edges } = chainFixture(MIN_CHAIN_LENGTH - 1);
  assert.deepEqual(spiralChains(nodes, edges), []);
});

test("a HUB is rejected however large it is", () => {
  // The guarantee the dense sections rest on. A star of 30 nodes is bigger than
  // any chain here and must still get no spiral: winding a hub would pull its
  // spokes into a ring and destroy the structure the layout found.
  const nodes = [node("hub", "2026-06-01T09:00")];
  const edges = [];
  for (let i = 0; i < 30; i += 1) {
    nodes.push(node(`s${i}`, `2026-06-02T09:0${i % 10}`));
    edges.push(edge("hub", `s${i}`));
  }
  assert.deepEqual(spiralChains(nodes, edges), []);
});

test("`related` edges never make a chain", () => {
  // They are symmetric and dense - treating them as chain evidence sweeps most
  // of a corpus into one component that is not a story.
  const { nodes, edges } = chainFixture(10);
  const related = edges.map((e) => ({ ...e, type: "related" }));
  assert.deepEqual(spiralChains(nodes, related), []);
});

test("two separate chains stay separate", () => {
  const a = chainFixture(8, "a");
  const b = chainFixture(9, "b");
  const chains = spiralChains([...a.nodes, ...b.nodes], [...a.edges, ...b.edges]);
  assert.equal(chains.length, 2);
  assert.deepEqual(chains.map((c) => c.length).sort(), [8, 9]);
});

test("an edge naming an absent node is ignored rather than inventing one", () => {
  const { nodes, edges } = chainFixture(9);
  const chains = spiralChains(nodes, [...edges, edge("n8", "ghost")]);
  assert.deepEqual(chains[0], ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"]);
});

test("radius grows with age, so the oldest sits innermost", () => {
  const { nodes, edges } = chainFixture(9);
  const seats = spiralAssignments(spiralChains(nodes, edges), edges);
  assert.equal(seats.get("n0")?.radius, SPIRAL_INNER_RADIUS);
  assert.equal(seats.get("n8")?.radius, SPIRAL_INNER_RADIUS + 8 * SPIRAL_RADIUS_STEP);
  assert.ok((seats.get("n0")?.radius ?? 0) < (seats.get("n8")?.radius ?? 0));
});

test("radius follows age ORDER, not elapsed time", () => {
  // A six-month gap mid-chain must not leave a visible void: that would read as
  // a missing node rather than as elapsed time.
  const ids = ["a", "b", "c", "d", "e", "f", "g", "h"];
  // A six-month hole between c and d.
  const stamps = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05"];
  const nodes = ids.map((id, i) => node(id, `${stamps[i]}T09:00`));
  const edges = ids.slice(1).map((id, i) => edge(ids[i], id));
  const seats = spiralAssignments(spiralChains(nodes, edges), edges);
  const radii = ids.map((id) => seats.get(id)!.radius);
  const gaps = radii.slice(1).map((r, i) => r - radii[i]);
  assert.deepEqual(new Set(gaps), new Set([SPIRAL_RADIUS_STEP]));
});

test("every member of one chain shares a centre", () => {
  const { nodes, edges } = chainFixture(9);
  const seats = spiralAssignments(spiralChains(nodes, edges), edges);
  const chains = new Set([...seats.values()].map((s) => s.chain));
  assert.equal(chains.size, 1);
});

test("nodes outside a chain get no seat at all", () => {
  // Not a weak pull - none. This is what leaves the dense middle governed by
  // exactly the forces it had before.
  const { nodes, edges } = chainFixture(9);
  const loose = [...nodes, node("loose", "2026-06-20T09:00")];
  const seats = spiralAssignments(spiralChains(loose, edges), edges);
  assert.equal(seats.has("loose"), false);
  assert.equal(seats.size, 9);
});


// --- Spine and spurs -------------------------------------------------------

test("the spine is the longest path through the component", () => {
  // A 9-node chain with a spur hanging off the middle. The spine must be the
  // nine, not a route that detours through the spur.
  const { nodes, edges } = chainFixture(9);
  const withSpur = [...nodes, node("spur", "2026-06-20T09:00")];
  const withEdge = [...edges, edge("n4", "spur")];
  const chains = spiralChains(withSpur, withEdge);
  const adjacency = new Map();
  for (const e of withEdge) {
    if (!adjacency.has(e.source)) adjacency.set(e.source, new Set());
    if (!adjacency.has(e.target)) adjacency.set(e.target, new Set());
    adjacency.get(e.source).add(e.target);
    adjacency.get(e.target).add(e.source);
  }
  const spine = chainSpine(chains[0], adjacency);
  assert.equal(spine.length, 9);
  assert.equal(spine.includes("spur"), false);
});

test("a terminating spur is marked, and sits OUTSIDE its anchor", () => {
  // The whole point: it points away from the centre instead of landing inside
  // the coil where it reads as part of the sequence.
  const { nodes, edges } = chainFixture(9);
  const withSpur = [...nodes, node("spur", "2026-06-20T09:00")];
  const withEdge = [...edges, edge("n4", "spur")];
  const seats = spiralAssignments(spiralChains(withSpur, withEdge), withEdge);
  const spur = seats.get("spur");
  const anchor = seats.get("n4");
  assert.equal(spur?.spur, true);
  assert.equal(anchor?.spur, false);
  assert.ok((spur?.radius ?? 0) > (anchor?.radius ?? 0), "a spur sits further out than its anchor");
  assert.equal(spur?.index, anchor?.index, "and shares its anchor's angle, so it lies on the same ray");
});

test("every spine member is marked as spine", () => {
  const { nodes, edges } = chainFixture(9);
  const seats = spiralAssignments(spiralChains(nodes, edges), edges);
  assert.equal([...seats.values()].every((s) => !s.spur), true);
});

test("a spur does not shift the seats of the spine", () => {
  // A side-node used to join the centroid and bend the spiral; the radii the
  // spine holds must be identical whether or not it is there.
  const { nodes, edges } = chainFixture(9);
  const bare = spiralAssignments(spiralChains(nodes, edges), edges);
  const withSpur = [...nodes, node("spur", "2026-06-20T09:00")];
  const withEdge = [...edges, edge("n4", "spur")];
  const spurred = spiralAssignments(spiralChains(withSpur, withEdge), withEdge);
  for (const id of nodes.map((n) => n.id)) {
    assert.equal(spurred.get(id)?.radius, bare.get(id)?.radius, `${id} moved`);
  }
});

test("the spine runs oldest to newest", () => {
  const { nodes, edges } = chainFixture(9);
  const seats = spiralAssignments(spiralChains(nodes, edges), edges);
  assert.equal(seats.get("n0")?.index, 0);
  assert.equal(seats.get("n8")?.index, 8);
});
