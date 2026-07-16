import { DataSet, Network } from "vis-network/standalone";
import cytoscape from "cytoscape";
import fixture from "../tests/fixtures/graph-renderer/bounded-neighbourhood.v1.json";
import "./renderer-benchmark.css";

const colors = ["#6f7cff", "#18a999", "#d9941a", "#8f63e8"];
const edgeColors = {
  related: "#8ab4ff", supersedes: "#f28b99", evolves: "#82b1ff", branch: "#81c995", topic: "#c58af9", agent: "#72d8c9", day: "#f6c76f",
};
const defaultCase = fixture.benchmark_cases[0].id;
let activeCase = defaultCase;
let selectedId = fixture.selection.selected_node_id;
let filtered = false;
let visNetwork;
let cy;

function nodeColor(node) {
  const communities = [...new Set(fixture.nodes.map((item) => item.community.id))];
  return colors[communities.indexOf(node.community.id) % colors.length];
}

function temporalX(node) {
  const dates = fixture.nodes.map((item) => Date.parse(item.temporal.value));
  const min = Math.min(...dates);
  const max = Math.max(...dates);
  const value = Date.parse(node.temporal.value);
  return max === min ? 0 : ((value - min) / (max - min) - 0.5) * 420;
}

function visibleGraph() {
  if (!filtered) return fixture;
  const connected = new Set([selectedId]);
  fixture.edges.forEach((edge) => {
    if (edge.source === selectedId) connected.add(edge.target);
    if (edge.target === selectedId) connected.add(edge.source);
  });
  return {
    ...fixture,
    nodes: fixture.nodes.filter((node) => connected.has(node.id)),
    edges: fixture.edges.filter((edge) => connected.has(edge.source) && connected.has(edge.target)),
  };
}

function currentCase() {
  return fixture.benchmark_cases.find((item) => item.id === activeCase);
}

function visOptions() {
  const mode = currentCase().layout;
  const hierarchy = mode === "evolution_hierarchy";
  return {
    autoResize: true,
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.55 } }, color: { inherit: false }, smooth: { type: "dynamic" }, width: 1.6 },
    interaction: { hover: true, keyboard: { enabled: true }, multiselect: false, navigationButtons: true },
    layout: hierarchy ? { hierarchical: { enabled: true, direction: "LR", sortMethod: "directed", levelSeparation: 180 } } : { randomSeed: 20260716 },
    nodes: { borderWidth: 2, font: { color: "#eaf0ff", face: "Inter", size: 14 }, shape: "dot", size: 17 },
    physics: hierarchy ? false : { barnesHut: { gravitationalConstant: -2400, centralGravity: 0.22, springConstant: 0.045, springLength: 145 }, stabilization: { iterations: 120 } },
  };
}

function visData(graph) {
  const temporal = currentCase().layout === "temporal_topology";
  return {
    nodes: graph.nodes.map((node) => {
      const rendererNode = {
        id: node.id, label: node.label, title: `${node.label}\n${node.temporal.value}`, color: { background: nodeColor(node), border: selectedId === node.id ? "#ffcc66" : "#dce6ff" }, value: 10 + node.connectivity * 3,
      };
      if (temporal) {
        rendererNode.x = temporalX(node);
        rendererNode.fixed = { x: true, y: false };
      }
      return rendererNode;
    }),
    edges: graph.edges.map((edge) => ({ id: edge.id, from: edge.source, to: edge.target, color: edgeColors[edge.edge_type], title: edge.edge_type, dashes: edge.edge_type === "topic" })),
  };
}

function cytoscapeElements(graph) {
  const temporal = currentCase().layout === "temporal_topology";
  return [
    ...graph.nodes.map((node) => ({ data: { id: node.id, label: node.label, color: nodeColor(node), selected: node.id === selectedId }, position: temporal ? { x: temporalX(node), y: 0 } : undefined })),
    ...graph.edges.map((edge) => ({ data: { id: edge.id, source: edge.source, target: edge.target, edgeType: edge.edge_type, color: edgeColors[edge.edge_type] } })),
  ];
}

function cytoscapeLayout() {
  const mode = currentCase().layout;
  if (mode === "evolution_hierarchy") return { name: "breadthfirst", directed: true, direction: "rightward", padding: 36, spacingFactor: 1.3, animate: false };
  return { name: "cose", animate: false, randomize: mode !== "temporal_topology", nodeRepulsion: () => 8200, idealEdgeLength: () => 145, padding: 36 };
}

