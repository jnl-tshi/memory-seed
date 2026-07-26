import assert from "node:assert/strict";
import { test } from "node:test";

import {
  anchorEntryIdFor,
  connectedIdsWithDecisionAnchors,
  decisionGroupId,
  decisionGroups,
  isDecisionRowId,
  parentIdsFor,
  satellitePositions,
  SATELLITE_RADIUS,
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

test("rows sit on their anchor's leash, so containment cannot drift", () => {
  const anchor = { x: 100, y: -40 };
  const positions = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  for (const rowId of [ROW_A1, ROW_A2]) {
    const point = positions.get(rowId)!;
    const distance = Math.sqrt((point.x - anchor.x) ** 2 + (point.y - anchor.y) ** 2);
    assert.ok(Math.abs(distance - SATELLITE_RADIUS) < 1e-9, `${rowId} is ${distance} from its anchor`);
  }
});

test("a row aims at its counterpart, so the line to its relative leaves on that side", () => {
  const anchor = { x: 0, y: 0 };
  const positions = satellitePositions({
    rowIds: [ROW_A1],
    anchor,
    counterparts: new Map([[ROW_A1, [{ x: 500, y: 0 }]]]),
  });
  const point = positions.get(ROW_A1)!;
  assert.ok(point.x > SATELLITE_RADIUS * 0.99, `aimed east, got x=${point.x}`);
  assert.ok(Math.abs(point.y) < 1e-6, `aimed east, got y=${point.y}`);
});

test("two rows aimed the same way still separate", () => {
  const anchor = { x: 0, y: 0 };
  const target = [{ x: 0, y: 300 }];
  const positions = satellitePositions({
    rowIds: [ROW_A1, ROW_A2],
    anchor,
    counterparts: new Map([
      [ROW_A1, target],
      [ROW_A2, target],
    ]),
  });
  const first = positions.get(ROW_A1)!;
  const second = positions.get(ROW_A2)!;
  const apart = Math.sqrt((first.x - second.x) ** 2 + (first.y - second.y) ** 2);
  assert.ok(apart > 20, `rows stacked ${apart} apart`);
});

test("row placement is deterministic - the same payload reproduces the same map", () => {
  const anchor = { x: 12, y: 34 };
  const first = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  const second = satellitePositions({ rowIds: [ROW_A1, ROW_A2], anchor });
  assert.deepEqual([...first.entries()], [...second.entries()]);
});
