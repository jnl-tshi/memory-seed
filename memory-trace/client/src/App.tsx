import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent } from "react";
import { ChevronDown, ChevronUp, GitBranch, LayoutPanelLeft, Network, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, RotateCcw, Search, X } from "lucide-react";
import { SettingsMenu, type InspectorDock, type Theme, type TrailStyle } from "./SettingsMenu";
import { api, DEFAULT_GRAPH_EDGE_TYPES, graphQuery, isCanonicalEntryId, SEARCH_LIMIT, searchQuery, setActiveWorktree, trailQuery, worktreesQuery, type ChunkResponse, type Facets, type RendererGraphEdge, type RendererGraphNode, type RendererGraphResponse, type RuntimeInfo, type SearchResponse, type SearchResult, type TrailResponse, type WorktreesResponse } from "./api";
import { EntryReader } from "./EntryReader";
import { readerScrollTarget } from "./inspectorScroll";
import { searchResultCursor, stepSearchCursor } from "./searchNavigation";
import { genuineSearchResults } from "./searchResults";
import { animateScrollTo, scrollDurationFor } from "./trailScroll";
import { stripTitleStamp, trailStamp, TRAIL_WINDOW_STEP } from "./trailModel";

const GraphWorkspace = lazy(() => import("./GraphWorkspace").then((module) => ({ default: module.GraphWorkspace })));
const TrailWorkspace = lazy(() => import("./TrailWorkspace").then((module) => ({ default: module.TrailWorkspace })));
type MatchHint = { entryId: string; heading: string };
type GraphScope = "overview" | "local" | "evolution" | "file";
type GraphViewMode = "graph" | "trail";
type LabelMode = "focus" | "minimal" | "all";
type GraphRange = "recent" | "all";

// Evolution scope shows a selected entry's lifecycle chain rather than its
// full local neighborhood: only the two edge types that carry lineage, and a
// depth deep enough for a realistic supersession/evolution chain without
// pulling in the whole graph.
const EVOLUTION_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["evolves", "supersedes"];
const EVOLUTION_DEPTH = 8;

// What the fetch asks the server for, keyed only by scope — never by the
// "Edges" filter row's toggle state. That row is a client-side visibility
// filter over an already-fetched graph (Obsidian-style: lines appear and
// disappear, nodes don't), not a query parameter, so the node set and the
// cose layout stay put no matter which chips are on.
function edgeTypesForScope(targetScope: GraphScope): RendererGraphEdge["edge_type"][] {
  return targetScope === "evolution" ? EVOLUTION_EDGE_TYPES : DEFAULT_GRAPH_EDGE_TYPES;
}

const EDGE_LABELS: Record<RendererGraphEdge["edge_type"], string> = {
  related: "Related",
  supersedes: "Replaces",
  evolves: "Evolves",
  branch: "Branch",
  topic: "Topic",
  agent: "Agent",
  day: "Day",
};

// BG1 taxonomy: authority (what authority an item's meaning carries) and
// provenance (where it came from) are SEPARATE axes — surfaced distinctly, never
// merged into a single trust score. "authored"/"authored_memory" is all that is
// emitted today; the labels make the UI ready for non-authored items.
const AUTHORITY_LABELS: Record<RendererGraphNode["authority_class"], string> = {
  authored: "Authored",
  computed_canonical: "Computed · canonical",
  git_derived: "Git-derived",
  provider_extracted: "Provider · extracted",
  provider_resolved: "Provider · resolved",
  provider_inferred: "Provider · inferred",
  generated: "Generated · advisory",
};

const PROVENANCE_LABELS: Record<RendererGraphNode["provenance_class"], string> = {
  authored_memory: "Authored memory",
  source_control: "Source control",
  pr_review: "PR review",
  automation_ci: "Automation · CI",
  annotation: "Annotation",
  release: "Release",
  generated_artefact: "Generated artefact",
};

// Authored/canonical/git-derived meanings are trusted project record; provider
// and generated meanings are advisory until promoted. A muted class marks the
// advisory band without collapsing the two axes into one score.
const ADVISORY_AUTHORITY = new Set<RendererGraphNode["authority_class"]>([
  "provider_extracted",
  "provider_resolved",
  "provider_inferred",
  "generated",
]);

function readDock(): InspectorDock {
  const value = localStorage.getItem("memory-trace:inspector-dock");
  return value === "right" || value === "bottom" || value === "hidden" ? value : "auto";
}

// User-adjustable pane widths (parity with the vanilla UI's draggable panes).
const NAV_WIDTH = { min: 200, max: 460, fallback: 264 };
const INSPECTOR_WIDTH = { min: 260, max: 620, fallback: 340 };

function readPaneWidth(key: string, bounds: { min: number; max: number; fallback: number }) {
  const value = Number(localStorage.getItem(key));
  return Number.isFinite(value) && value >= bounds.min && value <= bounds.max ? value : bounds.fallback;
}

