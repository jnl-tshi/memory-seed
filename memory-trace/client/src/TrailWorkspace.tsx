import { useEffect, useMemo, type ReactElement } from "react";
import type { TrailResponse } from "./api";
import {
  buildTrailModel,
  laneColorFamily,
  stripTitleStamp,
  TRAIL_CORNER,
  TRAIL_LANE_W,
  TRAIL_REL_ZONE,
  TRAIL_ROW,
} from "./trailModel";

const TEXT_CLEAR = 18; // dot radius + breathing gap past the last lane

export function TrailWorkspace({
  trail,
  windowSize,
  selectedEntryId,
  selectedChunkId,
  onSelectEntry,
  onLoadMore,
}: {
  trail: TrailResponse;
  windowSize: number;
  selectedEntryId: string | null;
  selectedChunkId: string | null;
  onSelectEntry: (entryId: string | null, chunkId: string) => void;
  onLoadMore: () => void;
}) {
  const model = useMemo(() => buildTrailModel(trail, windowSize), [trail, windowSize]);
  const { items, total, spans, laneOf, colorOf, linkRows, mergeEvents } = model;

  // React-parity harness (mirrors the vanilla `window.memoryTraceDebug`): a
  // read-only surface so the layout model can be invariant-checked and
  // cross-referenced against the vanilla Trail on the same corpus.
  useEffect(() => {
    (window as unknown as { memoryTraceNextDebug?: unknown }).memoryTraceNextDebug = { trailModel: model };
  }, [model]);

  if (!items.length) return <div className="loading-state">No entries with lineage data yet.</div>;

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

  const isSelected = (entryId: string | null, chunkId: string) =>
    (entryId !== null && entryId === selectedEntryId) || chunkId === selectedChunkId;

  const dots = items.flatMap((item, index) => {
    if (item.kind !== "node") return [];
    const branch = item.node.branch || "";
    const selected = isSelected(item.node.entry_id, item.node.chunk_id);
    return [
      <circle
        key={`dot-${item.node.id}`}
        cx={laneX(branch)}
        cy={rowY(index)}
        r={selected ? 6.5 : 4.5}
        fill={branch ? colorOf.get(branch) : "var(--trail-faint)"}
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
    const time = node.datetime ? node.datetime.slice(11, 16) : "";
    return (
      <button
        key={`row-${node.id}`}
        type="button"
        className={`trail-row${selected ? " selected" : ""}`}
        style={{ paddingLeft: rowIndent(envelopeLane[index]) }}
        title={`${node.title}${branch ? ` · ${branch}` : ""}`}
        onClick={() => onSelectEntry(node.entry_id, node.chunk_id)}
      >
        <span className="trail-time">{time}</span>
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

  return (
    <div className="trail-workspace">
      <div className="trail-viewbar">
        <span className="trail-meta">
          <strong>{shown}</strong> of {total} entries · newest first
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
            {trunk}
            {connectors}
            {laneSegments}
            {dots}
            {mergeDots}
          </svg>
          <div className="trail-rows">{rows}</div>
        </div>
      </div>
    </div>
  );
}
