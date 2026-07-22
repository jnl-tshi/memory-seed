// Pure graph-layout seeding, extracted from GraphWorkspace so the rules that
// decide WHERE nodes start (and how long the simulation runs) can be unit
// tested without a DOM or a Cytoscape instance — the same reason
// inspectorScroll/trailScroll are their own modules.
import type { RendererGraphNode } from "./api";

export type Point = { x: number; y: number };

/** Community-then-id: the deterministic order every placement rule below uses. */
function ordered(nodes: readonly RendererGraphNode[]): RendererGraphNode[] {
  return [...nodes].sort(
    (left, right) => left.community.id.localeCompare(right.community.id) || left.id.localeCompare(right.id),
  );
}

// Golden angle. Successive points differ by an irrational fraction of a turn,
// so no two ever line up into spokes.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const SPIRAL_SPACING = 64;

/**
 * Deterministic initial positions on a phyllotaxis spiral (sunflower packing).
 *
 * cose is a physics simulation: from a fixed starting arrangement it settles to
 * the same layout every time, so the map holds still across loads instead of
 * scrambling. The arrangement used to be a CIRCLE of radius `nodeCount * 14`,
 * which grew linearly with the corpus - about 6,500px at 462 nodes, a ring so
 * large the reduced iteration budget could never pull it closed, leaving edge
 * chords crossing an empty middle and a fit clamped past the viewport.
 *
 * A spiral grows with the square root instead, because it fills AREA rather
 * than a perimeter: the same 462 nodes seed inside ~1,400px. Nodes start near
 * their neighbours, so the simulation refines a rough layout instead of
 * building one from scratch.
 */
export function initialPositions(nodes: readonly RendererGraphNode[]): Map<string, Point> {
  const positions = new Map<string, Point>();
  ordered(nodes).forEach((node, index) => {
    const radius = SPIRAL_SPACING * Math.sqrt(index);
    const angle = index * GOLDEN_ANGLE;
    positions.set(node.id, { x: Math.round(Math.cos(angle) * radius), y: Math.round(Math.sin(angle) * radius) });
  });
  return positions;
}

/** Node ids that appear as an endpoint of at least one edge. */
export function connectedIds(edges: readonly GraphEdgeLike[]): Set<string> {
  const ids = new Set<string>();
  for (const edge of edges) {
    ids.add(edge.source);
    ids.add(edge.target);
  }
  return ids;
}

export type GraphEdgeLike = { source: string; target: string };

export type Bounds = { x1: number; y1: number; x2: number; y2: number };

const HALO_GAP = 180;
const HALO_RING_STEP = 90;
const HALO_MIN_ARC = 56;

/**
 * Places edgeless entries on rings OUTSIDE the connected layout.
 *
 * Roughly a fifth of entries carry no authored edge. They used not to render at
 * all, which made the coverage readout look like a cap; rendering them means
 * placing them somewhere. They are deliberately kept OUT of the cose
 * simulation: with no edges they have no spring to balance repulsion, so the
 * simulation would fling them across the connected core and cost iterations on
 * nodes carrying no structure.
 *
 * Instead this is the closed form of what a force layout would do to them -
 * mutual repulsion (even angular spacing, minimum arc between neighbours) plus
 * weak centre gravity (as close to the core as the spacing allows). Zero
 * simulation cost, and deterministic, so the halo is identical across reloads.
 */
export function haloPositions(
  isolates: readonly RendererGraphNode[],
  bounds: Bounds | null,
): Map<string, Point> {
  const positions = new Map<string, Point>();
  const list = ordered(isolates);
  if (!list.length) return positions;
  const centreX = bounds ? (bounds.x1 + bounds.x2) / 2 : 0;
  const centreY = bounds ? (bounds.y1 + bounds.y2) / 2 : 0;
  // The half-DIAGONAL, not half the longer side. A ring at max(w,h)/2 clears
  // the core's edges but cuts through its corners - measured on the live graph,
  // 82 of 107 isolates landed inside a 3484x3290 core that way. The diagonal is
  // the only radius that is outside a rectangle at every angle.
  const coreRadius = bounds
    ? Math.hypot(Math.abs(bounds.x2 - bounds.x1) / 2, Math.abs(bounds.y2 - bounds.y1) / 2)
    : 0;

  let index = 0;
  let ring = 0;
  while (index < list.length) {
    const radius = coreRadius + HALO_GAP + ring * HALO_RING_STEP;
    // As many as fit at this radius without crowding below the minimum arc.
    const capacity = Math.max(1, Math.floor((2 * Math.PI * radius) / HALO_MIN_ARC));
    const count = Math.min(capacity, list.length - index);
    for (let slot = 0; slot < count; slot += 1) {
      const angle = (slot / count) * Math.PI * 2;
      positions.set(list[index + slot].id, {
        x: Math.round(centreX + Math.cos(angle) * radius),
        y: Math.round(centreY + Math.sin(angle) * radius),
      });
    }
    index += count;
    ring += 1;
  }
  return positions;
}

