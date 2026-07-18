// Pure Trail layout model — a faithful port of the vanilla `trailModel`
// (static/app.js:709-1008), kept framework-free so it can be unit-tested and
// cross-checked against the vanilla `window.memoryTraceDebug.trailModel` on the
// same corpus. Scope: chronological rows + day separators, branch-lane
// assignment (greedy interval packing over fork-to-merge occupancy), colours,
// fork/merge connector rows, and trunk merge dots. Lifecycle-edge arrows and
// continuity lanes are deferred to later slices and are NOT computed here.
import type { TrailResponse, TrailEvent, MergeEvent } from "./api";

export const TRAIL_ROW = 30;
export const TRAIL_LANE_W = 14;
export const TRAIL_WINDOW_STEP = 60;
export const TRAIL_REL_LANES = ["supersedes", "evolves", "related"] as const;
export const TRAIL_REL_LANE_W = 12;
export const TRAIL_CORNER = 7;
export const TRAIL_REL_ZONE = TRAIL_REL_LANES.length * TRAIL_REL_LANE_W + 12;

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
};

function trailStamp(node: TrailEvent): number {
  return Date.parse(node.datetime || `${node.date}T00:00:00`) || 0;
}

export function stripTitleStamp(title: string): string {
  return String(title || "").replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*-\s*/, "");
}

export function buildTrailModel(trail: TrailResponse, window: number): TrailModel {
  const nodes = (trail.nodes || [])
    .filter((node) => node.entry_id)
    .sort((a, b) => trailStamp(b) - trailStamp(a) || String(a.id).localeCompare(String(b.id)));
  const total = nodes.length;
  const visible = nodes.slice(0, window);

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
  };
}

export function laneColorFamily(lane: number): string {
  return TRAIL_LANE_COLOR_FAMILIES[lane % TRAIL_LANE_COLOR_FAMILIES.length][0];
}
