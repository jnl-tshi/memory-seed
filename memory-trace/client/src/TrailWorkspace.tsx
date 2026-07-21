import { useEffect, useMemo, useRef, type CSSProperties, type ReactElement } from "react";
import type { TrailResponse, TrailEdge, TrailEvent } from "./api";
import type { TrailStyle } from "./SettingsMenu";
import {
  buildTrailModel,
  trailStamp,
  inDecisionGroup,
  isDecisionRow,
  laneColorFamily,
  pastelOf,
  stripTitleStamp,
  TRAIL_CONT_LANE_W,
  TRAIL_CONT_ZONE_PAD,
  TRAIL_CORNER,
  TRAIL_LANE_W,
  TRAIL_REL_LANE_W,
  TRAIL_REL_LANES,
  TRAIL_REL_ZONE,
  TRAIL_ROW,
} from "./trailModel";
import { elbowTo, handDrawnPoints, moveTo, pressurePath, ribbonPath, runBody, runPath, sampleQuadratic } from "./trailPath";
import { animateScrollTo, bandScrollTarget, scrollDurationFor } from "./trailScroll";

const CONTINUITY_COLOR: Record<string, string> = { rename: "var(--accent)", migration: "var(--edge-evolves)", removal: "var(--edge-supersedes)" };

const EDGE_INFO_RANK: Record<string, number> = { supersedes: 3, evolves: 2, related: 1 };
const TRAIL_DASH = "6 4";
const TRAIL_VERB: Record<string, string> = { supersedes: "replaces", evolves: "evolves", related: "relates to" };

const TEXT_CLEAR = 18; // dot radius + breathing gap past the last lane

