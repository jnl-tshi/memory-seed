import assert from "node:assert/strict";
import { test } from "node:test";

import {
  CHAIN_KIND_GROUPS,
  LIFECYCLE_CHAIN_KINDS,
  MIN_CHAIN_LENGTH,
  MIN_SPINE_CONCORDANCE,
  RELATED_CHAIN_KINDS,
  SPIRAL_INNER_RADIUS,
  SPIRAL_RADIUS_STEP,
  allSpiralAssignments,
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

// --- related as a second, lower-priority kind-group ------------------------
//
// A chain built entirely from `related` edges did not spiral (JNL, 2026-07-28).
// Merging `related` into the SAME connectivity graph as lifecycle edges was
// measured and rejected: on the live corpus it produced one ~500-node
// component that the degree caps correctly reject, because many nodes carry
// both kinds of edge to overlapping neighbours. Evaluated on its own, related
// looks nothing like that - these tests pin the two-group design that
// followed: independent connectivity per kind, tried in priority order,
// merged by `allSpiralAssignments`.

test("a related-only path is invisible to the DEFAULT (lifecycle) call", () => {
  const { nodes, edges } = chainFixture(9);
  const related = edges.map((e) => ({ ...e, type: "related" }));
  assert.deepEqual(spiralChains(nodes, related), []);
});

test("the same path qualifies when asked for the related kind explicitly", () => {
  const { nodes, edges } = chainFixture(9);
  const related = edges.map((e) => ({ ...e, type: "related" }));
  const chains = spiralChains(nodes, related, { kinds: RELATED_CHAIN_KINDS });
  assert.equal(chains.length, 1);
  assert.equal(chains[0].length, 9);
});

test("CHAIN_KIND_GROUPS tries lifecycle before related", () => {
  assert.equal(CHAIN_KIND_GROUPS[0], LIFECYCLE_CHAIN_KINDS);
  assert.equal(CHAIN_KIND_GROUPS[1], RELATED_CHAIN_KINDS);
});

test("allSpiralAssignments finds a related-only chain lifecycle never would", () => {
  const { nodes, edges } = chainFixture(9);
  const related = edges.map((e) => ({ ...e, type: "related" }));
  const seats = allSpiralAssignments(nodes, related);
  assert.equal(seats.size, 9);
  assert.equal(seats.get("n0")?.radius, SPIRAL_INNER_RADIUS);
});

test("a lifecycle chain takes priority: overlapping nodes keep their lifecycle seat", () => {
  // n0..n8 form a qualifying LIFECYCLE chain. A `related` edge also joins n8 to
  // an otherwise separate 8-node related path - if related won the overlap,
  // n8 would be reseated into the related chain's geometry instead.
  const life = chainFixture(9, "n");
  const rel = chainFixture(8, "r");
  const bridge = { source: "n8", target: "r0", type: "related" };
  const relatedEdges = rel.edges.map((e) => ({ ...e, type: "related" }));
  const seats = allSpiralAssignments([...life.nodes, ...rel.nodes], [...life.edges, ...relatedEdges, bridge]);

  const n8 = seats.get("n8");
  assert.equal(n8?.chain, "n0", "n8 keeps its LIFECYCLE chain, not the related one");
  assert.equal(n8?.spur, false);
});

test("a related chain still forms around the nodes lifecycle did not claim", () => {
  // Same fixture as above: r0..r7 have no lifecycle edges of their own, so once
  // n8 is excluded (claimed by the lifecycle group) they must still connect to
  // each other directly and qualify as their own related chain.
  const life = chainFixture(9, "n");
  const rel = chainFixture(8, "r");
  const bridge = { source: "n8", target: "r0", type: "related" };
  const relatedEdges = rel.edges.map((e) => ({ ...e, type: "related" }));
  const seats = allSpiralAssignments([...life.nodes, ...rel.nodes], [...life.edges, ...relatedEdges, bridge]);

  const relatedChains = new Set(rel.nodes.map((n) => seats.get(n.id)?.chain).filter(Boolean));
  assert.equal(relatedChains.size, 1, "r0..r7 form exactly one chain among themselves");
  assert.equal([...relatedChains][0], "r0");
  for (const n of rel.nodes) assert.notEqual(seats.get(n.id)?.chain, "n0");
});

test("removing a claimed cut-node can split a related chain in two, and each half is judged on its own", () => {
  // r0..r3 - CLAIMED - r4..r7, where CLAIMED is a lifecycle-chain member that
  // also happens to sit on the related path. Once it is excluded, the related
  // graph splits into two 4-node halves - each below MIN_CHAIN_LENGTH, so
  // neither should qualify on its own.
  const life = chainFixture(9, "n");
  const before = ["r0", "r1", "r2", "r3"].map((id, i) => node(id, `2026-06-${10 + i}T09:00`));
  const after = ["r4", "r5", "r6", "r7"].map((id, i) => node(id, `2026-06-${14 + i}T09:00`));
  const relatedPath = [
    edge("r0", "r1", "related"),
    edge("r1", "r2", "related"),
    edge("r2", "r3", "related"),
    edge("r3", "n8", "related"), // n8 is the cut-node: claimed by the lifecycle chain
    edge("n8", "r4", "related"),
    edge("r4", "r5", "related"),
    edge("r5", "r6", "related"),
    edge("r6", "r7", "related"),
  ];
  const seats = allSpiralAssignments([...life.nodes, ...before, ...after], [...life.edges, ...relatedPath]);

  assert.equal(seats.get("n8")?.chain, "n0", "the cut-node keeps its lifecycle seat");
  for (const id of ["r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7"]) {
    assert.equal(seats.has(id), false, `${id} is on a 4-node fragment, below the floor`);
  }
});

// --- The concordance gate ---------------------------------------------------
//
// Shape (size, degree) says a component is THREAD-LIKE. It says nothing about
// whether walking the thread walks through TIME - true for lifecycle edges by
// construction, but not for `related`, which records topical similarity with
// no temporal direction. Measured live on 2026-07-28: a chain that passed
// every degree check still only tracked chronology 76% of the time and its
// SIMULATED position was worse (53%) than that - a spiral that gets "the
// middle is older" wrong on a quarter of its members, which actively
// misleads rather than approximates. These tests pin the gate that catches it.

test("a chain whose topology zig-zags through time is excluded", () => {
  // A path a-b-c-...-h, degree- and size-qualifying, but dated so that walking
  // it does NOT walk through time: alternating early/late timestamps.
  const ids = ["a", "b", "c", "d", "e", "f", "g", "h"];
  const stamps = [
    "2026-06-10", "2026-06-01", "2026-06-11", "2026-06-02",
    "2026-06-12", "2026-06-03", "2026-06-13", "2026-06-04",
  ];
  const nodes = ids.map((id, i) => node(id, `${stamps[i]}T09:00`));
  const edges = ids.slice(1).map((id, i) => edge(ids[i], id, "related"));
  assert.deepEqual(spiralChains(nodes, edges, { kinds: RELATED_CHAIN_KINDS, minLength: 8 }), []);
});

test("the same shape, dated monotonically, is NOT excluded", () => {
  // Confirms the gate is about ORDER, not about being `related` per se - an
  // identical topology that does track time still qualifies.
  const { nodes, edges } = chainFixture(8);
  const related = edges.map((e) => ({ ...e, type: "related" }));
  const chains = spiralChains(nodes, related, { kinds: RELATED_CHAIN_KINDS, minLength: 8 });
  assert.equal(chains.length, 1);
});

test("a lower minConcordance readmits the zig-zag chain", () => {
  // The threshold is a real option, not a hardcoded cliff - a caller (the
  // settings UI, or a future experiment) can move it.
  const ids = ["a", "b", "c", "d", "e", "f", "g", "h"];
  const stamps = [
    "2026-06-10", "2026-06-01", "2026-06-11", "2026-06-02",
    "2026-06-12", "2026-06-03", "2026-06-13", "2026-06-04",
  ];
  const nodes = ids.map((id, i) => node(id, `${stamps[i]}T09:00`));
  const edges = ids.slice(1).map((id, i) => edge(ids[i], id, "related"));
  const excluded = spiralChains(nodes, edges, { kinds: RELATED_CHAIN_KINDS, minLength: 8 });
  const readmitted = spiralChains(nodes, edges, { kinds: RELATED_CHAIN_KINDS, minLength: 8, minConcordance: 0 });
  assert.deepEqual(excluded, []);
  assert.equal(readmitted.length, 1);
});

test("the default MIN_SPINE_CONCORDANCE sits between the measured pass and fail cases", () => {
  // 0.76 failed live, 0.95/1.00 passed. The default must separate them with
  // real margin on both sides, not sit on a razor's edge next to one case.
  assert.ok(MIN_SPINE_CONCORDANCE > 0.76, "must exclude the measured failing chain");
  assert.ok(MIN_SPINE_CONCORDANCE < 0.95, "must not exclude the measured passing chains");
});

test("lifecycle chains are unaffected by the gate at the default threshold", () => {
  // Lifecycle edges are authored older->newer, so topology IS chronology; the
  // gate should never bind on the default (lifecycle) kind-group in practice.
  const { nodes, edges } = chainFixture(9);
  assert.equal(spiralChains(nodes, edges).length, 1);
});
