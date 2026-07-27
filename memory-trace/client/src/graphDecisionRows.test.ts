import assert from "node:assert/strict";
import { test } from "node:test";

import {
  anchorEntryIdFor,
  connectedIdsWithDecisionAnchors,
  decisionGroupId,
  decisionGroups,
  haloDiameter,
  isDecisionRowId,
  parentIdsFor,
  ringPhase,
  satellitePositions,
  SATELLITE_RADIUS,
  simulationLinks,
  visibilityIdFor,
} from "./graphDecisionRows.ts";

const ROW_A1 = "mse_a#decisions/d1-first";
const ROW_A2 = "mse_a#decisions/d2-second";
const ROW_B3 = "mse_b#decisions/d3-third";

test("a decision-row id is recognised and resolves to its anchor entry", () => {
  assert.equal(isDecisionRowId(ROW_A1), true);
  assert.equal(isDecisionRowId("mse_a"), false);
  assert.equal(anchorEntryIdFor(ROW_A1), "mse_a");
  // An entry id passes through unchanged, so callers can map endpoints blind.
  assert.equal(anchorEntryIdFor("mse_a"), "mse_a");
});

test("rows group under their anchor, and a row whose anchor is absent is dropped", () => {
  const groups = decisionGroups([{ id: "mse_a" }, { id: ROW_A1 }, { id: ROW_A2 }, { id: ROW_B3 }]);
  assert.deepEqual([...groups.keys()], ["mse_a"]);
  assert.deepEqual(groups.get("mse_a")?.rowIds, [ROW_A1, ROW_A2]);
  assert.equal(groups.get("mse_a")?.groupId, decisionGroupId("mse_a"));
});

test("rows are ordered by ordinal NUMERICALLY, whatever order the payload listed", () => {
  // The ring reads as a clock face only if slot position means "place in the
  // entry". Numeric, not lexical: d10 sits after d9, not between d1 and d2 -
  // the same rule trailModel applies to Trail rows.
  const ROW_A10 = "mse_a#decisions/d10-tenth";
  const groups = decisionGroups([{ id: "mse_a" }, { id: ROW_A10 }, { id: ROW_A2 }, { id: ROW_A1 }]);
  assert.deepEqual(groups.get("mse_a")?.rowIds, [ROW_A1, ROW_A2, ROW_A10]);
});

test("the anchor is a CHILD of the container, never the container itself", () => {
  // The whole point of the synthetic group: a Cytoscape parent's position is
  // derived from its children, and this graph's simulation writes the anchor's
  // position on every tick. Filing the anchor as a sibling of its rows keeps it
  // positionable - and keeps its circle, its degree size and its topic fill.
  const parents = parentIdsFor(decisionGroups([{ id: "mse_a" }, { id: ROW_A1 }]));
  assert.equal(parents.get("mse_a"), decisionGroupId("mse_a"));
  assert.equal(parents.get(ROW_A1), decisionGroupId("mse_a"));
  assert.notEqual(parents.get(ROW_A1), "mse_a");
});

test("a decision-level edge credits its anchor entry as connected", () => {
  // The 2026-07-26 measurement this exists for: with rows on, ~11 anchors whose
  // ONLY relationships are decision-level would read as edgeless and be hidden
  // by the Orphans filter while their own rows stayed on screen.
  const connected = connectedIdsWithDecisionAnchors([{ source: ROW_A1, target: ROW_B3 }]);
  assert.equal(connected.has("mse_a"), true);
  assert.equal(connected.has("mse_b"), true);
  assert.equal(connected.has(ROW_A1), true);
  // And nothing else is invented: no third entry appears from a two-ended edge.
  assert.deepEqual([...connected].sort(), [ROW_A1, ROW_B3, "mse_a", "mse_b"].sort());
});

test("a row's visibility is decided by its anchor, so a group is never taken apart", () => {
  // Found live 2026-07-27, with Orphans off: once the server started expanding a
  // linked entry WHOLE, the rows carrying no edge failed the connectedness test
  // on their own degree and were dropped - so a 4-decision entry drew a ring of
  // one. A decision inside a shown entry is not an orphan; it is a decision.
  assert.equal(visibilityIdFor(ROW_A1), "mse_a");
  assert.equal(visibilityIdFor("mse_a"), "mse_a");
  const connected = connectedIdsWithDecisionAnchors([{ source: ROW_A1, target: ROW_B3 }]);
  // ROW_A2 has no edge of its own, but its anchor does - so it survives.
  assert.equal(connected.has(visibilityIdFor(ROW_A2)), true);
  assert.equal(connected.has(ROW_A2), false, "and it is NOT credited as an endpoint");
});

