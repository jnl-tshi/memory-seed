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
