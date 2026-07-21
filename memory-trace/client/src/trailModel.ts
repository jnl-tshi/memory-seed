// Pure Trail layout model — a faithful port of the vanilla `trailModel`
// (static/app.js:709-1008), kept framework-free so it can be unit-tested and
// cross-checked against the vanilla `window.memoryTraceDebug.trailModel` on the
// same corpus. Scope: chronological rows + day separators, branch-lane
// assignment (greedy interval packing over fork-to-merge occupancy), colours,
// fork/merge connector rows, and trunk merge dots. Lifecycle-edge arrows and
// continuity lanes are deferred to later slices and are NOT computed here.
import type { TrailResponse, TrailEvent, MergeEvent, TrailEdge } from "./api";

export const TRAIL_ROW = 30;
export const TRAIL_LANE_W = 14;
export const TRAIL_WINDOW_STEP = 60;
export const TRAIL_REL_LANES = ["supersedes", "evolves", "related"] as const;
export const TRAIL_REL_LANE_W = 12;
export const TRAIL_CORNER = 7;
export const TRAIL_REL_ZONE = TRAIL_REL_LANES.length * TRAIL_REL_LANE_W + 12;
export const TRAIL_CONT_LANE_W = 14;
export const TRAIL_CONT_ZONE_PAD = 14;
const TRAIL_CONTINUITY_KINDS = new Set(["rename", "migration", "removal"]);

// Four packs of three bright, well-separated hues. Lane 0 leads with main's
// indigo; each of the first four lanes cycles its pack across daisy-chained
// branches, deeper lanes pin to the pack's middle hue.
const TRAIL_LANE_COLOR_FAMILIES = [
  ["#6f7cff", "#3fa66a", "#d9941a"],
  ["#d94b63", "#22b8cf", "#7cb342"],
  ["#8f63e8", "#e8590c", "#18a999"],
  ["#db2777", "#3b82f6", "#16a34a"],
];

export type TrailItem = { kind: "day"; label: string } | { kind: "node"; node: TrailEvent };
export type Span = { first: number; last: number };
export type LinkRow = {
  forkRow?: number;
  mergeRow?: number;
  estimated: boolean;
  mergeLabel: string | null;
  forkLabel: string | null;
};
export type MergeDot = { row: number; sha: string; short: string; subject: string; count: number; chunkId: string };
export type ContinuityEvent = { key: string; row: number; entryId: string; kind: string; from: string; to: string | null; chainKey: string; lane: number };
export type ContinuityChain = { chainKey: string; lane: number; rows: number[]; events: ContinuityEvent[] };

export type TrailModel = {
  items: TrailItem[];
  total: number;
  rowOf: Map<string, number>;
  spans: Map<string, Span>;
  laneOf: Map<string, number>;
  colorOf: Map<string, string>;
  laneCount: number;
  linkRows: Map<string, LinkRow>;
  mergeEvents: MergeDot[];
  lifecycle: TrailEdge[];
  continuityEvents: ContinuityEvent[];
  continuityChains: ContinuityChain[];
  continuityLaneCount: number;
};

const REL_LANE_SET = new Set<string>(TRAIL_REL_LANES);

export function trailStamp(node: TrailEvent): number {
  return Date.parse(node.datetime || `${node.date}T00:00:00`) || 0;
}

export function stripTitleStamp(title: string): string {
  return String(title || "").replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*-\s*/, "");
}

// A decision row's rank within its entry group: "d1" -> 1, "d10" -> 10,
// absent -> 0. Parsed numerically because the rows in a group share one
// timestamp, so ordering falls entirely to this tiebreak - a string compare
// would put "d10" before "d2".
function decisionRank(node: TrailEvent): number {
  const match = /^d(\d+)$/.exec(node.decision_ordinal || "");
  return match ? Number(match[1]) : 0;
}

// THE trail ordering: newest first, then decision ordinal ascending (D1
// before D2..DN within an entry's group), then id for total stability.
// Exported so every consumer that orders trail nodes (the model here, the
// find bar's match list in App.tsx) shares one comparator instead of
// hand-duplicating it and drifting.
export function compareTrailNodes(a: TrailEvent, b: TrailEvent): number {
  return (
    trailStamp(b) - trailStamp(a) ||
    decisionRank(a) - decisionRank(b) ||
    String(a.id).localeCompare(String(b.id))
  );
}

