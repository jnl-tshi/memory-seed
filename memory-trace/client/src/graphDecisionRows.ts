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

/**
 * The synthetic id of a group's visible circle.
 *
 * A second element rather than styling the container, because Cytoscape draws a
 * COMPOUND PARENT as a rectangle whatever its `shape` says — verified live
 * 2026-07-27 with `shape: ellipse` reported by `style()` and a square on screen.
 * So the two jobs are split: the compound parent still carries CONTAINMENT (the
 * structural channel, invisible), and this ordinary child node carries the
 * DRAWING. It is a sibling of the anchor and the rows, positioned on the anchor,
 * sized to enclose the ring — see `haloDiameter`.
 */
export function decisionHaloId(entryId: string): string {
  return `dhalo:${entryId}`;
}

export type DecisionGroup = {
  /** The entry node id (also the group's own anchor child). */
  anchorId: string;
  /** Its rendered decision-row node ids, in ASCENDING ORDINAL order. */
  rowIds: string[];
  /** The synthetic compound-parent id every member is filed under. */
  groupId: string;
};

/**
 * The numeric ordinal in a decision-row id (`...#decisions/d12-slug` -> 12).
 *
 * Numeric, not lexical: `d10` sorts after `d9`, the same rule trailModel already
 * applies to Trail rows. Anything unparseable sorts last rather than throwing —
 * a row id that does not match the convention is a payload problem, not a reason
 * to drop a decision off the ring.
 */
function ordinalOf(rowId: string): number {
  const match = /#decisions\/d(\d+)/.exec(rowId);
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
}

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
  // Ordinal order, so the ring runs d1, d2, d3 clockwise from the top whatever
  // order the payload listed them in. Slot position is then readable as the
  // decision's place in the entry.
  for (const group of groups.values()) group.rowIds.sort((left, right) => ordinalOf(left) - ordinalOf(right));
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
 * The id whose connectedness decides whether this node is drawn.
 *
 * For a decision row that is its ANCHOR, never itself. A group appears whole or
 * not at all: the Orphans filter asks "does this ENTRY have an authored
 * relationship", and a decision inside a shown entry is not an orphan just
 * because no link names it — it is a decision that was made. Reading the row's
 * own degree hid exactly the rows that made a group complete, so a 4-decision
 * entry drew a ring of 1 (found live 2026-07-27, with Orphans off).
 */
export function visibilityIdFor(id: string): string {
  return isDecisionRowId(id) ? anchorEntryIdFor(id) : id;
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

/** How far a decision row sits from its anchor's centre, in graph units. */
export const SATELLITE_RADIUS = 46;

/**
 * Arc a row needs along the ring: its own diameter plus a clear gap.
 *
 * Used only to GROW the radius when a many-decision entry would otherwise crowd
 * its ring — the spacing stays equal either way.
 */
const MIN_ROW_ARC = 26;

/** Where the ring points when nothing on screen gives it a reason to turn. */
const DEFAULT_PHASE = -Math.PI / 2;

/** Air between the outermost row and the circle drawn around it. */
const HALO_CLEARANCE = 15;

/**
 * How far this entry's rows sit from it, given how many there are.
 *
 * Shared by the row placement and the circle drawn around them, so the two can
 * never disagree about where the ring is.
 */
export function ringRadius(rowCount: number, radius = SATELLITE_RADIUS): number {
  if (rowCount <= 0) return radius;
  return Math.max(radius, (rowCount * MIN_ROW_ARC) / (Math.PI * 2));
}

/** Diameter of the circle that encloses one entry's ring of decisions. */
export function haloDiameter(rowCount: number, radius = SATELLITE_RADIUS): number {
  return 2 * (ringRadius(rowCount, radius) + HALO_CLEARANCE);
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
 * The rows are spread EQUALLY around the anchor (JNL, 2026-07-27) in ordinal
 * order, so a group reads as a clock face: the gap between neighbours is always
 * 360/N and nothing on screen can change it.
 *
 * The ring is RIGID BUT FREE TO ROTATE (JNL, 2026-07-27). Equal spacing is the
 * hard constraint; the ring's phase is the one degree of freedom left, and it is
 * fitted to the group's own decision edges by `ringPhase` - so a row ends up on
 * the side its relative is on without any pair of rows ever crowding. An earlier
 * version aimed each row independently, which bought the same direction hint by
 * spending the spacing; and a version pinned at 12 o'clock kept the spacing but
 * threw the direction away. Rotating a rigid ring keeps both.
 *
 * The radius grows only when equal spacing would put the rows closer than
 * `MIN_ROW_ARC` apart, so a 3-decision group and a 12-decision group both read
 * cleanly without the common case drifting away from its anchor.
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
  if (!rowIds.length) return positions;
  const step = (Math.PI * 2) / rowIds.length;
  const spread = ringRadius(rowIds.length, radius);
  const phase = ringPhase({ rowIds, anchor, counterparts });
  rowIds.forEach((rowId, index) => {
    const angle = phase + index * step;
    positions.set(rowId, { x: anchor.x + Math.cos(angle) * spread, y: anchor.y + Math.sin(angle) * spread });
  });
  return positions;
}

/**
 * The rotation that best points each row at its own relatives.
 *
 * With slots fixed at `phase + i * step`, the phase that maximises
 * `sum(cos(phase + i * step - target_i))` is the closed form below - the circular
 * mean of each row's target direction less the slot it occupies. Exact, one pass,
 * no search, and it depends only on positions, so it reproduces across loads.
 *
 * Falls back to `DEFAULT_PHASE` (straight up) when no row has a counterpart on
 * screen, or when the targets cancel out exactly - two rows pulling opposite ways
 * leave the rotation genuinely undetermined, and an arbitrary answer there would
 * make the ring jitter between equally good positions.
 */
export function ringPhase(options: {
  rowIds: readonly string[];
  anchor: Point;
  counterparts?: ReadonlyMap<string, readonly Point[]>;
}): number {
  const { rowIds, anchor, counterparts } = options;
  if (!rowIds.length || !counterparts?.size) return DEFAULT_PHASE;
  const step = (Math.PI * 2) / rowIds.length;
  let sumSin = 0;
  let sumCos = 0;
  rowIds.forEach((rowId, index) => {
    let dx = 0;
    let dy = 0;
    for (const target of counterparts.get(rowId) ?? []) {
      dx += target.x - anchor.x;
      dy += target.y - anchor.y;
    }
    if (Math.sqrt(dx * dx + dy * dy) < 1e-6) return;
    const wanted = Math.atan2(dy, dx) - index * step;
    sumSin += Math.sin(wanted);
    sumCos += Math.cos(wanted);
  });
  if (Math.sqrt(sumSin * sumSin + sumCos * sumCos) < 1e-6) return DEFAULT_PHASE;
  return Math.atan2(sumSin, sumCos);
}
