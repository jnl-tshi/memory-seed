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
  /** 0-based position in age order, oldest first. Exposed for tests and tuning. */
  index: number;
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
  options?: { innerRadius?: number; step?: number },
): Map<string, SpiralAssignment> {
  const innerRadius = options?.innerRadius ?? SPIRAL_INNER_RADIUS;
  const step = options?.step ?? SPIRAL_RADIUS_STEP;
  const out = new Map<string, SpiralAssignment>();
  for (const members of chains) {
    if (!members.length) continue;
    const chain = members[0];
    members.forEach((id, index) => {
      out.set(id, { chain, radius: innerRadius + index * step, index });
    });
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
    const angle = seat.index * angleStep;
    out.set(id, { dx: Math.cos(angle) * seat.radius, dy: Math.sin(angle) * seat.radius });
  }
  return out;
}
