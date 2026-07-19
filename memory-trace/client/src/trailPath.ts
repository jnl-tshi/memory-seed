// Deterministic hand-drawn stroke geometry for the Trail rail.
//
// "Drawn" mode used to be a turbulence filter laid over perfectly straight
// <line>s. That displaces pixels but leaves the underlying geometry parallel,
// so neighbouring lanes wobbled *together* and read as visibly offset copies of
// the same straight line rather than as separate pen strokes.
//
// Here the character lives in the geometry instead: a low-frequency lateral
// wander splined through cubic Beziers, so each lane changes angle gently along
// its own length the way a pen drifts over a long stroke. The turbulence filter
// stays, demoted to fine surface grain.
//
// Everything is a pure function of (endpoints, seed key): no Math.random, no
// clock, no render counter. The same branch draws the same line on every
// render, so React re-renders never reshape the rail.

export type Point = { x: number; y: number };

export type HandDrawnOptions = {
  /** Peak lateral offset from the true straight line, in px. */
  maxDrift?: number;
  /** Target distance between interior control points, in px. */
  spacing?: number;
  /** Drift fades to zero within this distance of each endpoint, in px. */
  lockZone?: number;
  /** Catmull-Rom tangent scale: lower is tighter to the control polygon. */
  tension?: number;
};

export const HAND_DRAWN_DEFAULTS: Required<HandDrawnOptions> = {
  maxDrift: 1.1,
  spacing: 65,
  lockZone: 18,
  tension: 0.45,
};

/** FNV-1a. Stable across runs and platforms — unlike String.hashCode idioms. */
export function seedHash(key: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < key.length; i += 1) {
    hash ^= key.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/** mulberry32 — small, fast, well-distributed for the handful of draws we take. */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Two long, seeded sinusoids. Their wavelengths span several control points, so
// successive points move *together* — a pen drifting, not per-row jitter. The
// amplitudes sum to exactly 1, which is what bounds |wave| <= 1 analytically
// rather than by sampling.
function driftWave(seedKey: string, spacing: number): (distance: number) => number {
  const random = mulberry32(seedHash(seedKey));
  const phaseA = random() * Math.PI * 2;
  const phaseB = random() * Math.PI * 2;
  const waveA = (Math.PI * 2) / (spacing * (2.4 + random() * 1.1));
  const waveB = (Math.PI * 2) / (spacing * (4.3 + random() * 1.9));
  const sign = random() < 0.5 ? -1 : 1;
  return (distance) => sign * (0.62 * Math.sin(distance * waveA + phaseA) + 0.38 * Math.sin(distance * waveB + phaseB));
}

// Smoothstep ramp pinning drift to zero at both ends. This is what keeps dots
// centred on their lane and lets fork/merge elbows meet their runs exactly.
function endpointTaper(distance: number, length: number, lockZone: number): number {
  if (lockZone <= 0) return 1;
  const ramp = Math.max(0, Math.min(1, Math.min(distance, length - distance) / lockZone));
  return ramp * ramp * (3 - 2 * ramp);
}

/** 2dp is finer than a CSS pixel at any sane zoom and keeps `d` strings short. */
function fmt(value: number): string {
  const rounded = Math.round(value * 100) / 100;
  return Object.is(rounded, -0) ? "0" : String(rounded);
}

/**
 * Control points for a hand-drawn run between two exact endpoints.
 *
 * Drift is applied perpendicular to the run, so this works for vertical lanes,
 * horizontal connector legs and anything diagonal. Runs shorter than ~1.5x
 * `spacing` get no interior points and degrade to a straight two-point line.
 */
export function handDrawnPoints(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  seedKey: string,
  options: HandDrawnOptions = {},
): Point[] {
  const { maxDrift, spacing, lockZone } = { ...HAND_DRAWN_DEFAULTS, ...options };
  const start: Point = { x: x1, y: y1 };
  const end: Point = { x: x2, y: y2 };
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.hypot(dx, dy);
  if (!Number.isFinite(length) || length <= 0 || spacing <= 0) return [start, end];

  // Round-to-nearest keeps the realised gap near `spacing`; < 2 steps means the
  // run is too short to carry a believable wander, so it stays straight.
  const steps = Math.round(length / spacing);
  if (steps < 2) return [start, end];

  const alongX = dx / length;
  const alongY = dy / length;
  const perpX = -alongY;
  const perpY = alongX;
  const wave = driftWave(seedKey, spacing);

  const points: Point[] = [start];
  for (let i = 1; i < steps; i += 1) {
    const distance = (length * i) / steps;
    const offset = maxDrift * wave(distance) * endpointTaper(distance, length, lockZone);
    points.push({ x: x1 + alongX * distance + perpX * offset, y: y1 + alongY * distance + perpY * offset });
  }
  points.push(end);
  return points;
}

// Catmull-Rom -> cubic Bezier. Endpoints are duplicated rather than
// extrapolated so the curve starts and ends exactly on the given points.
function pathBody(points: Point[], tension: number): string {
  if (points.length < 2) return "";
  if (points.length === 2) return ` L ${fmt(points[1].x)} ${fmt(points[1].y)}`;
  let body = "";
  for (let i = 0; i < points.length - 1; i += 1) {
    const previous = points[i - 1] ?? points[i];
    const current = points[i];
    const next = points[i + 1];
    const following = points[i + 2] ?? points[i + 1];
    const c1x = current.x + ((next.x - previous.x) / 6) * tension;
    const c1y = current.y + ((next.y - previous.y) / 6) * tension;
    const c2x = next.x - ((following.x - current.x) / 6) * tension;
    const c2y = next.y - ((following.y - current.y) / 6) * tension;
    body += ` C ${fmt(c1x)} ${fmt(c1y)} ${fmt(c2x)} ${fmt(c2y)} ${fmt(next.x)} ${fmt(next.y)}`;
  }
  return body;
}

/** `d` for a run, hand-drawn when `handDrawn`, exactly straight otherwise. */
export function runPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  seedKey: string,
  handDrawn: boolean,
  options: HandDrawnOptions = {},
): string {
  return `M ${fmt(x1)} ${fmt(y1)}${runBody(x1, y1, x2, y2, seedKey, handDrawn, options)}`;
}

