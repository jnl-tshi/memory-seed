// Middle-third band arithmetic. Run with `npm test`.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  bandScrollTarget,
  easeInOutCubic,
  scrollDurationFor,
  TRAIL_SCROLL_MAX_MS,
  TRAIL_SCROLL_MIN_MS,
} from "./trailScroll.ts";

const VIEWPORT = 900; // band spans 300..600 of the viewport
const MAX = 10_000;

test("a row inside the middle third does not move", () => {
  // scrollTop 1000 -> band covers content 1300..1600.
  for (const rowCenter of [1300, 1450, 1600]) {
    assert.equal(bandScrollTarget(rowCenter, 1000, VIEWPORT, MAX), null, `row ${rowCenter} should hold`);
  }
});

test("a row above the band eases to the band's top edge", () => {
  const target = bandScrollTarget(1200, 1000, VIEWPORT, MAX);
  assert.equal(target, 900); // 1200 - 300 -> row sits exactly on the top edge
});

test("a row below the band eases to the band's bottom edge", () => {
  const target = bandScrollTarget(1800, 1000, VIEWPORT, MAX);
  assert.equal(target, 1200); // 1800 - 600 -> row sits exactly on the bottom edge
});

test("direction determines which edge is used", () => {
  const above = bandScrollTarget(500, 1000, VIEWPORT, MAX)!;
  const below = bandScrollTarget(2500, 1000, VIEWPORT, MAX)!;
  assert.ok(above < 1000, "scrolling up must decrease scrollTop");
  assert.ok(below > 1000, "scrolling down must increase scrollTop");
  assert.equal(above, 200); // 500 - 300
  assert.equal(below, 1900); // 2500 - 600
});

test("targets clamp to the scrollable range", () => {
  assert.equal(bandScrollTarget(10, 5000, VIEWPORT, MAX), 0, "cannot scroll above the top");
  assert.equal(bandScrollTarget(99_000, 0, VIEWPORT, MAX), MAX, "cannot scroll past the bottom");
});

test("a clamped target that equals the current position holds still", () => {
  // Already at the very top and the row is above the band: nothing to do.
  assert.equal(bandScrollTarget(100, 0, VIEWPORT, MAX), null);
  // Already at the very bottom and the row is below the band.
  assert.equal(bandScrollTarget(MAX + 800, MAX, VIEWPORT, MAX), null);
});

test("a zero-height viewport is a no-op rather than a divide-by-zero", () => {
  assert.equal(bandScrollTarget(500, 0, 0, MAX), null);
});

test("duration scales with distance and stays bounded", () => {
  assert.equal(scrollDurationFor(0), TRAIL_SCROLL_MIN_MS);
  assert.ok(scrollDurationFor(400) > scrollDurationFor(100), "further should take longer");
  assert.equal(scrollDurationFor(50_000), TRAIL_SCROLL_MAX_MS, "long jumps stay brisk");
  assert.equal(scrollDurationFor(-400), scrollDurationFor(400), "direction must not change duration");
});

test("easing accelerates and decelerates symmetrically", () => {
  assert.equal(easeInOutCubic(0), 0);
  assert.equal(easeInOutCubic(1), 1);
  assert.ok(Math.abs(easeInOutCubic(0.5) - 0.5) < 1e-9);
  // Symmetry: f(t) + f(1-t) === 1
  for (const t of [0.1, 0.25, 0.4, 0.75]) {
    assert.ok(Math.abs(easeInOutCubic(t) + easeInOutCubic(1 - t) - 1) < 1e-9, `asymmetric at ${t}`);
  }
  // Slow at the ends, fast in the middle.
  assert.ok(easeInOutCubic(0.1) < 0.1, "should accelerate from rest");
  assert.ok(easeInOutCubic(0.9) > 0.9, "should decelerate into rest");
});

test("easing clamps out-of-range progress", () => {
  assert.equal(easeInOutCubic(-1), 0);
  assert.equal(easeInOutCubic(2), 1);
});