export function nodeSetSignature(nodes: RendererGraphNode[]): string {
  return [...nodes].map((node) => node.id).sort().join("\n");
}

/** Where this mount's nodes start, and whether the simulation can be skipped.
 *
 * Every node that has a settled position from a previous layout gets it back,
 * ALWAYS — including when the node set matches exactly and the caller intends
 * to skip the simulation entirely. That case is precisely when the seeded
 * positions are the only thing placing the nodes: seeding it from the raw
 * circle instead strands every node on a ring whose radius grows with node
 * count, which past ~100 nodes sits outside the viewport (minZoom clamps the
 * fit) and leaves only edge chords crossing an empty canvas.
 *
 * `settled` true means "these are the finished positions, no layout needed".
 * `warmSeeded` means "some nodes were placed from a previous layout", which
 * lets the caller shorten the simulation for the ones that still must travel.
 */
export function seedPositions(
  nodes: RendererGraphNode[],
  edges: readonly GraphEdgeLike[],
  settledPositions: Map<string, Point>,
  settledSignature: string,
): { positions: Map<string, Point>; settled: boolean; warmSeeded: boolean } {
  const positions = initialPositions(nodes);
  const settled = settledPositions.size > 0 && nodeSetSignature(nodes) === settledSignature;
  let warmSeeded = false;
  if (settledPositions.size > 0) {
    for (const node of nodes) {
      const previous = settledPositions.get(node.id);
      if (previous) {
        positions.set(node.id, previous);
        warmSeeded = true;
      }
    }
    if (warmSeeded) {
      // Newcomers land beside the neighbours they will bond to, rather than on
      // the spiral's outer turns among strangers. "Show more" adds entries that
      // mostly attach to work already on screen, so this puts them a short
      // distance from where they belong and the halved warm iteration budget is
      // enough to finish the job.
      const adjacency = new Map<string, string[]>();
      for (const edge of edges) {
        (adjacency.get(edge.source) ?? adjacency.set(edge.source, []).get(edge.source)!).push(edge.target);
        (adjacency.get(edge.target) ?? adjacency.set(edge.target, []).get(edge.target)!).push(edge.source);
      }
      for (const node of nodes) {
        if (settledPositions.has(node.id)) continue;
        const anchors = (adjacency.get(node.id) ?? [])
          .map((neighbour) => settledPositions.get(neighbour))
          .filter((point): point is Point => Boolean(point));
        if (!anchors.length) continue;
        const centroid = anchors.reduce(
          (sum, point) => ({ x: sum.x + point.x / anchors.length, y: sum.y + point.y / anchors.length }),
          { x: 0, y: 0 },
        );
        // Deterministic offset from the id, so two newcomers sharing one
        // neighbour do not stack exactly on top of each other.
        let hash = 0;
        for (const character of node.id) hash = (hash * 31 + character.charCodeAt(0)) | 0;
        const angle = (Math.abs(hash) % 360) * (Math.PI / 180);
        const distance = 40 + (Math.abs(hash) % 40);
        positions.set(node.id, {
          x: Math.round(centroid.x + Math.cos(angle) * distance),
          y: Math.round(centroid.y + Math.sin(angle) * distance),
        });
      }
    }
  }
  return { positions, settled, warmSeeded };
}

// Measured cose cost with our exact options (900 iterations): 60 nodes 86ms,
// 500 nodes 4.6s, 1000 nodes 17.8s of main-thread block. 900 iterations is
// right at default size but unaffordable at "Show more" sizes, so above 150
// nodes the iteration budget scales down with node count; warm-seeded grown
// layouts (most of the big-graph cases) need even less to settle.
export function layoutIterations(nodeCount: number, warmSeeded: boolean): number {
  if (nodeCount <= 150) return 900;
  const scaled = Math.max(120, Math.round(900 * (150 / nodeCount)));
  return warmSeeded ? Math.max(80, Math.round(scaled / 2)) : scaled;
}
