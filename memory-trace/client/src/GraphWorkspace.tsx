import { useEffect, useMemo, useRef } from "react";
import type { Core } from "cytoscape";
import { Maximize2, Minus, Plus } from "lucide-react";
import { connectedNodeIds, type RendererGraphEdge, type RendererGraphNode, type RendererGraphResponse } from "./api";
import { layoutIterations, nodeSetSignature, seedPositions, type Point } from "./graphLayout";
import { outrankedEdgeIds } from "./graphEdges";
import { communityColourScale, communityLegend, inferredCommunityColours } from "./graphCommunities";

type GraphWorkspaceProps = {
  graph: RendererGraphResponse;
  selectedId: string | null;
  onSelect: (node: RendererGraphNode) => void;
  labelMode: "focus" | "minimal" | "all";
  theme: "light" | "dark";
  // Corpus-wide topic counts, so community colours are assigned from the whole
  // corpus rather than from whatever subset is currently loaded.
  corpusTopics: Readonly<Record<string, number>> | null;
  // Which edge types are switched on in the "Edges" filter row. Obsidian-style:
  // this only toggles line visibility on the graph already in memory — it must
  // never drive which nodes are rendered or trigger a re-layout.
  visibleEdgeTypes: RendererGraphEdge["edge_type"][];
};

// Cytoscape styles can't consume CSS custom properties, so resolve the theme
// tokens at mount time; the mount effect re-runs on theme change (safe — the
// deterministic layout reproduces identical positions).
function themeToken(name: string, fallback: string) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

// colourForCommunity moved to graphCommunities.ts so the legend and the nodes
// share one derivation. Two copies of the hash is exactly how a legend swatch
// ends up disagreeing with the node it claims to describe.

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

// Settled positions from the last completed layout, keyed by the node-id set
// they were computed for. Module-level so a remount (theme change, view
// round-trip) with the SAME node set restores positions instantly via a
// preset layout instead of re-running the simulation, and a GROWN node set
// ("Show more") seeds its old nodes where they already settled so only the
// additions need real layout work. The seeding rules themselves live in
// graphLayout.ts so they can be unit tested.
let settledSignature = "";
const settledPositions = new Map<string, Point>();

