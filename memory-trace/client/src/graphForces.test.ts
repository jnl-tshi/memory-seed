import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_FORCES, forceParameters, LINK_DISTANCE, readForceSettings, ticksPerPaint } from "./graphForces.ts";

test("physics steps per painted frame scale with the canvas, and stay bounded", () => {
  // Measured 2026-07-27: a frame in which anything moved costs ~85ms at ~1180
  // elements whether ONE node moved or all 303 did, so the lever is painting less
  // often. A small graph pays nothing for that and keeps per-tick motion.
  assert.equal(ticksPerPaint(133), 1, "a small graph keeps the smoothest motion");
  assert.equal(ticksPerPaint(400), 1);
  assert.equal(ticksPerPaint(800), 2);
  assert.equal(ticksPerPaint(1180), 3, "the corpus-scale case measured at ~85ms per painted frame");
  // Bounded: three steps still reads as movement, and an unbounded ramp would
  // eventually make the settle teleport.
  assert.equal(ticksPerPaint(100000), 3);
  // Degenerate inputs must never ask for zero steps, which would stall the loop.
  assert.equal(ticksPerPaint(0), 1);
  assert.equal(ticksPerPaint(-5), 1);
  assert.equal(ticksPerPaint(Number.NaN), 1);
});

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

// --- Chain spiral controls -------------------------------------------------

test("the shipped defaults ARE the configuration that was measured", () => {
  // 8 entries / 30 units / 1.75 rad is the setup the headless probe reported
  // 89% age-ordered over 633 degrees on. If a default drifts off it, the
  // evidence quoted for the feature stops describing what ships.
  const p = forceParameters(DEFAULT_FORCES);
  assert.equal(p.spiralMinLength, 8);
  assert.equal(Math.round(p.spiralStep), 30);
  assert.ok(Math.abs(p.spiralAngle - 1.75) < 0.005, `angle ${p.spiralAngle}`);
});

test("spiral strength 0 disables the force outright", () => {
  assert.equal(forceParameters({ ...DEFAULT_FORCES, spiral: 0 }).spiralStrength, 0);
});

test("every spiral control is monotonic across its slider", () => {
  const at = (over: Partial<typeof DEFAULT_FORCES>) => forceParameters({ ...DEFAULT_FORCES, ...over });
  assert.ok(at({ spiralMinLength: 0 }).spiralMinLength < at({ spiralMinLength: 1 }).spiralMinLength);
  assert.ok(at({ spiralTightness: 0 }).spiralStep < at({ spiralTightness: 1 }).spiralStep);
  assert.ok(at({ spiralWinding: 0 }).spiralAngle < at({ spiralWinding: 1 }).spiralAngle);
  assert.ok(at({ spiral: 0 }).spiralStrength < at({ spiral: 1 }).spiralStrength);
});

test("min chain length is a whole number of entries at every slider position", () => {
  // It counts nodes; a fractional floor would compare against a component size
  // and behave differently either side of a value the UI never shows.
  for (let i = 0; i <= 20; i += 1) {
    const value = forceParameters({ ...DEFAULT_FORCES, spiralMinLength: i / 20 }).spiralMinLength;
    assert.equal(value, Math.round(value));
  }
});

test("the spiral never outmuscles the link force it works alongside", () => {
  // A radial spring stronger than the link force turns a readable thread into a
  // bare ring: the radius wins and consecutive entries stop reading as adjacent.
  const maxSpiral = forceParameters({ ...DEFAULT_FORCES, spiral: 1 }).spiralStrength;
  const minLink = forceParameters({ ...DEFAULT_FORCES, linkForce: 0 }).linkStrength;
  assert.ok(maxSpiral < 1, `spiral tops out at ${maxSpiral}`);
  assert.ok(minLink > 0, "link force never reaches zero");
});
