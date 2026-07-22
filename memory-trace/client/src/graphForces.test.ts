import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_FORCES, forceParameters, LINK_DISTANCE, readForceSettings } from "./graphForces.ts";

test("sliders map to sane force units at both ends", () => {
  const low = forceParameters({ centre: 0, repel: 0, linkForce: 0 });
  const high = forceParameters({ centre: 1, repel: 1, linkForce: 1 });
  assert.ok(low.centreStrength > 0, "centre never reaches zero, or the graph drifts off-screen");
  assert.ok(high.centreStrength < 0.2, "centre never so strong the graph collapses to a point");
  assert.ok(low.chargeStrength < 0 && high.chargeStrength < low.chargeStrength, "charge is repulsive and increases");
  assert.ok(low.linkStrength > 0 && high.linkStrength <= 0.8);
  assert.equal(low.linkDistance, LINK_DISTANCE, "link distance is a constant, not a slider");
});

test("every force is monotonic in its slider", () => {
  const at = (value: number) => forceParameters({ centre: value, repel: value, linkForce: value });
  for (let step = 0; step < 10; step += 1) {
    const a = at(step / 10);
    const b = at((step + 1) / 10);
    assert.ok(b.centreStrength > a.centreStrength);
    assert.ok(b.chargeStrength < a.chargeStrength, "more repel means a more negative charge");
    assert.ok(b.linkStrength > a.linkStrength);
  }
});

test("repel is curved so the useful range is not crushed into the first tenth", () => {
  const magnitude = (value: number) => Math.abs(forceParameters({ ...DEFAULT_FORCES, repel: value }).chargeStrength);
  const lowerHalf = magnitude(0.5) - magnitude(0);
  const upperHalf = magnitude(1) - magnitude(0.5);
  assert.ok(upperHalf > lowerHalf * 2, "the top half of the slider must cover far more force than the bottom");
});

test("defaults reproduce the settle-only layout's character", () => {
  // cose ran nodeRepulsion 12_000 / idealEdgeLength 150 / gravity 0.3; turning
  // physics on should not rearrange a graph the reader already knows.
  const params = forceParameters(DEFAULT_FORCES);
  assert.equal(params.linkDistance, LINK_DISTANCE);
  assert.ok(params.chargeStrength < -400 && params.chargeStrength > -600);
});

test("stored settings are validated, not trusted", () => {
  assert.deepEqual(readForceSettings(undefined), DEFAULT_FORCES);
  assert.deepEqual(readForceSettings({ centre: "loud" }), DEFAULT_FORCES);
  assert.equal(readForceSettings({ repel: 5 }).repel, 1, "out of range clamps rather than escaping");
  assert.equal(readForceSettings({ repel: -3 }).repel, 0);
  assert.equal(readForceSettings({ centre: 0.8 }).centre, 0.8);
  // A partial blob keeps defaults for the rest.
  assert.equal(readForceSettings({ centre: 0.8 }).repel, DEFAULT_FORCES.repel);
});
