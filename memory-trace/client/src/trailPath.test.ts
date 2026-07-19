// Geometry contract for the Trail's hand-drawn rail.
//
// Run with `npm test` (node:test, native TypeScript stripping — no runner
// dependency). These assert the properties the rail depends on: identical
// output across renders, per-branch distinctness, exact endpoints so dots and
// elbows still meet, a hard drift bound, and Slick geometry left untouched.
import { test } from "node:test";
import assert from "node:assert/strict";

// Explicit .ts extension: node's ESM resolver does not guess extensions. These
// files sit outside the app tsconfig (see `exclude`), so the app build and
// typecheck never see this import style.
import { HAND_DRAWN_DEFAULTS, handDrawnPoints, runBody, runPath, seedHash } from "./trailPath.ts";

/** Every coordinate pair in a `d` string, in order. */
function coordinates(d: string): number[] {
  return (d.match(/-?\d+(?:\.\d+)?/g) ?? []).map(Number);
}

/** Perpendicular distance of each point from the straight line start->end. */
function drifts(points: { x: number; y: number }[]): number[] {
  const first = points[0];
  const last = points[points.length - 1];
  const dx = last.x - first.x;
  const dy = last.y - first.y;
  const length = Math.hypot(dx, dy);
  return points.map((point) => Math.abs((point.x - first.x) * (dy / length) - (point.y - first.y) * (dx / length)));
}

const LONG = { x1: 100, y1: 15, x2: 100, y2: 615 } as const;
const long = (seed: string) => runPath(LONG.x1, LONG.y1, LONG.x2, LONG.y2, seed, true);

test("seedHash is stable and distinguishes near-identical keys", () => {
  assert.equal(seedHash("main:lane"), seedHash("main:lane"));
  assert.notEqual(seedHash("main:lane"), seedHash("main:trunk"));
  assert.notEqual(seedHash("claude/feature/a"), seedHash("claude/feature/b"));
});

test("identical inputs produce identical paths across calls", () => {
  assert.equal(long("claude/feature/worktree-nav:lane"), long("claude/feature/worktree-nav:lane"));
});

test("different branch seeds produce different paths", () => {
  const branches = ["main", "claude/feature/worktree-nav", "claude/feature/trail-parity", "claude/docs/inbox", "claude/fix/a"];
  const paths = branches.map((branch) => long(`${branch}:lane`));
  assert.equal(new Set(paths).size, branches.length, "neighbouring lanes must not share a drift pattern");
});

test("the same branch differs by path role", () => {
  assert.notEqual(long("main:lane"), long("main:trunk"));
});

test("endpoints are exact", () => {
  const d = long("claude/feature/worktree-nav:lane");
  const numbers = coordinates(d);
  assert.deepEqual(numbers.slice(0, 2), [LONG.x1, LONG.y1], "path must start on the exact anchor");
  assert.deepEqual(numbers.slice(-2), [LONG.x2, LONG.y2], "path must end on the exact anchor");
});

test("endpoints stay exact for horizontal and diagonal runs", () => {
  for (const [x1, y1, x2, y2] of [
    [12, 40, 512, 40],
    [30, 20, 430, 420],
  ]) {
    const numbers = coordinates(runPath(x1, y1, x2, y2, "seed:run", true));
    assert.deepEqual(numbers.slice(0, 2), [x1, y1]);
    assert.deepEqual(numbers.slice(-2), [x2, y2]);
  }
});

test("drift stays inside the configured bound", () => {
  for (const branch of ["main", "claude/feature/a", "claude/feature/b", "zzz", "1"]) {
    const points = handDrawnPoints(100, 0, 100, 900, `${branch}:lane`);
    const maximum = Math.max(...drifts(points));
    assert.ok(maximum <= HAND_DRAWN_DEFAULTS.maxDrift + 1e-9, `${branch} drifted ${maximum}`);
    assert.ok(maximum > 0, `${branch} produced no drift at all`);
  }
});

test("drift is zero at the endpoints and tapers within the lock zone", () => {
  const points = handDrawnPoints(100, 0, 100, 900, "main:lane");
  const offsets = drifts(points);
  assert.equal(offsets[0], 0);
  assert.equal(offsets[offsets.length - 1], 0);
  // Any point inside the lock zone must be closer to the line than the bound.
  points.forEach((point, index) => {
    const fromEnd = Math.min(point.y - points[0].y, points[points.length - 1].y - point.y);
    if (fromEnd < HAND_DRAWN_DEFAULTS.lockZone) {
      assert.ok(offsets[index] < HAND_DRAWN_DEFAULTS.maxDrift, `point ${index} ignored the lock zone`);
    }
  });
});

test("drift is low-frequency, not per-row jitter", () => {
  // Successive control points must move together: the step-to-step change is a
  // fraction of the full range, which is what separates a pen drift from noise.
  const points = handDrawnPoints(100, 0, 100, 1200, "claude/feature/worktree-nav:lane");
  const offsets = drifts(points);
  const steps = offsets.slice(1).map((value, index) => Math.abs(value - offsets[index]));
  assert.ok(Math.max(...steps) < HAND_DRAWN_DEFAULTS.maxDrift, "a single step swung the full drift range");
});

test("control point spacing stays near the configured target", () => {
  const points = handDrawnPoints(100, 0, 100, 600, "main:lane");
  const gaps = points.slice(1).map((point, index) => point.y - points[index].y);
  for (const gap of gaps) {
    assert.ok(gap >= 45 && gap <= 95, `control points ${gap}px apart`);
  }
});

test("short spans degrade to a straight line", () => {
  // A single 30px row gap — the common case for adjacent entries on one lane.
  const short = runPath(100, 15, 100, 45, "main:lane", true);
  assert.equal(short, "M 100 15 L 100 45");
  assert.equal(handDrawnPoints(100, 15, 100, 45, "main:lane").length, 2);
});

test("degenerate runs do not throw or emit NaN", () => {
  for (const d of [runPath(50, 50, 50, 50, "s", true), runPath(0, 0, 0, 4, "s", true)]) {
    assert.ok(!d.includes("NaN"), d);
  }
});

test("Slick mode keeps exact straight geometry", () => {
  // Same coordinates the previous <line> elements used, for any length.
  assert.equal(runPath(100, 15, 100, 615, "main:lane", false), "M 100 15 L 100 615");
  assert.equal(runBody(100, 15, 100, 615, "main:lane", false), " L 100 615");
});

test("Slick mode ignores seed and options entirely", () => {
  const a = runPath(10, 20, 10, 800, "branch-a:lane", false);
  const b = runPath(10, 20, 10, 800, "branch-b:trunk", false, { maxDrift: 40 });
  assert.equal(a, b);
});

test("a hand-drawn run is curved, and a slick one is not", () => {
  assert.ok(long("main:lane").includes("C "), "long hand-drawn runs should emit Beziers");
  assert.ok(!runPath(LONG.x1, LONG.y1, LONG.x2, LONG.y2, "main:lane", false).includes("C "));
});