test("rows sit on their anchor's leash, so containment cannot drift", () => {
  const anchor = { x: 100, y: -40 };
  const positions = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  for (const rowId of [ROW_A1, ROW_A2]) {
    const point = positions.get(rowId)!;
    const distance = Math.sqrt((point.x - anchor.x) ** 2 + (point.y - anchor.y) ** 2);
    assert.ok(Math.abs(distance - SATELLITE_RADIUS) < 1e-9, `${rowId} is ${distance} from its anchor`);
  }
});

test("rows are spread EQUALLY by angle around the anchor", () => {
  // JNL, 2026-07-27. Equal spacing is the whole rule: no counterpart aiming, no
  // golden-angle fan, so the ring's shape depends on the entry alone and not on
  // what happens to be on screen beside it.
  const anchor = { x: 0, y: 0 };
  const rowIds = [ROW_A1, ROW_A2, "mse_a#decisions/d3-third", "mse_a#decisions/d4-fourth"];
  const positions = satellitePositions({ rowIds, anchor });
  const angles = rowIds.map((rowId) => {
    const point = positions.get(rowId)!;
    return Math.atan2(point.y - anchor.y, point.x - anchor.x);
  });
  const gaps = angles.slice(1).map((angle, index) => {
    let gap = angle - angles[index];
    while (gap <= 0) gap += Math.PI * 2;
    return gap;
  });
  for (const gap of gaps) {
    assert.ok(Math.abs(gap - (Math.PI * 2) / rowIds.length) < 1e-9, `uneven gap ${gap}`);
  }
});

test("with nothing to face, the ring rests straight up", () => {
  const positions = satellitePositions({ rowIds: [ROW_A1], anchor: { x: 0, y: 0 } });
  const point = positions.get(ROW_A1)!;
  assert.ok(Math.abs(point.x) < 1e-9, `expected x=0, got ${point.x}`);
  // Screen coordinates: negative y is up.
  assert.ok(Math.abs(point.y + SATELLITE_RADIUS) < 1e-9, `expected y=-${SATELLITE_RADIUS}, got ${point.y}`);
});

test("the ring ROTATES to face its relatives, and stays equally spaced doing it", () => {
  // JNL, 2026-07-27: rotational freedom around the entry, equal angles preserved.
  // The ring is rigid - one degree of freedom, fitted to the group's own edges -
  // so a row can point at its relative without any pair of rows crowding.
  const anchor = { x: 0, y: 0 };
  const rowIds = [ROW_A1, ROW_A2, "mse_a#decisions/d3-third"];
  const positions = satellitePositions({
    rowIds,
    anchor,
    // d1's relative sits due east, so d1 should end up due east.
    counterparts: new Map([[ROW_A1, [{ x: 400, y: 0 }]]]),
  });
  const first = positions.get(ROW_A1)!;
  assert.ok(first.x > SATELLITE_RADIUS * 0.99, `d1 should face east, got x=${first.x}`);
  assert.ok(Math.abs(first.y) < 1e-6, `d1 should face east, got y=${first.y}`);
  // ...and the other two moved with it, still 120 degrees apart.
  const angles = rowIds.map((rowId) => {
    const point = positions.get(rowId)!;
    return Math.atan2(point.y, point.x);
  });
  for (let index = 1; index < angles.length; index += 1) {
    let gap = angles[index] - angles[index - 1];
    while (gap <= 0) gap += Math.PI * 2;
    assert.ok(Math.abs(gap - (Math.PI * 2) / rowIds.length) < 1e-9, `spacing broke: ${gap}`);
  }
});

test("the rotation splits the difference when rows want different directions", () => {
  // Two rows, two relatives on opposite sides of where the slots already are:
  // a rigid ring cannot satisfy both, so it takes the circular mean rather than
  // obeying whichever row came first.
  const anchor = { x: 0, y: 0 };
  const east = { x: 300, y: 0 };
  const west = { x: -300, y: 0 };
  // Slots are 180 degrees apart, and the targets are 180 apart, so this fit is
  // exact: d1 east and d2 west.
  const positions = satellitePositions({
    rowIds: [ROW_A1, ROW_A2],
    anchor,
    counterparts: new Map([[ROW_A1, [east]], [ROW_A2, [west]]]),
  });
  assert.ok(positions.get(ROW_A1)!.x > SATELLITE_RADIUS * 0.99, "d1 faces its relative");
  assert.ok(positions.get(ROW_A2)!.x < -SATELLITE_RADIUS * 0.99, "d2 faces its relative");
});

test("a rotation that cancels out falls back rather than jittering", () => {
  // Both rows pulled the same way with slots 180 apart: the fit is genuinely
  // undetermined, so the ring must rest somewhere fixed instead of picking one of
  // two equally good answers and flipping between them each frame.
  const anchor = { x: 0, y: 0 };
  const target = [{ x: 0, y: 200 }];
  const phase = ringPhase({
    rowIds: [ROW_A1, ROW_A2],
    anchor,
    counterparts: new Map([[ROW_A1, target], [ROW_A2, target]]),
  });
  assert.equal(phase, -Math.PI / 2);
});

