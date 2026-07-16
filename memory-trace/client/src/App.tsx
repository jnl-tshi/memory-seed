import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { LayoutPanelLeft, List, Network, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, RotateCcw, Search, X } from "lucide-react";
import { api, DEFAULT_GRAPH_EDGE_TYPES, graphQuery, isCanonicalEntryId, searchQuery, type ChunkResponse, type Facets, type RendererGraphEdge, type RendererGraphNode, type RendererGraphResponse, type RuntimeInfo, type SearchResponse, type SearchResult } from "./api";

const GraphWorkspace = lazy(() => import("./GraphWorkspace").then((module) => ({ default: module.GraphWorkspace })));
type InspectorDock = "auto" | "right" | "bottom" | "hidden";
type GraphScope = "overview" | "local";
type GraphViewMode = "graph" | "list";
type LabelMode = "focus" | "minimal" | "all";
type GraphRange = "recent" | "all";

const EDGE_LABELS: Record<RendererGraphEdge["edge_type"], string> = {
  related: "Related",
  supersedes: "Replaces",
  evolves: "Evolves",
  branch: "Branch",
  topic: "Topic",
  agent: "Agent",
  day: "Day",
};

function readDock(): InspectorDock {
  const value = localStorage.getItem("memory-trace:inspector-dock");
  return value === "right" || value === "bottom" || value === "hidden" ? value : "auto";
}

function titleFor(node: RendererGraphNode | null) {
  return node ? node.label : "No entry selected";
}

