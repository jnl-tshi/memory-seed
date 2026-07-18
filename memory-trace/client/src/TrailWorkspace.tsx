import { useEffect, useMemo, type ReactElement } from "react";
import type { TrailResponse, TrailEdge, TrailEvent } from "./api";
import {
  buildTrailModel,
  laneColorFamily,
  stripTitleStamp,
  TRAIL_CORNER,
  TRAIL_LANE_W,
  TRAIL_REL_LANE_W,
  TRAIL_REL_LANES,
  TRAIL_REL_ZONE,
  TRAIL_ROW,
} from "./trailModel";

const EDGE_INFO_RANK: Record<string, number> = { supersedes: 3, evolves: 2, related: 1 };
const TRAIL_DASH = "6 4";
const TRAIL_VERB: Record<string, string> = { supersedes: "replaces", evolves: "evolves", related: "relates to" };

const TEXT_CLEAR = 18; // dot radius + breathing gap past the last lane

export function TrailWorkspace({
  trail,
  windowSize,
  selectedEntryId,
  selectedChunkId,
  query,
  onSelectEntry,
  onLoadMore,
}: {
  trail: TrailResponse;
  windowSize: number;
  selectedEntryId: string | null;
  selectedChunkId: string | null;
  query: string;
  onSelectEntry: (entryId: string | null, chunkId: string) => void;
  onLoadMore: () => void;
}) {
  const model = useMemo(() => buildTrailModel(trail, windowSize), [trail, windowSize]);
  const { items, total, rowOf, spans, laneOf, colorOf, linkRows, mergeEvents, lifecycle } = model;

  // React-parity harness (mirrors the vanilla `window.memoryTraceDebug`): a
  // read-only surface so the layout model can be invariant-checked and
  // cross-referenced against the vanilla Trail on the same corpus.
  useEffect(() => {
    (window as unknown as { memoryTraceNextDebug?: unknown }).memoryTraceNextDebug = { trailModel: model };
  }, [model]);

  if (!items.length) return <div className="loading-state">No entries with lineage data yet.</div>;

  // Search as a function over the Trail: a client-side substring filter over the
  // visible window (title, branch, or entry id). Matching rows keep full
  // presence and gain a marker dot; the rest dim, so lineage context never
  // disappears under a query.
  const searchTerm = query.trim().toLowerCase();
  const searching = searchTerm !== "";
  const rowMatch = (node: TrailEvent) =>
    searching &&
    (stripTitleStamp(node.title).toLowerCase().includes(searchTerm) ||
      (node.branch || "").toLowerCase().includes(searchTerm) ||
      (node.entry_id || "").toLowerCase().includes(searchTerm));

  // Continuity zone is deferred (0 for now); the relationship zone is kept
  // reserved so lifecycle-arrow lanes slot in later without re-laying-out.
  const laneX = (branch: string) => TRAIL_REL_ZONE + (laneOf.get(branch) || 0) * TRAIL_LANE_W + 7;
  const laneCenterX = (lane: number) => TRAIL_REL_ZONE + lane * TRAIL_LANE_W + 7;
  const rowY = (index: number) => index * TRAIL_ROW + TRAIL_ROW / 2;
  const railWidth = TRAIL_REL_ZONE + model.laneCount * TRAIL_LANE_W + 12;
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

  // Same-branch consecutive rows → vertical lane segments (no-branch rows get a
  // dot but no line).
  const branchRows = new Map<string, number[]>();
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const branch = item.node.branch || "";
    if (!branchRows.has(branch)) branchRows.set(branch, []);
    branchRows.get(branch)!.push(index);
  });

  const laneSegments: ReactElement[] = [];
  branchRows.forEach((rows, branch) => {
    if (branch === "") return;
    for (let i = 1; i < rows.length; i += 1) {
      laneSegments.push(
        <line
          key={`seg-${branch}-${i}`}
          x1={laneX(branch)}
          y1={rowY(rows[i - 1])}
          x2={laneX(branch)}
          y2={rowY(rows[i])}
          stroke={colorOf.get(branch)}
          strokeWidth={2}
          strokeOpacity={0.55}
        />,
      );
    }
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
      trunk.push(<line key="trunk-solid" x1={mainX} y1={topY} x2={mainX} y2={bottomY} stroke={mainColor} strokeWidth={2} strokeOpacity={0.55} strokeLinecap="round" />);
    }
    if (topY > 0) {
      trunk.push(<line key="trunk-phantom" x1={mainX} y1={0} x2={mainX} y2={topY} stroke={mainColor} strokeWidth={2} strokeOpacity={0.3} strokeDasharray="2 5" strokeLinecap="round" />);
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
      connectors.push(
        <path key={`fork-${branch}`} className="trail-link" d={`M ${mx} ${yf} L ${bx - r} ${yf} Q ${bx} ${yf} ${bx} ${yf - r} L ${bx} ${yb}`} fill="none" stroke={stroke} strokeWidth={2} strokeOpacity={0.55}>
          <title>{`${branch} · ${forkLabel ? `forked after ${forkLabel}` : estimated ? "fork point estimated" : "fork point"}`}</title>
        </path>,
      );
    }
    if (mergeRow !== undefined) {
      const yb = rowY(newest);
      const ym = rowY(mergeRow);
      connectors.push(
        <path key={`merge-${branch}`} className="trail-link" d={`M ${bx} ${yb} L ${bx} ${ym + r} Q ${bx} ${ym} ${bx - r} ${ym} L ${mx} ${ym}`} fill="none" stroke={stroke} strokeWidth={2} strokeOpacity={0.55}>
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
      onClick={() => onSelectEntry(entryIdForChunk(event.chunkId), event.chunkId)}
    >
      <title>{`${event.short} ${event.subject} · ${event.count} ${event.count === 1 ? "entry" : "entries"}`}</title>
    </circle>
  ));

  // Lifecycle arcs — routed lineage arrows through the reserved relationship
  // zone. Precedence: only the strongest edge per pair draws (replaces >
  // evolves > related). supersedes always shows (soft/pastel until the
  // selection touches it); evolves/related draw only for the selected entry.
  // Adjacent supersedes renders as a short bow beside the dots, not a route.
  const focusActive = selectedEntryId != null;
  const nodeAt = (id: string): TrailEvent | null => {
    const item = items[rowOf.get(id) ?? -1];
    return item && item.kind === "node" ? item.node : null;
  };
  const relLaneX = (type: string) => 8 + TRAIL_REL_LANES.indexOf(type as (typeof TRAIL_REL_LANES)[number]) * TRAIL_REL_LANE_W;
  const pairKey = (a: string, b: string) => (a < b ? `${a} ${b}` : `${b} ${a}`);
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
  const arcs: ReactElement[] = [];
  lifecycle.forEach((edge) => {
    if (!winsPair(edge)) return;
    const touched = focusActive && (edge.source === selectedEntryId || edge.target === selectedEntryId);
    if ((edge.type === "related" || edge.type === "evolves") && !touched) return;
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
    const width = touched ? 2.6 : 2;
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

  const isSelected = (entryId: string | null, chunkId: string) =>
    (entryId !== null && entryId === selectedEntryId) || chunkId === selectedChunkId;

  const dots = items.flatMap((item, index) => {
    if (item.kind !== "node") return [];
    const branch = item.node.branch || "";
    const selected = isSelected(item.node.entry_id, item.node.chunk_id);
    const miss = searching && !rowMatch(item.node) && !selected;
    return [
      <circle
        key={`dot-${item.node.id}`}
        cx={laneX(branch)}
        cy={rowY(index)}
        r={selected ? 6.5 : 4.5}
        fill={branch ? colorOf.get(branch) : "var(--trail-faint)"}
        fillOpacity={miss ? 0.35 : 1}
        stroke={selected ? "var(--accent-strong)" : "var(--trail-bg)"}
        strokeWidth={selected ? 2.5 : 2}
      />,
    ];
  });

  const rows = items.map((item, index) => {
    if (item.kind === "day") {
      return (
        <div key={`day-${index}`} className="trail-day" style={{ paddingLeft: rowIndent(envelopeLane[index]) }}>
          {item.label}
        </div>
      );
    }
    const node = item.node;
    const branch = node.branch || "";
    const showPill = Boolean(branch) && spans.get(branch)?.first === index;
    const selected = isSelected(node.entry_id, node.chunk_id);
    const matched = rowMatch(node);
    const miss = searching && !matched && !selected;
    const time = node.datetime ? node.datetime.slice(11, 16) : "";
    return (
      <button
        key={`row-${node.id}`}
        type="button"
        className={`trail-row${selected ? " selected" : ""}${matched ? " search-match" : ""}${miss ? " search-miss" : ""}`}
        style={{ paddingLeft: rowIndent(envelopeLane[index]) }}
        title={`${node.title}${branch ? ` · ${branch}` : ""}`}
        onClick={() => onSelectEntry(node.entry_id, node.chunk_id)}
      >
        <span className="trail-time">{time}</span>
        {matched && <span className="trail-match-dot" aria-hidden="true" />}
        <span className="trail-title">{stripTitleStamp(node.title)}</span>
        {showPill && (
          <span className="trail-branch" style={{ color: colorOf.get(branch) }}>
            {branch}
          </span>
        )}
      </button>
    );
  });

  const shown = items.filter((item) => item.kind === "node").length;
  const matchCount = searching ? items.filter((item) => item.kind === "node" && rowMatch(item.node)).length : 0;

  return (
    <div className="trail-workspace">
      <div className="trail-viewbar">
        <span className="trail-meta">
          <strong>{shown}</strong> of {total} entries · newest first
          {searching && <> · <strong>{matchCount}</strong> match{matchCount === 1 ? "" : "es"}</>}
        </span>
        <span className="trail-legend" aria-label="Relationship legend">
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
      <div className="trail-scroll">
        <div className="trail-body" style={{ height }}>
          <svg className="trail-rail" width={railWidth} height={height} viewBox={`0 0 ${railWidth} ${height}`} aria-hidden="true">
            <defs>
              {/* Hand-drawn voice: a fixed-seed turbulence displacement gives every
                  stroke a slight, deterministic pen wobble — sketchy warmth without
                  losing legibility. Dots and text stay crisp (outside the group). */}
              <filter id="trail-rough" x="-4%" y="-1%" width="108%" height="102%">
                <feTurbulence type="fractalNoise" baseFrequency="0.014" numOctaves={2} seed={7} result="noise" />
                <feDisplacementMap in="SourceGraphic" in2="noise" scale={2.4} xChannelSelector="R" yChannelSelector="G" />
              </filter>
              {(["supersedes", "evolves", "related"] as const).map((type) => (
                <marker key={`m-${type}`} id={`trail-arrow-${type}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill={`var(--edge-${type})`} />
                </marker>
              ))}
              {(["supersedes", "evolves"] as const).map((type) => (
                <marker key={`m-${type}-soft`} id={`trail-arrow-${type}-soft`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill={`var(--edge-${type}-soft)`} />
                </marker>
              ))}
            </defs>
            <g filter="url(#trail-rough)">
              {trunk}
              {connectors}
              {laneSegments}
              {arcs}
            </g>
            {dots}
            {mergeDots}
          </svg>
          <div className="trail-rows">{rows}</div>
        </div>
      </div>
    </div>
  );
}
