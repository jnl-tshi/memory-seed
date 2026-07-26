// Decision rows in the force graph: containment WITHOUT a fifth edge kind.
//
// Background (0_NEXT_STEPS item 8, decided by JNL 2026-07-26). The Graph can ask
// the server for per-decision rows (`include_decisions`, `decision_row_scope:
// "linked"`), which is what gives a decision-level edge like
// `B:d2 evolves A:d1` a real endpoint instead of leaving both entries drawn as
// orphans. The open question was how an anchor entry and its own decision rows
// stay together in a force layout, since a timeline gets that from adjacency and
// a graph gets it from nothing.
//
// The answer is NOT an edge. The four edge kinds (related_entries, supersedes,
// evolves, continuity) are AUTHORED SEMANTIC CLAIMS: forward-only, acyclic,
// dangling-ref validated, and validated as such at write time - which is exactly
// why `intra-entry-decision-ref` is an authoring ERROR (an entry and its own
// decisions are contemporaneous, so no forward-only claim between them can
// exist). Anchor-to-row containment is DERIVED and structural. Filing it in the
// edge set would put a derived fact in a channel defined as authored claims and
// force every edge-kind consumer to learn an exclusion.
//
// So containment travels through a structural channel: a `parent` field on the
// rendered node, i.e. a Cytoscape COMPOUND node. The group is a synthetic
// container holding the anchor AND its rows as siblings, never the anchor
// itself as the parent - see `decisionGroupId`.
//
// The pure geometry and set rules live here so they can be unit tested without a
// DOM or a Cytoscape instance, the same reason graphLayout.ts exists.
import type { Point } from "./graphLayout";
import type { GraphEdgeLike } from "./graphLayout";

/**
 * The separator in a decision row's node id: `{entry_id}#decisions/{dN}-{slug}`.
 *
 * This is the ratified decision-identity convention (an ADR-level decision is
 * `(entry_id, dN)`), and the same string TrailWorkspace/trailModel already test
 * against - one convention, not two.
 */
export const DECISION_ID_MARK = "#decisions/";

/** Is this node id a decision row rather than a whole entry? */
export function isDecisionRowId(id: string): boolean {
  return id.includes(DECISION_ID_MARK);
}

/**
 * The entry a decision-row id belongs to; the id unchanged for an entry.
 *
 * Same derivation the Inspector already uses for decision-level refs
 * (`otherId.split("#")[0]`), kept in one place now that two surfaces need it.
 */
export function anchorEntryIdFor(id: string): string {
  return id.split("#")[0];
}

/**
 * The synthetic compound-parent id for one entry's decision group.
 *
 * A separate container node, NOT the anchor itself, for two reasons:
 *
 *  1. Cytoscape DERIVES a compound parent's position from the bounding box of
 *     its children. Making the anchor the parent would take its position out of
 *     the simulation's hands - and this graph's simulation writes every node's
 *     position on every tick.
 *  2. The anchor is a first-class entry node: a circle sized by degree, filled
 *     by its topic mixture, rimmed when its community is authored. A parent node
 *     is an auto-sized box, so the entry would lose the whole visual vocabulary
 *     the rest of the map reads in.
 *
 * As a CHILD of the container the anchor keeps both: children are freely
 * positionable, and the container's box simply wraps wherever anchor and rows
 * are. The `dgroup:` prefix cannot collide with an entry id (`mse_`/`ms-`) or a
 * row id (which always contains `#decisions/`).
 */
export function decisionGroupId(entryId: string): string {
  return `dgroup:${entryId}`;
}

export type DecisionGroup = {
  /** The entry node id (also the group's own anchor child). */
  anchorId: string;
  /** Its rendered decision-row node ids, in payload order. */
  rowIds: string[];
  /** The synthetic compound-parent id every member is filed under. */
  groupId: string;
};

type NodeLike = { id: string };

/**
 * Group the payload's decision rows under their anchor entries.
 *
 * A row whose anchor is absent from the rendered set is dropped rather than
 * given a container of its own: an orphaned decision row would claim to be an
 * entry, and the anchor is what carries the title and timestamp a reader needs.
 * Under `decision_row_scope: "linked"` the anchor is always in the payload (the
 * server expands rows from entries it is already returning), so this is a guard,
 * not a routine case.
 */
export function decisionGroups(nodes: readonly NodeLike[]): Map<string, DecisionGroup> {
  const present = new Set(nodes.map((node) => node.id));
  const groups = new Map<string, DecisionGroup>();
  for (const node of nodes) {
    if (!isDecisionRowId(node.id)) continue;
    const anchorId = anchorEntryIdFor(node.id);
    if (!present.has(anchorId)) continue;
    const group = groups.get(anchorId) ?? { anchorId, rowIds: [], groupId: decisionGroupId(anchorId) };
    group.rowIds.push(node.id);
    groups.set(anchorId, group);
  }
  return groups;
}

