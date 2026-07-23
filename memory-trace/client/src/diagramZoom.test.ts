import assert from "node:assert/strict";
import test from "node:test";

import { clampScale, fitTransform, MAX_SCALE, MIN_SCALE, panBy, zoomAbout } from "./diagramZoom.ts";

test("fit centres the stage and never enlarges past natural size", () => {
  // Stage smaller than viewport: shown at 1:1 and centred, NOT blown up -
  // stroke widths in an authored diagram are absolute, so upscaling a small
  // diagram just makes it blurry and coarse.
  const small = fitTransform(1000, 800, 400, 300);
  assert.equal(small.scale, 1);
  assert.equal(small.x, 300);
  assert.equal(small.y, 250);

  // Stage larger than viewport: scaled down to the tighter axis.
  const large = fitTransform(1000, 800, 4000, 1600);
  assert.ok(large.scale < 1);
  assert.ok(Math.abs(large.scale - (1000 - 24) / 4000) < 1e-9, "width is the binding constraint here");
  // ...and the scaled stage is centred on BOTH axes, not pinned to a corner -
  // this is what "Fit centres the diagram" rests on.
  assert.ok(Math.abs(large.x - (1000 - 4000 * large.scale) / 2) < 1e-9, "centred horizontally when scaled down");
  assert.ok(Math.abs(large.y - (800 - 1600 * large.scale) / 2) < 1e-9, "centred vertically when scaled down");
});

test("fit survives a zero-sized stage rather than dividing by zero", () => {
  // Fires on the frame before the SVG has laid out; must not produce NaN.
  const t = fitTransform(800, 600, 0, 0);
  assert.deepEqual(t, { scale: 1, x: 0, y: 0 });
});

test("zoom keeps the point under the cursor fixed", () => {
  const start = { scale: 1, x: 0, y: 0 };
  const zoomed = zoomAbout(start, 2, 100, 50);
  // The content at (100,50) before the zoom must still be at (100,50) after,
  // or the diagram slides out from under the pointer on every wheel tick.
  assert.equal(zoomed.x + 100 * zoomed.scale, 100);
  assert.equal(zoomed.y + 50 * zoomed.scale, 50);
});

test("scale clamps at both ends and zoom cannot escape them", () => {
  assert.equal(clampScale(1000), MAX_SCALE);
  assert.equal(clampScale(0.0001), MIN_SCALE);
  let t = { scale: 1, x: 0, y: 0 };
  for (let i = 0; i < 200; i += 1) t = zoomAbout(t, 1.25, 0, 0);
  assert.equal(t.scale, MAX_SCALE);
  for (let i = 0; i < 400; i += 1) t = zoomAbout(t, 1 / 1.25, 0, 0);
  assert.equal(t.scale, MIN_SCALE);
});

test("pan translates without touching scale", () => {
  const t = panBy({ scale: 2.5, x: 10, y: -4 }, 6, 9);
  assert.deepEqual(t, { scale: 2.5, x: 16, y: 5 });
});
