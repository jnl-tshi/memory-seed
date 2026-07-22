// Bounded motion for the graph: which nodes a drag is allowed to move, and how
// long motion may last. Pure and DOM-free so the containment rules can be
// tested without a simulation - the same reason graphLayout is its own module.
//
// Proposal §6.5 governs everything here. Motion is an exploration affordance,
// never evidence: a position that moves must not imply a changed relationship,
// timestamp, rank, or any authored fact. Every rule below exists to keep motion
// LOCAL and FINITE, so it can never be mistaken for the graph restructuring
// itself.

export type MotionEdge = { source: string; target: string };

/**
 * The most nodes that may be under live physics at once.
 *
 * Measured, not guessed: cose over the shipped options blocks the main thread
 * for 1177ms warm at 467 nodes (e2e-scale measurements.json, step 16). Live
 * per-frame physics at that size is unaffordable, so continuous motion is
 * confined to a neighbourhood this size and everything larger gets an end
 * state instead.
 */
export const LIVE_MOTION_MAX = 150;

/** Hard stop on cooling after a drag, however slowly the simulation settles. */
export const REHEAT_COOL_CAP_MS = 1500;

export function buildAdjacency(edges: readonly MotionEdge[]): Map<string, string[]> {
  const adjacency = new Map<string, string[]>();
  const add = (from: string, to: string) => {
    const list = adjacency.get(from);
    if (list) list.push(to);
    else adjacency.set(from, [to]);
  };
  for (const edge of edges) {
    add(edge.source, edge.target);
    add(edge.target, edge.source);
  }
  return adjacency;
}

export type Neighbourhood = {
  /** Nodes the simulation may move, including the dragged node itself. */
  simIds: string[];
  /** Nodes bordering the sim set, held FIXED so forces cannot travel past them. */
  pinnedIds: string[];
};

/**
 * The bounded region a drag is allowed to disturb.
 *
 * Two hops by default: one hop alone barely reads as "the graph responded",
 * while three routinely engulfs a hub's entire component. If two hops exceeds
 * the cap the walk falls back to one, and only if THAT still exceeds it does it
 * truncate - so the region stays a whole neighbourhood rather than an arbitrary
 * slice whenever possible.
 *
 * The pinned ring is what makes this local rather than a whole-graph
 * simulation in disguise: boundary nodes are included in the force computation
 * so the sim set feels a realistic pull from its surroundings, but they never
 * move, so nothing propagates beyond them.
 *
 * Deterministic: BFS order, and ties broken by id, so the same drag disturbs
 * the same nodes every time.
 */
export function reheatNeighbourhood(
  originId: string,
  adjacency: Map<string, string[]>,
  cap: number = LIVE_MOTION_MAX,
): Neighbourhood {
  const walk = (maxHops: number): string[] => {
    const seen = new Set<string>([originId]);
    const order = [originId];
    let frontier = [originId];
    for (let hop = 0; hop < maxHops; hop += 1) {
      const next: string[] = [];
      for (const current of [...frontier].sort()) {
        for (const neighbour of [...(adjacency.get(current) ?? [])].sort()) {
          if (seen.has(neighbour)) continue;
          seen.add(neighbour);
          order.push(neighbour);
          next.push(neighbour);
        }
      }
      frontier = next;
    }
    return order;
  };

  let simIds = walk(2);
  if (simIds.length > cap) simIds = walk(1);
  if (simIds.length > cap) simIds = simIds.slice(0, cap);

  const inSim = new Set(simIds);
  const pinned = new Set<string>();
  for (const id of simIds) {
    for (const neighbour of adjacency.get(id) ?? []) {
      if (!inSim.has(neighbour)) pinned.add(neighbour);
    }
  }
  return { simIds, pinnedIds: [...pinned].sort() };
}
