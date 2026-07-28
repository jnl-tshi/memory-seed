/**
 * Long chains, and the radius each of their members should sit at.
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
 *
 * TWO KIND-GROUPS, TRIED IN PRIORITY ORDER (JNL, 2026-07-28: a chain drawn in
 * `related` edges did not spiral, and should). Lifecycle edges (`evolves`,
 * `replaces`, `continuity`) are tried first; `related` is tried second, over
 * only whatever nodes lifecycle chains did not already claim. They are NEVER
 * merged into one connectivity graph - measured, and merging produces a single
 * ~500-node component that the degree caps correctly reject, because many
 * nodes carry both kinds of edge to overlapping neighbours. Evaluated on its
 * own, `related` looks nothing like that: a dominant blob plus several
 * genuinely path-shaped threads. See `CHAIN_KIND_GROUPS` and
 * `allSpiralAssignments`, the entry point that applies the priority order.
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

/**
 * Lifecycle edges: authored, directional, the strongest chain evidence.
 * Renamed from `CHAIN_EDGE_KINDS` when `related` was added as a SEPARATE,
 * lower-priority group below - see `CHAIN_KIND_GROUPS`.
 */
export const LIFECYCLE_CHAIN_KINDS = new Set(["evolves", "replaces", "continuity"]);

/**
 * `related` on its own, never merged with lifecycle edges into one connectivity
 * graph. Merging was tried and measured: on the live corpus it produces ONE
 * 496-node component (because many nodes carry both kinds of edge to
 * overlapping neighbours), which the degree caps correctly reject - so the
 * merge bought nothing. Evaluated as its OWN graph, `related` looks completely
 * different: one 405-node blob (still correctly rejected) plus several
 * genuinely path-shaped components, including a 15-node chain at max degree 3
 * / mean degree 1.87 - well inside the same bounds lifecycle chains meet.
 * `related` is symmetric and dense in aggregate, but a specific thread of it
 * can still be a real story; the two only look the same when pooled together.
 */
export const RELATED_CHAIN_KINDS = new Set(["related"]);

/**
 * Kind-groups tried in PRIORITY order. Earlier groups claim nodes first; a
 * later group's connectivity is computed only among what is left over, so a
 * node with an authored lifecycle edge always keeps that home and a `related`
 * thread never reassigns it. See `allSpiralAssignments`, the entry point that
 * actually applies this order - `spiralChains`/`spiralAssignments` take one
 * group at a time and know nothing about priority themselves.
 */
export const CHAIN_KIND_GROUPS: readonly (ReadonlySet<string>)[] = [LIFECYCLE_CHAIN_KINDS, RELATED_CHAIN_KINDS];

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

/**
 * The floor on how well a chain's TOPOLOGY has to track actual chronology
 * before it is allowed to spiral, measured as the fraction of member pairs
 * whose spine order agrees with their timestamp order (the better of the two
 * directions, since which end is "first" is not yet decided at this point).
 *
 * Size and degree caps say a component is SHAPED like a thread. They say
 * nothing about whether walking that thread actually walks through time -
 * true for lifecycle edges by construction (`evolves`/`replaces` are authored
 * FROM an older entry TO a newer one, so topology and chronology are the same
 * fact twice), but not for `related`, which records topical similarity with no
 * temporal direction at all.
 *
 * Measured directly on the corpus (2026-07-28, JNL circled a chain that was
 * not spiraling): a lifecycle chain scored 95% concordant, and one candidate
 * `related` chain scored 100% - but a second, the one actually circled, scored
 * only 76%, and its rendered position was WORSE after the simulation settled
 * (53%) than its topology alone predicted. Winding it would draw a spiral that
 * gets "the middle is older" wrong on roughly a quarter of its members - not a
 * rough approximation of the timeline, a materially misleading one, which is
 * worse than the plain unwound line it replaces. 0.85 sits with real margin on
 * both sides of the measured cases: comfortably above the 76% that failed,
 * comfortably below the 95%/100% that passed.
 */
export const MIN_SPINE_CONCORDANCE = 0.85;

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
 * What fraction of member PAIRS agree between the spine's walked order and
 * their actual timestamp order - the better of the two directions, since
 * which end reads as "first" is not decided yet at this point.
 *
 * This is what `MIN_SPINE_CONCORDANCE` gates on. 1.0 means the topology and
 * the calendar tell the same story; 0.5 means they are unrelated; a lifecycle
 * chain scores near 1.0 by construction, a `related` chain scores whatever the
 * corpus happens to give it.
 */
