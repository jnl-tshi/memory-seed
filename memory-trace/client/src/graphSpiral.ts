/**
 * Long lifecycle chains, and the radius each of their members should sit at.
 *
 * A chain of `evolves`/`replaces` edges is a story told in order, and a force
 * layout draws it as a wandering thread that crosses the map and reads as
 * nothing in particular. Winding it into a spiral - oldest at the centre,
 * newest on the outside - makes the thread compact AND makes it carry time,
 * which the graph otherwise cannot show at all (JNL, 2026-07-28).
 *
 * THE SPIRAL IS NOT DRAWN. Nothing here positions anything. This module answers
 * one question - "which nodes belong to a long chain, and at what radius from
 * that chain's own centre" - and a radial spring in the simulation does the
 * rest. The spiral emerges: members sit at increasing radii around a shared
 * centre while the link force still pulls consecutive members together, and the
 * only shape satisfying both is a winding one.
 *
 * WHAT PROTECTS THE DENSE SECTIONS is that this returns an assignment for chain
 * members and NOBODY ELSE. A node outside a qualifying chain gets no radial
 * force at all - not a weak one - so the crowded middle of the graph is
 * governed by exactly the forces it was before.
 */

export interface SpiralNodeLike {
  id: string;
  /** ISO timestamp or date. Missing sorts oldest, so a chain still orders. */
  datetime?: string | null;
  date?: string | null;
}

export interface SpiralEdgeLike {
  source: string;
  target: string;
  /** The renderer's edge payload spells this `type`, not `kind`. */
  type?: string | null;
}

/** Edge kinds that make a chain. `related` is excluded and that is the point:
 *  it is symmetric and dense, and treating it as chain evidence would sweep
 *  most of the corpus into one component that is not a story at all. */
export const CHAIN_EDGE_KINDS = new Set(["evolves", "replaces", "continuity"]);

/** Shorter runs are a fork in a workstream, not a thread worth winding.
 *
 *  RAISED FROM 5 TO 8 after measuring. A chain's centre is its own members'
 *  centroid, so for five nodes the centre sits among them and "inner versus
 *  outer" is barely defined: the long chain settled 89% age-ordered with a 736
 *  degree sweep, while the five- and six-node chains came out 40-50% ordered -
 *  no better than chance. The force earns its place on long threads, which is
 *  what it was asked for; applying it to short ones bought noise. */
export const MIN_CHAIN_LENGTH = 8;

/** The node with the most neighbours. A path tops out at 2; allowing 3 tolerates
 *  a single side branch without admitting a hub.
 *
 *  MAX degree, not mean, and the difference is the whole test. Mean degree
 *  cannot distinguish a star from a path: any tree has mean degree 2(n-1)/n,
 *  just under 2, so a 30-spoke hub scores 1.94 and a straight chain scores 1.67.
 *  A first version used the mean and would have wound every hub in the corpus
 *  into a ring; the unit test for a star is what caught it. */
export const MAX_CHAIN_DEGREE = 3;

/** A second, independent guard against DENSE components. A tree of any shape has
 *  mean degree under 2, so anything above that carries extra edges - cycles and
 *  cross-links - and is a mesh rather than a thread. */
export const MAX_CHAIN_MEAN_DEGREE = 2.4;

/** Where a chain's innermost (oldest) member sits, in graph units. */
export const SPIRAL_INNER_RADIUS = 46;

/** How much further out each successive member sits. Larger unwinds the
 *  spiral toward a ring; smaller tightens it toward a knot. */
export const SPIRAL_RADIUS_STEP = 30;

export interface SpiralAssignment {
  /** Which chain this node belongs to - the chain's oldest member's id. */
  chain: string;
  /** Distance this node should hold from its chain's centre. */
  radius: number;
  /** 0-based position along the SPINE, oldest first. A spur inherits its
   *  anchor's index - it sits at the same point in the story. */
  index: number;
  /**
   * True for a node hanging OFF the spine rather than lying along it.
   *
   * A spur is pushed outward past its anchor and is excluded from the chain's
   * centroid. Both matter: a terminating side-node that joined the centroid
   * dragged the centre toward itself and bent the spiral out of shape, and
   * without the extra radius it sat wherever the link force happened to leave
   * it, often INSIDE the coil where it read as part of the sequence.
   */
  spur: boolean;
}

