// Arc 2d: minimal, offline, built-in diagram layout engine (flowchart/sequence
// subset). Ported from the vanilla reader's renderDiagramBlock and friends
// (memory-trace/memory_trace/static/app.js) — same parsing and Sugiyama-style
// layout math, but producing plain data instead of HTML strings so the React
// renderer can build actual SVG/JSX elements. No third-party library, no
// network, no LLM. Any diagram type this doesn't handle, or any parse
// failure, should degrade to showing the raw source — never a blank frame.

export interface DiagramPoint {
  x: number;
  y: number;
}

export interface FlowNode {
  id: string;
  lines: string[];
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FlowEdge {
  path: string;
  label: string;
  labelX: number;
  labelY: number;
}

export interface FlowchartLayout {
  kind: "flowchart";
  width: number;
  height: number;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface SequenceParticipant {
  name: string;
  x: number;
}

export interface SequenceMessage {
  x1: number;
  x2: number;
  y: number;
  text: string;
  dashed: boolean;
}

export interface SequenceLayout {
  kind: "sequence";
  width: number;
  height: number;
  headTop: number;
  headHeight: number;
  lifelineBottom: number;
  participants: SequenceParticipant[];
  messages: SequenceMessage[];
}

export type DiagramLayout = FlowchartLayout | SequenceLayout;

/** Which parser applies, from the diagram source's first line. Mirrors renderDiagramBlock's dispatch. */
export function diagramKind(source: string): "flowchart" | "sequence" | null {
  const first = String(source || "").trim().split("\n")[0]?.trim().toLowerCase() ?? "";
  if (first.startsWith("sequencediagram")) return "sequence";
  if (first.startsWith("flowchart") || first.startsWith("graph")) return "flowchart";
  return null;
}

/** Parse a diagram; returns null (never throws) so the caller can fall back to raw source. */
export function parseDiagram(source: string): DiagramLayout | null {
  const kind = diagramKind(source);
  try {
    if (kind === "sequence") return parseSequenceDiagram(source);
    if (kind === "flowchart") return parseFlowchart(source);
  } catch {
    return null;
  }
  return null;
}

interface ParsedToken {
  id: string;
  label: string;
}

function diagramNode(token: string): ParsedToken | null {
  const match = String(token).trim().match(/^([A-Za-z0-9_-]+)\s*(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\})?/);
  if (!match) return null;
  return { id: match[1], label: (match[2] || match[3] || match[4] || match[1]).trim() };
}

function diagramLabelLines(label: string, fallback: string): string[] {
  const lines = String(label || fallback)
    .replace(/^["']|["']$/g, "")
    .split(/<br\s*\/?>/i)
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.length ? lines : [fallback];
}

function diagramNodeSize(lines: string[]): { width: number; height: number } {
  const longest = Math.max(1, ...lines.map((line) => line.length));
  return {
    width: Math.min(260, Math.max(116, longest * 7 + 30)),
    height: Math.max(40, 14 + lines.length * 16),
  };
}

interface RawEdge {
  from: string;
  to: string;
  label: string;
}

// Compact Sugiyama-style coordinate assignment. Ranks establish the primary
// direction; each later rank is centred on its incoming neighbours, with a
// separation pass preventing overlaps. This keeps merge nodes between their
// contributing branches instead of pinning every rank to its first row.
function diagramFlowLayout(nodes: Map<string, string>, edges: RawEdge[], horizontal: boolean, rightToLeft: boolean) {
  const margin = 24;
  const rankGap = 78;
  const crossGap = 26;
  const ids = [...nodes.keys()];
  const order = new Map(ids.map((id, index) => [id, index]));
  const lines = new Map(ids.map((id) => [id, diagramLabelLines(nodes.get(id) ?? id, id)]));
  const sizes = new Map(ids.map((id) => [id, diagramNodeSize(lines.get(id) ?? [id])]));
  const rank = new Map(ids.map((id) => [id, 0]));
  for (let pass = 0; pass < ids.length; pass += 1) {
    let changed = false;
    edges.forEach((edge) => {
      const next = Math.min(ids.length - 1, (rank.get(edge.from) ?? 0) + 1);
      if (next > (rank.get(edge.to) ?? 0)) {
        rank.set(edge.to, next);
        changed = true;
      }
    });
    if (!changed) break;
  }

  const byRank = new Map<number, string[]>();
  ids.forEach((id) => {
    const value = rank.get(id) ?? 0;
    if (!byRank.has(value)) byRank.set(value, []);
    byRank.get(value)!.push(id);
  });
  const rankValues = [...byRank.keys()].sort((a, b) => a - b);
  const incoming = new Map<string, string[]>(ids.map((id) => [id, []]));
  edges.forEach((edge) => incoming.get(edge.to)?.push(edge.from));
  const crossCenters = new Map<string, number>();

  rankValues.forEach((value, rankIndex) => {
    const rankIds = byRank.get(value)!;
    const crossSize = (id: string) => (horizontal ? sizes.get(id)!.height : sizes.get(id)!.width);
    const desired = new Map(rankIds.map((id, index) => {
      const predecessors = incoming.get(id)!.filter((parent) => crossCenters.has(parent));
      const center = predecessors.length
        ? predecessors.reduce((sum, parent) => sum + crossCenters.get(parent)!, 0) / predecessors.length
        : margin + crossSize(id) / 2 + index * (crossSize(id) + crossGap);
      return [id, center] as const;
    }));
    rankIds.sort((a, b) => desired.get(a)! - desired.get(b)! || order.get(a)! - order.get(b)!);
    let cursor = margin;
    const placed: { id: string; center: number; half: number }[] = [];
    rankIds.forEach((id) => {
      const half = crossSize(id) / 2;
      const center = Math.max(desired.get(id)!, cursor + half);
      placed.push({ id, center, half });
      cursor = center + half + crossGap;
    });
    if (rankIndex > 0 && placed.length) {
      const desiredMean = placed.reduce((sum, item) => sum + desired.get(item.id)!, 0) / placed.length;
      const actualMean = placed.reduce((sum, item) => sum + item.center, 0) / placed.length;
      const availableShift = placed[0].center - placed[0].half - margin;
      const shift = Math.min(Math.max(0, actualMean - desiredMean), Math.max(0, availableShift));
      placed.forEach((item) => { item.center -= shift; });
    }
    placed.forEach((item) => crossCenters.set(item.id, item.center));
  });

  // Pull a linear chain back onto the centre of the fork it leads into. This
  // removes the left-aligned "spine" of a top-down flowchart without moving a
  // merge away from the midpoint of its incoming branches.
  const outgoing = new Map<string, string[]>(ids.map((id) => [id, []]));
  edges.forEach((edge) => outgoing.get(edge.from)?.push(edge.to));
  const forkCentred = new Set<string>();
  [...rankValues].reverse().forEach((value) => {
    const rankIds = byRank.get(value)!;
    if (rankIds.length !== 1) return;
    const id = rankIds[0];
    const successors = outgoing.get(id)!;
    if (successors.length > 1) {
      crossCenters.set(id, successors.reduce((sum, child) => sum + crossCenters.get(child)!, 0) / successors.length);
      forkCentred.add(id);
    } else if (successors.length === 1 && forkCentred.has(successors[0])) {
      crossCenters.set(id, crossCenters.get(successors[0])!);
      forkCentred.add(id);
    }
  });

  const rankExtents = new Map(rankValues.map((value) => [value, Math.max(
    ...byRank.get(value)!.map((id) => (horizontal ? sizes.get(id)!.width : sizes.get(id)!.height)),
  )]));
  const rankStarts = new Map<number, number>();
  let mainCursor = margin;
  rankValues.forEach((value) => {
    rankStarts.set(value, mainCursor);
    mainCursor += rankExtents.get(value)! + rankGap;
  });
  const mainExtent = mainCursor - rankGap + margin;
  const crossExtent = Math.max(...ids.map((id) => crossCenters.get(id)! + (horizontal ? sizes.get(id)!.height : sizes.get(id)!.width) / 2)) + margin;
  const width = horizontal ? mainExtent : crossExtent;
  const height = horizontal ? crossExtent : mainExtent;
  const positions = new Map<string, DiagramPoint>();
  ids.forEach((id) => {
    const size = sizes.get(id)!;
    const normalMain = rankStarts.get(rank.get(id)!)!;
    let x = horizontal ? normalMain : crossCenters.get(id)! - size.width / 2;
    const y = horizontal ? crossCenters.get(id)! - size.height / 2 : normalMain;
    if (horizontal && rightToLeft) x = width - margin - size.width - (normalMain - margin);
    positions.set(id, { x, y });
  });
  return { height, lines, positions, sizes, width };
}

function diagramEdgePath(from: DiagramPoint, to: DiagramPoint, horizontal: boolean): string {
  if (horizontal) {
    const delta = (to.x - from.x) / 2;
    return `M ${from.x} ${from.y} C ${from.x + delta} ${from.y}, ${to.x - delta} ${to.y}, ${to.x} ${to.y}`;
  }
  const delta = (to.y - from.y) / 2;
  return `M ${from.x} ${from.y} C ${from.x} ${from.y + delta}, ${to.x} ${to.y - delta}, ${to.x} ${to.y}`;
}

function parseFlowchart(text: string): FlowchartLayout {
  const rawLines = text.split("\n");
  const lines = rawLines.slice(1).map((line) => line.trim()).filter(Boolean);
  const horizontal = /^(flowchart|graph)\s+(lr|rl)/i.test(rawLines[0]);
  const rightToLeft = /^(flowchart|graph)\s+rl/i.test(rawLines[0]);
  const nodes = new Map<string, string>();
  const edges: RawEdge[] = [];
  const note = (node: ParsedToken | null) => {
    if (node && !nodes.has(node.id)) nodes.set(node.id, node.label);
  };
  for (const line of lines) {
    if (!line.includes("-->")) {
      note(diagramNode(line));
      continue;
    }
    const [lhs, rhsRaw] = line.split(/-->/);
    let rhs = rhsRaw;
    let label = "";
    const labelled = rhs.match(/^\s*\|([^|]*)\|\s*(.*)$/);
    if (labelled) {
      label = labelled[1].trim();
      rhs = labelled[2];
    }
    const a = diagramNode(lhs);
    const b = diagramNode(rhs);
    note(a);
    note(b);
    if (a && b) edges.push({ from: a.id, to: b.id, label });
  }
  if (!nodes.size) throw new Error("no nodes");
  const layout = diagramFlowLayout(nodes, edges, horizontal, rightToLeft);

  const flowEdges: FlowEdge[] = edges.map((edge) => {
    const a = layout.positions.get(edge.from);
    const b = layout.positions.get(edge.to);
    const aSize = layout.sizes.get(edge.from);
    const bSize = layout.sizes.get(edge.to);
    if (!a || !b || !aSize || !bSize) return null;
    const from = horizontal
      ? { x: rightToLeft ? a.x : a.x + aSize.width, y: a.y + aSize.height / 2 }
      : { x: a.x + aSize.width / 2, y: a.y + aSize.height };
    const to = horizontal
      ? { x: rightToLeft ? b.x + bSize.width : b.x, y: b.y + bSize.height / 2 }
      : { x: b.x + bSize.width / 2, y: b.y };
    return {
      path: diagramEdgePath(from, to, horizontal),
      label: edge.label,
      labelX: (from.x + to.x) / 2,
      labelY: (from.y + to.y) / 2 - 5,
    };
  }).filter((edge): edge is FlowEdge => edge !== null);

  const flowNodes: FlowNode[] = [...layout.lines.keys()].map((id) => {
    const p = layout.positions.get(id)!;
    const size = layout.sizes.get(id)!;
    return { id, lines: layout.lines.get(id)!, x: p.x, y: p.y, width: size.width, height: size.height };
  });

  return { kind: "flowchart", width: layout.width, height: layout.height, nodes: flowNodes, edges: flowEdges };
}

function parseSequenceDiagram(text: string): SequenceLayout {
  const lines = text.split("\n").slice(1).map((line) => line.trim()).filter(Boolean);
  const order: string[] = [];
  const seen = new Set<string>();
  const rawMessages: { from: string; to: string; text: string; dashed: boolean }[] = [];
  const add = (name: string) => {
    if (name && !seen.has(name)) {
      seen.add(name);
      order.push(name);
    }
  };
  for (const line of lines) {
    const participant = line.match(/^participant\s+(.+)$/i);
    if (participant) {
      add(participant[1].trim());
      continue;
    }
    const msg = line.match(/^(\w[\w -]*?)\s*(--?>>?|--?>)\s*(\w[\w -]*?)\s*:\s*(.*)$/);
    if (msg) {
      add(msg[1].trim());
      add(msg[3].trim());
      rawMessages.push({ from: msg[1].trim(), to: msg[3].trim(), text: msg[4].trim(), dashed: msg[2].includes("--") });
    }
  }
  if (!order.length) throw new Error("no participants");

  const colW = 150;
  const topH = 40;
  const rowH = 46;
  const width = 24 + order.length * colW;
  const height = topH + 30 + rawMessages.length * rowH + 20;
  const colX = (name: string) => 24 + order.indexOf(name) * colW + colW / 2 - 24;

  const participants: SequenceParticipant[] = order.map((name) => ({ name, x: colX(name) }));
  const messages: SequenceMessage[] = rawMessages.map((message, index) => ({
    x1: colX(message.from),
    x2: colX(message.to),
    y: topH + 40 + index * rowH,
    text: message.text,
    dashed: message.dashed,
  }));

  return {
    kind: "sequence",
    width,
    height,
    headTop: 12,
    headHeight: topH,
    lifelineBottom: height - 12,
    participants,
    messages,
  };
}