function recentDateFrom(runtime: RuntimeInfo | null) {
  const latest = runtime?.date_bounds[1];
  if (!latest) return null;
  const date = new Date(`${latest}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - 6);
  return date.toISOString().slice(0, 10);
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
  const [scope, setScope] = useState<GraphScope>("overview");
  const [viewMode, setViewMode] = useState<GraphViewMode>("graph");
  const [labelMode, setLabelMode] = useState<LabelMode>("focus");
  const [range, setRange] = useState<GraphRange>("recent");
  const [edgeTypes, setEdgeTypes] = useState<RendererGraphEdge["edge_type"][]>(DEFAULT_GRAPH_EDGE_TYPES);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const graphRequest = useRef(0);
  const searchInput = useRef<HTMLInputElement>(null);

  const loadGraph = useCallback(async ({
    nextScope,
    nextTopic,
    nextEdgeTypes,
    entryId,
    preferredEntryId,
    keepCurrentOnEmpty = false,
    dateFrom,
  }: {
    nextScope: GraphScope;
    nextTopic: string | null;
    nextEdgeTypes: RendererGraphEdge["edge_type"][];
    entryId?: string | null;
    preferredEntryId?: string | null;
    keepCurrentOnEmpty?: boolean;
    dateFrom?: string | null;
  }) => {
    const request = ++graphRequest.current;
    setIsLoading(true);
    try {
      setError(null);
      const nextGraph = await graphQuery({
        entryId: entryId ?? (nextScope === "local" ? preferredEntryId : null),
        edgeTypes: nextEdgeTypes,
        topic: nextTopic,
        dateFrom,
      });
      if (request !== graphRequest.current) return null;
      if (keepCurrentOnEmpty && nextGraph.nodes.length === 0) return nextGraph;
      setGraph(nextGraph);
      setSelected((prior) => nextGraph.nodes.find((node) => node.source.entry_id === preferredEntryId) ?? nextGraph.nodes.find((node) => node.id === prior?.id) ?? nextGraph.nodes[0] ?? null);
      return nextGraph;
    } catch (reason) {
      if (request === graphRequest.current) setError(reason instanceof Error ? reason.message : "Unable to update the relationship map.");
      return null;
    } finally {
      if (request === graphRequest.current) setIsLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [nextRuntime, nextFacets] = await Promise.all([api<RuntimeInfo>("/runtime"), api<Facets>("/facets")]);
      setRuntime(nextRuntime);
      setFacets(nextFacets);
      await loadGraph({
        nextScope: scope,
        nextTopic: activeTopic,
        nextEdgeTypes: edgeTypes,
        preferredEntryId: selected?.source.entry_id,
        dateFrom: scope === "overview" && range === "recent" ? recentDateFrom(nextRuntime) : null,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Memory Trace.");
    }
  }, [activeTopic, edgeTypes, loadGraph, range, scope, selected?.source.entry_id]);

  useEffect(() => { void load(); }, []); // Initial project load only; controls issue deliberate scoped requests.
  useEffect(() => { localStorage.setItem("memory-trace:inspector-dock", dock); }, [dock]);
  useEffect(() => {
    if (!selected) { setChunk(null); return; }
    let cancelled = false;
    void api<ChunkResponse>(`/chunks/${encodeURIComponent(selected.source.chunk_id)}`).then((nextChunk) => { if (!cancelled) setChunk(nextChunk); }).catch(() => { if (!cancelled) setChunk(null); });
    return () => { cancelled = true; };
  }, [selected]);

  const select = useCallback((node: RendererGraphNode) => { setSelected(node); setSearch(null); }, []);
  const topics = useMemo(() => Object.entries(facets?.topics ?? {}).slice(0, 10), [facets]);
  const inspectorVisible = dock !== "hidden";

  async function requestGraph(nextScope: GraphScope, nextTopic = activeTopic, nextEdgeTypes = edgeTypes, entryId?: string | null, preferredEntryId?: string | null, keepCurrentOnEmpty = false, dateFrom = nextScope === "overview" && range === "recent" ? recentDateFrom(runtime) : null) {
    return loadGraph({ nextScope, nextTopic, nextEdgeTypes, entryId, preferredEntryId: preferredEntryId ?? selected?.source.entry_id, keepCurrentOnEmpty, dateFrom });
  }

  async function focusEntry(entryId: string) {
    const nextGraph = await requestGraph("local", null, edgeTypes, entryId, entryId, true, null);
    if (!nextGraph) return;
    if (!nextGraph.nodes.some((node) => node.source.entry_id === entryId)) {
      setError(`No entry exists with id ${entryId}.`);
      return;
    }
    setScope("local");
    setActiveTopic(null);
    setSearch(null);
  }

  async function runSearch(rawValue: string) {
    const value = rawValue.trim();
    if (!value) { setSearch(null); return; }
    if (isCanonicalEntryId(value)) {
      await focusEntry(value);
      return;
    }
    try {
      setError(null);
      setIsSearching(true);
      setSearch(await searchQuery(value));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search Memory Trace.");
    } finally {
      setIsSearching(false);
    }
  }

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSearch(searchInput.current?.value ?? query);
  }

  async function chooseSearchResult(result: SearchResult) {
    if (result.entry_id) {
      setQuery(result.entry_id);
      await focusEntry(result.entry_id);
      return;
    }
    const node = graph?.nodes.find((item) => item.source.chunk_id === result.chunk_id);
    if (node) select(node);
  }

  async function changeScope(nextScope: GraphScope) {
    const entryId = nextScope === "local" ? selected?.source.entry_id : null;
    if (nextScope === "local" && !entryId) {
      setError("Choose an entry before narrowing the graph.");
      return;
    }
    setScope(nextScope);
    await requestGraph(nextScope, activeTopic, edgeTypes, entryId, entryId);
  }

  async function chooseTopic(nextTopic: string | null) {
    setActiveTopic(nextTopic);
    await requestGraph(scope, nextTopic, edgeTypes, scope === "local" ? selected?.source.entry_id : null);
  }

  async function toggleEdge(edgeType: RendererGraphEdge["edge_type"]) {
    const nextEdgeTypes = edgeTypes.includes(edgeType) ? edgeTypes.filter((item) => item !== edgeType) : [...edgeTypes, edgeType];
    setEdgeTypes(nextEdgeTypes);
    await requestGraph(scope, activeTopic, nextEdgeTypes, scope === "local" ? selected?.source.entry_id : null);
  }

  async function changeRange(nextRange: GraphRange) {
    setRange(nextRange);
    await requestGraph(scope, activeTopic, edgeTypes, scope === "local" ? selected?.source.entry_id : null, undefined, false, nextRange === "recent" ? recentDateFrom(runtime) : null);
  }

  return (
    <div className={`trace-shell inspector-${dock} ${leftOpen ? "navigation-open" : "navigation-hidden"}`}>
      <header className="topbar">
        <div className="brand"><Network size={19} aria-hidden="true" /><span>Memory Trace</span><small>Next</small></div>
        <div className="project-summary">{runtime ? `${runtime.label} · ${runtime.entry_count} entries` : "Loading project"}</div>
        <div className="trace-search-wrap">
          <form className="trace-search" onSubmit={submitSearch} role="search"><Search size={16} aria-hidden="true" /><input ref={searchInput} value={query} onChange={(event) => { setQuery(event.target.value); setSearch(null); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void runSearch(event.currentTarget.value); } }} placeholder="Search memory or entry ID" aria-label="Search memory or entry ID" />{query && <button className="icon-button search-clear" type="button" onClick={() => { setQuery(""); setSearch(null); }} aria-label="Clear search" title="Clear search"><X size={14} /></button>}</form>
          {search && <div className="search-results" role="listbox" aria-label="Search results">{search.results.length ? search.results.map((result) => <button type="button" key={result.chunk_id} className="search-result" onClick={() => void chooseSearchResult(result)}><strong>{result.entry_title || result.heading_path[result.heading_path.length - 1] || result.chunk_id}</strong><small>{result.entry_id || result.date}</small></button>) : <div className="search-empty">No matching entries</div>}</div>}
        </div>
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
        <section className="navigation-section"><h2>Topics</h2><div className="topic-list"><button type="button" className={activeTopic === null ? "topic active" : "topic"} onClick={() => void chooseTopic(null)} aria-pressed={activeTopic === null}>All</button>{topics.map(([topic, count]) => <button type="button" className={activeTopic === topic ? "topic active" : "topic"} key={topic} onClick={() => void chooseTopic(topic)} aria-pressed={activeTopic === topic}>{topic}<b>{count}</b></button>)}</div></section>
        <section className="navigation-section entry-list"><h2>Entries</h2>{graph?.nodes.slice(0, 24).map((node) => <button key={node.id} type="button" className={node.id === selected?.id ? "entry selected" : "entry"} aria-pressed={node.id === selected?.id} onClick={() => select(node)}><span>{node.label}</span><small>{node.temporal.value}</small></button>)}</section>
      </aside>}

      <main className="workspace" id="trace-workspace">
        <div className="workspace-bar"><div><span className="eyebrow">Graph workspace</span><h1>Relationship map</h1></div><div className="workspace-actions"><div className="segment-control" aria-label="Graph scope"><button type="button" aria-pressed={scope === "overview"} onClick={() => void changeScope("overview")}>Overview</button><button type="button" aria-pressed={scope === "local"} onClick={() => void changeScope("local")}>Local</button></div><div className="segment-control" aria-label="Graph date range"><button type="button" aria-pressed={range === "recent"} onClick={() => void changeRange("recent")}>Recent</button><button type="button" aria-pressed={range === "all"} onClick={() => void changeRange("all")}>All dates</button></div><div className="segment-control" aria-label="Graph presentation"><button type="button" aria-pressed={viewMode === "graph"} onClick={() => setViewMode("graph")}><Network size={14} aria-hidden="true" /><span>Graph</span></button><button type="button" aria-pressed={viewMode === "list"} onClick={() => setViewMode("list")}><List size={14} aria-hidden="true" /><span>List</span></button></div><label className="label-menu"><span>Labels</span><select value={labelMode} onChange={(event) => setLabelMode(event.target.value as LabelMode)} aria-label="Graph labels"><option value="focus">Focus</option><option value="minimal">Minimal</option><option value="all">All</option></select></label><span className="status-pill">{isLoading ? "Updating" : "Cytoscape.js"}</span></div></div>
        <div className="graph-filter-bar" aria-label="Graph filters"><span>Edges</span>{DEFAULT_GRAPH_EDGE_TYPES.map((edgeType) => <button type="button" key={edgeType} className={`edge-filter edge-${edgeType}`} aria-pressed={edgeTypes.includes(edgeType)} onClick={() => void toggleEdge(edgeType)}>{EDGE_LABELS[edgeType]}</button>)}{activeTopic && <button type="button" className="active-topic" onClick={() => void chooseTopic(null)}>{activeTopic}<X size={13} aria-hidden="true" /></button>}</div>
        {error && <div className="error-state" role="alert">{error}</div>}
        {graph && <Suspense fallback={<div className="loading-state">Loading graph</div>}><GraphWorkspace graph={graph} selectedId={selected?.id ?? null} onSelect={select} labelMode={labelMode} viewMode={viewMode} /></Suspense>}
        {!graph && <div className="loading-state">Loading graph</div>}
      </main>

      {inspectorVisible && <aside className="inspector" id="trace-inspector" aria-label="Inspector">
        <div className="inspector-bar"><div><span className="eyebrow">Inspector</span><h2>{titleFor(selected)}</h2></div><button className="icon-button" type="button" onClick={() => setDock("hidden")} aria-label="Hide inspector" title="Hide inspector"><X size={17} /></button></div>
        <div className="dock-control" aria-label="Inspector position"><span>Dock</span>{(["auto", "right", "bottom"] as const).map((option) => <button key={option} type="button" aria-pressed={dock === option} onClick={() => setDock(option)}>{option}</button>)}</div>
        {selected && <div className="inspector-content"><dl className="metadata"><div><dt>Entry ID</dt><dd>{selected.source.entry_id || "Not recorded"}</dd></div><div><dt>Date</dt><dd>{selected.temporal.value}</dd></div><div><dt>Agent</dt><dd>{selected.source.agent}</dd></div><div><dt>Links</dt><dd>{selected.connectivity}</dd></div><div><dt>Topics</dt><dd>{selected.source.topics.join(", ") || "None"}</dd></div><div><dt>Diagrams</dt><dd>{chunk?.diagrams.length ?? 0}</dd></div></dl><p>{chunk?.excerpt ?? "Loading entry details"}</p></div>}
      </aside>}
    </div>
  );
}
