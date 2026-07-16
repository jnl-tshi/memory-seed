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
};

const COMMUNITY_COLOURS = ["#23a99a", "#6688e8", "#d99a2b", "#c76d99", "#8f76d4", "#6aa869"];

function colourForCommunity(node: RendererGraphNode) {
  let hash = 0;
  for (const character of node.community.fingerprint || node.community.id) hash = (hash * 31 + character.charCodeAt(0)) | 0;
  return COMMUNITY_COLOURS[Math.abs(hash) % COMMUNITY_COLOURS.length];
}

function visibleEdges(graph: RendererGraphResponse, selectedId: string | null) {
  return graph.edges.filter((edge) => edge.edge_type !== "evolves" || (selectedId !== null && (edge.source === selectedId || edge.target === selectedId)));
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

export function GraphWorkspace({ graph, selectedId, onSelect, labelMode, viewMode }: GraphWorkspaceProps) {
  const container = useRef<HTMLDivElement>(null);
  const cytoscape = useRef<Core | null>(null);
  const visible = useMemo(() => visibleEdges(graph, selectedId), [graph, selectedId]);
  const renderedNodeIds = useMemo(() => new Set([...visible.flatMap((edge) => [edge.source, edge.target]), ...(selectedId ? [selectedId] : [])]), [selectedId, visible]);
  const renderedNodes = useMemo(() => graph.nodes.filter((node) => renderedNodeIds.has(node.id)), [graph.nodes, renderedNodeIds]);
  const renderedEdges = visible;
  const labelIds = useMemo(() => labelIdsFor(graph, selectedId, labelMode), [graph, labelMode, selectedId]);

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

  useEffect(() => {
    let disposed = false;

    async function mount() {
      const { default: createCytoscape } = await import("cytoscape");
      if (disposed || !container.current) return;
      const cy = createCytoscape({
        container: container.current,
        elements: [
          ...renderedNodes.map((node) => ({
            data: {
              id: node.id,
              label: node.id === selectedId || labelIds.has(node.id) ? node.label : "",
              title: node.label,
              agent: node.source.agent,
              selected: node.id === selectedId ? "yes" : "no",
              colour: colourForCommunity(node),
              size: 22 + Math.min(18, node.connectivity * 3),
            },
          })),
          ...renderedEdges.map((edge, index) => ({
            data: { id: edge.id || `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, type: edge.edge_type },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(colour)",
              "border-color": "#d9f1ec",
              "border-width": 2,
              "label": "data(label)",
              "font-family": "Inter, sans-serif",
              "font-size": 11,
              "font-weight": 600,
              "color": "#e9f3f0",
              "text-wrap": "ellipsis",
              "text-max-width": "132px",
              "text-outline-color": "#10201e",
              "text-outline-width": 3,
              "text-valign": "bottom",
              "text-margin-y": 8,
              "width": "data(size)",
              "height": "data(size)",
            },
          },
          {
            selector: 'node[selected = "yes"]',
            style: { "border-color": "#ffe4a2", "border-width": 5, "overlay-color": "#efb345", "overlay-opacity": 0.26, "overlay-padding": 5 },
          },
          { selector: "edge", style: { "curve-style": "unbundled-bezier", "control-point-distances": 38, "control-point-weights": 0.5, "line-color": "#7a9cba", "target-arrow-color": "#7a9cba", "target-arrow-shape": "triangle", "width": 2, "opacity": 0.85 } },
          { selector: 'edge[type = "related"]', style: { "line-color": "#74a6ce", "target-arrow-color": "#74a6ce" } },
          { selector: 'edge[type = "supersedes"]', style: { "line-style": "dashed", "line-color": "#e18494", "target-arrow-color": "#e18494" } },
          { selector: 'edge[type = "evolves"]', style: { "line-style": "dotted", "line-color": "#7cc6e8", "target-arrow-color": "#7cc6e8", "width": 2.5 } },
          { selector: 'edge[type = "topic"]', style: { "line-style": "dotted", "line-color": "#a88acc", "target-arrow-color": "#a88acc", "opacity": 0.58 } },
        ],
        layout: { name: "preset" },
        minZoom: 0.35,
        maxZoom: 2.4,
        wheelSensitivity: 0.16,
      });
      cy.on("tap", "node", (event) => {
        const node = graph.nodes.find((item) => item.id === event.target.id());
        if (node) onSelect(node);
      });
      cytoscape.current = cy;
      const layout = cy.layout({ name: "cose", animate: false, padding: 52, nodeRepulsion: () => 12_000, idealEdgeLength: () => 150, gravity: 0.3, numIter: 900 });
      layout.one("layoutstop", () => { if (!disposed) cy.fit(cy.elements(), 52); });
      layout.run();
    }

    if (viewMode === "graph") void mount();
    return () => {
      disposed = true;
      cytoscape.current?.destroy();
      cytoscape.current = null;
    };
  }, [graph, labelIds, onSelect, renderedEdges, renderedNodes, selectedId, viewMode]);

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