/**
 * The same run without its leading move — for composing multi-leg paths such as
 * fork/merge connectors, where the rounded elbow between legs stays exact.
 */
export function runBody(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  seedKey: string,
  handDrawn: boolean,
  options: HandDrawnOptions = {},
): string {
  if (!handDrawn) return ` L ${fmt(x2)} ${fmt(y2)}`;
  const tension = options.tension ?? HAND_DRAWN_DEFAULTS.tension;
  return pathBody(handDrawnPoints(x1, y1, x2, y2, seedKey, options), tension);
}

/**
 * A closed, variable-width outline around a centerline — the "pressure" of a
 * real pen, which a constant `stroke-width` cannot express.
 *
 * The centerline is passed in unchanged (it is exactly `handDrawnPoints`
 * output), so the wander and this width modulation stay independent concerns:
 * every geometry guarantee about the centerline still holds.
 *
 * Width tapers back to `baseWidth` at both ends so a ribbon meets a
 * constant-width neighbour — a fork elbow, a merge leg — without a visible step.
 * Returns "" when the run is too short to carry variation; callers fall back to
 * an ordinary stroke, which also keeps the round caps that short runs want.
 */
export function ribbonEdges(
  points: Point[],
  baseWidth: number,
  variation: number,
  seedKey: string,
  options: HandDrawnOptions = {},
): { left: Point[]; right: Point[]; half: number[] } | null {
  const { spacing, lockZone } = { ...HAND_DRAWN_DEFAULTS, ...options };
  if (points.length < 3 || !(baseWidth > 0) || !(variation > 0)) return null;

  const distances = [0];
  for (let i = 1; i < points.length; i += 1) {
    distances.push(distances[i - 1] + Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y));
  }
  const length = distances[distances.length - 1];
  if (!(length > 0)) return null;

  // A separate seed from the drift: pen pressure and pen drift are unrelated,
  // and sharing a wave would make every stroke thickest exactly where it bends.
  const wave = driftWave(`${seedKey}:pressure`, spacing);
  const half = points.map((_, index) => {
    const distance = distances[index];
    const swing = variation * wave(distance) * endpointTaper(distance, length, lockZone);
    return (baseWidth / 2) * (1 + swing);
  });

  // Central-difference normals so the offset follows the curve smoothly rather
  // than kinking at every control point.
  const left: Point[] = [];
  const right: Point[] = [];
  points.forEach((point, index) => {
    const previous = points[Math.max(0, index - 1)];
    const next = points[Math.min(points.length - 1, index + 1)];
    const dx = next.x - previous.x;
    const dy = next.y - previous.y;
    const magnitude = Math.hypot(dx, dy) || 1;
    const normalX = -dy / magnitude;
    const normalY = dx / magnitude;
    left.push({ x: point.x + normalX * half[index], y: point.y + normalY * half[index] });
    right.push({ x: point.x - normalX * half[index], y: point.y - normalY * half[index] });
  });
  return { left, right, half };
}

export function ribbonPath(
  points: Point[],
  baseWidth: number,
  variation: number,
  seedKey: string,
  options: HandDrawnOptions = {},
): string {
  const edges = ribbonEdges(points, baseWidth, variation, seedKey, options);
  if (!edges) return "";
  const tension = options.tension ?? HAND_DRAWN_DEFAULTS.tension;
  const back = edges.right.slice().reverse();
  return (
    `M ${fmt(edges.left[0].x)} ${fmt(edges.left[0].y)}` +
    pathBody(edges.left, tension) +
    ` L ${fmt(back[0].x)} ${fmt(back[0].y)}` +
    pathBody(back, tension) +
    " Z"
  );
}

/** Convenience: hand-drawn centerline plus pressure, in one call. */
export function pressurePath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  seedKey: string,
  baseWidth: number,
  variation: number,
  options: HandDrawnOptions = {},
): string {
  return ribbonPath(handDrawnPoints(x1, y1, x2, y2, seedKey, options), baseWidth, variation, seedKey, options);
}

/** A move command, formatted identically to the one `runPath` emits. */
export function moveTo(x: number, y: number): string {
  return `M ${fmt(x)} ${fmt(y)}`;
}

/** A quadratic elbow, kept geometrically exact in both stroke styles. */
export function elbowTo(cx: number, cy: number, x: number, y: number): string {
  return ` Q ${fmt(cx)} ${fmt(cy)} ${fmt(x)} ${fmt(y)}`;
}

export const __testing = { fmt, endpointTaper, driftWave };