/**
 * Which rendered node each node id is filed under, or undefined for a node that
 * belongs to no group. Feeds Cytoscape's `data.parent` directly.
 */
export function parentIdsFor(groups: ReadonlyMap<string, DecisionGroup>): Map<string, string> {
  const parents = new Map<string, string>();
  for (const group of groups.values()) {
    parents.set(group.anchorId, group.groupId);
    for (const rowId of group.rowIds) parents.set(rowId, group.groupId);
  }
  return parents;
}

/**
 * Edge endpoints, with every decision-row endpoint ALSO crediting its anchor.
 *
 * The Orphans filter asks "does this entry have an authored relationship". Once
 * decision rows are on, an entry whose only ties are decision-level does - the
 * tie terminates on its row. Reading raw endpoints would answer no and hide the
 * anchor while keeping its rows, which is both wrong and structurally broken
 * (a group with no anchor). This is a rule about VISIBILITY, and deliberately
 * not an edge: nothing entry-level is emitted, drawn, or exported.
 */
export function connectedIdsWithDecisionAnchors(edges: readonly GraphEdgeLike[]): Set<string> {
  const ids = new Set<string>();
  for (const edge of edges) {
    for (const endpoint of [edge.source, edge.target]) {
      ids.add(endpoint);
      if (isDecisionRowId(endpoint)) ids.add(anchorEntryIdFor(endpoint));
    }
  }
  return ids;
}

/** Golden angle - successive fan slots never line up into spokes. */
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/** How far a decision row sits from its anchor's centre, in graph units. */
export const SATELLITE_RADIUS = 46;

/** Closest two rows of one entry may sit, measured as an angle at the anchor. */
const MIN_SEPARATION = Math.PI / 5;

/** Fold an angle into (-pi, pi] so two angles can be compared by difference. */
function normalise(angle: number): number {
  let value = angle;
  while (value <= -Math.PI) value += Math.PI * 2;
  while (value > Math.PI) value -= Math.PI * 2;
  return value;
}

/**
 * Where one entry's decision rows sit, given where its anchor sits.
 *
 * Rows are NOT simulation participants. Their position is derived from the
 * anchor's every time the anchor's changes, which makes containment true by
 * construction: a row cannot drift out of its group, no leash force is needed,
 * and - the property that matters most here - turning decision rows ON does not
 * move a single anchor, because the rows exert no force on anything. The map a
 * reader had is still the map they have, with decisions added to it.
 *
 * Direction carries information where it can: a row with decision edges points
 * at the mean direction of its counterparts, so the line to its relative leaves
 * the group on the side that relative is on. With no counterpart on screen (or a
 * counterpart sitting exactly on the anchor) it falls back to its fan slot,
 * which depends only on the row's index - so the arrangement is deterministic
 * and reproduces across loads.
 */
export function satellitePositions(options: {
  rowIds: readonly string[];
  anchor: Point;
  /** Counterpart positions per row: the far end of each of its decision edges. */
  counterparts?: ReadonlyMap<string, readonly Point[]>;
  radius?: number;
}): Map<string, Point> {
  const { rowIds, anchor, counterparts, radius = SATELLITE_RADIUS } = options;
  const positions = new Map<string, Point>();
  const taken: number[] = [];
  rowIds.forEach((rowId, index) => {
    // A half-slot turn on top of the index so a lone row does not sit due east
    // of its anchor, where an entry-level edge would run straight through it.
    let angle = normalise((index + 0.5) * GOLDEN_ANGLE);
    const targets = counterparts?.get(rowId) ?? [];
    let dx = 0;
    let dy = 0;
    for (const target of targets) {
      dx += target.x - anchor.x;
      dy += target.y - anchor.y;
    }
    if (Math.sqrt(dx * dx + dy * dy) > 1e-6) angle = Math.atan2(dy, dx);
    // Two rows of one entry must never coincide, and two counterparts in the
    // same direction would put them there. A row landing on top of one already
    // placed rotates away in fixed steps until it clears, so the aim survives as
    // far as it can and the rows stay legibly apart. Deterministic: the walk
    // depends only on payload order.
    for (
      let attempt = 0;
      attempt <= rowIds.length * 2 && taken.some((other) => Math.abs(normalise(other - angle)) < MIN_SEPARATION);
      attempt += 1
    ) {
      angle = normalise(angle + MIN_SEPARATION);
    }
    taken.push(angle);
    positions.set(rowId, { x: anchor.x + Math.cos(angle) * radius, y: anchor.y + Math.sin(angle) * radius });
  });
  return positions;
}
