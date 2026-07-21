// Pure graph-layout seeding, extracted from GraphWorkspace so the rules that
// decide WHERE nodes start (and how long the simulation runs) can be unit
// tested without a DOM or a Cytoscape instance — the same reason
// inspectorScroll/trailScroll are their own modules.
import type { RendererGraphNode } from "./api";

export type Point = { x: number; y: number };

// Deterministic initial positions: nodes ordered by community then id, placed
// on a circle. cose is a physics simulation — from a fixed starting
// arrangement it settles to the same layout every time, so the map holds still
// across loads and reloads instead of scrambling.
export function initialPositions(nodes: RendererGraphNode[]): Map<string, Point> {
  const ordered = [...nodes].sort(
    (left, right) => left.community.id.localeCompare(right.community.id) || left.id.localeCompare(right.id),
  );
  const radius = Math.max(220, ordered.length * 14);
  const positions = new Map<string, Point>();
  ordered.forEach((node, index) => {
    const angle = (index / Math.max(1, ordered.length)) * Math.PI * 2;
    positions.set(node.id, { x: Math.round(Math.cos(angle) * radius), y: Math.round(Math.sin(angle) * radius) });
  });
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
