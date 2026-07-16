import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { LayoutPanelLeft, Network, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, RotateCcw, X } from "lucide-react";
import { api, graphQuery, type ChunkResponse, type Facets, type RendererGraphNode, type RendererGraphResponse, type RuntimeInfo } from "./api";

const GraphWorkspace = lazy(() => import("./GraphWorkspace").then((module) => ({ default: module.GraphWorkspace })));
type InspectorDock = "auto" | "right" | "bottom" | "hidden";

function readDock(): InspectorDock {
  const value = localStorage.getItem("memory-trace:inspector-dock");
  return value === "right" || value === "bottom" || value === "hidden" ? value : "auto";
}

function titleFor(node: RendererGraphNode | null) {
  return node ? node.label : "No entry selected";
}

export default function App() {
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);
  const [facets, setFacets] = useState<Facets | null>(null);
  const [graph, setGraph] = useState<RendererGraphResponse | null>(null);
  const [selected, setSelected] = useState<RendererGraphNode | null>(null);
  const [chunk, setChunk] = useState<ChunkResponse | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [dock, setDock] = useState<InspectorDock>(readDock);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [nextRuntime, nextFacets, nextGraph] = await Promise.all([api<RuntimeInfo>("/runtime"), api<Facets>("/facets"), graphQuery()]);
      setRuntime(nextRuntime);
      setFacets(nextFacets);
      setGraph(nextGraph);
      setSelected((prior) => nextGraph.nodes.find((node) => node.id === prior?.id) ?? nextGraph.nodes[0] ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Memory Trace.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { localStorage.setItem("memory-trace:inspector-dock", dock); }, [dock]);
  useEffect(() => {
    if (!selected) { setChunk(null); return; }
    void api<ChunkResponse>(`/chunks/${encodeURIComponent(selected.source.chunk_id)}`).then(setChunk).catch(() => setChunk(null));
  }, [selected]);

  const select = useCallback((node: RendererGraphNode) => setSelected(node), []);
  const topics = useMemo(() => Object.entries(facets?.topics ?? {}).slice(0, 10), [facets]);
  const inspectorVisible = dock !== "hidden";

  return (
    <div className={`trace-shell inspector-${dock} ${leftOpen ? "navigation-open" : "navigation-hidden"}`}>
      <header className="topbar">
        <div className="brand"><Network size={19} aria-hidden="true" /><span>Memory Trace</span><small>Next</small></div>
        <div className="project-summary">{runtime ? `${runtime.label} · ${runtime.entry_count} entries` : "Loading project"}</div>
        <div className="topbar-actions">
          <button className="icon-button" type="button" onClick={() => setLeftOpen((value) => !value)} aria-label="Toggle navigation" title="Toggle navigation">
            {leftOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
          <button className="icon-button" type="button" onClick={() => setDock((value) => value === "hidden" ? "auto" : "hidden")} aria-label="Toggle inspector" title="Toggle inspector">
            {inspectorVisible ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
          </button>
          <button className="icon-button" type="button" onClick={() => void load()} aria-label="Refresh project" title="Refresh project"><RotateCcw size={17} /></button>
        </div>
      </header>

      {leftOpen && <aside className="navigation-pane" aria-label="Navigation">
        <div className="pane-heading"><LayoutPanelLeft size={16} aria-hidden="true" /> <span>Project</span></div>
        <dl className="metric-list"><div><dt>Entries</dt><dd>{runtime?.entry_count ?? "-"}</dd></div><div><dt>Chunks</dt><dd>{facets?.runtime.chunk_count ?? "-"}</dd></div></dl>
        <section className="navigation-section"><h2>Topics</h2><div className="topic-list">{topics.map(([topic, count]) => <span className="topic" key={topic}>{topic}<b>{count}</b></span>)}</div></section>
        <section className="navigation-section entry-list"><h2>Entries</h2>{graph?.nodes.slice(0, 24).map((node) => <button key={node.id} type="button" className={node.id === selected?.id ? "entry selected" : "entry"} aria-pressed={node.id === selected?.id} onClick={() => select(node)}><span>{node.label}</span><small>{node.temporal.value}</small></button>)}</section>
      </aside>}

      <main className="workspace" id="trace-workspace">
        <div className="workspace-bar"><div><span className="eyebrow">Graph workspace</span><h1>Relationship map</h1></div><span className="status-pill">Cytoscape.js</span></div>
        {error && <div className="error-state" role="alert">{error}</div>}
        {!error && graph && <Suspense fallback={<div className="loading-state">Loading graph</div>}><GraphWorkspace graph={graph} selectedId={selected?.id ?? null} onSelect={select} /></Suspense>}
        {!error && !graph && <div className="loading-state">Loading graph</div>}
      </main>

      {inspectorVisible && <aside className="inspector" id="trace-inspector" aria-label="Inspector">
        <div className="inspector-bar"><div><span className="eyebrow">Inspector</span><h2>{titleFor(selected)}</h2></div><button className="icon-button" type="button" onClick={() => setDock("hidden")} aria-label="Hide inspector" title="Hide inspector"><X size={17} /></button></div>
        <div className="dock-control" aria-label="Inspector position"><span>Dock</span>{(["auto", "right", "bottom"] as const).map((option) => <button key={option} type="button" aria-pressed={dock === option} onClick={() => setDock(option)}>{option}</button>)}</div>
        {selected && <div className="inspector-content"><dl className="metadata"><div><dt>Date</dt><dd>{selected.temporal.value}</dd></div><div><dt>Agent</dt><dd>{selected.source.agent}</dd></div><div><dt>Links</dt><dd>{selected.connectivity}</dd></div><div><dt>Topics</dt><dd>{selected.source.topics.join(", ") || "None"}</dd></div></dl><p>{chunk?.excerpt ?? "Loading entry details"}</p></div>}
      </aside>}
    </div>
  );
}