/**
 * The longest path through a component - its spine.
 *
 * Two breadth-first passes: the farthest node from any start is an endpoint of
 * a longest path, and the farthest node from THAT is the other end. Exact on a
 * tree, and these components are near-trees by construction (mean degree <= 2.4),
 * so a cycle can only make it slightly short - never wrong in a way that
 * matters, since anything off the returned path is treated as a spur.
 */
export function chainSpine(members: readonly string[], adjacency: ReadonlyMap<string, Set<string>>): string[] {
  if (members.length < 2) return [...members];
  const walk = (from: string) => {
    const previous = new Map<string, string | null>([[from, null]]);
    const queue = [from];
    let last = from;
    for (let head = 0; head < queue.length; head += 1) {
      const id = queue[head];
      last = id;
      for (const next of adjacency.get(id) ?? []) {
        if (previous.has(next)) continue;
        previous.set(next, id);
        queue.push(next);
      }
    }
    return { last, previous };
  };
  const first = walk(members[0]).last;
  const { last, previous } = walk(first);
  const path: string[] = [];
  for (let at: string | null | undefined = last; at != null; at = previous.get(at)) path.push(at);
  return path;
}

const timeOf = (node: SpiralNodeLike): string => node.datetime || node.date || "";

/**
 * Members of every qualifying chain, oldest first.
 *
 * A chain is a connected component over lifecycle edges only, at least
 * `MIN_CHAIN_LENGTH` long, and path-like rather than hub-like. Ordering is by
 * timestamp rather than by walking the edges: a component may branch, and a
 * walk would have to pick an arbitrary path through it, whereas time is total
 * and is the axis the spiral is meant to encode.
 */
export function spiralChains(
  nodes: readonly SpiralNodeLike[],
  edges: readonly SpiralEdgeLike[],
  options?: { minLength?: number; maxMeanDegree?: number; maxDegree?: number },
): string[][] {
  const minLength = options?.minLength ?? MIN_CHAIN_LENGTH;
  const maxMeanDegree = options?.maxMeanDegree ?? MAX_CHAIN_MEAN_DEGREE;
  const maxDegree = options?.maxDegree ?? MAX_CHAIN_DEGREE;
  const known = new Map(nodes.map((node) => [node.id, node]));
  const adjacency = new Map<string, Set<string>>();
  let kept = 0;
  for (const edge of edges) {
    if (edge.type && !CHAIN_EDGE_KINDS.has(edge.type)) continue;
    if (!known.has(edge.source) || !known.has(edge.target) || edge.source === edge.target) continue;
    kept += 1;
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  }
  if (!kept) return [];

  const seen = new Set<string>();
  const chains: string[][] = [];
  for (const start of adjacency.keys()) {
    if (seen.has(start)) continue;
    const component: string[] = [];
    const queue = [start];
    seen.add(start);
    while (queue.length) {
      const id = queue.pop()!;
      component.push(id);
      for (const next of adjacency.get(id) ?? []) {
        if (seen.has(next)) continue;
        seen.add(next);
        queue.push(next);
      }
    }
    if (component.length < minLength) continue;
    const degrees = component.map((id) => adjacency.get(id)?.size ?? 0);
    if (Math.max(...degrees) > maxDegree) continue;
    if (degrees.reduce((a, b) => a + b, 0) / component.length > maxMeanDegree) continue;
    component.sort((a, b) => {
      const ta = timeOf(known.get(a)!);
      const tb = timeOf(known.get(b)!);
      return ta === tb ? a.localeCompare(b) : ta.localeCompare(tb);
    });
    chains.push(component);
  }
  return chains;
}

/**
 * id -> the chain and radius the simulation should hold it at.
 *
 * Radius grows with AGE ORDER, not with the raw timestamp, so an evenly wound
 * spiral is produced whether a chain spans a day or six months. A gap-scaled
 * radius would leave a quiet fortnight as a visible void, which reads as a
 * missing node rather than as elapsed time.
 */
