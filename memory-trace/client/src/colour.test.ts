import assert from "node:assert/strict";
import test from "node:test";

import { hexToOklab, minimumSeparation, mixHex, oklabDistance } from "./colour.ts";

test("identical colours are zero apart", () => {
  assert.equal(oklabDistance("#be6877", "#be6877"), 0);
});

test("distance is perceptual, not sRGB arithmetic", () => {
  // The whole reason this module exists. These two blues are FURTHER apart in
  // raw sRGB than the blue/yellow pair, yet obviously harder to tell apart.
  const blues = oklabDistance("#6688e8", "#5f8fd6");
  const blueYellow = oklabDistance("#6688e8", "#d1a255");
  assert.ok(blues < blueYellow, "two blues must measure closer than a blue and an ochre");
});

test("minimumSeparation finds the closest pair, not the average", () => {
  const separation = minimumSeparation(["#000000", "#ffffff", "#fefefe"]);
  assert.ok(separation < 0.02, `expected the near-identical whites to dominate, got ${separation}`);
});

test("a set of fewer than two colours has no separation to report", () => {
  assert.equal(minimumSeparation([]), 0);
  assert.equal(minimumSeparation(["#be6877"]), 0);
});

test("mixing moves toward the target and terminates at it", () => {
  assert.equal(mixHex("#000000", "#ffffff", 0), "#000000");
  assert.equal(mixHex("#000000", "#ffffff", 1), "#ffffff");
});

test("mixing clamps rather than extrapolating", () => {
  assert.equal(mixHex("#000000", "#ffffff", -3), "#000000");
  assert.equal(mixHex("#000000", "#ffffff", 9), "#ffffff");
});

test("mixing happens in linear light, not in gamma-encoded hex", () => {
  // Averaging sRGB hex directly gives #7f7f7f, which reads far darker than a
  // true half-way blend. Linear mixing lands near #bcbcbc.
  const midpoint = hexToOklab(mixHex("#000000", "#ffffff", 0.5))[0];
  const naive = hexToOklab("#7f7f7f")[0];
  assert.ok(midpoint > naive + 0.1, `linear midpoint ${midpoint} should be clearly lighter than ${naive}`);
});