// Light (the warm humanist default) unless the user chose otherwise or their
// system prefers dark.
function readTheme(): Theme {
  const stored = localStorage.getItem("memory-trace:theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Trail stroke presentation. Lifted out of TrailWorkspace so the settings menu
// can own every preference in one place; the Trail keeps only its derivations.
// Defaults are JNL's chosen combination: Thick + Drawn, wobble 1.60, pressure
// 0.30.
function readTrailStyle(): TrailStyle {
  const clamp = (value: unknown, fallback: number, max: number) =>
    typeof value === "number" && Number.isFinite(value) ? Math.min(max, Math.max(0, value)) : fallback;
  try {
    const stored = JSON.parse(localStorage.getItem("memory-trace:trail-settings") || "{}");
    return {
      thickness: stored.thickness === "fine" ? "fine" : "thick",
      style: stored.style === "slick" ? "slick" : "hand",
      wobble: clamp(stored.wobble, 1.6, 3),
      pressure: clamp(stored.pressure, 0.3, 1),
    };
  } catch {
    return { thickness: "thick", style: "hand", wobble: 1.6, pressure: 0.3 };
  }
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
  const [matchHint, setMatchHint] = useState<MatchHint | null>(null);
  const [selectionMuted, setSelectionMuted] = useState(false);
  const [leftOpen, setLeftOpen] = useState(true);
  const [dock, setDock] = useState<InspectorDock>(readDock);
  const [navWidth, setNavWidth] = useState(() => readPaneWidth("memory-trace:nav-width", NAV_WIDTH));
  const [inspectorWidth, setInspectorWidth] = useState(() => readPaneWidth("memory-trace:inspector-width", INSPECTOR_WIDTH));
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [trailStyle, setTrailStyle] = useState<TrailStyle>(readTrailStyle);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<GraphScope>("overview");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<GraphViewMode>("trail");
  const [trail, setTrail] = useState<TrailResponse | null>(null);
  // Full-corpus entry index (one fetch at load): resolves ids to titles for the
  // left pane's context panel and supplies typed lifecycle edges.
  const [entryIndex, setEntryIndex] = useState<TrailResponse | null>(null);
  const [worktrees, setWorktrees] = useState<WorktreesResponse | null>(null);
  const [worktree, setWorktree] = useState<string | null>(null);
  // The vanilla "train of thought" worktree loader, kept with a fixed rhythm:
  // the ride always lasts at least the baseline so it stays readable now that
  // switches are fast; only genuinely longer compute extends the middle leg.
  const [switchLabel, setSwitchLabel] = useState<string | null>(null);
  const [switchStage, setSwitchStage] = useState(0);
  const [trailWindow, setTrailWindow] = useState(TRAIL_WINDOW_STEP);
  const [trailError, setTrailError] = useState<string | null>(null);
  const [labelMode, setLabelMode] = useState<LabelMode>("focus");
  const [range, setRange] = useState<GraphRange>("recent");
  const [edgeTypes, setEdgeTypes] = useState<RendererGraphEdge["edge_type"][]>(DEFAULT_GRAPH_EDGE_TYPES);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const fullTextCursorRef = useRef(-1);
  const [fullTextPosition, setFullTextPosition] = useState(-1);
  // Ctrl-F-style find bar. Dismissing hides it until the query changes again,
  // so it never nags once you have found what you came for.
  const [findOpen, setFindOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const graphRequest = useRef(0);
  const searchInput = useRef<HTMLInputElement>(null);
  const inspectorContent = useRef<HTMLDivElement>(null);
  const cancelInspectorScroll = useRef<(() => void) | null>(null);
  const inspectorScrollFor = useRef<string | null>(null);

  const loadGraph = useCallback(async ({
    nextScope,
    nextTopic,
    nextEdgeTypes,
    entryId,
    preferredEntryId,
    keepCurrentOnEmpty = false,
    dateFrom,
    depth,
    path,
  }: {
    nextScope: GraphScope;
    nextTopic: string | null;
    nextEdgeTypes: RendererGraphEdge["edge_type"][];
    entryId?: string | null;
    preferredEntryId?: string | null;
    keepCurrentOnEmpty?: boolean;
    dateFrom?: string | null;
    depth?: number;
    path?: string | null;
  }) => {
    const request = ++graphRequest.current;
    setIsLoading(true);
    try {
      setError(null);
      const nextGraph = await graphQuery({
        entryId: entryId ?? (nextScope !== "overview" && nextScope !== "file" ? preferredEntryId : null),
        edgeTypes: nextEdgeTypes,
        topic: nextTopic,
        dateFrom,
        depth,
        path: nextScope === "file" ? path : null,
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
      void trailQuery({ limit: 1000 }).then(setEntryIndex).catch(() => {});
      void worktreesQuery().then(setWorktrees).catch(() => {});
      await loadGraph({
        nextScope: scope,
        nextTopic: activeTopic,
        nextEdgeTypes: edgeTypesForScope(scope),
        preferredEntryId: selected?.source.entry_id,
        dateFrom: scope === "overview" && range === "recent" ? recentDateFrom(nextRuntime) : null,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load Memory Trace.");
    }
  }, [activeTopic, loadGraph, range, scope, selected?.source.entry_id]);

  // The Trail is a full-history timeline with its own client-side window, so it
  // ignores the graph's recent-range control and fetches the whole corpus (up to
  // the endpoint cap), respecting only the active topic filter.
  const loadTrail = useCallback(async () => {
    try {
      setTrailError(null);
      setTrail(await trailQuery({ topic: activeTopic, limit: 1000 }));
    } catch (reason) {
      setTrailError(reason instanceof Error ? reason.message : "Unable to load the Trail.");
    }
  }, [activeTopic]);

  useEffect(() => { void load(); }, []); // Initial project load only; controls issue deliberate scoped requests.
  useEffect(() => {
    if (viewMode !== "trail") return;
    setTrailWindow(TRAIL_WINDOW_STEP);
    void loadTrail();
  }, [viewMode, loadTrail]);
  useEffect(() => { localStorage.setItem("memory-trace:inspector-dock", dock); }, [dock]);
  useEffect(() => { localStorage.setItem("memory-trace:nav-width", String(navWidth)); }, [navWidth]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("memory-trace:theme", theme);
  }, [theme]);
  useEffect(() => { localStorage.setItem("memory-trace:inspector-width", String(inspectorWidth)); }, [inspectorWidth]);
  useEffect(() => {
    localStorage.setItem("memory-trace:trail-settings", JSON.stringify(trailStyle));
    localStorage.removeItem("memory-trace:trail-tune"); // legacy tuning-panel key
  }, [trailStyle]);

  // Pointer-driven pane resize: capture moves on window for the drag's
  // duration; widths clamp to sane bounds and persist across sessions.
  function startPaneResize(kind: "nav" | "inspector") {
    return (event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      const handle = event.currentTarget;
      handle.classList.add("dragging");
      const move = (pointer: PointerEvent) => {
        if (kind === "nav") setNavWidth(Math.min(NAV_WIDTH.max, Math.max(NAV_WIDTH.min, pointer.clientX)));
        else setInspectorWidth(Math.min(INSPECTOR_WIDTH.max, Math.max(INSPECTOR_WIDTH.min, window.innerWidth - pointer.clientX)));
      };
      const stop = () => {
        handle.classList.remove("dragging");
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", stop);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", stop);
    };
  }
  useEffect(() => {
    if (!selected) { setChunk(null); return; }
    let cancelled = false;
    void api<ChunkResponse>(`/chunks/${encodeURIComponent(selected.source.chunk_id)}`).then((nextChunk) => { if (!cancelled) setChunk(nextChunk); }).catch(() => { if (!cancelled) setChunk(null); });
    return () => { cancelled = true; };
  }, [selected]);

  // Two-stage selection: clicking the already-selected entry mutes the focus
  // emphasis (pinned) without losing the selection; clicking again unmutes.
  const select = useCallback((node: RendererGraphNode, options: { preserveSearch?: boolean; preserveHint?: boolean } = {}) => {
    setSelected((prior) => {
      if (prior?.id === node.id) { setSelectionMuted((muted) => !muted); return prior; }
      setSelectionMuted(false);
      return node;
    });
    if (!options.preserveSearch) {
      setSearch(null);
      fullTextCursorRef.current = -1;
      setFullTextPosition(-1);
    }
    if (!options.preserveHint) setMatchHint(null);
  }, []);
  const indexById = useMemo(() => {
    const map = new Map<string, { title: string; date: string; datetime: string | null; branch: string | null }>();
    entryIndex?.nodes.forEach((node) => map.set(node.id, { title: node.title, date: node.date, datetime: node.datetime, branch: node.branch ?? null }));
    return map;
  }, [entryIndex]);

  type ContextItem = { key: string; entryId: string; kind: string; title: string };
  // The left pane shows the selection's context: typed lifecycle links (from
  // the entry index's edges), commit siblings, and topic-similar entries.
  // With nothing selected it falls back to the newest entries.
  const contextItems = useMemo<ContextItem[]>(() => {
    const entryId = selected?.source.entry_id;
    if (!entryId) {
      return (entryIndex?.nodes ?? [])
        .slice()
        .sort((a, b) => (b.datetime || b.date).localeCompare(a.datetime || a.date))
        .slice(0, 24)
        .map((node) => ({ key: `r-${node.id}`, entryId: node.id, kind: "recent", title: stripTitleStamp(node.title) }));
    }
    const TYPE_LABEL: Record<string, string> = { evolves: "evolves", supersedes: "replaces", related: "related" };
    const items: ContextItem[] = [];
    const seen = new Set<string>([entryId]);
    (entryIndex?.edges ?? []).forEach((edge) => {
      if (!(edge.type in TYPE_LABEL)) return;
      const other = edge.source === entryId ? edge.target : edge.target === entryId ? edge.source : null;
      if (!other || seen.has(other)) return;
      const node = indexById.get(other);
      if (!node) return;
      seen.add(other);
      items.push({ key: `e-${other}`, entryId: other, kind: TYPE_LABEL[edge.type], title: stripTitleStamp(node.title) });
    });
    (chunk?.commit_entries ?? []).forEach((brief) => {
      if (!brief.entry_id || seen.has(brief.entry_id)) return;
      seen.add(brief.entry_id);
      items.push({ key: `c-${brief.chunk_id}`, entryId: brief.entry_id, kind: "commit", title: stripTitleStamp(brief.title) });
    });
    (chunk?.suggestions?.same_topic ?? []).slice(0, 5).forEach((brief) => {
      if (!brief.entry_id || seen.has(brief.entry_id)) return;
      seen.add(brief.entry_id);
      items.push({ key: `s-${brief.chunk_id}`, entryId: brief.entry_id, kind: "similar", title: stripTitleStamp(brief.title) });
    });
    return items;
  }, [selected?.source.entry_id, entryIndex, indexById, chunk]);

  // Grouped by relationship for the panel: one header per kind, not a chip
  // per row.
  const contextGroups = useMemo<[string, ContextItem[]][]>(() => {
    const order = ["related", "replaces", "evolves", "commit", "similar", "recent"];
    const groups = new Map<string, ContextItem[]>();
    contextItems.forEach((item) => groups.set(item.kind, [...(groups.get(item.kind) ?? []), item]));
    return order.filter((kind) => groups.has(kind)).map((kind) => [kind, groups.get(kind)!]);
  }, [contextItems]);

  // Branch and evolves live only in the entry's YAML block, which is now
  // collapsed — so surface them in the metadata grid instead. Both come from
  // `entryIndex` (the full-corpus Trail response the context panel already
  // uses), which carries `branch` per node and typed lifecycle edges; the graph
  // projection exposes neither, and this avoids widening the v1 contract.
  const selectedBranch = selected?.source.entry_id ? indexById.get(selected.source.entry_id)?.branch ?? null : null;
  const selectedEvolves = useMemo(() => {
    const entryId = selected?.source.entry_id;
    if (!entryId) return [] as { entryId: string; title: string }[];
    return (entryIndex?.edges ?? [])
      .filter((edge) => edge.type === "evolves" && edge.source === entryId)
      .map((edge) => ({ entryId: edge.target, title: stripTitleStamp(indexById.get(edge.target)?.title ?? edge.target) }));
  }, [selected?.source.entry_id, entryIndex, indexById]);

  // Find-bar matches run over the WHOLE corpus (entryIndex), not the Trail's
  // loaded window — otherwise "next match" could not reach an entry that has
  // not been paged in yet, which is exactly what a Ctrl-F is for. Ordered
  // newest-first to match the Trail's own row order.
  const matchEntries = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term || isCanonicalEntryId(term)) return [];
    return (entryIndex?.nodes ?? [])
      .filter((node) => node.entry_id)
      .slice()
      .sort((a, b) => trailStamp(b) - trailStamp(a) || String(a.id).localeCompare(String(b.id)))
      .filter((node) =>
        stripTitleStamp(node.title).toLowerCase().includes(term) ||
        (node.branch || "").toLowerCase().includes(term) ||
        (node.entry_id || "").toLowerCase().includes(term))
      .map((node) => node.id);
  }, [query, entryIndex]);
  // Every full-text consumer reads THIS, never `search.results` — the server
  // returns the whole corpus ranked, so the raw list tails off into score-0
  // filler that cycling would otherwise march straight through.
  const fullTextResults = useMemo(() => genuineSearchResults(search?.results ?? []), [search]);
  // Which list the find bar's counter and chevrons are driving. One bar, one
  // pair of buttons; the two cursors below are internal and never both on
  // screen. Running a full-text search switches the source, Escape switches it
  // back.
  //
  // Escape does not restore the local POSITION, and should not: full-text
  // navigation moved the selection, and the re-homing effect below re-points
  // the local cursor at whatever is on screen — which for a body-only match is
  // not a title match at all, so it lands on -1. The bar then reads "–/n",
  // meaning "you are not on one of these"; stepping starts from the top. That
  // is honest, where holding the old position would claim you were on match 2
  // while the reader showed something else entirely.
  const findMode: "title" | "text" = search ? "text" : "title";
  // The cursor advances SYNCHRONOUSLY in a ref, because selecting an entry is
  // async: deriving the position from `selected` alone made held Enter (or fast
  // clicks) step only once, since every repeat read the same stale position.
  const matchCursorRef = useRef(-1);
  const [matchPosition, setMatchPosition] = useState(-1);
  const setMatchCursor = useCallback((index: number) => {
    matchCursorRef.current = index;
    setMatchPosition(index);
  }, []);
  const setFullTextCursor = useCallback((index: number) => {
    fullTextCursorRef.current = index;
    setFullTextPosition(index);
  }, []);
  // A fresh query re-opens the bar even if the last one was dismissed, and
  // restarts the cycle.
  useEffect(() => { setFindOpen(true); setMatchCursor(-1); }, [query, setMatchCursor]);
  // Selecting from anywhere else (a Trail row, the context panel) re-homes the
  // cursor so the next step continues from what is actually on screen.
  const selectedEntryId = selected?.source.entry_id;
  useEffect(() => {
    if (!selectedEntryId || !matchEntries.length) return;
    if (matchEntries[matchCursorRef.current] === selectedEntryId) return;
    setMatchCursor(matchEntries.indexOf(selectedEntryId));
  }, [selectedEntryId, matchEntries, setMatchCursor]);

  // Switching worktree swaps the entire corpus: scope the API, clear every
  // per-corpus piece of state, and reload. Each checkout is its own memory
  // view (different branches carry different session entries).
  async function chooseWorktree(path: string) {
    const next = worktrees && path === worktrees.default ? null : path;
    const label = worktrees?.worktrees.find((item) => item.path === path)?.label ?? "";
    const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
    setSwitchLabel(label);
    setSwitchStage(0);
    const startedAt = performance.now();
    // Fixed rhythm: depart at 600ms regardless of compute speed.
    const departTimer = setTimeout(() => setSwitchStage((stage) => Math.max(stage, 1)), 600);
    try {
      setWorktree(next);
      setActiveWorktree(next);
      setSelected(null);
      setChunk(null);
      setMatchHint(null);
      setSelectionMuted(false);
      setSearch(null);
      setFullTextCursor(-1);
      setQuery("");
      setTrail(null);
      setEntryIndex(null);
      setTrailWindow(TRAIL_WINDOW_STEP);
      setActiveTopic(null);
      setScope("overview");
      await load();
      if (viewMode === "trail") await loadTrail();
      // Arrival never before 1250ms (readable ride); a slow cold rebuild holds
      // the middle leg until the data is truly loaded.
      const beforeArrival = performance.now() - startedAt;
      if (beforeArrival < 1250) await wait(1250 - beforeArrival);
      setSwitchStage(2);
      const total = performance.now() - startedAt;
      await wait(Math.max(350, 1600 - total));
    } finally {
      clearTimeout(departTimer);
      setSwitchLabel(null);
      setSwitchStage(0);
    }
  }

  const ensureTrailVisible = useCallback((count: number) => setTrailWindow((value) => Math.max(value, count)), []);

  // Opening from the context panel selects the entry and, in Trail mode, the
  // Trail scrolls to it (TrailWorkspace watches the selection).
  async function openContextEntry(entryId: string) {
    await focusEntry(entryId);
  }

  const topics = useMemo(() => Object.entries(facets?.topics ?? {}).slice(0, 10), [facets]);
  const inspectorVisible = dock !== "hidden";

  async function requestGraph(nextScope: GraphScope, nextTopic = activeTopic, nextEdgeTypes = edgeTypesForScope(nextScope), entryId?: string | null, preferredEntryId?: string | null, keepCurrentOnEmpty = false, dateFrom = nextScope === "overview" && range === "recent" ? recentDateFrom(runtime) : null, depth = nextScope === "evolution" ? EVOLUTION_DEPTH : undefined, path = nextScope === "file" ? filePath : null) {
    return loadGraph({ nextScope, nextTopic, nextEdgeTypes, entryId, preferredEntryId: preferredEntryId ?? selected?.source.entry_id, keepCurrentOnEmpty, dateFrom, depth, path });
  }

  async function focusEntry(entryId: string, options: { preserveHint?: boolean; preserveSearch?: boolean } = {}) {
    if (!options.preserveHint) setMatchHint(null);
    const nextGraph = await requestGraph("local", null, undefined, entryId, entryId, true, null);
    if (!nextGraph) return;
    if (!nextGraph.nodes.some((node) => node.source.entry_id === entryId)) {
      setError(`No entry exists with id ${entryId}.`);
      return;
    }
    setScope("local");
    setActiveTopic(null);
    if (!options.preserveSearch) {
      setSearch(null);
      setFullTextCursor(-1);
    }
  }

  // Trail selection: reuse the already-loaded graph node when present (cheap,
  // keeps the Inspector's full metadata); otherwise pull the entry into the
  // graph via focusEntry so the Inspector can render it.
  function selectFromTrail(entryId: string | null, chunkId: string) {
    if (entryId != null && selected?.source.entry_id === entryId) { setSelectionMuted((muted) => !muted); return; }
    const node = graph?.nodes.find((item) => (entryId != null && item.source.entry_id === entryId) || item.source.chunk_id === chunkId);
    if (node) { select(node); return; }
    if (entryId) void focusEntry(entryId);
  }

  // Cycle to the next/previous match, wrapping around. Selecting the entry is
  // all this does — the Trail watches the selection and eases the row into
  // view, growing its window first when the match is older than what is loaded.
  async function jumpToMatch(step: number) {
    if (!matchEntries.length) return;
    const from = matchCursorRef.current >= 0 ? matchCursorRef.current : step > 0 ? -1 : 0;
    const next = (from + step + matchEntries.length) % matchEntries.length;
    setMatchCursor(next);
    setFindOpen(true);
    await focusEntry(matchEntries[next], { preserveHint: true });
  }

  // Index is derived, not passed: it must be a position in the FILTERED list,
  // which is the only list the counter and the cursor ever speak about.
  async function chooseFullTextResult(result: SearchResult) {
    setFullTextCursor(searchResultCursor(fullTextResults, result));
    if (result.entry_id) {
      setMatchHint(hintFor(result, result.entry_id));
      await focusEntry(result.entry_id, { preserveHint: true, preserveSearch: true });
      return;
    }
    const node = graph?.nodes.find((item) => item.source.chunk_id === result.chunk_id);
    if (node) {
      const entryId = node.source.entry_id;
      if (entryId) setMatchHint(hintFor(result, entryId));
      select(node, { preserveHint: true, preserveSearch: true });
    }
  }

  async function jumpToFullTextResult(step: number) {
    if (!fullTextResults.length) return;
    const next = stepSearchCursor(fullTextCursorRef.current, fullTextResults.length, step);
    await chooseFullTextResult(fullTextResults[next]);
  }

  // The single entry point behind the find bar's chevrons and Enter/Shift+Enter.
  function jumpToFind(step: number) {
    return findMode === "text" ? jumpToFullTextResult(step) : jumpToMatch(step);
  }

  /** Whether the active mode has anything to step through. */
  function findCount(): number {
    return findMode === "text" ? fullTextResults.length : matchEntries.length;
  }

  function dismissFullTextSearch() {
    setSearch(null);
    setFullTextCursor(-1);
  }

  // Keyboard grammar ported from the vanilla UI, which the React workspace had
  // dropped: "/" focuses search from anywhere, Enter/Shift+Enter cycle matches,
  // Escape dismisses. Held in a ref so the listener subscribes once but never
  // reads stale state (same pattern as GraphWorkspace's tap handler).
  const keyHandler = useRef<(event: KeyboardEvent) => void>(() => {});
  keyHandler.current = (event: KeyboardEvent) => {
    const target = event.target as HTMLElement | null;
    const inSearch = target === searchInput.current;
    const typing = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
    if (event.key === "/" && !typing) {
      event.preventDefault();
      searchInput.current?.focus();
      return;
    }
    if (event.key === "Escape") {
      if (search) { dismissFullTextSearch(); return; }
      setFindOpen(false);
      if (inSearch) searchInput.current?.blur();
      return;
    }
    // Enter is deliberately NOT handled here. The search box sits inside a
    // <form>, so a real Enter would fire both this listener and the form's
    // implicit submission — stepping twice, or cycling and opening the dropdown
    // at once. It is handled in exactly one place: the input's own onKeyDown,
    // which can preventDefault the submit and read shiftKey.
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => keyHandler.current(event);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function runSearch(rawValue: string) {
    const value = rawValue.trim();
    if (!value) { dismissFullTextSearch(); return; }
    if (isCanonicalEntryId(value)) {
      await focusEntry(value);
      return;
    }
    try {
      setError(null);
      setIsSearching(true);
      const response = await searchQuery(value);
      setSearch(response);
      setFullTextCursor(-1);
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

  // Best matched subsection for a search result: the section whose chunk_id is
  // the best match (else the first), reduced to its leaf heading. Entry-level
  // matches with no subsection return null (no highlight).
  function hintFor(result: SearchResult, entryId: string): MatchHint | null {
    const sections = result.matched_sections ?? [];
    const best = sections.find((section) => section.chunk_id === result.best_match_chunk_id) ?? sections[0];
    const heading = best?.heading_path?.[best.heading_path.length - 1];
    return heading ? { entryId, heading } : null;
  }

  async function changeScope(nextScope: GraphScope) {
    // File scope is entered only via onOpenFile (it seeds from a path, not a
    // selected entry) - the segment control never offers it directly.
    const entryId = nextScope !== "overview" && nextScope !== "file" ? selected?.source.entry_id : null;
    if (nextScope !== "overview" && nextScope !== "file" && !entryId) {
      setError("Choose an entry before narrowing the graph.");
      return;
    }
    setScope(nextScope);
    await requestGraph(nextScope, activeTopic, undefined, entryId, entryId);
  }

  async function openFileMode(path: string) {
    setFilePath(path);
    setScope("file");
    setViewMode("graph");
    await requestGraph("file", activeTopic, undefined, null, null, false, undefined, undefined, path);
  }

  async function chooseTopic(nextTopic: string | null) {
    setActiveTopic(nextTopic);
    await requestGraph(scope, nextTopic, undefined, scope !== "overview" && scope !== "file" ? selected?.source.entry_id : null);
  }

  // Obsidian-style: this is a client-side visibility filter over the already-
  // fetched graph, not a query parameter — it never refetches, never changes
  // which nodes are on the map, and never re-runs the layout. GraphWorkspace
  // applies it as an in-place presentation pass (see edge-filtered/EDGE_LABELS).
  function toggleEdge(edgeType: RendererGraphEdge["edge_type"]) {
    setEdgeTypes((current) => (current.includes(edgeType) ? current.filter((item) => item !== edgeType) : [...current, edgeType]));
  }

  async function changeRange(nextRange: GraphRange) {
    setRange(nextRange);
    await requestGraph(scope, activeTopic, undefined, scope === "local" ? selected?.source.entry_id : null, undefined, false, nextRange === "recent" ? recentDateFrom(runtime) : null);
  }

  // The hint only applies to the entry it was computed for — a stale hint from
  // the previous result must not highlight a same-named heading in this one.
  const matchHeading = matchHint && selected?.source.entry_id === matchHint.entryId ? matchHint.heading : null;

  // Bring the matched section into view. Rendering the highlight is not enough:
  // the band is often far down a long entry, so without this you cycle results
  // and the reader just sits at the top showing no visible reason it moved.
  useEffect(() => {
    const container = inspectorContent.current;
    if (!container || !chunk) return;
    // A section that matched gets anchored under the top edge; an entry-level
    // match (no matching subsection, so nothing to point at) goes to the head
    // of the entry rather than inheriting the last one's scroll offset.
    const element = matchHeading ? container.querySelector<HTMLElement>(".match-highlight") : null;
    if (matchHeading && !element) return;
    const key = `${chunk.chunk_id}::${matchHeading ?? ""}`;
    if (inspectorScrollFor.current === key) return;
    inspectorScrollFor.current = key;
    const top = element
      ? element.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop
      : 0;
    const target = element
      ? readerScrollTarget(top, container.scrollTop, container.clientHeight, container.scrollHeight - container.clientHeight)
      : (container.scrollTop === 0 ? null : 0);
    if (target === null) return;
    cancelInspectorScroll.current?.();
    cancelInspectorScroll.current = animateScrollTo(container, target, scrollDurationFor(target - container.scrollTop));
  }, [chunk, matchHeading]);
  useEffect(() => () => cancelInspectorScroll.current?.(), []);

  return (
    <div className={`trace-shell inspector-${dock} ${leftOpen ? "navigation-open" : "navigation-hidden"}`} style={{ "--nav-w": `${navWidth}px`, "--insp-w": `${inspectorWidth}px` } as CSSProperties}>
      <header className="topbar">
        <button className="icon-button" type="button" onClick={() => setLeftOpen((value) => !value)} aria-label="Toggle navigation" title="Toggle navigation">
          {leftOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </button>
        <div className="brand"><Network size={19} aria-hidden="true" /><span>Memory Trace</span></div>
        <div className="project-summary">{runtime ? `${runtime.label} · ${runtime.entry_count} entries` : "Loading project"}</div>
        <div className="trace-search-wrap">
          <form className="trace-search" onSubmit={submitSearch} role="search"><Search size={16} aria-hidden="true" /><input ref={searchInput} value={query} onChange={(event) => { setQuery(event.target.value); dismissFullTextSearch(); }} onKeyDown={(event) => { if (event.key !== "Enter") return; event.preventDefault(); if (event.ctrlKey || event.metaKey) { void runSearch(event.currentTarget.value); return; } if (findCount()) { void jumpToFind(event.shiftKey ? -1 : 1); return; } if (findMode === "text") return; void runSearch(event.currentTarget.value); }} placeholder="Search memory or entry ID" aria-label="Search memory or entry ID" />{query && <button className="icon-button search-clear" type="button" onClick={() => { setQuery(""); dismissFullTextSearch(); }} aria-label="Clear search" title="Clear search"><X size={14} /></button>}</form>
          {/* One bar for both search modes. Full-text used to open a dropdown
              here instead, which meant reaching entry bodies cost you the
              counter, the chevrons and the Trail's scroll animation — you were
              back to picking from a list. Now "all text" only switches what
              this bar is stepping through.

              It renders whenever there is a query, not only when something
              matched: the "all text" button lives INSIDE the bar, so gating on
              local matches left a query that hit no title with no route to
              full-text at all except Ctrl+Enter. */}
          {findOpen && (search !== null || query.trim() !== "") && (
            <div className="find-bar" role="status" aria-live="polite" aria-label="Search matches">
              {isSearching ? <span className="find-note">searching…</span> : findCount() === 0 ? (
                <span className="find-note">{findMode === "text" ? "no matches" : "no title matches"}</span>
              ) : (
                <span className="find-count">
                  {(findMode === "text" ? fullTextPosition : matchPosition) + 1 || "–"}
                  <span className="find-sep">/</span>
                  {/* The server ranks the whole corpus, so a full page of hits
                      may not be all of them — say so rather than claim 100. */}
                  {findMode === "text" && fullTextResults.length === SEARCH_LIMIT ? `${SEARCH_LIMIT}+` : findCount()}
                </span>
              )}
              <button type="button" className="find-step" onClick={() => void jumpToFind(-1)} disabled={findCount() === 0} aria-label="Previous match" title="Previous match (Shift+Enter)"><ChevronUp size={14} /></button>
              <button type="button" className="find-step" onClick={() => void jumpToFind(1)} disabled={findCount() === 0} aria-label="Next match" title="Next match (Enter)"><ChevronDown size={14} /></button>
              {/* Same slot in both modes now: a toggle, not a one-way door. Title
                  mode turns full-text search on; text mode's click turns it back
                  off, so choosing a search type never requires reaching for the
                  separate dismiss button on the far right. */}
              <button type="button" className="find-all" aria-pressed={findMode === "text"}
                      onClick={() => { if (findMode === "text") dismissFullTextSearch(); else void runSearch(query); }}
                      aria-label={findMode === "text" ? "Showing full-text results — click to search titles only" : "Search full text including entry bodies"}
                      title={findMode === "text" ? "Full-text results active — click to search titles only (Esc)" : "Search full text, including entry bodies (Ctrl+Enter)"}>
                <Search size={12} aria-hidden="true" />all text
              </button>
              <button type="button" className="find-step" onClick={() => { if (findMode === "text") dismissFullTextSearch(); else setFindOpen(false); }} aria-label={findMode === "text" ? "Dismiss full-text results" : "Dismiss find bar"} title="Dismiss (Esc)"><X size={13} /></button>
            </div>
          )}
        </div>
        {/* The view switch lives here, above both workspaces: it chooses which
            workspace you are in, so it does not belong to either one's own bar
            of view-specific controls. */}
        <div className="segment-control view-switch" aria-label="Workspace view">
          <button type="button" aria-pressed={viewMode === "trail"} onClick={() => setViewMode("trail")}><GitBranch size={14} aria-hidden="true" /><span>Trail</span></button>
          <button type="button" aria-pressed={viewMode === "graph"} onClick={() => setViewMode("graph")}><Network size={14} aria-hidden="true" /><span>Graph</span></button>
        </div>
        <div className="topbar-actions">
          <SettingsMenu trailStyle={trailStyle} onTrailStyle={setTrailStyle} dock={dock} onDock={setDock} theme={theme} onTheme={setTheme} />
          <button className="icon-button" type="button" onClick={() => setDock((value) => value === "hidden" ? "auto" : "hidden")} aria-label="Toggle inspector" title="Toggle inspector">
            {inspectorVisible ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
          </button>
          <button className="icon-button" type="button" onClick={() => void load()} aria-label="Refresh project" title="Refresh project"><RotateCcw size={17} /></button>
        </div>
      </header>

      {leftOpen && <aside className="navigation-pane" aria-label="Navigation">
        <div className="pane-resize pane-resize-nav" role="separator" aria-orientation="vertical" aria-label="Resize navigation" title="Drag to resize" onPointerDown={startPaneResize("nav")} />
        <div className="pane-heading"><LayoutPanelLeft size={16} aria-hidden="true" /> <span>Project</span></div>
        <dl className="metric-list"><div><dt>Entries</dt><dd>{runtime?.entry_count ?? "-"}</dd></div><div><dt>Chunks</dt><dd>{facets?.runtime.chunk_count ?? "-"}</dd></div></dl>
        {worktrees && worktrees.worktrees.length > 1 && (
          <label className="worktree-picker">
            <span>Worktree</span>
            <select value={worktree ?? worktrees.default} onChange={(event) => void chooseWorktree(event.target.value)} aria-label="Worktree">
              {worktrees.worktrees.map((item) => (
                <option key={item.id} value={item.path}>
                  {item.label}{item.is_primary ? " (primary)" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
        <section className="navigation-section"><h2>Topics</h2><div className="topic-list"><button type="button" className={activeTopic === null ? "topic active" : "topic"} onClick={() => void chooseTopic(null)} aria-pressed={activeTopic === null}>All</button>{topics.map(([topic, count]) => <button type="button" className={activeTopic === topic ? "topic active" : "topic"} key={topic} onClick={() => void chooseTopic(topic)} aria-pressed={activeTopic === topic}>{topic}<b>{count}</b></button>)}</div></section>
        <section className="navigation-section entry-list"><h2>{selected?.source.entry_id ? "Context" : "Recent"}</h2>{selected?.source.entry_id && <p className="context-subject" title={selected.label}>{stripTitleStamp(selected.label)}</p>}{contextGroups.length ? contextGroups.map(([kind, group]) => <div key={kind} className="context-group">{kind !== "recent" && <h3 className={`context-group-h context-type-${kind}`}>{kind === "commit" ? "same commit" : kind}</h3>}{group.map((item) => <button key={item.key} type="button" className="entry" title={item.title} onClick={() => void openContextEntry(item.entryId)}><span>{item.title}</span></button>)}</div>) : <p className="context-empty">{selected?.source.entry_id ? "No linked context for this entry." : "Loading entries"}</p>}</section>
      </aside>}

      <main className="workspace" id="trace-workspace">
        {switchLabel !== null && (
          <div className="worktree-loader" data-stage={switchStage} role="status" aria-live="polite">
            <svg className="wt-map" viewBox="0 0 240 240" width="240" height="240" aria-hidden="true">
              <line className="wt-track" x1={34} y1={30} x2={34} y2={210} />
              <line className="wt-track-lit" x1={34} y1={30} x2={34} y2={210} pathLength={1} />
              {[30, 120, 210].map((y, i) => <circle key={y} className="wt-station" data-i={i} cx={34} cy={y} r={5.5} />)}
              {["Leaving the platform", "Reading branch memory", `Arriving${switchLabel ? ` at ${switchLabel}` : ""}`].map((text, i) => (
                <text key={text} className="wt-label" data-i={i} x={52} y={[30, 120, 210][i] + 4}>{text}</text>
              ))}
              <g className="wt-train"><circle className="wt-train-halo" cx={34} cy={0} r={11} /><rect x={25} y={-6} width={18} height={12} rx={4} /></g>
            </svg>
            <div className="wt-caption">
              <div className="wt-title">Switching worktree{switchLabel ? ` \u00b7 ${switchLabel}` : ""}</div>
              <div className="wt-sub">following the train of thought\u2026</div>
            </div>
          </div>
        )}
        {/* Scope, date range and labels only shape the GRAPH projection — the
            Trail always renders full history through its own window — so they
            are hidden in Trail view rather than sitting there inert. */}
        <div className="workspace-bar"><div><span className="eyebrow">{viewMode === "trail" ? "Trail" : "Graph workspace"}</span><h1>{viewMode === "trail" ? "Decision timeline" : "Relationship map"}</h1></div><div className="workspace-actions">{viewMode !== "trail" && <><div className="segment-control" aria-label="Graph scope"><button type="button" aria-pressed={scope === "overview"} onClick={() => void changeScope("overview")}>Overview</button><button type="button" aria-pressed={scope === "local"} onClick={() => void changeScope("local")}>Local</button><button type="button" aria-pressed={scope === "evolution"} onClick={() => void changeScope("evolution")}>Evolution</button>{filePath && <button type="button" aria-pressed={scope === "file"} onClick={() => void openFileMode(filePath)}>{"File: " + (filePath.split(/[\\/]/).pop() ?? filePath)}</button>}</div><div className="segment-control" aria-label="Graph date range"><button type="button" aria-pressed={range === "recent"} onClick={() => void changeRange("recent")}>Recent</button><button type="button" aria-pressed={range === "all"} onClick={() => void changeRange("all")}>All dates</button></div><label className="label-menu"><span>Labels</span><select value={labelMode} onChange={(event) => setLabelMode(event.target.value as LabelMode)} aria-label="Graph labels"><option value="focus">Focus</option><option value="minimal">Minimal</option><option value="all">All</option></select></label></>}<span className="status-pill">{viewMode === "trail" ? "Trail" : isLoading ? "Updating" : "Cytoscape.js"}</span></div></div>
        {viewMode !== "trail" && scope !== "evolution" && scope !== "file" && <div className="graph-filter-bar" aria-label="Graph filters"><span>Edges</span>{DEFAULT_GRAPH_EDGE_TYPES.map((edgeType) => <button type="button" key={edgeType} className={`edge-filter edge-${edgeType}`} aria-pressed={edgeTypes.includes(edgeType)} onClick={() => toggleEdge(edgeType)}>{EDGE_LABELS[edgeType]}</button>)}{activeTopic && <button type="button" className="active-topic" onClick={() => void chooseTopic(null)}>{activeTopic}<X size={13} aria-hidden="true" /></button>}</div>}
        {viewMode !== "trail" && scope === "evolution" && <div className="graph-filter-bar" aria-label="Graph filters"><span>Edges</span><span className="count">Evolves + Replaces only · lifecycle chain</span>{activeTopic && <button type="button" className="active-topic" onClick={() => void chooseTopic(null)}>{activeTopic}<X size={13} aria-hidden="true" /></button>}</div>}
        {viewMode !== "trail" && scope === "file" && <div className="graph-filter-bar" aria-label="Graph filters"><span>File</span><span className="count" title={filePath ?? ""}>{"Entries that touched " + (filePath ?? "this file")}</span><button type="button" className="active-topic" onClick={() => void changeScope("overview")}>Clear<X size={13} aria-hidden="true" /></button></div>}
        {viewMode === "trail" ? (
          <>
            {trailError && <div className="error-state" role="alert">{trailError}</div>}
            {trail ? (
              <Suspense fallback={<div className="loading-state">Loading trail</div>}>
                <TrailWorkspace trail={trail} trailStyle={trailStyle} windowSize={trailWindow} selectedEntryId={selected?.source.entry_id ?? null} selectedChunkId={selected?.source.chunk_id ?? null} query={query} selectionMuted={selectionMuted} commitSiblingIds={chunk?.commit_entry_ids ?? []} onSelectEntry={selectFromTrail} onEnsureVisible={ensureTrailVisible} onLoadMore={() => setTrailWindow((value) => value + TRAIL_WINDOW_STEP)} />
              </Suspense>
            ) : (
              <div className="loading-state">Loading trail</div>
            )}
          </>
        ) : (
          <>
            {error && <div className="error-state" role="alert">{error}</div>}
            {/* The "Edges" filter row is hidden in Evolution/File scope (it has
                nothing to do with a fixed lineage chain or a file's touches),
                so a stale toggle left over from Overview/Local must not carry
                through and blank out edges the user never chose to hide there. */}
            {graph && <Suspense fallback={<div className="loading-state">Loading graph</div>}><GraphWorkspace graph={graph} selectedId={selected?.id ?? null} onSelect={select} labelMode={labelMode} theme={theme} visibleEdgeTypes={scope === "evolution" || scope === "file" ? edgeTypesForScope(scope) : edgeTypes} /></Suspense>}
            {!graph && <div className="loading-state">Loading graph</div>}
          </>
        )}
      </main>

      {inspectorVisible && <aside className="inspector" id="trace-inspector" aria-label="Inspector">
        {dock !== "bottom" && <div className="pane-resize pane-resize-inspector" role="separator" aria-orientation="vertical" aria-label="Resize inspector" title="Drag to resize" onPointerDown={startPaneResize("inspector")} />}
        <div className="inspector-bar"><div><span className="eyebrow">Inspector</span><h2>{titleFor(selected)}</h2></div><button className="icon-button" type="button" onClick={() => setDock("hidden")} aria-label="Hide inspector" title="Hide inspector"><X size={17} /></button></div>
        {selected && <div className="inspector-content" ref={inspectorContent}>
          {/* Metadata is grouped rather than one long column, and the grid is a
              CSS container query on the pane itself — so it reflows as the
              inspector is dragged wider/narrower and when it docks to the
              bottom, independently of the viewport. Authority and provenance
              stay on separate lines: they are distinct axes (BG1), never merged. */}
          <dl className="metadata">
            <div className="meta-item meta-wide"><dt>Entry ID</dt><dd className="meta-mono">{selected.source.entry_id || "Not recorded"}</dd></div>
            <div className="meta-item"><dt>Date</dt><dd>{selected.temporal.value}</dd></div>
            <div className="meta-item"><dt>Agent</dt><dd>{selected.source.agent}</dd></div>
            <div className="meta-item"><dt>Authority</dt><dd><span className={ADVISORY_AUTHORITY.has(selected.authority_class) ? "authority-badge advisory" : "authority-badge"}>{AUTHORITY_LABELS[selected.authority_class]}</span></dd></div>
            <div className="meta-item"><dt>Provenance</dt><dd>{PROVENANCE_LABELS[selected.provenance_class]}</dd></div>
            {selected.provider && <div className="meta-item"><dt>Provider</dt><dd>{selected.provider}{selected.revision ? ` · ${selected.revision}` : ""}</dd></div>}
            {selected.stale && <div className="meta-item meta-wide"><dt>Freshness</dt><dd className="stale-flag">Stale — projection behind source</dd></div>}
            {selectedBranch && <div className="meta-item meta-wide"><dt>Branch</dt><dd className="meta-mono">{selectedBranch}</dd></div>}
            <div className="meta-item"><dt>Links</dt><dd>{selected.connectivity}</dd></div>
            <div className="meta-item"><dt>Diagrams</dt><dd>{chunk?.diagrams.length ?? 0}</dd></div>
            {selectedEvolves.length > 0 && (
              <div className="meta-item meta-wide"><dt>Evolves</dt><dd><span className="meta-links">{selectedEvolves.map((item) => (
                <button key={item.entryId} type="button" className="meta-link" title={item.entryId} onClick={() => void focusEntry(item.entryId)}>{item.title}</button>
              ))}</span></dd></div>
            )}
            <div className="meta-item meta-wide"><dt>Topics</dt><dd>{selected.source.topics.length ? <span className="meta-topics">{selected.source.topics.map((topic) => <span className="meta-topic" key={topic}>{topic}</span>)}</span> : "None"}</dd></div>
          </dl>
          <EntryReader chunk={chunk} matchHeading={matchHeading} onOpenEntry={(entryId) => void focusEntry(entryId)} onOpenFile={(path) => void openFileMode(path)} />
        </div>}
      </aside>}
    </div>
  );
}