test("the halo encloses the ring it frames, at every row count", () => {
  // The circle and the row placement must derive the ring from one function, or
  // the disc drifts off the diamonds it is supposed to contain.
  for (const count of [1, 2, 3, 6, 20]) {
    const rowIds = Array.from({ length: count }, (_unused, index) => `mse_a#decisions/d${index + 1}-x`);
    const positions = satellitePositions({ rowIds, anchor: { x: 0, y: 0 } });
    const furthest = Math.max(...rowIds.map((id) => {
      const point = positions.get(id)!;
      return Math.sqrt(point.x ** 2 + point.y ** 2);
    }));
    assert.ok(haloDiameter(count) / 2 > furthest, `${count} rows reach ${furthest}, halo radius ${haloDiameter(count) / 2}`);
  }
});

test("the ring grows only when equal spacing would crowd the rows", () => {
  const anchor = { x: 0, y: 0 };
  const distanceFor = (count: number) => {
    const rowIds = Array.from({ length: count }, (_unused, index) => `mse_a#decisions/d${index + 1}-x`);
    const point = satellitePositions({ rowIds, anchor }).get(rowIds[0])!;
    return Math.sqrt(point.x ** 2 + point.y ** 2);
  };
  // The common cases stay on the base radius rather than drifting off the anchor.
  assert.ok(Math.abs(distanceFor(2) - SATELLITE_RADIUS) < 1e-9);
  assert.ok(Math.abs(distanceFor(8) - SATELLITE_RADIUS) < 1e-9);
  // A crowded ring pushes out instead of overlapping.
  assert.ok(distanceFor(20) > SATELLITE_RADIUS, `20 rows stayed at ${distanceFor(20)}`);
});

test("row placement is deterministic - the same payload reproduces the same map", () => {
  const anchor = { x: 12, y: 34 };
  const first = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  const second = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  assert.deepEqual([...first.entries()], [...second.entries()]);
});


// --- simulationLinks: decision-level forces pass through to the entry --------

const KNOWN = new Set(["mse_a", "mse_b", "mse_c"]);

test("an edge on a decision row pulls that row's ENTRY", () => {
  // The bug this replaced: the row matched no simulation node, so the edge was
  // dropped from the link force while still being drawn - a line across the map
  // exerting nothing.
  const links = simulationLinks([{ source: ROW_A1, target: "mse_b" }], KNOWN);
  assert.deepEqual(links, [{ source: "mse_a", target: "mse_b" }]);
});

test("an edge between two entries' rows joins the two entries", () => {
  const links = simulationLinks([{ source: ROW_A1, target: ROW_B3 }], KNOWN);
  assert.deepEqual(links, [{ source: "mse_a", target: "mse_b" }]);
});

test("an edge between two rows of the SAME entry is not a link", () => {
  // Drawn, but meaningless as a force: it would pull an entry toward itself.
  assert.deepEqual(simulationLinks([{ source: ROW_A1, target: ROW_A2 }], KNOWN), []);
});

test("a pair joined many times over is pulled once", () => {
  // Five decision-level edges between the same entries must not pull five times
  // as hard as one entry-level edge. 696 decision edges exist; this is the
  // difference between a map and a knot.
  const links = simulationLinks(
    [
      { source: ROW_A1, target: ROW_B3 },
      { source: ROW_A2, target: "mse_b" },
      { source: "mse_a", target: "mse_b" },
      { source: "mse_b", target: ROW_A1 },
    ],
    KNOWN,
  );
  assert.deepEqual(links, [{ source: "mse_a", target: "mse_b" }]);
});

test("direction does not create a second link for the same pair", () => {
  const links = simulationLinks(
    [
      { source: "mse_a", target: "mse_b" },
      { source: "mse_b", target: "mse_a" },
    ],
    KNOWN,
  );
  assert.equal(links.length, 1);
});

test("an endpoint outside the simulation is skipped, not invented", () => {
  assert.deepEqual(simulationLinks([{ source: "mse_a", target: "mse_zz" }], KNOWN), []);
  assert.deepEqual(simulationLinks([{ source: "mse_zz#decisions/d1-x", target: "mse_a" }], KNOWN), []);
});

test("ordinary entry-to-entry edges are unchanged", () => {
  const links = simulationLinks(
    [
      { source: "mse_a", target: "mse_b" },
      { source: "mse_b", target: "mse_c" },
    ],
    KNOWN,
  );
  assert.deepEqual(links, [
    { source: "mse_a", target: "mse_b" },
    { source: "mse_b", target: "mse_c" },
  ]);
});