// Pastel companion for decision child rows: same hue as the branch colour,
// lifted toward light and desaturated so D2..DN read as "part of D1's entry"
// rather than new events. Pure hex->HSL->hex math (this module is
// deliberately framework- and DOM-free), tuned to stay legible on both the
// warm-light and charcoal-dark themes.
export function pastelOf(hex: string): string {
  const value = hex.replace("#", "");
  const r = parseInt(value.slice(0, 2), 16) / 255;
  const g = parseInt(value.slice(2, 4), 16) / 255;
  const b = parseInt(value.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  let h = 0;
  if (delta > 0) {
    if (max === r) h = ((g - b) / delta + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / delta + 2) / 6;
    else h = ((r - g) / delta + 4) / 6;
  }
  const s = 0.42;
  const l = 0.74;
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const channel = (t: number) => {
    let x = t;
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  const toHex = (t: number) => Math.round(channel(t) * 255).toString(16).padStart(2, "0");
  return `#${toHex(h + 1 / 3)}${toHex(h)}${toHex(h - 1 / 3)}`;
}

export function buildTrailModel(trail: TrailResponse, window: number): TrailModel {
  const nodes = (trail.nodes || [])
    .filter((node) => node.entry_id)
    .sort(compareTrailNodes);
  // "N of M ENTRIES" stays honest: decision child rows are extra ROWS of one
  // entry, not entries - they inflate the item list but never this count.
  const total = nodes.filter((node) => decisionRank(node) <= 1).length;
  // Never bisect a decision group: if the window cut lands inside one (the
  // next hidden node is a decision CHILD), extend to the end of that group
  // so a bracket/pastel row never dangles without its anchor.
  let window_ = Math.min(window, nodes.length);
  while (window_ < nodes.length && decisionRank(nodes[window_]) > 1) window_ += 1;
  const visible = nodes.slice(0, window_);

  const items: TrailItem[] = [];
  let lastDay: string | null = null;
  for (const node of visible) {
    if (node.date !== lastDay) {
      items.push({ kind: "day", label: node.date });
      lastDay = node.date;
    }
    items.push({ kind: "node", node });
  }

  const rowOf = new Map<string, number>();
  items.forEach((item, index) => {
    if (item.kind === "node") rowOf.set(item.node.id, index);
  });
  const spans = new Map<string, Span>();
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const branch = item.node.branch || "";
    const span = spans.get(branch) || { first: index, last: index };
    span.first = Math.min(span.first, index);
    span.last = Math.max(span.last, index);
    spans.set(branch, span);
  });

  const mainRowList: number[] = [];
  items.forEach((item, index) => {
    if (item.kind === "node" && item.node.branch === "main") mainRowList.push(index);
  });
  const nodeRows: { row: number; stamp: number }[] = [];
  items.forEach((item, index) => {
    if (item.kind === "node") nodeRows.push({ row: index, stamp: trailStamp(item.node) });
  });
  // A commit is a TIME on the trunk, not an entry row: anchor it at a fractional
  // row linearly interpolated between the two entries whose stamps bracket it.
  const interpRow = (iso: string | null | undefined): number | undefined => {
    const t = Date.parse(iso || "");
    if (!Number.isFinite(t) || !nodeRows.length) return undefined;
    if (t >= nodeRows[0].stamp) return nodeRows[0].row;
    if (t <= nodeRows[nodeRows.length - 1].stamp) return nodeRows[nodeRows.length - 1].row;
    for (let i = 0; i < nodeRows.length - 1; i += 1) {
      const upper = nodeRows[i];
      const lower = nodeRows[i + 1];
      if (t <= upper.stamp && t >= lower.stamp) {
        const span = upper.stamp - lower.stamp;
        const frac = span > 0 ? (upper.stamp - t) / span : 0.5;
        return upper.row + frac * (lower.row - upper.row);
      }
    }
    return nodeRows[nodeRows.length - 1].row;
  };

  const mergeEvents: MergeDot[] = (trail.merges || []).flatMap((event: MergeEvent) => {
    const entryRows = (event.entry_ids || [])
      .map((id) => rowOf.get(id))
      .filter((row): row is number => row !== undefined);
    if (!entryRows.length) return [];
    const newestRow = Math.min(...entryRows);
    let row = interpRow(event.date);
    if (row === undefined) return [];
    row = Math.min(row, newestRow - 0.5);
    const newestItem = items[newestRow];
    const chunkId = newestItem && newestItem.kind === "node" ? newestItem.node.chunk_id : "";
    return [{ row, sha: event.sha, short: event.short, subject: event.subject, count: entryRows.length, chunkId }];
  });
  const mergeRowBySha = new Map(mergeEvents.map((event) => [event.sha, event.row]));

  const branchMeta = trail.branches || {};
  const linkRows = new Map<string, LinkRow>();
  // Lane occupancy runs fork-to-merge, not just a branch's own entry rows:
  // branches with disjoint entry ranges that converge on the same merge still
  // run in parallel and must not share a lane.
  const occupancy = new Map<string, Span>();
  spans.forEach((span, branch) => {
    if (branch === "" || branch === "main") return;
    const heuristicFork = mainRowList.find((row) => row > span.last);
    const heuristicMerge = [...mainRowList].reverse().find((row) => row < span.first);
    const info = branchMeta[branch];
    let forkRow: number | undefined;
    let mergeRow: number | undefined;
    let estimated = true;
    let mergeLabel: string | null = null;
    let forkLabel: string | null = null;
    if (info && !info.estimated) {
      estimated = false;
      if (info.merge) {
        mergeRow = mergeRowBySha.has(info.merge.sha) ? mergeRowBySha.get(info.merge.sha) : interpRow(info.merge.date);
        if (mergeRow !== undefined) mergeRow = Math.min(mergeRow, span.first - 0.5);
        mergeLabel = `${info.merge.short} ${info.merge.subject}`;
      }
      if (info.fork) {
        forkRow = interpRow(info.fork.date);
        if (forkRow !== undefined) forkRow = Math.max(forkRow, span.last + 0.5);
        forkLabel = info.fork.short;
      } else {
        forkRow = heuristicFork;
      }
    } else {
      forkRow = heuristicFork;
      mergeRow = heuristicMerge;
    }
    linkRows.set(branch, { forkRow, mergeRow, estimated, mergeLabel, forkLabel });
    occupancy.set(branch, {
      first: mergeRow !== undefined ? Math.min(span.first, Math.floor(mergeRow)) : span.first,
      last: forkRow !== undefined ? Math.max(span.last, Math.ceil(forkRow)) : span.last,
    });
  });
  const mainSpan = spans.get("main");
  if (mainSpan) occupancy.set("main", { ...mainSpan });

  // main pins to lane 0; the rest allocate oldest-first (larger row index =
  // older, since newest is at the top), ties toward the more compact span.
  const branches = [...occupancy.keys()].sort((a, b) => {
    if (a === "main") return -1;
    if (b === "main") return 1;
    const entryA = spans.get(a)!;
    const entryB = spans.get(b)!;
    return (
      entryB.first - entryA.first ||
      (entryA.last - entryA.first) - (entryB.last - entryB.first) ||
      entryB.last - entryA.last
    );
  });
  const laneOf = new Map<string, number>();
  const colorOf = new Map<string, string>();
  const laneIntervals: Span[][] = [];
  const laneBranchOrder: string[][] = [];
  branches.forEach((branch) => {
    const span = occupancy.get(branch)!;
    // Touching at one shared junction row (a branch merges exactly where the
    // next forks) is daisy-chaining, not parallelism — those share a lane.
    // Lane 0 is main's alone: a non-main branch that merely touches main's span
    // must not render as a continuation of main.
    let lane = laneIntervals.findIndex(
      (intervals, index) =>
        (branch === "main" || index > 0) &&
        intervals.every((occupied) => span.last <= occupied.first || span.first >= occupied.last),
    );
    if (lane === -1) {
      lane = laneIntervals.length;
      laneIntervals.push([]);
      laneBranchOrder.push([]);
    }
    laneIntervals[lane].push(span);
    laneBranchOrder[lane].push(branch);
    laneOf.set(branch, lane);
  });
  // Colour keys off lane + position-within-lane. Within a lane, branches cycle
  // their family in chronological (top-to-bottom) order so daisy-chained
  // branches reuse a freed lane as distinct back-to-back entries.
  laneBranchOrder.forEach((laneBranches, lane) => {
    const family = TRAIL_LANE_COLOR_FAMILIES[lane % TRAIL_LANE_COLOR_FAMILIES.length];
    laneBranches
      .slice()
      .sort((a, b) => occupancy.get(a)!.first - occupancy.get(b)!.first)
      .forEach((branch, i) => colorOf.set(branch, lane < 4 ? family[i % family.length] : family[1]));
  });

  // Lifecycle edges (supersedes/evolves/related) whose endpoints are both
  // visible — the routed arrows the view draws through the relationship zone.
  const lifecycle = (trail.edges || []).filter(
    (edge) => REL_LANE_SET.has(edge.type) && rowOf.has(edge.source) && rowOf.has(edge.target),
  );

  // Continuity events (rename/migration/removal blocks on entries), grouped
  // into chains by shared labels (union-find over from/to), then greedy
  // interval-packed into their own lane band left of the relationship zone.
  const continuityEvents: ContinuityEvent[] = [];
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const blocks = Array.isArray(item.node.continuity) ? item.node.continuity : [];
    blocks.forEach((block, blockIndex) => {
      if (!block || !TRAIL_CONTINUITY_KINDS.has(block.kind) || !block.from) return;
      continuityEvents.push({
        key: `${item.node.id}:${blockIndex}`,
        row: index,
        entryId: item.node.entry_id || item.node.id,
        kind: block.kind,
        from: block.from,
        to: block.to || null,
        chainKey: "",
        lane: 0,
      });
    });
  });
  const contParent = new Map<string, string>();
  const contTouch = (label: string) => { if (label && !contParent.has(label)) contParent.set(label, label); };
  const contFind = (label: string): string => {
    let cur = label;
    while (contParent.get(cur) !== cur) { contParent.set(cur, contParent.get(contParent.get(cur)!)!); cur = contParent.get(cur)!; }
    return cur;
  };
  continuityEvents.forEach((event) => {
    contTouch(event.from);
    if (event.to) { contTouch(event.to); const a = contFind(event.from); const b = contFind(event.to); if (a !== b) contParent.set(a, b); }
  });
  const chainsByKey = new Map<string, { rows: number[]; events: ContinuityEvent[] }>();
  continuityEvents.forEach((event) => {
    event.chainKey = contFind(event.from);
    const chain = chainsByKey.get(event.chainKey) || { rows: [], events: [] };
    chain.rows.push(event.row);
    chain.events.push(event);
    chainsByKey.set(event.chainKey, chain);
  });
  const contIntervals: Span[][] = [];
  const contLaneOf = new Map<string, number>();
  [...chainsByKey.entries()]
    .map(([chainKey, chain]) => ({ chainKey, first: Math.min(...chain.rows), last: Math.max(...chain.rows) }))
    .sort((a, b) => (b.first - a.first) || (a.last - a.first) - (b.last - b.first) || a.chainKey.localeCompare(b.chainKey))
    .forEach((chain) => {
      let lane = contIntervals.findIndex((intervals) => intervals.every((occupied) => chain.last < occupied.first || chain.first > occupied.last));
      if (lane === -1) { lane = contIntervals.length; contIntervals.push([]); }
      contIntervals[lane].push({ first: chain.first, last: chain.last });
      contLaneOf.set(chain.chainKey, lane);
    });
  continuityEvents.forEach((event) => { event.lane = contLaneOf.get(event.chainKey) || 0; });
  const continuityChains: ContinuityChain[] = [...chainsByKey.entries()]
    .map(([chainKey, chain]) => ({
      chainKey,
      lane: contLaneOf.get(chainKey) || 0,
      rows: chain.rows.slice().sort((a, b) => a - b),
      events: chain.events.slice().sort((a, b) => a.row - b.row),
    }))
    .sort((a, b) => a.lane - b.lane || a.rows[0] - b.rows[0]);

  return {
    items,
    total,
    rowOf,
    spans,
    laneOf,
    colorOf,
    laneCount: laneIntervals.length,
    linkRows,
    mergeEvents,
    lifecycle,
    continuityEvents,
    continuityChains,
    continuityLaneCount: contIntervals.length,
  };
}

export function laneColorFamily(lane: number): string {
  return TRAIL_LANE_COLOR_FAMILIES[lane % TRAIL_LANE_COLOR_FAMILIES.length][0];
}