export function TrailWorkspace({
  trail,
  trailStyle,
  windowSize,
  selectedEntryId,
  selectedChunkId,
  query,
  selectionMuted,
  commitSiblingIds,
  onEnsureVisible,
  onSelectEntry,
  onLoadMore,
}: {
  trail: TrailResponse;
  trailStyle: TrailStyle;
  windowSize: number;
  selectedEntryId: string | null;
  selectedChunkId: string | null;
  query: string;
  selectionMuted: boolean;
  commitSiblingIds: string[];
  onEnsureVisible: (count: number) => void;
  onSelectEntry: (entryId: string | null, chunkId: string, decision?: { heading: string }) => void;
  onLoadMore: () => void;
}) {
  // Stroke presentation is owned by the settings menu (App); the Trail keeps
  // only the derivations its geometry needs. Line thickness Fine 1.8 / Thick
  // 2.5; arrowheads use userSpaceOnUse so they stay the same size in both
  // (calibrated to the fine line).
  const strokeW = trailStyle.thickness === "thick" ? 2.5 : 1.8;
  const handDrawn = trailStyle.style === "hand";
  const pressure = handDrawn ? trailStyle.pressure : 0;

  const model = useMemo(() => buildTrailModel(trail, windowSize), [trail, windowSize]);
  const { items, total, rowOf, spans, laneOf, colorOf, linkRows, mergeEvents, lifecycle, continuityEvents, continuityChains, continuityLaneCount } = model;

  // React-parity harness (mirrors the vanilla `window.memoryTraceDebug`): a
  // read-only surface so the layout model can be invariant-checked and
  // cross-referenced against the vanilla Trail on the same corpus.
  useEffect(() => {
    (window as unknown as { memoryTraceNextDebug?: unknown }).memoryTraceNextDebug = { trailModel: model };
  }, [model]);

  // Clicks that originate inside the Trail select a row that is already on
  // screen — recentring it would yank the list out from under the user. Only
  // outside-origin selections (context panel, find bar) auto-scroll.
  const suppressScroll = useRef(false);
  const scroller = useRef<HTMLDivElement>(null);
  const cancelScroll = useRef<(() => void) | null>(null);
  const scrollHandledFor = useRef<string | null>(null);
  // Loading a corpus auto-selects a graph node, and that selection must NOT
  // drag the Trail to wherever that entry happens to sit — a new corpus opens
  // at the top. The first selection after a reset is adopted silently; every
  // later one scrolls normally.
  const adoptWithoutScroll = useRef(true);
  useEffect(() => () => cancelScroll.current?.(), []);

  // Starting Trace, or switching worktree/topic, presents a new corpus. A new
  // `trail` object is exactly that signal — growing the window (Load older)
  // keeps the same object, so paging never jumps back to the top.
  useEffect(() => {
    cancelScroll.current?.();
    if (scroller.current) scroller.current.scrollTop = 0;
    scrollHandledFor.current = null;
    adoptWithoutScroll.current = true;
  }, [trail]);

  // Bring the selection into view: if the selected entry is older than the
  // loaded window, grow the window to include it; once its row exists, ease it
  // to the near edge of the middle third (see trailScroll.ts).
  useEffect(() => {
    if (!selectedEntryId) { scrollHandledFor.current = null; return; }
    if (suppressScroll.current) { suppressScroll.current = false; scrollHandledFor.current = selectedEntryId; return; }
    // The corpus's opening selection is adopted where it stands, leaving the
    // Trail at the top (see adoptWithoutScroll).
    if (adoptWithoutScroll.current) { adoptWithoutScroll.current = false; scrollHandledFor.current = selectedEntryId; return; }
    // One auto-scroll per selection: re-renders (chunk loads, prop identity
    // churn) must never re-scroll a selection that was already handled.
    if (scrollHandledFor.current === selectedEntryId) return;
    const index = model.rowOf.get(selectedEntryId);
    if (index === undefined) {
      const ordered = (trail.nodes || [])
        .filter((node) => node.entry_id)
        .sort((a, b) => trailStamp(b) - trailStamp(a) || String(a.id).localeCompare(String(b.id)));
      const position = ordered.findIndex((node) => node.id === selectedEntryId);
      // Grow past the target by a viewport's worth of rows. Loading exactly up
      // to it would leave it as the very last row, pinned to the bottom of the
      // pane with nothing beneath it to scroll against — it could never reach
      // the band edge.
      const headroom = Math.ceil((scroller.current?.clientHeight ?? 0) / TRAIL_ROW);
      if (position >= 0) onEnsureVisible(position + 1 + headroom);
      return; // not handled yet — the window grows, the effect re-runs, then scrolls
    }
    scrollHandledFor.current = selectedEntryId;
    const element = scroller.current;
    if (!element) return;
    // Row geometry is known exactly from the model, so no DOM measurement:
    // every row is TRAIL_ROW tall and the rail shares these coordinates.
    const rowCenter = index * TRAIL_ROW + TRAIL_ROW / 2;
    const target = bandScrollTarget(rowCenter, element.scrollTop, element.clientHeight, element.scrollHeight - element.clientHeight);
    if (target === null) return; // already inside the stable band
    cancelScroll.current?.();
    cancelScroll.current = animateScrollTo(element, target, scrollDurationFor(target - element.scrollTop));
  }, [selectedEntryId, model, trail, onEnsureVisible]);

  if (!items.length) return <div className="loading-state">No entries with lineage data yet.</div>;

  // Search as a function over the Trail: a client-side substring filter over the
  // visible window (title, branch, or entry id). Matching rows keep full
  // presence and gain a marker dot; the rest dim, so lineage context never
  // disappears under a query.
  const searchTerm = query.trim().toLowerCase();
  const searching = searchTerm !== "";
  const rowMatchOwn = (node: TrailEvent) =>
    searching &&
    (stripTitleStamp(node.title).toLowerCase().includes(searchTerm) ||
      (node.branch || "").toLowerCase().includes(searchTerm) ||
      (node.entry_id || "").toLowerCase().includes(searchTerm));
  // Search highlights whole decision GROUPS (per JNL): if any row of a
  // multi-decision entry matches - the entry title on the anchor, or a
  // decision name on a child - every row sharing that entry_id lights up, so
  // a match never leaves siblings dimmed mid-group.
  const matchedGroupEntries = useMemo(() => {
    if (!searching) return new Set<string>();
    const matched = new Set<string>();
    for (const node of model.items) {
      if (node.kind !== "node" || !inDecisionGroup(node.node)) continue;
      if (rowMatchOwn(node.node) && node.node.entry_id) matched.add(node.node.entry_id);
    }
    return matched;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- rowMatchOwn derives from searchTerm
  }, [model.items, searchTerm, searching]);
  const rowMatch = (node: TrailEvent) =>
    rowMatchOwn(node) || Boolean(inDecisionGroup(node) && node.entry_id && matchedGroupEntries.has(node.entry_id));

  // Continuity zone is deferred (0 for now); the relationship zone is kept
  // reserved so lifecycle-arrow lanes slot in later without re-laying-out.
  const continuityZoneWidth = continuityLaneCount ? continuityLaneCount * TRAIL_CONT_LANE_W + TRAIL_CONT_ZONE_PAD : 0;
  const laneX = (branch: string) => continuityZoneWidth + TRAIL_REL_ZONE + (laneOf.get(branch) || 0) * TRAIL_LANE_W + 7;
  const laneCenterX = (lane: number) => continuityZoneWidth + TRAIL_REL_ZONE + lane * TRAIL_LANE_W + 7;
  const continuityLaneX = (lane: number) => 8 + lane * TRAIL_CONT_LANE_W + 6;
  const rowY = (index: number) => index * TRAIL_ROW + TRAIL_ROW / 2;
  const railWidth = continuityZoneWidth + TRAIL_REL_ZONE + model.laneCount * TRAIL_LANE_W + 12;
  const rowIndent = (lane: number) => Math.round(laneCenterX(lane) + TEXT_CLEAR);
  const height = items.length * TRAIL_ROW;
  const mainColor = colorOf.get("main") || laneColorFamily(0);

  // Per-row text indent follows the git-graph silhouette: text starts just right
  // of the rightmost lane alive at that row, using fork-to-merge occupancy so it
  // clears connectors, not just entry rows.
  const envelopeLane = new Array(items.length).fill(0);
  laneOf.forEach((lane, branch) => {
    const span = spans.get(branch);
    if (!span) return;
    const link = linkRows.get(branch);
    const first = branch === "main" ? span.first : link?.mergeRow !== undefined ? Math.min(span.first, Math.floor(link.mergeRow)) : span.first;
    const last = branch === "main" ? span.last : link?.forkRow !== undefined ? Math.max(span.last, Math.ceil(link.forkRow)) : span.last;
    for (let i = first; i <= last && i < envelopeLane.length; i += 1) {
      if (lane > envelopeLane[i]) envelopeLane[i] = lane;
    }
  });

  // Contiguous row ranges belonging to one multi-decision entry. Shared by the
  // indent stabiliser below and the group brackets further down so the two can
  // never disagree about where a group starts and ends.
  const groups: { first: number; last: number }[] = [];
  {
    let start = -1;
    let entry: string | null = null;
    const close = (end: number) => {
      if (start >= 0 && end > start) groups.push({ first: start, last: end });
      start = -1;
      entry = null;
    };
    items.forEach((item, index) => {
      // The anchor counts as in-group: it is the entry's heading row, so it
      // must share the group's indent or the heading staggers against its own
      // subheadings - the stagger the block-indent rule below exists to kill.
      const inGroup = item.kind === "node" && inDecisionGroup(item.node);
      const id = inGroup && item.kind === "node" ? item.node.entry_id : null;
      if (inGroup && id === entry) return;
      if (start >= 0) close(index - 1);
      if (inGroup) { start = index; entry = id; }
    });
    if (start >= 0) close(items.length - 1);
  }
  // A decision group is ONE entry, so its rows indent as one block: every row
  // takes the group's widest envelope lane. Per-row indents made a lane that
  // opened or closed partway through a group stagger its own decisions, which
  // read as the text jittering between rows of the same entry.
  groups.forEach(({ first, last }) => {
    let widest = 0;
    for (let row = first; row <= last; row += 1) widest = Math.max(widest, envelopeLane[row]);
    for (let row = first; row <= last; row += 1) envelopeLane[row] = widest;
  });

  // Same-branch consecutive rows → vertical lane segments (no-branch rows get a
  // dot but no line).
  const branchRows = new Map<string, number[]>();
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const branch = item.node.branch || "";
    if (!branchRows.has(branch)) branchRows.set(branch, []);
    branchRows.get(branch)!.push(index);
  });

  // One stroke per branch, not one per row gap. The old per-pair <line>s were
  // collinear and shared endpoints, so their union was already a single
  // vertical line — but a 30px segment is far too short to carry a believable
  // pen drift, so drawing the whole run as one path is what lets a long branch
  // read as one confident stroke instead of a nervous polyline.
  // A pressure ribbon when the run is long enough to carry width variation,
  // otherwise an ordinary stroke — which is also what keeps round caps on the
  // short runs that want them.
  const railStroke = (key: string, x1: number, y1: number, x2: number, y2: number, seedKey: string, colour: string | undefined, extra: Record<string, unknown> = {}) => {
    const ribbon = pressure > 0 ? pressurePath(x1, y1, x2, y2, seedKey, strokeW, pressure) : "";
    if (ribbon) return <path key={key} d={ribbon} fill={colour} fillOpacity={0.55} {...extra} />;
    return <path key={key} d={runPath(x1, y1, x2, y2, seedKey, handDrawn)} fill="none" stroke={colour} strokeWidth={strokeW} strokeOpacity={0.55} strokeLinecap="round" strokeLinejoin="round" {...extra} />;
  };

  // Connectors carry pressure too, otherwise fork/merge runs read as machine
  // strokes next to hand-drawn lanes and the sketch illusion breaks. The elbow
  // is flattened into the same polyline so the ribbon turns the corner with it.
  const connectorRibbon = (points: { x: number; y: number }[], seedKey: string) =>
    pressure > 0 ? ribbonPath(points, strokeW, pressure, seedKey) : "";
  const connectorProps = (ribbon: string, d: string, colour: string | undefined) =>
    ribbon
      ? ({ d: ribbon, fill: colour, fillOpacity: 0.55 } as const)
      : ({ d, fill: "none", stroke: colour, strokeWidth: strokeW, strokeOpacity: 0.55, strokeLinecap: "round", strokeLinejoin: "round" } as const);

  const laneSegments: ReactElement[] = [];
  branchRows.forEach((rows, branch) => {
    if (branch === "" || rows.length < 2) return;
    const x = laneX(branch);
    laneSegments.push(railStroke(`seg-${branch}`, x, rowY(rows[0]), x, rowY(rows[rows.length - 1]), `${branch}:lane`, colorOf.get(branch)));
  });

  // Main trunk: solid spine from main's newest real commit (newest of {main
  // entry, merge dot}) down to its newest entry; dashed phantom above.
  const mainRows = branchRows.get("main") || [];
  const mergeRowsForTrunk = mergeEvents.map((event) => event.row);
  const trunk: ReactElement[] = [];
  if (mainRows.length || mergeRowsForTrunk.length) {
    const mainX = laneX("main");
    const topRow = Math.min(...(mainRows.length ? [mainRows[0]] : []), ...mergeRowsForTrunk);
    const topY = Math.max(0, rowY(topRow));
    const bottomRow = mainRows.length ? mainRows[0] : Math.max(...mergeRowsForTrunk);
    const bottomY = rowY(bottomRow);
    if (bottomY > topY) {
      trunk.push(railStroke("trunk-solid", mainX, topY, mainX, bottomY, "main:trunk", mainColor));
    }
    if (topY > 0) {
      trunk.push(<path key="trunk-phantom" d={runPath(mainX, 0, mainX, topY, "main:phantom", handDrawn)} fill="none" stroke={mainColor} strokeWidth={strokeW} strokeOpacity={0.3} strokeDasharray="2 5" strokeLinecap="round" strokeLinejoin="round" />);
    }
  }

  // Fork/merge connectors: rounded-elbow gitgraph paths. Unmerged branches
  // dangle (no fabricated merge).
  const connectors: ReactElement[] = [];
  linkRows.forEach(({ forkRow, mergeRow, mergeLabel, forkLabel, estimated }, branch) => {
    const rows = branchRows.get(branch) || [];
    if (!rows.length) return;
    const newest = rows[0];
    const oldest = rows[rows.length - 1];
    const bx = laneX(branch);
    const mx = laneX("main");
    const r = TRAIL_CORNER;
    const stroke = colorOf.get(branch);
    if (forkRow !== undefined) {
      const yf = rowY(forkRow);
      const yb = rowY(oldest);
      // Legs drift; the elbow between them stays exact, so the corner radius
      // still reads as a deliberate gitgraph turn rather than a wobble.
      const d =
        moveTo(mx, yf) +
        runBody(mx, yf, bx - r, yf, `${branch}:fork-leg`, handDrawn) +
        elbowTo(bx, yf, bx, yf - r) +
        runBody(bx, yf - r, bx, yb, `${branch}:fork`, handDrawn);
      const ribbon = connectorRibbon(
        [
          ...handDrawnPoints(mx, yf, bx - r, yf, `${branch}:fork-leg`),
          ...sampleQuadratic({ x: bx - r, y: yf }, { x: bx, y: yf }, { x: bx, y: yf - r }).slice(1),
          ...handDrawnPoints(bx, yf - r, bx, yb, `${branch}:fork`).slice(1),
        ],
        `${branch}:fork`,
      );
      connectors.push(
        <path key={`fork-${branch}`} className="trail-link" {...connectorProps(ribbon, d, stroke)}>
          <title>{`${branch} · ${forkLabel ? `forked after ${forkLabel}` : estimated ? "fork point estimated" : "fork point"}`}</title>
        </path>,
      );
    }
    if (mergeRow !== undefined) {
      const yb = rowY(newest);
      const ym = rowY(mergeRow);
      const d =
        moveTo(bx, yb) +
        runBody(bx, yb, bx, ym + r, `${branch}:merge`, handDrawn) +
        elbowTo(bx, ym, bx - r, ym) +
        runBody(bx - r, ym, mx, ym, `${branch}:merge-leg`, handDrawn);
      const ribbon = connectorRibbon(
        [
          ...handDrawnPoints(bx, yb, bx, ym + r, `${branch}:merge`),
          ...sampleQuadratic({ x: bx, y: ym + r }, { x: bx, y: ym }, { x: bx - r, y: ym }).slice(1),
          ...handDrawnPoints(bx - r, ym, mx, ym, `${branch}:merge-leg`).slice(1),
        ],
        `${branch}:merge`,
      );
      connectors.push(
        <path key={`merge-${branch}`} className="trail-link" {...connectorProps(ribbon, d, stroke)}>
          <title>{`${branch} · ${mergeLabel ? `merged by ${mergeLabel}` : estimated ? "merge point estimated" : "merge point"}`}</title>
        </path>,
      );
    }
  });

  // Trunk merge dots — one ring per real merge commit at its commit-time row.
  const entryIdForChunk = (chunkId: string) => trail.nodes.find((node) => node.chunk_id === chunkId)?.entry_id ?? null;
  const mergeDots = mergeEvents.map((event) => (
    <circle
      key={`mdot-${event.sha}-${event.row}`}
      className="trail-merge-dot"
      cx={laneX("main")}
      cy={rowY(event.row)}
      r={3.5}
      fill="var(--trail-bg)"
      stroke={mainColor}
      strokeWidth={2}
      onClick={() => { suppressScroll.current = true; onSelectEntry(entryIdForChunk(event.chunkId), event.chunkId); }}
    >
      <title>{`${event.short} ${event.subject} · ${event.count} ${event.count === 1 ? "entry" : "entries"}`}</title>
    </circle>
  ));

  // Lifecycle arcs — routed lineage arrows through the reserved relationship
  // zone. Precedence: only the strongest edge per pair draws (replaces >
  // evolves > related). supersedes always shows (soft/pastel until the
  // selection touches it); evolves/related draw only for the selected entry.
  // Adjacent supersedes renders as a short bow beside the dots, not a route.
  const focusActive = selectedEntryId != null && !selectionMuted;
  const nodeAt = (id: string): TrailEvent | null => {
    const item = items[rowOf.get(id) ?? -1];
    return item && item.kind === "node" ? item.node : null;
  };
  const relLaneX = (type: string) => continuityZoneWidth + 8 + TRAIL_REL_LANES.indexOf(type as (typeof TRAIL_REL_LANES)[number]) * TRAIL_REL_LANE_W;
  const pairKey = (a: string, b: string) => (a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`);
  const strongestByPair = new Map<string, TrailEdge>();
  lifecycle.forEach((edge) => {
    const key = pairKey(edge.source, edge.target);
    const cur = strongestByPair.get(key);
    if (!cur || EDGE_INFO_RANK[edge.type] > EDGE_INFO_RANK[cur.type]) strongestByPair.set(key, edge);
  });
  const winsPair = (edge: TrailEdge) => strongestByPair.get(pairKey(edge.source, edge.target)) === edge;
  const adjacentRows = (rowA: number, rowB: number) => {
    const lo = Math.min(rowA, rowB);
    const hi = Math.max(rowA, rowB);
    return items.slice(lo + 1, hi).every((item) => item.kind !== "node");
  };
  // Two-rule related model: routes are reserved for branch hops; same-branch
  // related context renders as row brackets. Adjacent same-lane evolves chains
  // render as a single SVG bracket beside the dots instead of out-and-back hops.
  const sameBranch = (a: string, b: string) => (nodeAt(a)?.branch || "") === (nodeAt(b)?.branch || "");
  const adjacentRowsOf = (a: string, b: string) => adjacentRows(rowOf.get(a)!, rowOf.get(b)!);
  const bracketEvolves = new Set(
    lifecycle.filter(
      (edge) => edge.type === "evolves" && winsPair(edge) && adjacentRowsOf(edge.source, edge.target) && sameBranch(edge.source, edge.target),
    ),
  );
  const chainPrimary = new Set<string>();
  const chainSecondary = new Set<string>();
  if (focusActive && selectedEntryId && rowOf.has(selectedEntryId)) {
    const selectedBranch = nodeAt(selectedEntryId)?.branch || "";
    const related = lifecycle.filter((edge) => edge.type === "related");
    const firstOrder = new Set<string>();
    related.forEach((edge) => {
      if (edge.source === selectedEntryId) firstOrder.add(edge.target);
      if (edge.target === selectedEntryId) firstOrder.add(edge.source);
    });
    related.forEach((edge) => {
      if (edge.source === selectedEntryId && (nodeAt(edge.target)?.branch || "") === selectedBranch) chainPrimary.add(edge.target);
      else if (edge.target === selectedEntryId && (nodeAt(edge.source)?.branch || "") === selectedBranch) chainSecondary.add(edge.source);
    });
    related.forEach((edge) => {
      if (firstOrder.has(edge.source) && edge.target !== selectedEntryId && !firstOrder.has(edge.target) && (nodeAt(edge.target)?.branch || "") === selectedBranch) chainSecondary.add(edge.target);
      if (firstOrder.has(edge.target) && edge.source !== selectedEntryId && !firstOrder.has(edge.source) && (nodeAt(edge.source)?.branch || "") === selectedBranch) chainSecondary.add(edge.source);
    });
    chainPrimary.forEach((id) => chainSecondary.delete(id));
    chainSecondary.delete(selectedEntryId);
  }
  const commitSiblings = new Set(focusActive ? commitSiblingIds.filter((id) => id !== selectedEntryId) : []);

  const arcs: ReactElement[] = [];
  lifecycle.forEach((edge) => {
    if (!winsPair(edge)) return;
    if (bracketEvolves.has(edge)) return;
    const touched = focusActive && (edge.source === selectedEntryId || edge.target === selectedEntryId);
    if ((edge.type === "related" || edge.type === "evolves") && !touched) return;
    if (edge.type === "related" && sameBranch(edge.source, edge.target)) return;
    const source = nodeAt(edge.source);
    const target = nodeAt(edge.target);
    if (!source || !target) return;
    const sRow = rowOf.get(edge.source)!;
    const tRow = rowOf.get(edge.target)!;
    const sx = laneX(source.branch || "");
    const sy = rowY(sRow);
    const tx = laneX(target.branch || "");
    const ty = rowY(tRow);
    const soft = edge.type !== "related" && !touched;
    const stroke = soft ? `var(--edge-${edge.type}-soft)` : `var(--edge-${edge.type})`;
    const marker = soft ? `trail-arrow-${edge.type}-soft` : `trail-arrow-${edge.type}`;
    const opacity = touched ? 0.95 : focusActive ? 0.5 : 0.9;
    const width = touched ? strokeW + 0.6 : strokeW;
    const tip = `${stripTitleStamp(source.title)} ${TRAIL_VERB[edge.type]} ${stripTitleStamp(target.title)}`;
    const key = `arc-${edge.source}-${edge.target}-${edge.type}`;
    if (edge.type === "supersedes" && adjacentRows(sRow, tRow)) {
      const bow = 11;
      const d = `M ${sx} ${sy} C ${sx - bow} ${sy + (ty - sy) * 0.3}, ${tx - bow} ${ty - (ty - sy) * 0.3}, ${tx} ${ty}`;
      arcs.push(
        <path key={key} d={d} fill="none" stroke={stroke} strokeWidth={width} strokeDasharray={TRAIL_DASH} strokeOpacity={opacity} markerEnd={`url(#${marker})`}>
          <title>{tip}</title>
        </path>,
      );
      return;
    }
    const lx = relLaneX(edge.type);
    const r = TRAIL_CORNER;
    const dir = ty > sy ? 1 : -1;
    const d = `M ${sx} ${sy} L ${lx + r} ${sy} Q ${lx} ${sy} ${lx} ${sy + r * dir} L ${lx} ${ty - r * dir} Q ${lx} ${ty} ${lx + r} ${ty} L ${tx} ${ty}`;
    arcs.push(
      <path key={key} d={d} fill="none" stroke={stroke} strokeWidth={width} strokeDasharray={TRAIL_DASH} strokeOpacity={opacity} markerEnd={`url(#${marker})`}>
        <title>{tip}</title>
      </path>,
    );
  });

  // Daisy-chained adjacent evolves within one lane: one square bracket per
  // maximal chain, drawn only when the chain touches the active selection.
  const evolvesBrackets: ReactElement[] = [];
  if (bracketEvolves.size) {
    const parent = new Map<number, number>();
    const find = (x: number): number => {
      while (parent.get(x) !== x) { parent.set(x, parent.get(parent.get(x)!)!); x = parent.get(x)!; }
      return x;
    };
    bracketEvolves.forEach((edge) => {
      const ra = rowOf.get(edge.source)!;
      const rb = rowOf.get(edge.target)!;
      if (!parent.has(ra)) parent.set(ra, ra);
      if (!parent.has(rb)) parent.set(rb, rb);
      parent.set(find(ra), find(rb));
    });
    const chains = new Map<number, number[]>();
    [...parent.keys()].forEach((row) => {
      const root = find(row);
      chains.set(root, [...(chains.get(root) ?? []), row]);
    });
    chains.forEach((rowsIn, root) => {
      const rowsSorted = rowsIn.slice().sort((a, b) => a - b);
      const first = items[rowsSorted[0]];
      if (first.kind !== "node") return;
      const touched = focusActive && rowsSorted.some((r) => { const it = items[r]; return it.kind === "node" && it.node.entry_id === selectedEntryId; });
      if (!touched) return;
      const x = laneX(first.node.branch || "") - 9;
      const top = rowY(rowsSorted[0]);
      const bot = rowY(rowsSorted[rowsSorted.length - 1]);
      evolvesBrackets.push(
        <path key={`ebr-${root}`} d={`M ${x + 5} ${top} L ${x} ${top} L ${x} ${bot} L ${x + 5} ${bot}`} fill="none" stroke="var(--edge-evolves)" strokeWidth={strokeW + 0.2} strokeLinejoin="round" strokeLinecap="round" strokeOpacity={0.95}>
          <title>{`evolves chain (${rowsSorted.length})`}</title>
        </path>,
      );
    });
  }

  // Continuity chains: a vertical line per multi-row chain in the left band,
  // with per-event glyphs (rename circle, migration diamond, removal square+X).
  const continuityMarks: ReactElement[] = [];
  continuityChains.forEach((chain) => {
    const x = continuityLaneX(chain.lane);
    const touched = focusActive && chain.events.some((event) => event.entryId === selectedEntryId);
    if (chain.rows.length > 1) {
      continuityMarks.push(
        <line key={`cchain-${chain.chainKey}`} x1={x} y1={rowY(chain.rows[0])} x2={x} y2={rowY(chain.rows[chain.rows.length - 1])} stroke={touched ? "var(--text)" : "var(--border-2)"} strokeWidth={1.75} strokeOpacity={touched ? 0.9 : 0.6} strokeLinecap="round" />,
      );
    }
    chain.events.forEach((event) => {
      const y = rowY(event.row);
      const colour = CONTINUITY_COLOR[event.kind] || "var(--muted)";
      const tip = `${event.kind} - ${event.from}${event.to ? ` -> ${event.to}` : ""}`;
      if (event.kind === "migration") {
        continuityMarks.push(
          <path key={`cev-${event.key}`} d={`M ${x} ${y - 5} L ${x + 5} ${y} L ${x} ${y + 5} L ${x - 5} ${y} Z`} fill="var(--bg)" stroke={colour} strokeWidth={1.6}><title>{tip}</title></path>,
        );
      } else if (event.kind === "removal") {
        continuityMarks.push(
          <g key={`cev-${event.key}`}>
            <rect x={x - 4.5} y={y - 4.5} width={9} height={9} rx={2} fill="var(--bg)" stroke={colour} strokeWidth={1.6}><title>{tip}</title></rect>
            <line x1={x - 2.4} y1={y - 2.4} x2={x + 2.4} y2={y + 2.4} stroke={colour} strokeWidth={1.4} />
            <line x1={x - 2.4} y1={y + 2.4} x2={x + 2.4} y2={y - 2.4} stroke={colour} strokeWidth={1.4} />
          </g>,
        );
      } else {
        continuityMarks.push(
          <circle key={`cev-${event.key}`} cx={x} cy={y} r={4.2} fill="var(--bg)" stroke={colour} strokeWidth={1.6}><title>{tip}</title></circle>,
        );
      }
    });
  });

  // Rows inside a rendered decision group demand an EXACT chunk match:
  // previously entry_id uniquely identified one row, but a group's rows all
  // share it - the permissive OR-match would light the whole group and make
  // clicking D2 indistinguishable from D1. The ANCHOR needs excluding too,
  // not just the decision rows: it also carries the group's entry_id, so a
  // permissive match would light it alongside whichever decision is selected.
  // Its own chunk_id still matches when the entry itself is selected, so this
  // yields exactly one lit row in both states. Ordinary rows - the corpus
  // majority - keep the permissive rule unchanged.
  const isSelected = (node: TrailEvent) =>
    node.chunk_id === selectedChunkId ||
    (!inDecisionGroup(node) && node.entry_id !== null && node.entry_id === selectedEntryId);

  const dots = items.flatMap((item, index) => {
    if (item.kind !== "node") return [];
    const node = item.node;
    const branch = node.branch || "";
    const selected = isSelected(node);
    const miss = searching && !rowMatch(node) && !selected;
    // Every decision row D1..DN carries a pastel of the branch colour at a
    // smaller radius: same event stream, subordinate weight - "a decision
    // inside this entry", not a new event. The anchor keeps the full colour.
    const isChild = isDecisionRow(node);
    const baseColor = branch ? colorOf.get(branch)! : "var(--trail-faint)";
    return [
      <circle
        key={`dot-${node.id}`}
        cx={laneX(branch)}
        cy={rowY(index)}
        r={selected ? (isChild ? 5.5 : 6.5) : isChild ? 3.5 : 4.5}
        fill={isChild && branch ? pastelOf(colorOf.get(branch)!) : baseColor}
        fillOpacity={miss ? 0.35 : 1}
        stroke={selected ? "var(--accent-strong)" : "var(--trail-bg)"}
        strokeWidth={selected ? 2.5 : 2}
      />,
    ];
  });

  // One bracket per multi-decision entry, sitting just right of the time
  // column and spanning the group's rows - the visual "these are one entry's
  // decisions" grouping. The rows share one indent (stabilised above), so the
  // bracket has a single x for the whole span.
  const decisionBrackets = groups.flatMap(({ first, last }) => {
    const anchor = items[first];
    if (anchor.kind !== "node") return [];
    const x = rowIndent(envelopeLane[first]) + 34 + 5; // time column is 34px; sit in the row gap
    const top = rowY(first) - 9;
    const bot = rowY(last) + 9;
    const colour = pastelOf(colorOf.get(anchor.node.branch || "") || laneColorFamily(0));
    return [
      <path
        key={`dbr-${anchor.node.id}`}
        d={`M ${x + 4} ${top} L ${x} ${top + 4} L ${x} ${bot - 4} L ${x + 4} ${bot}`}
        fill="none"
        stroke={colour}
        strokeWidth={1.4}
        strokeLinejoin="round"
        strokeLinecap="round"
        strokeOpacity={0.9}
      >
        {/* Count comes from the anchor's decision_count, NOT the row span:
            the span now includes the anchor row itself, so geometry would
            claim one decision too many. */}
        <title>{`${anchor.node.decision_count} decisions in this entry`}</title>
      </path>,
    ];
  });

  const rows = items.map((item, index) => {
    if (item.kind === "day") {
      return (
        <div key={`day-${index}`} className="trail-day" style={{ "--indent": `${rowIndent(envelopeLane[index])}px` } as CSSProperties}>
          {item.label}
        </div>
      );
    }
    const node = item.node;
    const branch = node.branch || "";
    const showPill = Boolean(branch) && spans.get(branch)?.first === index;
    const selected = isSelected(node);
    const matched = rowMatch(node);
    const miss = searching && !matched && !selected;
    const isChild = isDecisionRow(node);
    // Decision rows share the anchor's timestamp; repeating it would read as N
    // separate moments, so only the anchor shows the time.
    const time = !isChild && node.datetime ? node.datetime.slice(11, 16) : "";
    return (
      <button
        key={`row-${node.id}`}
        data-entry={node.entry_id || undefined}
        data-decision={node.decision_ordinal || undefined}
        type="button"
        className={`trail-row${isChild ? " decision-row" : ""}${selected ? (selectionMuted ? " pinned" : " selected") : ""}${matched ? " search-match" : ""}${miss ? " search-miss" : ""}${chainPrimary.has(node.id) ? " chain-primary" : chainSecondary.has(node.id) ? " chain-secondary" : ""}${commitSiblings.has(node.id) ? " commit-sibling" : ""}`}
        style={{ "--indent": `${rowIndent(envelopeLane[index])}px` } as CSSProperties}
        title={`${node.title}${branch ? ` · ${branch}` : ""}`}
        onClick={() => {
          suppressScroll.current = true;
          onSelectEntry(node.entry_id, node.chunk_id, isChild ? { heading: node.title } : undefined);
        }}
      >
        <span className="trail-time">{time}</span>
        {matched && <span className="trail-match-dot" aria-hidden="true" />}
        <span className="trail-title">{stripTitleStamp(node.title)}</span>
        {(node.has_diagram || showPill) && (
          <span className="trail-row-end">
            {node.has_diagram && <span className="trail-diagram-badge" title="Has a decision diagram (open the entry to view)" aria-label="Has decision diagram">{"◇"}</span>}
            {showPill && (
              <span className="trail-branch" style={{ color: colorOf.get(branch) }}>
                {branch}
              </span>
            )}
          </span>
        )}
      </button>
    );
  });

  const shown = items.filter((item) => item.kind === "node" && !isDecisionRow(item.node)).length;
  const matchCount = searching ? items.filter((item) => item.kind === "node" && rowMatch(item.node)).length : 0;

  return (
    <div className="trail-workspace">
      <div className="trail-viewbar">
        <span className="trail-meta">
          <strong>{shown}</strong> of {total} entries · newest first
          {searching && <> · <strong>{matchCount}</strong> match{matchCount === 1 ? "" : "es"}</>}
        </span>
        <span className="trail-legend" aria-label="Relationship legend">
          {continuityLaneCount > 0 && (
            <>
              <span className="trail-legend-item"><span className="trail-cont-key" style={{ borderColor: "var(--accent)" }} />rename</span>
              <span className="trail-legend-item"><span className="trail-cont-key trail-cont-key-diamond" style={{ borderColor: "var(--edge-evolves)" }} />migration</span>
              <span className="trail-legend-item"><span className="trail-cont-key" style={{ borderColor: "var(--edge-supersedes)" }} />removal</span>
            </>
          )}
          <span className="trail-legend-item"><span className="trail-legend-line" style={{ borderColor: "var(--edge-supersedes)" }} />replaces</span>
          <span className="trail-legend-item"><span className="trail-legend-line" style={{ borderColor: "var(--edge-evolves)" }} />evolves · on select</span>
          <span className="trail-legend-item"><span className="trail-legend-line" style={{ borderColor: "var(--edge-related)" }} />related · on select</span>
        </span>
        {shown < total && (
          <button type="button" className="trail-more" onClick={onLoadMore}>
            Load older
          </button>
        )}
      </div>
      <div className="trail-scroll" ref={scroller}>
        <div className="trail-body" style={{ height }}>
          <svg className="trail-rail" width={railWidth} height={height} viewBox={`0 0 ${railWidth} ${height}`} aria-hidden="true">
            <defs>
              {/* Surface grain only. The pen's *drift* now lives in the path
                  geometry (trailPath.ts), which is what stops neighbouring lanes
                  reading as offset copies of one straight line. This filter is
                  demoted to the ink texture on top of it: short-wave noise at a
                  sub-pixel scale, so it roughens edges without bending strokes.
                  A long-wave, high-scale displacement here would reintroduce
                  exactly the correlated sideways shift we removed. No blur —
                  the spline already carries the smooth character, and blurring
                  only costs legibility. Dots and text stay outside the group. */}
              {/* Tuned against the magnified rail: displacement is +/- scale/2,
                  so scale 0.9 keeps the edge within half a pixel of the true
                  spline — grain, not a second wobble. Longer waves (or a bigger
                  scale) visibly rippled a 1.8px stroke and read as the jagged
                  line this treatment set out to remove. */}
              <filter id="trail-rough" x="-2%" y="-1%" width="104%" height="102%">
                <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves={2} seed={7} result="noise" />
                <feDisplacementMap in="SourceGraphic" in2="noise" scale={trailStyle.wobble} xChannelSelector="R" yChannelSelector="G" />
              </filter>
              {(["supersedes", "evolves", "related"] as const).map((type) => (
                <marker key={`m-${type}`} id={`trail-arrow-${type}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill={`var(--edge-${type})`} />
                </marker>
              ))}
              {(["supersedes", "evolves"] as const).map((type) => (
                <marker key={`m-${type}-soft`} id={`trail-arrow-${type}-soft`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill={`var(--edge-${type}-soft)`} />
                </marker>
              ))}
            </defs>
            <g filter={handDrawn ? "url(#trail-rough)" : undefined}>
              {trunk}
              {connectors}
              {laneSegments}
              {arcs}
            </g>
            {continuityLaneCount > 0 && <rect className="trail-cont-zone" x={0} y={0} width={continuityZoneWidth - 4} height={height} rx={6} />}
            {continuityMarks}
            {evolvesBrackets}
            {dots}
            {mergeDots}
          </svg>
          {/* Decision-group brackets sit right of the TIME column, which lives
              outside the rail's narrow viewBox (rowIndent reaches railWidth at
              deep lanes) - so they get their own full-width overlay aligned to
              the same row grid instead of clipping inside the rail. */}
          {decisionBrackets.length > 0 && (
            <svg className="trail-decision-brackets" height={height} aria-hidden="true">
              {decisionBrackets}
            </svg>
          )}
          <div className="trail-rows">{rows}</div>
        </div>
      </div>
    </div>
  );
}
