import { useEffect, useMemo, useRef } from "react";
import type { Core } from "cytoscape";
import { Maximize2, Minus, Plus } from "lucide-react";
import type { RendererGraphNode, RendererGraphResponse } from "./api";

type GraphWorkspaceProps = {
  graph: RendererGraphResponse;
  selectedId: string | null;
  onSelect: (node: RendererGraphNode) => void;
  labelMode: "focus" | "minimal" | "all";
  viewMode: "graph" | "list";
  theme: "light" | "dark";
};

// Cytoscape styles can't consume CSS custom properties, so resolve the theme
// tokens at mount time; the mount effect re-runs on theme change (safe — the
// deterministic layout reproduces identical positions).
function themeToken(name: string, fallback: string) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

const COMMUNITY_COLOURS = ["#23a99a", "#6688e8", "#d99a2b", "#c76d99", "#8f76d4", "#6aa869"];

function colourForCommunity(node: RendererGraphNode) {
  let hash = 0;
  for (const character of node.community.fingerprint || node.community.id) hash = (hash * 31 + character.charCodeAt(0)) | 0;
  return COMMUNITY_COLOURS[Math.abs(hash) % COMMUNITY_COLOURS.length];
}

function labelIdsFor(graph: RendererGraphResponse, selectedId: string | null, labelMode: GraphWorkspaceProps["labelMode"]) {
  if (labelMode === "all") return new Set(graph.nodes.map((node) => node.id));
  if (labelMode === "minimal") return new Set(selectedId ? [selectedId] : []);
  return new Set(
    [...graph.nodes]
      .sort((left, right) => right.connectivity - left.connectivity || right.importance_score - left.importance_score)
      .slice(0, 12)
      .map((node) => node.id),
  );
}

function groupedNodes(graph: RendererGraphResponse) {
  const groups = new Map<string, RendererGraphNode[]>();
  for (const node of graph.nodes) {
    const key = `${node.community.label}\u0000${node.community.id}`;
    groups.set(key, [...(groups.get(key) ?? []), node]);
  }
  return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
}

// Deterministic initial positions: nodes ordered by community then id, placed on
// a circle. cose is a physics simulation — from a fixed starting arrangement it
// settles to the same layout every time, so the map holds still across loads
// and reloads instead of scrambling.
function initialPositions(nodes: RendererGraphNode[]) {
  const ordered = [...nodes].sort(
    (left, right) => left.community.id.localeCompare(right.community.id) || left.id.localeCompare(right.id),
  );
  const radius = Math.max(220, ordered.length * 14);
  const positions = new Map<string, { x: number; y: number }>();
  ordered.forEach((node, index) => {
    const angle = (index / Math.max(1, ordered.length)) * Math.PI * 2;
    positions.set(node.id, { x: Math.round(Math.cos(angle) * radius), y: Math.round(Math.sin(angle) * radius) });
  });
  return positions;
}

