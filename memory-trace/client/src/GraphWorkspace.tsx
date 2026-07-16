import { useEffect, useRef } from "react";
import type { Core } from "cytoscape";
import type { GraphNode, GraphResponse } from "./api";

type GraphWorkspaceProps = {
  graph: GraphResponse;
  selectedId: string | null;
  onSelect: (node: GraphNode) => void;
};

function visibleLabel(node: GraphNode, selectedId: string | null, labelIds: Set<string>) {
  return node.id === selectedId || labelIds.has(node.id) ? node.title : "";
}

export function GraphWorkspace({ graph, selectedId, onSelect }: GraphWorkspaceProps) {
  const container = useRef<HTMLDivElement>(null);
  const cytoscape = useRef<Core | null>(null);

  useEffect(() => {
    let disposed = false;
    const labelIds = new Set(
      [...graph.nodes]
        .sort((left, right) => right.connectivity - left.connectivity || right.importance_score - left.importance_score)
        .slice(0, 12)
        .map((node) => node.id),
    );

    async function mount() {
      const { default: createCytoscape } = await import("cytoscape");
      if (disposed || !container.current) return;
      const cy = createCytoscape({
        container: container.current,
        elements: [
          ...graph.nodes.map((node) => ({
            data: {
              id: node.id,
              label: visibleLabel(node, selectedId, labelIds),
              title: node.title,
              agent: node.agent,
              selected: node.id === selectedId ? "yes" : "no",
            },
          })),
          ...graph.edges.map((edge, index) => ({
            data: { id: `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target, type: edge.type },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#25786e",
              "border-color": "#a8e7d8",
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
              "width": 20,
              "height": 20,
            },
          },
          {
            selector: 'node[selected = "yes"]',
            style: { "background-color": "#efb345", "border-color": "#fff0be", "border-width": 4, "width": 28, "height": 28 },
          },
          { selector: "edge", style: { "curve-style": "bezier", "line-color": "#52756f", "width": 1.5, "opacity": 0.7 } },
          { selector: 'edge[type = "supersedes"]', style: { "line-style": "dashed", "target-arrow-shape": "triangle", "target-arrow-color": "#e28686" } },
          { selector: 'edge[type = "evolves"]', style: { "line-style": "dotted", "target-arrow-shape": "triangle", "target-arrow-color": "#93bce8" } },
          { selector: 'edge[type = "topic"]', style: { "line-color": "#9573c2", "opacity": 0.45 } },
        ],
        layout: { name: "cose", animate: false, padding: 52, nodeRepulsion: () => 7000, idealEdgeLength: () => 110 },
        minZoom: 0.35,
        maxZoom: 2.4,
        wheelSensitivity: 0.16,
      });
      cy.on("tap", "node", (event) => {
        const node = graph.nodes.find((item) => item.id === event.target.id());
        if (node) onSelect(node);
      });
      cytoscape.current = cy;
    }

    void mount();
    return () => {
      disposed = true;
      cytoscape.current?.destroy();
      cytoscape.current = null;
    };
  }, [graph, onSelect, selectedId]);

  return <div className="graph-canvas" ref={container} aria-label="Memory graph" role="application" />;
}
