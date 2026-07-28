// A soft push toward fewer edge crossings — an ideal the layout leans into,
// not a constraint it enforces. Untangling a graph exactly is a hard
// combinatorial problem; this settles for a force that nudges crossing edges
// apart every tick, the same way chainSpiralForce nudges chain members into a
// spiral. It sometimes leaves a crossing in a dense cluster where the link
// and charge forces disagree with it, and that is an acceptable outcome, not
// a bug — see graphLayout.ts and the ADR both forces already answer to for
// why the dense sections are not to be disturbed to chase this.
//
// Extracted as its own pure module (same reason as graphSpiral/graphLayout)
// so the geometry and the candidate-selection can be unit tested without a
// simulation, and so the O(E^2) exact count stays a measurement tool rather
// than something that ever runs in the hot path.

export type CrossPoint = { x: number; y: number };
export type CrossEdge = { source: string; target: string };

function orientation(p: CrossPoint, q: CrossPoint, r: CrossPoint): number {
  const value = (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  return value > 0 ? 1 : value < 0 ? -1 : 0;
}

/**
 * True when segment a1-a2 properly crosses segment b1-b2 — strictly, at an
 * interior point of both. Segments that only touch (a shared endpoint, or one
 * grazing the other's line) return false: two edges meeting at the node they
 * both connect to are not a crossing to resolve, they are the same joint.
 * Collinear overlap is likewise left alone — vanishingly rare for a physics
 * layout and not worth the extra branch on every candidate pair.
 */
export function segmentsCross(a1: CrossPoint, a2: CrossPoint, b1: CrossPoint, b2: CrossPoint): boolean {
  const o1 = orientation(a1, a2, b1);
  const o2 = orientation(a1, a2, b2);
  const o3 = orientation(b1, b2, a1);
  const o4 = orientation(b1, b2, a2);
  return o1 !== 0 && o2 !== 0 && o3 !== 0 && o4 !== 0 && o1 !== o2 && o3 !== o4;
}

/**
 * Exact crossing count, all edge pairs. O(E^2) — a measurement tool for
 * before/after comparisons and tests, never called per tick. Edges sharing an
 * endpoint are skipped, same rule as the force below.
 */
export function countCrossings(positions: ReadonlyMap<string, CrossPoint>, edges: readonly CrossEdge[]): number {
  let count = 0;
  for (let i = 0; i < edges.length; i += 1) {
    const a = edges[i];
    const a1 = positions.get(a.source);
    const a2 = positions.get(a.target);
    if (!a1 || !a2) continue;
    for (let j = i + 1; j < edges.length; j += 1) {
      const b = edges[j];
      if (a.source === b.source || a.source === b.target || a.target === b.source || a.target === b.target) continue;
      const b1 = positions.get(b.source);
      const b2 = positions.get(b.target);
      if (!b1 || !b2) continue;
      if (segmentsCross(a1, a2, b1, b2)) count += 1;
    }
  }
  return count;
}

type ForceNode = { id: string; x: number; y: number; vx?: number; vy?: number };

export type CrossingForceOptions = {
  /** Grid cell size, in graph units, used only to find candidate pairs —
   * roughly one link length, so a typical edge touches a handful of cells and
   * a cell holds few enough edges to check exhaustively. */
  cellSize?: number;
  /** Hard ceiling on candidate pairs examined per tick, independent of graph
   * size. The grid already keeps candidates close to O(E); this is the
   * backstop for the pathological case — one crowded cell — so a single tick
   * can never blow the frame budget ticksPerPaint is tuned against. Being
   * under budget on a large graph just means fewer crossings get resolved
   * that tick, which is the same "ideal, not a rule" trade the module exists
   * to make. */
  maxChecks?: number;
};

const DEFAULT_CELL = 90;
const DEFAULT_MAX_CHECKS = 6000;

function cellKey(cx: number, cy: number): string {
  return cx + ":" + cy;
}

/**
 * A d3-force-compatible force: every tick, finds edge pairs whose bounding
 * boxes are near enough to be candidates (via a uniform grid, not an O(E^2)
 * scan), checks the candidates exactly, and for each real crossing pushes
 * each edge's midpoint away from the other's. That widens the gap that makes
 * them cross — a mild, symmetric nudge, not a claim about which edge should
 * move or a guarantee the crossing resolves before the two are pulled back
 * together by other forces.
 */
export function edgeCrossingForce(
  getEdges: () => readonly CrossEdge[],
  strength: () => number,
  options: CrossingForceOptions = {},
) {
  const cellSize = options.cellSize ?? DEFAULT_CELL;
  const maxChecks = options.maxChecks ?? DEFAULT_MAX_CHECKS;
  let byId = new Map<string, ForceNode>();

  const force = (alpha: number) => {
    const power = strength();
    const edges = getEdges();
    if (!power || edges.length < 2) return;

    const buckets = new Map<string, number[]>();
    for (let i = 0; i < edges.length; i += 1) {
      const edge = edges[i];
      const a = byId.get(edge.source);
      const b = byId.get(edge.target);
      if (!a || !b) continue;
      const c0x = Math.floor(Math.min(a.x, b.x) / cellSize);
      const c1x = Math.floor(Math.max(a.x, b.x) / cellSize);
      const c0y = Math.floor(Math.min(a.y, b.y) / cellSize);
      const c1y = Math.floor(Math.max(a.y, b.y) / cellSize);
      for (let cx = c0x; cx <= c1x; cx += 1) {
        for (let cy = c0y; cy <= c1y; cy += 1) {
          const key = cellKey(cx, cy);
          (buckets.get(key) ?? buckets.set(key, []).get(key)!).push(i);
        }
      }
    }

    let checks = 0;
    const seen = new Set<string>();
    outer: for (const indices of buckets.values()) {
      for (let x = 0; x < indices.length; x += 1) {
        for (let y = x + 1; y < indices.length; y += 1) {
          if (checks >= maxChecks) break outer;
          const i = indices[x];
          const j = indices[y];
          const pairKey = i < j ? i + ":" + j : j + ":" + i;
          if (seen.has(pairKey)) continue;
          seen.add(pairKey);
          checks += 1;
          const edgeA = edges[i];
          const edgeB = edges[j];
          if (
            edgeA.source === edgeB.source ||
            edgeA.source === edgeB.target ||
            edgeA.target === edgeB.source ||
            edgeA.target === edgeB.target
          ) continue;
          const a1 = byId.get(edgeA.source);
          const a2 = byId.get(edgeA.target);
          const b1 = byId.get(edgeB.source);
          const b2 = byId.get(edgeB.target);
          if (!a1 || !a2 || !b1 || !b2) continue;
          if (!segmentsCross(a1, a2, b1, b2)) continue;
          const midAx = (a1.x + a2.x) / 2;
          const midAy = (a1.y + a2.y) / 2;
          const midBx = (b1.x + b2.x) / 2;
          const midBy = (b1.y + b2.y) / 2;
          let dx = midAx - midBx;
          let dy = midAy - midBy;
          const distance = Math.hypot(dx, dy) || 1e-6;
          dx /= distance;
          dy /= distance;
          const push = power * alpha;
          nudge(a1, dx, dy, push);
          nudge(a2, dx, dy, push);
          nudge(b1, -dx, -dy, push);
          nudge(b2, -dx, -dy, push);
        }
      }
    }
  };
  force.initialize = (nodes: ForceNode[]) => {
    byId = new Map(nodes.map((node) => [node.id, node]));
  };
  return force;
}

function nudge(node: ForceNode, dx: number, dy: number, push: number): void {
  node.vx = (node.vx ?? 0) + dx * push;
  node.vy = (node.vy ?? 0) + dy * push;
}