function renderNodeList(panel, graph) {
  const list = panel.querySelector(".renderer-list");
  list.replaceChildren(...graph.nodes.map((node) => {
    const item = document.createElement("li");
    item.textContent = `${node.label} (${node.community.label})`;
    if (node.id === selectedId) item.classList.add("is-selected");
    return item;
  }));
}

function showStatus(panel, value) { panel.querySelector(".renderer-status").textContent = value; }

function renderVis() {
  const panel = document.querySelector("[data-renderer=vis]");
  const surface = panel.querySelector(".renderer-surface");
  const graph = visibleGraph();
  visNetwork?.destroy();
  const start = performance.now();
  visNetwork = new Network(surface, { nodes: new DataSet(visData(graph).nodes), edges: new DataSet(visData(graph).edges) }, visOptions());
  visNetwork.on("selectNode", (event) => {
    const next = event.nodes[0];
    if (next !== selectedId) {
      selectedId = next;
      renderAll();
    }
  });
  visNetwork.fit({ animation: false });
  visNetwork.once("stabilizationIterationsDone", () => showStatus(panel, `ready ${Math.round(performance.now() - start)}ms | ${graph.nodes.length} nodes | selected: ${selectedId}`));
  window.setTimeout(() => showStatus(panel, `ready ${Math.round(performance.now() - start)}ms | ${graph.nodes.length} nodes | selected: ${selectedId}`), 180);
  visNetwork.selectNodes([selectedId]);
  visNetwork.redraw();
  renderNodeList(panel, graph);
}

function renderCytoscape() {
  const panel = document.querySelector("[data-renderer=cytoscape]");
  const surface = panel.querySelector(".renderer-surface");
  const graph = visibleGraph();
  cy?.destroy();
  const start = performance.now();
  cy = cytoscape({
    container: surface,
    elements: cytoscapeElements(graph),
    style: [
      { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: "#eaf0ff", "font-size": 12, "text-valign": "bottom", "text-margin-y": 8, width: 30, height: 30, "border-width": 2, "border-color": "#dce6ff" } },
      { selector: "node:selected", style: { "border-color": "#ffcc66", "border-width": 5 } },
      { selector: "edge", style: { width: 2, "line-color": "data(color)", "target-arrow-color": "data(color)", "target-arrow-shape": "triangle", "curve-style": "bezier" } },
    ],
    minZoom: 0.15, maxZoom: 4, wheelSensitivity: 0.2,
  });
  cy.on("select", "node", (event) => {
    const next = event.target.id();
    if (next !== selectedId) {
      selectedId = next;
      renderAll();
    }
  });
  const layout = cy.layout(cytoscapeLayout());
  layout.one("layoutstop", () => showStatus(panel, `ready ${Math.round(performance.now() - start)}ms | ${graph.nodes.length} nodes | selected: ${selectedId}`));
  layout.run();
  cy.$id(selectedId).select();
  renderNodeList(panel, graph);
}

function renderAll() { renderVis(); renderCytoscape(); }

function buildApp() {
  const app = document.querySelector("#benchmark-app");
  app.innerHTML = `
    <main class="benchmark">
      <header class="benchmark-header"><h1>Renderer evidence harness</h1><p>Both adapters consume <code>${fixture.fixture_id}</code>. This is benchmark evidence, not the shipped graph.</p></header>
      <section class="benchmark-controls" aria-label="Benchmark controls"><fieldset><legend>Layout</legend>${fixture.benchmark_cases.map((item) => `<button type="button" data-case="${item.id}" aria-pressed="${item.id === activeCase}">${item.id}</button>`).join("")}</fieldset><label><input id="connected-filter" type="checkbox"> Connected to selected node</label></section>
      <p class="benchmark-note">Use pointer or keyboard navigation to pan, zoom, and select. The accessible list records the same visible nodes.</p>
      <section class="renderer-grid" aria-label="Renderer comparison">${["vis", "cytoscape"].map((name) => `<article class="renderer-panel" data-renderer="${name}"><header><h2>${name === "vis" ? "vis-network" : "Cytoscape.js"}</h2><span>${currentCase().layout}</span></header><div class="renderer-surface" tabindex="0" aria-label="${name} graph canvas"></div><p class="renderer-status" role="status">initializing</p><details><summary>Visible nodes</summary><ol class="renderer-list"></ol></details></article>`).join("")}</section>
    </main>`;
  app.querySelectorAll("[data-case]").forEach((button) => button.addEventListener("click", () => { activeCase = button.dataset.case; renderAll(); }));
  app.querySelector("#connected-filter").addEventListener("change", (event) => { filtered = event.target.checked; renderAll(); });
  renderAll();
}

buildApp();