export function GraphWorkspace({ graph, selectedId, onSelect, labelMode, viewMode, theme }: GraphWorkspaceProps) {
  const container = useRef<HTMLDivElement>(null);
  const cytoscape = useRef<Core | null>(null);
  // Refs so the tap handler and selection effect never force an instance remount.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const graphRef = useRef(graph);
  graphRef.current = graph;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;
  const labelIdsRef = useRef<Set<string>>(new Set());

  // In-place presentation pass — selection ring, labels, evolves reveal. Reads
  // current state from refs so both the mount (async) and the update effect can
  // apply it without racing each other.
  const applyPresentation = (cy: Core) => {
    const currentSelected = selectedIdRef.current;
    const currentLabels = labelIdsRef.current;
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const id = node.id();
        node.data("selected", id === currentSelected ? "yes" : "no");
        node.data("label", id === currentSelected || currentLabels.has(id) ? node.data("title") : "");
      });
      cy.edges('[type = "evolves"]').forEach((edge) => {
        const touched = currentSelected !== null && (edge.data("source") === currentSelected || edge.data("target") === currentSelected);
        edge.toggleClass("hidden-until-selected", !touched);
      });
    });
  };

  // The rendered element set is SELECTION-INDEPENDENT: every node that carries
  // any edge renders, always. Selecting must never add/remove elements or move
  // the map — evolves edges reveal via style, not element churn.
  const renderedNodes = useMemo(() => {
    const connected = new Set(graph.edges.flatMap((edge) => [edge.source, edge.target]));
    return graph.nodes.filter((node) => connected.has(node.id));
  }, [graph]);
  const labelIds = useMemo(() => labelIdsFor(graph, selectedId, labelMode), [graph, labelMode, selectedId]);
  labelIdsRef.current = labelIds;

  const fit = () => cytoscape.current?.fit(cytoscape.current.elements(), 52);
  const zoom = (factor: number) => {
    const cy = cytoscape.current;
    if (!cy) return;
    cy.zoom({ level: Math.max(cy.minZoom(), Math.min(cy.maxZoom(), cy.zoom() * factor)), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  const selectAdjacent = (direction: 1 | -1) => {
    if (!graph.nodes.length) return;
    const ordered = [...graph.nodes].sort((left, right) => left.temporal.value.localeCompare(right.temporal.value) || left.label.localeCompare(right.label));
    const currentIndex = Math.max(0, ordered.findIndex((node) => node.id === selectedId));
    onSelect(ordered[(currentIndex + direction + ordered.length) % ordered.length]);
  };

  // Mount ONCE per graph payload. Selection, label mode, and evolves visibility
  // are applied in place by the effect below — never by rebuilding the instance,
  // never by re-running layout. The map only moves when the data changes.
  useEffect(() => {
    let disposed = false;

    async function mount() {
      const { default: createCytoscape } = await import("cytoscape");
      if (disposed || !container.current) return;
      const positions = initialPositions(renderedNodes);
      const nodeBorder = themeToken("--panel", "#142a26");
      const nodeText = themeToken("--text-bright", "#e9f3f0");
      const nodeOutline = themeToken("--bg", "#10201e");
      const selectedRing = themeToken("--accent-strong", "#efb345");
      const edgeRelated = themeToken("--edge-related", "#74a6ce");
      const edgeSupersedes = themeToken("--edge-supersedes", "#e18494");
      const edgeEvolves = themeToken("--edge-evolves", "#7cc6e8");
      const edgeTopic = themeToken("--edge-topic", "#a88acc");
      const cy = createCytoscape({
        container: container.current,
        elements: [
          ...renderedNodes.map((node) => ({
            data: {
              id: node.id,
              label: "",
              title: node.label,
              agent: node.source.agent,
              selected: "no",
              colour: colourForCommunity(node),
              size: 22 + Math.min(18, node.connectivity * 3),
            },
            position: positions.get(node.id),
          })),
          ...graph.edges.map((edge, index) => ({
            data: { id: edge.id || `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, type: edge.edge_type },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(colour)",
              "border-color": nodeBorder,
              "border-width": 2,
              "label": "data(label)",
              "font-family": "Inter, sans-serif",
              "font-size": 11,
              "font-weight": 600,
              "color": nodeText,
              "text-wrap": "ellipsis",
              "text-max-width": "132px",
              "text-outline-color": nodeOutline,
              "text-outline-width": 3,
              "text-valign": "bottom",
              "text-margin-y": 8,
              "width": "data(size)",
              "height": "data(size)",
            },
          },
          {
            selector: 'node[selected = "yes"]',
            style: { "border-color": selectedRing, "border-width": 5, "overlay-color": selectedRing, "overlay-opacity": 0.26, "overlay-padding": 5 },
          },
          // Straight edges: curvature carried no information and read as noise.
          { selector: "edge", style: { "curve-style": "straight", "line-color": edgeRelated, "target-arrow-color": edgeRelated, "target-arrow-shape": "triangle", "width": 2, "opacity": 0.85 } },
          { selector: 'edge[type = "related"]', style: { "line-color": edgeRelated, "target-arrow-color": edgeRelated } },
          { selector: 'edge[type = "supersedes"]', style: { "line-style": "dashed", "line-color": edgeSupersedes, "target-arrow-color": edgeSupersedes } },
          { selector: 'edge[type = "evolves"]', style: { "line-style": "dotted", "line-color": edgeEvolves, "target-arrow-color": edgeEvolves, "width": 2.5 } },
          { selector: 'edge[type = "topic"]', style: { "line-style": "dotted", "line-color": edgeTopic, "target-arrow-color": edgeTopic, "opacity": 0.58 } },
          { selector: "edge.hidden-until-selected", style: { display: "none" } },
        ],
        layout: { name: "preset" },
        minZoom: 0.35,
        maxZoom: 2.4,
        wheelSensitivity: 0.16,
      });
      cy.on("tap", "node", (event) => {
        const node = graphRef.current.nodes.find((item) => item.id === event.target.id());
        if (node) onSelectRef.current(node);
      });
      cytoscape.current = cy;
      // Debug/parity surface (same pattern as the Trail's memoryTraceNextDebug
      // harness): lets stability be asserted from outside — positions must not
      // move on selection.
      const debugHost = window as unknown as { memoryTraceNextDebug?: Record<string, unknown> };
      debugHost.memoryTraceNextDebug = { ...(debugHost.memoryTraceNextDebug ?? {}), graphCy: cy };
      applyPresentation(cy);
      const layout = cy.layout({ name: "cose", animate: false, padding: 52, randomize: false, nodeRepulsion: () => 12_000, idealEdgeLength: () => 150, gravity: 0.3, numIter: 900 });
      layout.one("layoutstop", () => { if (!disposed) cy.fit(cy.elements(), 52); });
      layout.run();
    }

    if (viewMode === "graph") void mount();
    return () => {
      disposed = true;
      cytoscape.current?.destroy();
      cytoscape.current = null;
    };
  }, [graph, renderedNodes, viewMode, theme]);

  // Presentation updates on selection/label changes: in place, no element
  // churn, no layout, no camera movement.
  useEffect(() => {
    const cy = cytoscape.current;
    if (!cy || viewMode !== "graph") return;
    applyPresentation(cy);
  }, [labelIds, selectedId, viewMode, graph]);

  if (viewMode === "list") {
    return <section className="graph-list-view" aria-label="Memory graph list">
      {groupedNodes(graph).map(([key, nodes]) => {
        const [community] = key.split("\u0000");
        return (
          <section className="community-group" key={key}>
            <h2>{community}</h2>
            {nodes.map((node) => (
              <button key={node.id} type="button" className={node.id === selectedId ? "graph-list-item selected" : "graph-list-item"} aria-pressed={node.id === selectedId} onClick={() => onSelect(node)}>
                <span>{node.label}</span>
                <small>{node.temporal.value} - {node.connectivity} links</small>
              </button>
            ))}
          </section>
        );
      })}
    </section>;
  }

  return <section className="graph-workspace" aria-label="Memory graph workspace">
    <div className="graph-controls" aria-label="Graph view controls">
      <button className="icon-button" type="button" onClick={() => zoom(0.82)} aria-label="Zoom out" title="Zoom out"><Minus size={16} /></button>
      <button className="icon-button" type="button" onClick={fit} aria-label="Fit graph" title="Fit graph"><Maximize2 size={16} /></button>
      <button className="icon-button" type="button" onClick={() => zoom(1.22)} aria-label="Zoom in" title="Zoom in"><Plus size={16} /></button>
    </div>
    <div className="graph-canvas" ref={container} aria-label="Memory graph" role="application" tabIndex={0} aria-keyshortcuts="+ - 0 ArrowLeft ArrowRight" onKeyDown={(event) => {
      if (event.key === "+" || event.key === "=") { event.preventDefault(); zoom(1.22); }
      if (event.key === "-") { event.preventDefault(); zoom(0.82); }
      if (event.key === "0" || event.key === "Home") { event.preventDefault(); fit(); }
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); selectAdjacent(-1); }
      if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); selectAdjacent(1); }
    }} />
  </section>;
}