export function GraphWorkspace({ graph, selectedId, onSelect, labelMode, theme, visibleEdgeTypes, corpusTopics }: GraphWorkspaceProps) {
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
  const visibleEdgeTypesRef = useRef(visibleEdgeTypes);
  visibleEdgeTypesRef.current = visibleEdgeTypes;
  // Selection restyle was the one metric that grew with corpus size: 5-13ms
  // below ~400 nodes but 47-102ms at 1000 edges, because every selection swept
  // the whole edge set. The sweep's result depends only on the edge set and the
  // visible-type filter - never on which node is selected - so it is memoized
  // on exactly those two inputs and drops out of the selection path entirely.
  const outrankedMemo = useRef<{ edges: unknown; typesKey: string; value: Set<string> } | null>(null);

  // In-place presentation pass — selection ring, labels, edge filter. Reads
  // current state from refs so both the mount (async) and the update effect
  // can apply it without racing each other.
  const applyPresentation = (cy: Core) => {
    const currentSelected = selectedIdRef.current;
    const currentLabels = labelIdsRef.current;
    const currentVisibleTypes = visibleEdgeTypesRef.current;
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const id = node.id();
        node.data("selected", id === currentSelected ? "yes" : "no");
        node.data("label", id === currentSelected || currentLabels.has(id) ? node.data("title") : "");
      });
      // Edge visibility is the "Edges" filter row's business ALONE: a type
      // that is switched on is drawn for every node pair that has it, always.
      // Evolves edges used to additionally hide unless they touched the
      // selection, which contradicted their own chip reading as ON and made
      // the map's lineage invisible until you happened to click the right
      // node. Turning a chip off still hides that type outright, Obsidian
      // style, and never touches which nodes exist or where they sit.
      //
      // One line per PAIR: two entries often carry several relationships at
      // once, which drew coincident lines and let the weakest one (a topic
      // tag) paint over the strongest (a supersession). Only the most
      // consequential relationship survives - see EDGE_PRIORITY. The winner is
      // chosen among the types currently switched ON, so switching a type off
      // promotes whatever it was covering rather than blanking the pair.
      // Keyed on the graph's edge ARRAY IDENTITY, which changes only when a new
      // graph is fetched, so a stale set can never survive a reload.
      const typesKey = currentVisibleTypes.join(",");
      const memo = outrankedMemo.current;
      let outranked: Set<string>;
      if (memo && memo.edges === graphRef.current.edges && memo.typesKey === typesKey) {
        outranked = memo.value;
      } else {
        outranked = outrankedEdgeIds(
          cy.edges().map((edge) => ({
            id: edge.id(),
            source: edge.data("source"),
            target: edge.data("target"),
            type: edge.data("type"),
          })),
          currentVisibleTypes,
        );
        outrankedMemo.current = { edges: graphRef.current.edges, typesKey, value: outranked };
      }
      cy.edges().forEach((edge) => {
        edge.toggleClass("edge-filtered", !currentVisibleTypes.includes(edge.data("type")));
        edge.toggleClass("edge-outranked", outranked.has(edge.id()));
      });
    });
  };

  // The rendered element set is SELECTION-INDEPENDENT: every node that carries
  // any edge renders, always. Selecting must never add/remove elements or move
  // the map — selection only restyles (ring, labels).
  const renderedNodes = useMemo(() => {
    const connected = connectedNodeIds(graph);
    return graph.nodes.filter((node) => connected.has(node.id));
  }, [graph]);
  // Counted over renderedNodes, not graph.nodes: a node with no edge is not
  // drawn, so counting the payload would advertise swatches for communities
  // that are nowhere on screen.
  const legend = useMemo(() => communityLegend(renderedNodes, corpusTopics), [renderedNodes, corpusTopics]);
  const colourOf = useMemo(() => communityColourScale(corpusTopics), [corpusTopics]);
  // Topicless nodes take a pastel blend of the communities that reach them
  // (directly, or as decaying residue down a topicless chain). Pastel is a
  // property of the community colour alone, so no theme dependency here.
  const inferredColours = useMemo(
    () => inferredCommunityColours(renderedNodes, graph.edges, colourOf),
    [renderedNodes, graph.edges, colourOf],
  );
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
      const signature = nodeSetSignature(renderedNodes);
      const { positions, settled, warmSeeded } = seedPositions(renderedNodes, settledPositions, settledSignature);
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
              colour: inferredColours.get(node.id) ?? colourOf(node),
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
          { selector: "edge.edge-filtered", style: { display: "none" } },
          { selector: "edge.edge-outranked", style: { display: "none" } },
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
      const finishLayout = () => {
        if (disposed) return;
        cy.fit(cy.elements(), 52);
        settledSignature = signature;
        settledPositions.clear();
        cy.nodes().forEach((node) => {
          const position = node.position();
          settledPositions.set(node.id(), { x: position.x, y: position.y });
        });
      };
      if (settled) {
        // Preset positions ARE the settled layout: fit and done, zero
        // simulation - this is what makes theme toggles and Trail/Graph
        // round trips instant regardless of graph size.
        finishLayout();
        return;
      }
      const layout = cy.layout({
        name: "cose",
        animate: false,
        padding: 52,
        randomize: false,
        nodeRepulsion: () => 12_000,
        idealEdgeLength: () => 150,
        gravity: 0.3,
        numIter: layoutIterations(renderedNodes.length, warmSeeded),
      });
      layout.one("layoutstop", finishLayout);
      layout.run();
    }

    void mount();
    return () => {
      disposed = true;
      cytoscape.current?.destroy();
      cytoscape.current = null;
    };
  }, [graph, renderedNodes, theme]);

  // Presentation updates on selection/label/edge-filter changes: in place, no
  // element churn, no layout, no camera movement.
  useEffect(() => {
    const cy = cytoscape.current;
    if (!cy) return;
    applyPresentation(cy);
  }, [labelIds, selectedId, graph, visibleEdgeTypes]);

  return <section className="graph-workspace" aria-label="Memory graph workspace">
    {/* Overlaid on the canvas rather than added as a row: .workspace's grid
        reserves exactly three rows (bar / filters / content), so a fourth
        sibling collapses the canvas to zero height. A legend also belongs
        beside the thing it explains. */}
    {legend.length > 0 && (
      <div className="graph-legend" aria-label="Topic community legend">
        <span className="graph-legend-title">Topics</span>
        {legend.map((entry) => (
          <span key={entry.id} className={`graph-legend-item${entry.topic ? "" : " graph-legend-item-none"}`}>
            <span className="graph-legend-key" style={{ background: entry.colour }} aria-hidden="true" />
            {entry.label}
            <b>{entry.count}</b>
          </span>
        ))}
      </div>
    )}
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