export function spiralAssignments(
  chains: readonly (readonly string[])[],
  edges: readonly SpiralEdgeLike[] = [],
  options?: { innerRadius?: number; step?: number },
): Map<string, SpiralAssignment> {
  const innerRadius = options?.innerRadius ?? SPIRAL_INNER_RADIUS;
  const step = options?.step ?? SPIRAL_RADIUS_STEP;
  const out = new Map<string, SpiralAssignment>();
  for (const members of chains) {
    if (!members.length) continue;
    const chain = members[0];
    const inChain = new Set(members);
    const adjacency = new Map<string, Set<string>>();
    for (const edge of edges) {
      if (edge.type && !CHAIN_EDGE_KINDS.has(edge.type)) continue;
      if (!inChain.has(edge.source) || !inChain.has(edge.target) || edge.source === edge.target) continue;
      if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
      if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
      adjacency.get(edge.source)!.add(edge.target);
      adjacency.get(edge.target)!.add(edge.source);
    }
    // With no edges given, every member is treated as spine - the pre-spine
    // behaviour, and what a caller asking only about radii wants.
    let spine = adjacency.size ? chainSpine(members, adjacency) : [...members];
    // Orient oldest-first. `members` arrives in age order, so whichever end of
    // the spine appears earlier there is the older one.
    if (spine.length > 1 && members.indexOf(spine[0]) > members.indexOf(spine[spine.length - 1])) {
      spine = spine.reverse();
    }
    const seatOf = new Map<string, number>();
    spine.forEach((id, index) => {
      seatOf.set(id, index);
      out.set(id, { chain, radius: innerRadius + index * step, index, spur: false });
    });
    // Anything off the spine hangs off its nearest spine node, one step further
    // out - so it points AWAY from the centre instead of sitting inside the coil.
    for (const id of members) {
      if (seatOf.has(id)) continue;
      let anchorIndex = 0;
      for (const neighbour of adjacency.get(id) ?? []) {
        const seat = seatOf.get(neighbour);
        if (seat !== undefined) {
          anchorIndex = seat;
          break;
        }
      }
      out.set(id, { chain, radius: innerRadius + (anchorIndex + 1) * step, index: anchorIndex, spur: true });
    }
  }
  return out;
}

/** Radians between consecutive members when a chain is first laid out. About
 *  100 degrees, so a chain of 5 completes more than one turn and the winding
 *  direction is unambiguous from the start. */
export const SPIRAL_ANGLE_STEP = 1.75;

/**
 * Where a chain member should START, given its chain's centre.
 *
 * The radial spring fixes how FAR a node sits from its centre and says nothing
 * about WHERE around it - so two members can settle with their radii swapped
 * and the chain winds inward, newest at the middle. Measured on the real corpus
 * before this existed: of five chains, three ordered correctly and two came out
 * inverted, which is exactly the coin-flip you would expect from an unconstrained
 * angle.
 *
 * A force layout keeps the topology it starts with, so seeding the angle settles
 * it. This is not a layout - the simulation still moves every node - it is an
 * initial condition that makes the CORRECT winding the one the springs then
 * maintain.
 */
export function spiralSeedOffsets(
  assignments: ReadonlyMap<string, SpiralAssignment>,
  options?: { angleStep?: number },
): Map<string, { dx: number; dy: number }> {
  const angleStep = options?.angleStep ?? SPIRAL_ANGLE_STEP;
  const out = new Map<string, { dx: number; dy: number }>();
  for (const [id, seat] of assignments) {
    // A spur takes its ANCHOR's angle - `index` is the anchor's seat - and its
    // own larger radius, so it starts on the same ray, further out. That is
    // what "points away from the centre" means geometrically, and seeding it
    // there is what stops the link force parking it inside the coil.
    const angle = seat.index * angleStep;
    out.set(id, { dx: Math.cos(angle) * seat.radius, dy: Math.sin(angle) * seat.radius });
  }
  return out;
}