function spineConcordance(spine: readonly string[], known: ReadonlyMap<string, SpiralNodeLike>): number {
  if (spine.length < 2) return 1;
  const times = spine.map((id) => timeOf(known.get(id)!));
  let forward = 0;
  let total = 0;
  for (let i = 0; i < times.length; i += 1) {
    for (let j = i + 1; j < times.length; j += 1) {
      total += 1;
      if (times[j] >= times[i]) forward += 1;
    }
  }
  return total ? Math.max(forward, total - forward) / total : 1;
}

/**
 * Members of every qualifying chain, oldest first, for ONE kind-group.
 *
 * A chain is a connected component over the given edge `kinds` (lifecycle
 * edges unless told otherwise - see `CHAIN_KIND_GROUPS` for running several
 * groups in priority order), at least `MIN_CHAIN_LENGTH` long, and path-like
 * rather than hub-like. Ordering is by timestamp rather than by walking the
 * edges: a component may branch, and a walk would have to pick an arbitrary
 * path through it, whereas time is total
 * and is the axis the spiral is meant to encode.
 */
export function spiralChains(
  nodes: readonly SpiralNodeLike[],
  edges: readonly SpiralEdgeLike[],
  options?: {
    minLength?: number;
    maxMeanDegree?: number;
    maxDegree?: number;
    kinds?: ReadonlySet<string>;
    minConcordance?: number;
  },
): string[][] {
  const minLength = options?.minLength ?? MIN_CHAIN_LENGTH;
  const maxMeanDegree = options?.maxMeanDegree ?? MAX_CHAIN_MEAN_DEGREE;
  const maxDegree = options?.maxDegree ?? MAX_CHAIN_DEGREE;
  const kinds = options?.kinds ?? LIFECYCLE_CHAIN_KINDS;
  const minConcordance = options?.minConcordance ?? MIN_SPINE_CONCORDANCE;
  const known = new Map(nodes.map((node) => [node.id, node]));
  const adjacency = new Map<string, Set<string>>();
  let kept = 0;
  for (const edge of edges) {
    if (edge.type && !kinds.has(edge.type)) continue;
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
    // Shape alone is not enough: a component can be perfectly path-like and
    // still not track time, because only lifecycle edges are authored with a
    // direction. `adjacency` already contains only this component's own
    // same-kind edges (components partition the graph, so no neighbour of a
    // member can lie outside it), so the spine walked here is exactly the one
    // `spiralAssignments` will walk again later - duplicated on purpose rather
    // than threading a cache through two functions with different callers.
    if (spineConcordance(chainSpine(component, adjacency), known) < minConcordance) continue;
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
  options?: { innerRadius?: number; step?: number; kinds?: ReadonlySet<string> },
): Map<string, SpiralAssignment> {
  const innerRadius = options?.innerRadius ?? SPIRAL_INNER_RADIUS;
  const step = options?.step ?? SPIRAL_RADIUS_STEP;
  const kinds = options?.kinds ?? LIFECYCLE_CHAIN_KINDS;
  const out = new Map<string, SpiralAssignment>();
  for (const members of chains) {
    if (!members.length) continue;
    const chain = members[0];
    const inChain = new Set(members);
    const adjacency = new Map<string, Set<string>>();
    for (const edge of edges) {
      if (edge.type && !kinds.has(edge.type)) continue;
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

/**
 * The seats for every kind-group, tried in PRIORITY order and merged.
 *
 * This is the entry point a caller should use - `spiralChains`/
 * `spiralAssignments` know about only one kind-group each and nothing about
 * priority between them.
 *
 * Each group's connectivity is computed only among nodes the EARLIER groups
 * did not already claim. A node with an authored lifecycle edge always keeps
 * that home; a `related` thread never reassigns it, and its own component is
 * whatever remains connected once such nodes are removed from consideration -
 * which may be smaller than the raw `related` component, or split in two if a
 * claimed node was the only thing joining two halves. That is the intended
 * behaviour, not a bug: a `related` story yields to a stronger, authored one
 * wherever they overlap, rather than the two silently fighting over one seat.
 */
export function allSpiralAssignments(
  nodes: readonly SpiralNodeLike[],
  edges: readonly SpiralEdgeLike[],
  options?: {
    groups?: readonly (ReadonlySet<string>)[];
    minLength?: number;
    maxMeanDegree?: number;
    maxDegree?: number;
    minConcordance?: number;
    innerRadius?: number;
    step?: number;
  },
): Map<string, SpiralAssignment> {
  const groups = options?.groups ?? CHAIN_KIND_GROUPS;
  const claimed = new Set<string>();
  const out = new Map<string, SpiralAssignment>();
  for (const kinds of groups) {
    const available = nodes.filter((node) => !claimed.has(node.id));
    const chains = spiralChains(available, edges, { ...options, kinds });
    const seats = spiralAssignments(chains, edges, { ...options, kinds });
    for (const [id, seat] of seats) {
      out.set(id, seat);
      claimed.add(id);
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
