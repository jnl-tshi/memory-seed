const state = {
  runtime: null,
  facets: null,
  view: localStorage.getItem("ml:view") || "search",
  theme: localStorage.getItem("ml:theme") || "dark",
  accent: localStorage.getItem("ml:accent") || "indigo",
  query: "",
  agent: "",
  user: "",
  topic: "",
  granularity: "entry",
  sort: "relevance",
  density: "comfortable",
  dateFrom: "",
  dateTo: "",
  timelineZoom: "day",
  timelineHideEmpty: localStorage.getItem("ml:timelineHideEmpty") === "1",
  timelineSelectedBucket: "",
  graphScope: "all",
  graphSizeMode: localStorage.getItem("ml:graphSizeMode") || "links",
  graphEdgeTypes: new Set(["related"]),
  graphTransform: { x: 0, y: 0, scale: 1 },
  graphHover: "",
  trailWindow: 60,
  leftCollapsed: localStorage.getItem("ml:leftCollapsed") === "1",
  topicsExpanded: false,
  results: [],
  timeline: null,
  graph: null,
  selected: null,
  selectedId: null,
  nextCursor: null,
  loadSeq: 0,
  // Entry-level UI results plan: when a search result's best match came from a
  // subsection, remember which heading to highlight/scroll-to inside the parent
  // entry reader (never a separate selectable record).
  matchHint: null,
  pendingMatchScroll: false,
};

const app = document.getElementById("app");
const agentColors = ["#6f7cff", "#18a999", "#d9941a", "#d94b63", "#8f63e8", "#4f98d9"];
let paneObserver = null;

function api(path) {
  return fetch(path).then((response) => {
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  });
}

function qs(params) {
  const out = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value != null) out.set(key, value);
  });
  return out.toString();
}

async function boot() {
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.dataset.accent = state.accent;
  restorePanes();
  [state.runtime, state.facets] = await Promise.all([api("/api/runtime"), api("/api/facets")]);
  seedDates();
  await loadView();
  installDelegatedEvents();
  render();
}

function seedDates() {
  const bounds = state.facets?.runtime?.date_bounds || [];
  state.dateFrom = bounds[0] || "";
  state.dateTo = bounds[1] || "";
}

async function loadView() {
  if (state.view === "search") await loadSearch();
  if (state.view === "timeline") await loadTimeline();
  if (state.view === "graph" || state.view === "trail") await loadGraph();
}

// Trail is a git-graph timeline: intra-branch lineage gives the lanes, and the
// two lifecycle edges (supersedes = replaces, evolves = refines) draw as arcs.
// Fixed edge set - not the graph view's toggleable chips. Plain relatedness is
// deliberately excluded: it swamped the lineage signal.
const TRAIL_EDGE_TYPES = "branch,supersedes,evolves";

async function loadSearch(cursor = null, append = false, token = state.loadSeq) {
  const params = qs({
    q: state.query,
    limit: 30,
    cursor,
    granularity: state.granularity,
    agent: state.agent,
    user: state.user,
    topic: state.topic,
    date_from: state.dateFrom,
    date_to: state.dateTo,
    sort: state.sort,
  });
  const page = await api(`/api/search?${params}`);
  if (token !== state.loadSeq) return false;
  state.results = append ? [...state.results, ...page.results] : page.results;
  state.nextCursor = page.next_cursor;
  if (!state.selectedId && state.results[0]) await selectChunk(state.results[0].chunk_id, false);
  return true;
}

async function loadTimeline(token = state.loadSeq) {
  const params = qs({
    date_from: state.dateFrom,
    date_to: state.dateTo,
    agent: state.agent,
    user: state.user,
    topic: state.topic,
    zoom: state.timelineZoom,
    include_empty: state.timelineHideEmpty ? "false" : "true",
    limit: 500,
  });
  state.timeline = await api(`/api/timeline?${params}`);
  if (token !== state.loadSeq) return false;
  if (!state.selectedId && state.timeline.stream[0]) await selectChunk(state.timeline.stream[0].chunk_id, false);
  return true;
}

async function loadGraph(token = state.loadSeq) {
  // Trail always fetches the full corpus (windowing happens client-side so
  // "load older" needs no round trip) and ignores the graph view's scope.
  const trail = state.view === "trail";
  const params = qs({
    entry_id: !trail && state.graphScope === "neighborhood" ? state.selected?.entry_id || state.selectedId : "",
    granularity: "entry",
    agent: state.agent,
    user: state.user,
    topic: state.topic,
    date_from: state.dateFrom,
    date_to: state.dateTo,
    depth: 1,
    edge_types: trail ? TRAIL_EDGE_TYPES : [...state.graphEdgeTypes].join(","),
    limit: trail || state.graphScope === "all" ? 1000 : 90,
  });
  state.graph = await api(`/api/graph?${params}`);
  return token === state.loadSeq;
}

async function selectChunk(chunkId, rerender = true, token = state.loadSeq) {
  state.selectedId = chunkId;
  const selected = await api(`/api/chunks/${encodeURIComponent(chunkId)}`);
  if (token !== state.loadSeq) return false;
  state.selected = selected;
  if (state.view === "graph" || state.view === "trail") await loadGraph(token);
  if (rerender) render();
  return true;
}

function render() {
  const scrollState = captureCenterScroll();
  const focusState = captureFocusedInput();
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.dataset.accent = state.accent;
  app.innerHTML = `
    <div class="app">
      ${topbar()}
      <div class="shell ${state.leftCollapsed ? "left-collapsed" : ""}">
        <aside class="pane left" data-pane="left">${leftPane()}</aside>
        <div class="resizer" data-resize="left"></div>
        <main class="pane center" data-pane="center">${centerPane()}</main>
        <div class="resizer" data-resize="right"></div>
        <aside class="pane right" data-pane="right">${rightPane()}</aside>
      </div>
    </div>`;
  bindResizers();
  observePanes();
  restoreCenterScroll(scrollState);
  restoreFocusedInput(focusState);
  applyMatchHighlight();
}

// render() replaces the whole DOM, which destroys the element the user is
// typing in: focus, caret, and any keystrokes newer than the debounced state
// would be lost mid-word without capturing the live input here.
function captureFocusedInput() {
  const active = document.activeElement;
  if (!active || !active.id || !("value" in active)) return null;
  let start = null;
  let end = null;
  try {
    start = active.selectionStart;
    end = active.selectionEnd;
  } catch {
    // Selection is unsupported on some input types (e.g. date).
  }
  return { id: active.id, value: active.value, start, end };
}

function restoreFocusedInput(focusState) {
  if (!focusState) return;
  const el = document.getElementById(focusState.id);
  if (!el) return;
  if ("value" in el && el.value !== focusState.value) el.value = focusState.value;
  el.focus();
  if (typeof focusState.start === "number" && typeof el.setSelectionRange === "function") {
    try {
      el.setSelectionRange(focusState.start, focusState.end);
    } catch {
      // Same input types as above.
    }
  }
}

function topbar() {
  const tabs = [["search", "Search"], ["timeline", "Timeline"], ["graph", "Graph"], ["trail", "Trail"]]
    .map(([key, label]) => `<button type="button" class="tab ${state.view === key ? "active" : ""}" data-view="${key}">${label}</button>`)
    .join("");
  return `
    <header class="topbar">
      <button type="button" class="icon-button" data-toggle-left title="${state.leftCollapsed ? "Show sidebar" : "Hide sidebar"}">☰</button>
      <div class="brand"><span class="brand-mark"></span><span>Memory Trace</span></div>
      <div class="runtime-chip"><span class="runtime-dot"></span><span>${esc(state.runtime?.label || "runtime")}</span><span>${state.runtime?.entry_count || 0} entries</span></div>
      ${state.view === "search"
        ? `<div class="searchbox"><span>⌕</span><input id="query" value="${escAttr(state.query)}" placeholder="Search memory, tags, files, decisions" spellcheck="false"></div>`
        : `<div class="searchbox-spacer"></div>`}
      <div class="segmented">${tabs}</div>
      <button type="button" class="icon-button" data-theme title="Theme">${state.theme === "dark" ? "◐" : "◑"}</button>
      <div class="palette">${["indigo", "teal", "amber", "ruby", "violet"].map((name) => `<button type="button" class="${state.accent === name ? "active" : ""}" data-accent="${name}" title="${name}" style="background:${palettePreview(name)}"></button>`).join("")}</div>
    </header>`;
}

function leftPane() {
  const facets = state.facets || { agents: {}, users: {}, topics: {}, runtime: {} };
  return `
    <div class="metric-grid">
      <div class="metric"><strong>${facets.runtime.entry_count || 0}</strong><span>entries</span></div>
      <div class="metric"><strong>${facets.runtime.chunk_count || 0}</strong><span>chunks</span></div>
    </div>
    <div class="section-title"><span>Saved Views</span></div>
    ${savedButton("Recent work", "", "", "newest")}
    ${savedButton("Design decisions", "design decision", "", "relevance")}
    ${savedButton("Related graph", "", "graph", "relevance")}
    <div class="section-title"><span>Filters</span><button type="button" class="chip" data-reset>Reset</button></div>
    <label class="section-title"><span>Date From</span></label><input type="date" id="date-from" value="${escAttr(state.dateFrom)}">
    <label class="section-title"><span>Date To</span></label><input type="date" id="date-to" value="${escAttr(state.dateTo)}">
    <div class="section-title"><span>Agent</span></div>
    ${filterRows(facets.agents, "agent", state.agent)}
    <div class="section-title"><span>User</span></div>
    ${filterRows(facets.users, "user", state.user)}
    <div class="section-title"><span>Topics</span></div>
    <div class="chip-list">${topicChips(facets)}</div>
    <div class="section-title"><span>Granularity</span></div>
    <div class="segmented">${["entry", "section", "all"].map((item) => `<button type="button" class="tab ${state.granularity === item ? "active" : ""}" data-granularity="${item}">${item}</button>`).join("")}</div>`;
}

function topicChips(facets) {
  // Facet hygiene: cap the visible list (Hick's law) behind an explicit
  // "+N more" toggle instead of a 40-chip wall.
  const entries = Object.entries(facets.topics || {});
  const cap = 12;
  const shown = state.topicsExpanded ? entries : entries.slice(0, cap);
  const chips = shown.map(([topic, count]) => `<button type="button" class="chip ${state.topic === topic ? "active" : ""}" data-topic="${escAttr(topic)}">#${esc(topic)} <span class="count">${count}</span></button>`);
  if (entries.length > cap) {
    chips.push(`<button type="button" class="chip" data-topics-more>${state.topicsExpanded ? "show less" : `+${entries.length - cap} more`}</button>`);
  }
  return chips.join("");
}

// Applied-filter chips: active filters stay visible and removable at the point
// of use instead of buried in the sidebar. Date chips only appear when the
// range differs from the corpus bounds.
function filterChips() {
  const bounds = state.facets?.runtime?.date_bounds || [];
  const chips = [];
  if (state.agent) chips.push(["agent", `agent: ${state.agent}`]);
  if (state.user) chips.push(["user", `user: ${state.user}`]);
  if (state.topic) chips.push(["topic", `#${state.topic}`]);
  if (state.dateFrom && state.dateFrom !== (bounds[0] || "")) chips.push(["dateFrom", `from ${state.dateFrom}`]);
  if (state.dateTo && state.dateTo !== (bounds[1] || "")) chips.push(["dateTo", `to ${state.dateTo}`]);
  return chips.map(([key, label]) => `<button type="button" class="chip filter-chip" data-clear-filter="${key}" title="Clear this filter">${esc(label)} ×</button>`).join("");
}

function savedButton(label, query, view, sort) {
  return `<button type="button" class="row-button" data-saved-query="${escAttr(query)}" data-saved-view="${escAttr(view)}" data-saved-sort="${escAttr(sort)}"><span class="swatch"></span><span>${label}</span><span class="count">preset</span></button>`;
}

function filterRows(values, kind, active) {
  const entries = Object.entries(values || {});
  if (!entries.length) return `<div class="count">None</div>`;
  return [
    `<button type="button" class="row-button ${!active ? "active" : ""}" data-${kind}=""><span class="swatch"></span><span>All</span><span class="count">${entries.reduce((sum, item) => sum + item[1], 0)}</span></button>`,
    ...entries.map(([key, count], index) => `<button type="button" class="row-button ${active === key ? "active" : ""}" data-${kind}="${escAttr(key)}"><span class="swatch" style="background:${agentColors[index % agentColors.length]}"></span><span>${esc(key)}</span><span class="count">${count}</span></button>`),
  ].join("");
}

function centerPane() {
  const densityClass = `density-${state.density}`;
  if (state.view === "timeline") return `<section class="${densityClass} timeline-view">${timelineView()}</section>`;
  if (state.view === "trail") return `<section class="${densityClass}">${trailView()}</section>`;
  if (state.view === "graph") return `<section class="${densityClass}">${graphView()}</section>`;
  return `<section class="${densityClass}">${searchView()}</section>`;
}

function searchView() {
  return `
    <div class="viewbar">
      <span class="meta"><strong>${state.results.length}</strong> ${state.granularity === "entry" ? "entries" : "results"} shown ${state.nextCursor ? "of more" : ""}</span>
      ${filterChips()}
      <span class="spacer"></span>
      <select id="sort">${["relevance", "newest", "oldest"].map((item) => `<option value="${item}" ${state.sort === item ? "selected" : ""}>${item}</option>`).join("")}</select>
      <div class="segmented">${["comfortable", "compact"].map((item) => `<button type="button" class="tab ${state.density === item ? "active" : ""}" data-density="${item}">${item}</button>`).join("")}</div>
    </div>
    <div class="scroll">
      ${state.results.length ? resultList() : `<div class="empty">No session entries match the current filters.</div>`}
      ${state.nextCursor ? `<button type="button" class="chip" data-more>Load more</button>` : ""}
    </div>`;
}

function resultList() {
  // Scores only mean something against a query; on empty-query browsing they
  // are uniform zeros and would just be noise.
  const showScore = Boolean(state.query.trim());
  if (state.density === "compact") {
    return `<div class="results">${state.results.map((item) => `<div class="compact-row ${item.chunk_id === state.selectedId ? "selected" : ""}" data-chunk="${escAttr(item.chunk_id)}" title="${escAttr(item.title)}"><span>${item.date} ${item.time || ""}</span><span>${esc(stripTitleStamp(item.title))}${(item.matched_sections || []).length ? ` <span class="count">· ${(item.matched_sections || []).length} matched section${(item.matched_sections || []).length === 1 ? "" : "s"}</span>` : ""}</span><span class="optional-wide">${esc(item.agent_type || "")}</span><span>${showScore ? Number(item.score || 0).toFixed(1) : ""}</span></div>`).join("")}</div>`;
  }
  // Minimal glance state (overview-first): date + title (+ score under a
  // query). Excerpts, topics, agent, and matched sections all live in the
  // reader on selection.
  return `<div class="results">${state.results.map((item) => {
    const matched = (item.matched_sections || []).length;
    return `
    <article class="card ${item.chunk_id === state.selectedId ? "selected" : ""}" data-chunk="${escAttr(item.chunk_id)}" title="${escAttr(item.title)}">
      <div class="card-head"><span>${item.date} ${item.time || ""}</span>${matched ? `<span class="count">${matched} matched section${matched === 1 ? "" : "s"}</span>` : ""}${showScore ? `<span class="score">${Number(item.score || 0).toFixed(1)}</span>` : ""}</div>
      <h3>${esc(stripTitleStamp(item.title))}</h3>
    </article>`;
  }).join("")}</div>`;
}

function timelineView() {
  const timeline = state.timeline;
  if (!timeline) return `<div class="empty">Timeline loading</div>`;
  const max = Math.max(1, ...timeline.buckets.map((bucket) => bucket.count));
  const bucketMin = 44;
  const byDay = groupBy(timeline.stream, (item) => item.date);
  const zoomControls = ["day", "12h", "6h", "3h"]
    .map((item) => `<button type="button" class="tab ${state.timelineZoom === item ? "active" : ""}" data-timeline-zoom="${item}">${item}</button>`)
    .join("");
  return `
    <div class="viewbar">
      <span class="meta">Activity overview</span>
      ${filterChips()}
      <span class="spacer"></span>
      <button type="button" class="chip ${state.timelineHideEmpty ? "active" : ""}" data-timeline-empty>${state.timelineHideEmpty ? "Showing active days" : "Showing empty days"}</button>
      <div class="segmented timeline-zoom" role="group" aria-label="Timeline granularity">${zoomControls}</div>
    </div>
    <div class="timeline-overview">
      <div class="overview-scroll">
        <div class="overview" style="--bucket-count:${timeline.buckets.length}; --bucket-min:${bucketMin}px">${timeline.buckets.map((bucket) => {
          const selected = state.timelineSelectedBucket === bucket.start;
          return `<button type="button" class="bucket ${bucket.count ? "active" : ""} ${selected ? "selected" : ""}" data-bucket-date="${escAttr(bucket.date)}" data-bucket-start="${escAttr(bucket.start)}" data-bucket-end="${escAttr(bucket.end)}" title="${escAttr(bucket.label)} · ${bucket.count}" style="height:${18 + (bucket.count / max) * 58}px"><span class="bucket-label">${esc(formatBucketLabel(bucket))}</span><span class="bucket-count">${bucket.count || ""}</span></button>`;
        }).join("")}</div>
      </div>
    </div>
    <div class="timeline-stream">
      ${Object.entries(byDay).map(([day, items]) => `<div class="day-group" id="day-${day}"><div class="day-head">${day} · ${items.length} entries</div>${items.map((item) => `<div class="timeline-item" data-chunk="${escAttr(item.chunk_id)}" data-entry-datetime="${escAttr(timelineItemDatetime(item))}" title="${escAttr(item.title)}${item.agent_type ? escAttr(` · ${item.agent_type}`) : ""}"><span class="timeline-time">${item.time || "00:00"}</span><span class="timeline-title">${esc(stripTitleStamp(item.title))}</span></div>`).join("")}</div>`).join("")}
    </div>`;
}

function graphView() {
  const graph = state.graph;
  if (!graph) return `<div class="empty">Graph loading</div>`;
  const positions = graphPositions(graph.nodes, graph.edges);
  const related = graphRelatedIds(graph, state.graphHover);
  return `
    <div class="viewbar">
      <span class="meta">${graph.nodes.length} nodes · ${graph.edges.length} edges</span>
      ${filterChips()}
      <span class="spacer"></span>
      <div class="segmented">${[["all", "All entries"], ["neighborhood", "Neighborhood"]].map(([scope, label]) => `<button type="button" class="tab ${state.graphScope === scope ? "active" : ""}" data-graph-scope="${scope}">${label}</button>`).join("")}</div>
      <button type="button" class="chip" data-graph-reset>Reset view</button>
      <button type="button" class="chip" data-graph-fit>Fit view</button>
      <button type="button" class="chip ${state.graphSizeMode === "importance" ? "active" : ""}" data-graph-size title="Toggle node size between link connectivity and importance score">Size: ${state.graphSizeMode === "importance" ? "importance" : "links"}</button>
      ${["related", "topic", "agent", "day"].map((type) => `<button type="button" class="chip edge-chip ${state.graphEdgeTypes.has(type) ? "active" : ""}" data-edge="${type}" style="border-color:${edgeColor(type)}">${type}</button>`).join("")}
    </div>
    <div class="graph-stage">
      <svg class="graph-canvas" data-graph-canvas viewBox="0 0 1000 620" role="img">
      <defs>
        <marker id="arrow-supersedes" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("supersedes")}"></path>
        </marker>
      </defs>
      <g class="graph-layer" transform="translate(${state.graphTransform.x} ${state.graphTransform.y}) scale(${state.graphTransform.scale})">
      ${graph.edges.map((edge) => {
        const a = positions[edge.source], b = positions[edge.target];
        if (!a || !b) return "";
        const highlight = state.graphHover && (edge.source === state.graphHover || edge.target === state.graphHover);
        const dim = state.graphHover && !highlight;
        // supersedes: directed + dashed status edge, never conflated with related.
        const width = edge.type === "supersedes" ? 2.2 : edge.type === "branch" ? 1.6 : edge.type === "related" ? 2 : 1;
        const dash = edge.type === "supersedes" ? ' stroke-dasharray="6 4"' : "";
        const marker = edge.type === "supersedes" ? ' marker-end="url(#arrow-supersedes)"' : "";
        return `<line class="graph-edge graph-edge-${edge.type} ${highlight ? "graph-related" : ""} ${dim ? "graph-dim" : ""}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${edgeColor(edge.type)}" stroke-width="${width}"${dash}${marker}></line>`;
      }).join("")}
      ${graph.nodes.map((node, index) => {
        const p = positions[node.id];
        const selected = node.chunk_id === state.selectedId || node.id === state.selected?.entry_id;
        const highlight = state.graphHover && (node.id === state.graphHover || related.has(node.id));
        const dim = state.graphHover && !highlight;
        const sizeVal = state.graphSizeMode === "importance" ? Number(node.importance_score || 0) : Number(node.connectivity || 0);
        const radius = selected ? 18 : Math.min(16, 7 + sizeVal * 2.2);
        return `<g class="graph-node ${highlight ? "graph-related" : ""} ${dim ? "graph-dim" : ""}" data-node-id="${escAttr(node.id)}" data-chunk="${escAttr(node.chunk_id)}"><circle class="graph-hit" cx="${p.x}" cy="${p.y}" r="${Math.max(radius + 10, 20)}"></circle><circle cx="${p.x}" cy="${p.y}" r="${radius}" fill="${agentColor(node.agent)}" stroke="${selected ? "var(--accent)" : "var(--bg)"}" stroke-width="3"></circle><text class="graph-label" data-graph-label x="${p.x}" y="${p.y - 15}" text-anchor="middle">${esc(graphTitle(node.title))}</text><title>${esc(node.title)}</title></g>`;
      }).join("")}
      </g>
      </svg>
    </div>`;
}

// --- Trail: interactive git-graph timeline ----------------------------------
// Newest entry at the top, one straight lane per branch (lowest free lane,
// freed when the branch's visible life ends - interval coloring, the
// "straight branches" scheme git clients use). Lifecycle arcs bow through the
// left gutter: supersedes = dashed (replaces), evolves = dotted (refines).
// Day separators share the fixed row height so SVG y stays index * ROW.
const TRAIL_ROW = 30;
const TRAIL_LANE_W = 14;
const TRAIL_GUTTER = 30;
const TRAIL_WINDOW_STEP = 60;
const trailBranchColors = ["#6f7cff", "#3fa66a", "#d9941a", "#8f63e8", "#18a999", "#d94b63", "#4f98d9", "#b8873b", "#7a8ff2", "#5bb98c"];

function trailStamp(node) {
  return Date.parse(node.datetime || `${node.date}T00:00:00`) || 0;
}

function trailTitle(node) {
  return stripTitleStamp(node.title);
}

function trailModel(graph) {
  const nodes = (graph.nodes || [])
    .filter((node) => node.entry_id)
    .sort((a, b) => trailStamp(b) - trailStamp(a) || String(a.id).localeCompare(String(b.id)));
  const total = nodes.length;
  const visible = nodes.slice(0, state.trailWindow);

  const items = [];
  let lastDay = null;
  for (const node of visible) {
    if (node.date !== lastDay) {
      items.push({ kind: "day", label: node.date });
      lastDay = node.date;
    }
    items.push({ kind: "node", node });
  }

  // Branch intervals over display rows (top = newest). A branch owns its lane
  // from its newest to its oldest visible row.
  const rowOf = new Map();
  items.forEach((item, index) => {
    if (item.kind === "node") rowOf.set(item.node.id, index);
  });
  const spans = new Map();
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const branch = item.node.branch || "";
    const span = spans.get(branch) || { first: index, last: index };
    span.first = Math.min(span.first, index);
    span.last = Math.max(span.last, index);
    spans.set(branch, span);
  });
  const branches = [...spans.keys()].sort((a, b) => spans.get(a).first - spans.get(b).first || spans.get(b).last - spans.get(a).last);
  const laneOf = new Map();
  const colorOf = new Map();
  const laneBusyUntil = [];
  branches.forEach((branch, order) => {
    const span = spans.get(branch);
    let lane = laneBusyUntil.findIndex((busy) => busy < span.first);
    if (lane === -1) {
      lane = laneBusyUntil.length;
      laneBusyUntil.push(-1);
    }
    laneBusyUntil[lane] = span.last;
    laneOf.set(branch, lane);
    colorOf.set(branch, trailBranchColors[order % trailBranchColors.length]);
  });

  const lifecycle = (graph.edges || []).filter(
    (edge) => (edge.type === "supersedes" || edge.type === "evolves") && rowOf.has(edge.source) && rowOf.has(edge.target)
  );
  return { items, total, rowOf, spans, laneOf, colorOf, laneCount: laneBusyUntil.length, lifecycle };
}

function trailView() {
  const graph = state.graph;
  if (!graph) return `<div class="empty">Trail loading</div>`;
  const model = trailModel(graph);
  const { items, total, rowOf, spans, laneOf, colorOf, lifecycle } = model;
  if (!items.length) return `<div class="empty">No entries with lineage data yet.</div>`;
  const laneX = (branch) => TRAIL_GUTTER + (laneOf.get(branch) || 0) * TRAIL_LANE_W + 7;
  const rowY = (index) => index * TRAIL_ROW + TRAIL_ROW / 2;
  const railWidth = TRAIL_GUTTER + model.laneCount * TRAIL_LANE_W + 12;
  const height = items.length * TRAIL_ROW;
  const selectedEntry = state.selected?.entry_id || "";

  // Lane continuity: connect consecutive visible rows of the same branch.
  // Entries with no recorded branch get a dot but no line - continuity that
  // was never recorded is not drawn.
  const laneRows = new Map();
  items.forEach((item, index) => {
    if (item.kind !== "node" || !item.node.branch) return;
    const branch = item.node.branch;
    if (!laneRows.has(branch)) laneRows.set(branch, []);
    laneRows.get(branch).push(index);
  });
  const laneSegments = [...laneRows.entries()].flatMap(([branch, rows]) =>
    rows.slice(1).map((row, i) => `<line x1="${laneX(branch)}" y1="${rowY(rows[i])}" x2="${laneX(branch)}" y2="${rowY(row)}" stroke="${colorOf.get(branch)}" stroke-width="2" stroke-opacity="0.55"></line>`)
  );

  const arcs = lifecycle.map((edge) => {
    const sourceItem = items[rowOf.get(edge.source)];
    const targetItem = items[rowOf.get(edge.target)];
    const sx = laneX(sourceItem.node.branch || "");
    const sy = rowY(rowOf.get(edge.source));
    const tx = laneX(targetItem.node.branch || "");
    const ty = rowY(rowOf.get(edge.target));
    const bow = Math.max(4, TRAIL_GUTTER - 8 - Math.min(18, Math.abs(ty - sy) / TRAIL_ROW));
    const touched = selectedEntry && (edge.source === selectedEntry || edge.target === selectedEntry);
    const dash = edge.type === "supersedes" ? "6 4" : "2 3";
    return `<path d="M ${sx} ${sy} C ${bow} ${sy} ${bow} ${ty} ${tx} ${ty}" fill="none" stroke="${edgeColor(edge.type)}" stroke-width="${touched ? 2.4 : 1.6}" stroke-dasharray="${dash}" stroke-opacity="${!selectedEntry || touched ? 0.9 : 0.3}" marker-end="url(#trail-arrow-${edge.type})"><title>${esc(trailTitle(sourceItem.node))} ${edge.type === "supersedes" ? "replaces" : "refines"} ${esc(trailTitle(targetItem.node))}</title></path>`;
  });

  const dots = items.flatMap((item, index) => {
    if (item.kind !== "node") return [];
    const branch = item.node.branch || "";
    const selected = item.node.entry_id === selectedEntry || item.node.chunk_id === state.selectedId;
    return [`<circle cx="${laneX(branch)}" cy="${rowY(index)}" r="${selected ? 6.5 : 4.5}" fill="${branch ? colorOf.get(branch) : "var(--faint)"}" stroke="${selected ? "var(--accent-strong)" : "var(--bg)"}" stroke-width="${selected ? 2.5 : 2}"></circle>`];
  });

  const rows = items.map((item, index) => {
    if (item.kind === "day") return `<div class="trail-day">${esc(item.label)}</div>`;
    const node = item.node;
    const branch = node.branch || "";
    const tip = branch && spans.get(branch)?.first === index;
    const selected = node.entry_id === selectedEntry || node.chunk_id === state.selectedId;
    const time = node.datetime ? node.datetime.slice(11, 16) : "";
    return `
      <div class="trail-row ${selected ? "selected" : ""}" data-chunk="${escAttr(node.chunk_id)}" title="${escAttr(node.title)}${branch ? escAttr(` · ${branch}`) : ""}">
        <span class="trail-time">${time}</span>
        <span class="trail-title">${esc(trailTitle(node))}</span>
        ${tip ? `<span class="trail-branch" style="color:${colorOf.get(branch)}">${esc(branch)}</span>` : ""}
      </div>`;
  });

  const shown = items.filter((item) => item.kind === "node").length;
  return `
    <div class="viewbar">
      <span class="meta"><strong>${shown}</strong> of ${total} entries · newest first</span>
      <span class="spacer"></span>
      <span class="legend-item"><span class="legend-line legend-line-dashed" style="border-color:${edgeColor("supersedes")}"></span>replaces</span>
      <span class="legend-item"><span class="legend-line legend-line-dotted" style="border-color:${edgeColor("evolves")}"></span>refines</span>
      ${shown < total ? `<button type="button" class="chip" data-trail-more>Load older</button>` : ""}
    </div>
    <div class="trail-scroll">
      <div class="trail-body">
        <svg class="trail-rail" width="${railWidth}" height="${height}" viewBox="0 0 ${railWidth} ${height}" aria-hidden="true">
          <defs>
            <marker id="trail-arrow-supersedes" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("supersedes")}"></path></marker>
            <marker id="trail-arrow-evolves" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("evolves")}"></path></marker>
          </defs>
          ${laneSegments.join("")}
          ${arcs.join("")}
          ${dots.join("")}
        </svg>
        <div class="trail-rows">${rows.join("")}</div>
      </div>
      ${shown < total ? `<button type="button" class="chip trail-more" data-trail-more>Load older entries</button>` : ""}
    </div>`;
}

function rightPane() {
  const selected = state.selected;
  if (!selected) return `<div class="empty">Select a memory to inspect details.</div>`;
  const linkGroups = [
    ["Related", selected.related_entries || []],
    ["Backlinks", selected.backlinks || []],
  ];
  return `
    <div class="detail-header">
      <div class="entry-meta"><span>${selected.date} ${selected.time || ""}</span><span>${esc(selected.agent_type || "")}</span></div>
      <h2>${esc(selected.title)}</h2>
      <div class="count">${esc(selected.chunk_id)}</div>
    </div>
    <section class="detail-section">
      <h4>Entry${matchNote(selected)}</h4>
      <div class="chip-list">${(selected.sections || []).map((section) => `<span class="chip">${esc(section)}</span>`).join("")}</div>
      <div class="markdown">${markdown(selected.text || "")}</div>
    </section>
    ${diagramsSection(selected)}
    <section class="detail-section">
      <h4>Linked Memories</h4>
      ${linkGroups.map(([label, ids]) => `<div><div class="count">${label} · ${ids.length}</div>${ids.map((id) => `<button type="button" class="link-card" data-entry="${escAttr(id)}">${esc(id)}</button>`).join("")}</div>`).join("")}
    </section>
    <section class="detail-section">
      <h4>Suggestions</h4>
      ${Object.entries(selected.suggestions || {}).map(([label, items]) => `<div><div class="count">${label.replace("_", " ")}</div>${items.map((item) => `<button type="button" class="link-card" data-chunk="${escAttr(item.chunk_id)}">${esc(item.title)}<br><span class="count">${item.date}</span></button>`).join("")}</div>`).join("")}
    </section>
    <section class="detail-section">
      <h4>Raw Metadata</h4>
      <dl class="raw-grid">${Object.entries(selected.metadata || {}).map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(String(value ?? ""))}</dd>`).join("")}</dl>
    </section>`;
}

function installDelegatedEvents() {
  const queryInput = debounce(async (value) => {
    state.query = value;
    await reloadCurrentView();
  }, 180);
  let graphDrag = null;
  let suppressGraphClick = false;

  app.addEventListener("input", (event) => {
    if (event.target?.id === "query") queryInput(event.target.value);
  });

  app.addEventListener("wheel", (event) => {
    if (!event.target.closest("[data-graph-canvas]")) return;
    event.preventDefault();
    const next = Math.max(0.45, Math.min(2.6, state.graphTransform.scale + (event.deltaY < 0 ? 0.08 : -0.08)));
    state.graphTransform.scale = next;
    render();
  }, { passive: false });

  app.addEventListener("pointerdown", (event) => {
    if (!event.target.closest("[data-graph-canvas]") || event.target.closest("[data-node-id]")) return;
    graphDrag = { x: event.clientX, y: event.clientY, panX: state.graphTransform.x, panY: state.graphTransform.y };
  });

  window.addEventListener("pointermove", (event) => {
    if (!graphDrag) return;
    state.graphTransform.x = graphDrag.panX + event.clientX - graphDrag.x;
    state.graphTransform.y = graphDrag.panY + event.clientY - graphDrag.y;
    render();
  });

  window.addEventListener("pointerup", () => {
    graphDrag = null;
  });

  app.addEventListener("mouseenter", (event) => {
    const node = event.target.closest("[data-node-id]");
    if (!node) return;
    if (state.graphHover === node.dataset.nodeId) return;
    state.graphHover = node.dataset.nodeId;
    render();
  }, true);

  app.addEventListener("mouseout", (event) => {
    if (!state.graphHover || event.relatedTarget?.closest?.("[data-graph-canvas]")) return;
    clearGraphHover();
  });

  app.addEventListener("change", async (event) => {
    const target = event.target;
    if (!target) return;
    if (target.id === "sort") {
      state.sort = target.value;
      await reloadCurrentView();
    } else if (target.id === "date-from") {
      await updateFilter("dateFrom", target.value);
    } else if (target.id === "date-to") {
      await updateFilter("dateTo", target.value);
    } else if (target.id === "timeline-zoom") {
      state.timelineZoom = target.value;
      await reloadCurrentView();
    }
  });

  app.addEventListener("pointerup", async (event) => {
    if (event.button && event.button !== 0) return;
    const graphNode = event.target.closest("[data-node-id][data-chunk]") || findGraphNodeFromPoint(event.clientX, event.clientY);
    if (!graphNode) return;
    suppressGraphClick = true;
    await openGraphChunk(graphNode.dataset.chunk);
  });

  app.addEventListener("click", async (event) => {
    const graphNode = event.target.closest("[data-node-id][data-chunk]");
    if (graphNode) {
      if (suppressGraphClick) {
        suppressGraphClick = false;
        return;
      }
      await openGraphChunk(graphNode.dataset.chunk);
      return;
    }
    const graphHit = event.target.closest("[data-graph-canvas]") ? findGraphNodeFromPoint(event.clientX, event.clientY) : null;
    if (graphHit) {
      if (suppressGraphClick) {
        suppressGraphClick = false;
        return;
      }
      await openGraphChunk(graphHit.dataset.chunk);
      return;
    }

    const target = event.target.closest("button, [data-chunk]");
    if (!target) return;

    if (target.dataset.theme !== undefined) {
      state.theme = state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("ml:theme", state.theme);
      render();
      return;
    }
    if (target.dataset.accent) {
      state.accent = target.dataset.accent;
      localStorage.setItem("ml:accent", state.accent);
      render();
      return;
    }
    if (target.dataset.view) {
      await setView(target.dataset.view);
      return;
    }
    if (target.dataset.agent !== undefined) {
      await updateFilter("agent", target.dataset.agent);
      return;
    }
    if (target.dataset.user !== undefined) {
      await updateFilter("user", target.dataset.user);
      return;
    }
    if (target.dataset.topic) {
      await updateFilter("topic", state.topic === target.dataset.topic ? "" : target.dataset.topic);
      return;
    }
    if (target.dataset.granularity) {
      await updateFilter("granularity", target.dataset.granularity);
      return;
    }
    if (target.dataset.density) {
      state.density = target.dataset.density;
      render();
      return;
    }
    if (target.dataset.timelineZoom) {
      state.timelineZoom = target.dataset.timelineZoom;
      await reloadCurrentView();
      return;
    }
    if (target.dataset.timelineEmpty !== undefined) {
      state.timelineHideEmpty = !state.timelineHideEmpty;
      localStorage.setItem("ml:timelineHideEmpty", state.timelineHideEmpty ? "1" : "0");
      await reloadCurrentView();
      return;
    }
    if (target.dataset.graphScope) {
      state.graphScope = target.dataset.graphScope;
      state.graphHover = "";
      await reloadCurrentView();
      return;
    }
    if (target.dataset.graphReset !== undefined) {
      resetGraphView();
      return;
    }
    if (target.dataset.graphFit !== undefined) {
      fitGraphView();
      return;
    }
    if (target.dataset.reset !== undefined) {
      await resetFilters();
      return;
    }
    if (target.dataset.more !== undefined) {
      const token = ++state.loadSeq;
      await loadSearch(state.nextCursor, true, token);
      if (token === state.loadSeq) render();
      return;
    }
    if (target.dataset.trailMore !== undefined) {
      state.trailWindow += TRAIL_WINDOW_STEP;
      render();
      return;
    }
    if (target.dataset.toggleLeft !== undefined) {
      state.leftCollapsed = !state.leftCollapsed;
      localStorage.setItem("ml:leftCollapsed", state.leftCollapsed ? "1" : "0");
      render();
      return;
    }
    if (target.dataset.topicsMore !== undefined) {
      state.topicsExpanded = !state.topicsExpanded;
      render();
      return;
    }
    if (target.dataset.clearFilter) {
      const key = target.dataset.clearFilter;
      const bounds = state.facets?.runtime?.date_bounds || [];
      const cleared = key === "dateFrom" ? bounds[0] || "" : key === "dateTo" ? bounds[1] || "" : "";
      await updateFilter(key, cleared);
      return;
    }
    if (target.dataset.bucketStart) {
      selectTimelineBucket(target);
      return;
    }
    if (target.dataset.graphSize !== undefined) {
      state.graphSizeMode = state.graphSizeMode === "importance" ? "links" : "importance";
      localStorage.setItem("ml:graphSizeMode", state.graphSizeMode);
      render();
      return;
    }
    if (target.dataset.edge) {
      state.graphEdgeTypes.has(target.dataset.edge) ? state.graphEdgeTypes.delete(target.dataset.edge) : state.graphEdgeTypes.add(target.dataset.edge);
      await reloadCurrentView();
      return;
    }
    if (target.dataset.savedQuery !== undefined) {
      state.query = target.dataset.savedQuery;
      state.sort = target.dataset.savedSort;
      if (target.dataset.savedView) state.view = target.dataset.savedView;
      await reloadCurrentView();
      return;
    }
    if (target.dataset.entry) {
      const token = ++state.loadSeq;
      await selectChunk(target.dataset.entry, true, token);
      return;
    }
    if (target.dataset.chunk) {
      const hint = matchHintFor(target.dataset.chunk);
      state.matchHint = hint;
      state.pendingMatchScroll = Boolean(hint);
      const token = ++state.loadSeq;
      await selectChunk(target.dataset.chunk, true, token);
    }
  });
}

// Entry-level UI results: derive the best-matching subsection heading for a
// search result so the reader can scroll to and highlight it inside the parent
// entry. Returns null for entry-level matches or non-search selections (e.g.
// suggestions/graph nodes whose chunk_id is not in the current results).
function matchHintFor(chunkId) {
  const item = (state.results || []).find((result) => result.chunk_id === chunkId);
  const sections = item && item.matched_sections ? item.matched_sections : [];
  if (!item || !sections.length) return null;
  const best = sections.find((section) => section.chunk_id === item.best_match_chunk_id) || sections[0];
  const heading = (best.heading_path || []).slice(-1)[0];
  return heading ? { entryId: item.entry_id, heading } : null;
}

// Post-render: mark the matched subsection inside the reader and, once per
// selection, scroll it into view. Idempotent - safe to call on every render.
function applyMatchHighlight() {
  const hint = state.matchHint;
  if (!hint || !state.selected || state.selected.entry_id !== hint.entryId) return;
  const container = document.querySelector(".pane.right .markdown");
  if (!container) return;
  const target = [...container.querySelectorAll("h4")].find(
    (node) => node.textContent.trim() === hint.heading,
  );
  if (!target) return;
  target.classList.add("match-highlight");
  let node = target.nextElementSibling;
  while (node && node.tagName !== "H4") {
    node.classList.add("match-highlight-body");
    node = node.nextElementSibling;
  }
  if (state.pendingMatchScroll) {
    target.scrollIntoView({ block: "center" });
    state.pendingMatchScroll = false;
  }
}

// Reader section for authored Class-2 decision diagrams (Arc 2d). Frozen,
// point-in-time reasoning diagrams rendered client-side beside their entry;
// nothing shows when an entry has no sidecar (no empty frame).
function diagramsSection(selected) {
  const blocks = (selected.diagrams || []).flatMap((sidecar) =>
    (sidecar.mermaid_blocks || []).map((source) => ({ source, title: sidecar.title })),
  );
  if (!blocks.length) return "";
  return `
    <section class="detail-section">
      <h4>Decision diagrams</h4>
      ${blocks.map((block) => `<figure class="diagram">${block.title ? `<figcaption class="count">${esc(block.title)}</figcaption>` : ""}${renderDiagramBlock(block.source)}</figure>`).join("")}
    </section>`;
}

// Small reader-header note naming the matched subsection, when one is active for
// the open entry. Consistent "Best match" microcopy - never raw chunk language.
function matchNote(selected) {
  const hint = state.matchHint;
  if (!hint || !selected || selected.entry_id !== hint.entryId) return "";
  return ` · <span class="match-note">Best match: ${esc(hint.heading)}</span>`;
}

async function setView(view) {
  state.view = view;
  localStorage.setItem("ml:view", view);
  await reloadCurrentView();
}

async function updateFilter(key, value) {
  state[key] = value;
  if (key === "dateFrom" || key === "dateTo" || key === "agent" || key === "user" || key === "topic") {
    state.timelineSelectedBucket = "";
  }
  await reloadCurrentView();
}

async function resetFilters() {
  state.agent = "";
  state.user = "";
  state.topic = "";
  state.granularity = "entry";
  state.sort = "relevance";
  state.timelineSelectedBucket = "";
  seedDates();
  await reloadCurrentView();
}

async function reloadCurrentView() {
  const token = ++state.loadSeq;
  await loadView();
  if (token === state.loadSeq) render();
}

async function openGraphChunk(chunkId) {
  state.graphHover = "";
  const token = ++state.loadSeq;
  await selectChunk(chunkId, true, token);
}

function selectTimelineBucket(target) {
  const bucket = {
    date: target.dataset.bucketDate,
    start: target.dataset.bucketStart,
    end: target.dataset.bucketEnd,
  };
  state.timelineSelectedBucket = bucket.start;
  markSelectedTimelineBucket(bucket.start);
  scrollTimelineToBucket(bucket);
}

function markSelectedTimelineBucket(bucketStart) {
  document.querySelectorAll(".bucket.selected").forEach((bucket) => bucket.classList.remove("selected"));
  const selected = document.querySelector(`.bucket[data-bucket-start="${cssEscape(bucketStart)}"]`);
  if (selected) selected.classList.add("selected");
}

function findGraphNodeFromPoint(x, y) {
  let nearest = null;
  let nearestDistance = Number.POSITIVE_INFINITY;
  document.querySelectorAll("[data-node-id][data-chunk]").forEach((node) => {
    const rect = node.getBoundingClientRect();
    const inside = x >= rect.left - 4 && x <= rect.right + 4 && y >= rect.top - 4 && y <= rect.bottom + 4;
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distance = Math.hypot(x - centerX, y - centerY);
    if (inside || distance < 24) {
      if (distance < nearestDistance) {
        nearest = node;
        nearestDistance = distance;
      }
    }
  });
  return nearest;
}

function scrollTimelineToBucket(bucket) {
  const stream = document.querySelector(".timeline-stream");
  const target = findTimelineBucketTarget(bucket);
  if (!stream || !target) return;
  stream.scrollTo({
    top: Math.max(0, target.offsetTop - stream.offsetTop),
    behavior: "smooth",
  });
}

function findTimelineBucketTarget(bucket) {
  const items = Array.from(document.querySelectorAll(".timeline-item[data-entry-datetime]"));
  const exact = items.find((item) => {
    const value = item.dataset.entryDatetime;
    return value >= bucket.start && value < bucket.end;
  });
  if (exact) return exact;
  return document.getElementById(`day-${bucket.date}`);
}

function clearGraphHover() {
  state.graphHover = "";
  render();
}

function resetGraphView() {
  state.graphTransform = { x: 0, y: 0, scale: 1 };
  render();
}

function captureCenterScroll() {
  const stateBySelector = {};
  [".scroll", ".timeline-stream", ".overview-scroll"].forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) stateBySelector[selector] = { top: element.scrollTop, left: element.scrollLeft };
  });
  return stateBySelector;
}

function restoreCenterScroll(scrollState) {
  Object.entries(scrollState || {}).forEach(([selector, position]) => {
    const element = document.querySelector(selector);
    if (!element) return;
    element.scrollTop = position.top || 0;
    element.scrollLeft = position.left || 0;
  });
}

function fitGraphView() {
  if (!state.graph?.nodes?.length) {
    resetGraphView();
    return;
  }
  const positions = graphPositions(state.graph.nodes, state.graph.edges);
  const points = Object.values(positions);
  const minX = Math.min(...points.map((point) => point.x));
  const maxX = Math.max(...points.map((point) => point.x));
  const minY = Math.min(...points.map((point) => point.y));
  const maxY = Math.max(...points.map((point) => point.y));
  const width = Math.max(1, maxX - minX);
  const height = Math.max(1, maxY - minY);
  const scale = Math.max(0.45, Math.min(2.6, Math.min(880 / width, 500 / height)));
  state.graphTransform = {
    x: 500 - ((minX + maxX) / 2) * scale,
    y: 310 - ((minY + maxY) / 2) * scale,
    scale,
  };
  render();
}

function restorePanes() {
  const left = localStorage.getItem("ml:left");
  const right = localStorage.getItem("ml:right");
  if (left) document.documentElement.style.setProperty("--left-width", `${left}px`);
  if (right) document.documentElement.style.setProperty("--right-width", `${right}px`);
}

function bindResizers() {
  document.querySelectorAll("[data-resize]").forEach((handle) => {
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      const side = handle.dataset.resize;
      const startX = event.clientX;
      const rootStyle = getComputedStyle(document.documentElement);
      const prop = side === "left" ? "--left-width" : "--right-width";
      const current = Number.parseInt(rootStyle.getPropertyValue(prop), 10) || (side === "left" ? 260 : 390);
      const move = (moveEvent) => {
        const delta = moveEvent.clientX - startX;
        const next = side === "left" ? current + delta : current - delta;
        const clamped = Math.max(side === "left" ? 190 : 260, Math.min(side === "left" ? 420 : 560, next));
        document.documentElement.style.setProperty(prop, `${clamped}px`);
        localStorage.setItem(`ml:${side}`, String(clamped));
      };
      const up = () => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
    });
  });
}

function observePanes() {
  if (!window.ResizeObserver) return;
  if (paneObserver) paneObserver.disconnect();
  paneObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const width = entry.contentRect.width;
      entry.target.classList.toggle("density-compact", width < 330);
      entry.target.classList.toggle("density-expanded", width > 520);
    }
  });
  document.querySelectorAll("[data-pane]").forEach((pane) => paneObserver.observe(pane));
}

function groupBy(items, fn) {
  return items.reduce((acc, item) => {
    const key = fn(item);
    (acc[key] = acc[key] || []).push(item);
    return acc;
  }, {});
}

function formatBucketLabel(bucket) {
  if (state.timelineZoom === "day") return bucket.date.slice(5);
  const start = new Date(bucket.start);
  const monthDay = bucket.date.slice(5);
  const hour = String(start.getHours()).padStart(2, "0");
  return `${monthDay} ${hour}`;
}

function timelineItemDatetime(item) {
  return `${item.date}T${item.time || "00:00"}:00`;
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function graphPositions(nodes, edges = []) {
  const positions = {};
  const centerX = 500;
  const centerY = 310;
  const links = graphDegrees({ edges });
  const layoutLinks = layoutSimilarityLinks(nodes, edges);
  nodes.forEach((node, index) => {
    const seed = hashString(node.id || `${index}`);
    const angle = ((seed % 3600) / 3600) * Math.PI * 2;
    const ring = 0.22 + (((seed >>> 8) % 1000) / 1000) * 0.78;
    const degreePull = Math.max(0.55, 1 - (links[node.id] || 0) * 0.025);
    const wobbleX = (((seed >>> 18) % 1000) / 1000 - 0.5) * 72;
    const wobbleY = (((seed >>> 28) % 1000) / 1000 - 0.5) * 52;
    positions[node.id] = {
      x: centerX + Math.cos(angle) * 420 * ring * degreePull + wobbleX,
      y: centerY + Math.sin(angle) * 250 * ring * degreePull + wobbleY,
    };
  });
  for (let pass = 0; pass < 3; pass += 1) {
    layoutLinks.forEach((edge) => {
      const a = positions[edge.source], b = positions[edge.target];
      if (!a || !b) return;
      const midX = (a.x + b.x) / 2;
      const midY = (a.y + b.y) / 2;
      const strength = edge.strength || 0.03;
      a.x += (midX - a.x) * strength;
      a.y += (midY - a.y) * strength;
      b.x += (midX - b.x) * strength;
      b.y += (midY - b.y) * strength;
    });
  }
  return positions;
}

function layoutSimilarityLinks(nodes, edges) {
  const visible = new Set(nodes.map((node) => node.id));
  const links = [];
  const seen = new Set();
  edges.filter((edge) => edge.type === "related").forEach((edge) => {
    if (!visible.has(edge.source) || !visible.has(edge.target)) return;
    const key = [edge.source, edge.target].sort().join("|");
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ source: edge.source, target: edge.target, strength: 0.075 });
  });
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const topicScore = sharedTopicScore(nodes[i], nodes[j]);
      const dateScore = dateProximityScore(nodes[i], nodes[j]);
      const strength = topicScore * 0.045 + dateScore * 0.026;
      if (strength <= 0.01) continue;
      const key = [nodes[i].id, nodes[j].id].sort().join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      links.push({ source: nodes[i].id, target: nodes[j].id, strength });
    }
  }
  return links;
}

function sharedTopicScore(left, right) {
  const leftTopics = new Set(left.topics || []);
  const rightTopics = new Set(right.topics || []);
  if (!leftTopics.size || !rightTopics.size) return 0;
  let shared = 0;
  leftTopics.forEach((topic) => {
    if (rightTopics.has(topic)) shared += 1;
  });
  return Math.min(1, shared / Math.max(leftTopics.size, rightTopics.size));
}

function dateProximityScore(left, right) {
  const leftTime = Date.parse(left.date || "");
  const rightTime = Date.parse(right.date || "");
  if (Number.isNaN(leftTime) || Number.isNaN(rightTime)) return 0;
  const days = Math.abs(leftTime - rightTime) / 86400000;
  if (days > 14) return 0;
  return Math.max(0, 1 - days / 14);
}

function graphRelatedIds(graph, nodeId) {
  const related = new Set();
  if (!nodeId) return related;
  graph.edges.forEach((edge) => {
    if (edge.source === nodeId) related.add(edge.target);
    if (edge.target === nodeId) related.add(edge.source);
  });
  return related;
}

function graphDegrees(graph) {
  const degree = {};
  graph.edges.forEach((edge) => {
    degree[edge.source] = (degree[edge.source] || 0) + 1;
    degree[edge.target] = (degree[edge.target] || 0) + 1;
  });
  return degree;
}

// Entry titles start with their timestamp; every list view already shows the
// date/time in its own column, so strip the prefix instead of repeating it.
function stripTitleStamp(title) {
  return String(title || "").replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*-\s*/, "");
}

function graphTitle(title) {
  const value = String(title || "");
  return value.length > 56 ? `${value.slice(0, 53)}...` : value;
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function edgeColor(type) {
  // Edge-type color semantics live as design tokens in styles.css (one defined
  // job per color). supersedes is a status edge and must never read as plain
  // relatedness; branch is a lineage axis. This is the single JS reference.
  return {
    related: "var(--edge-related)",
    topic: "var(--edge-topic)",
    agent: "var(--edge-agent)",
    day: "var(--edge-day)",
    supersedes: "var(--edge-supersedes)",
    evolves: "var(--edge-evolves)",
    branch: "var(--edge-branch)",
  }[type] || "var(--muted)";
}

function agentColor(agent) {
  const value = agent || "unknown";
  return agentColors[hashString(value) % agentColors.length];
}

// --- Arc 2d: minimal, offline, built-in diagram renderer ---------------------
// Renders the flowchart/sequence subset agents actually author in Class-2
// decision-diagram sidecars. No third-party library, no network, no LLM. Any
// diagram type we don't handle (or any parse failure) degrades to the raw
// Mermaid source in a <pre> - never a blank frame.
function renderDiagramBlock(source) {
  const text = String(source || "").trim();
  try {
    const first = text.split("\n")[0].trim().toLowerCase();
    if (first.startsWith("sequencediagram")) return renderSequenceDiagram(text);
    if (first.startsWith("flowchart") || first.startsWith("graph")) return renderFlowchart(text);
  } catch (error) {
    /* fall through to source */
  }
  return `<pre class="diagram-source">${esc(text)}</pre>`;
}

function _diagramNode(token) {
  const match = String(token).trim().match(/^([A-Za-z0-9_-]+)\s*(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\})?/);
  if (!match) return null;
  return { id: match[1], label: (match[2] || match[3] || match[4] || match[1]).trim() };
}

function renderFlowchart(text) {
  const lines = text.split("\n").slice(1).map((line) => line.trim()).filter(Boolean);
  const horizontal = /^(flowchart|graph)\s+(lr|rl)/i.test(text.split("\n")[0]);
  const rightToLeft = /^(flowchart|graph)\s+rl/i.test(text.split("\n")[0]);
  const nodes = new Map();
  const edges = [];
  const note = (node) => { if (node && !nodes.has(node.id)) nodes.set(node.id, node.label); };
  for (const line of lines) {
    if (!line.includes("-->")) {
      const solo = _diagramNode(line);
      note(solo);
      continue;
    }
    const [lhs, rhsRaw] = line.split(/-->/);
    let rhs = rhsRaw, label = "";
    const labelled = rhs.match(/^\s*\|([^|]*)\|\s*(.*)$/);
    if (labelled) { label = labelled[1].trim(); rhs = labelled[2]; }
    const a = _diagramNode(lhs), b = _diagramNode(rhs);
    note(a); note(b);
    if (a && b) edges.push({ from: a.id, to: b.id, label });
  }
  if (!nodes.size) throw new Error("no nodes");
  // Longest-path layering from roots (nodes with no incoming edge).
  const indeg = new Map([...nodes.keys()].map((id) => [id, 0]));
  edges.forEach((edge) => indeg.set(edge.to, (indeg.get(edge.to) || 0) + 1));
  const layer = new Map([...nodes.keys()].map((id) => [id, 0]));
  for (let pass = 0; pass < nodes.size; pass += 1) {
    let changed = false;
    edges.forEach((edge) => {
      const next = layer.get(edge.from) + 1;
      if (next > layer.get(edge.to)) { layer.set(edge.to, next); changed = true; }
    });
    if (!changed) break;
  }
  const byLayer = new Map();
  [...nodes.keys()].forEach((id) => {
    const key = layer.get(id);
    if (!byLayer.has(key)) byLayer.set(key, []);
    byLayer.get(key).push(id);
  });
  const boxW = 130, boxH = 40, gapMain = 78, gapCross = 26;
  const pos = new Map();
  let maxCross = 0;
  [...byLayer.entries()].sort((a, b) => a[0] - b[0]).forEach(([lyr, ids]) => {
    ids.forEach((id, i) => {
      const mainSize = horizontal ? boxW : boxH;
      const crossSize = horizontal ? boxH : boxW;
      const effectiveLayer = horizontal && rightToLeft ? byLayer.size - 1 - lyr : lyr;
      const main = 24 + effectiveLayer * (mainSize + gapMain);
      const cross = 24 + i * (crossSize + gapCross);
      pos.set(id, horizontal ? { x: main, y: cross } : { x: cross, y: main });
    });
    maxCross = Math.max(maxCross, ids.length);
  });
  const layers = byLayer.size;
  const width = horizontal ? 48 + layers * boxW + Math.max(0, layers - 1) * gapMain : 48 + maxCross * boxW + Math.max(0, maxCross - 1) * gapCross;
  const height = horizontal ? 48 + maxCross * boxH + Math.max(0, maxCross - 1) * gapCross : 48 + layers * boxH + Math.max(0, layers - 1) * gapMain;
  const edgeSvg = edges.map((edge) => {
    const a = pos.get(edge.from), b = pos.get(edge.to);
    if (!a || !b) return "";
    const x1 = horizontal ? (rightToLeft ? a.x : a.x + boxW) : a.x + boxW / 2;
    const y1 = horizontal ? a.y + boxH / 2 : a.y + boxH;
    const x2 = horizontal ? (rightToLeft ? b.x + boxW : b.x) : b.x + boxW / 2;
    const y2 = horizontal ? b.y + boxH / 2 : b.y;
    const midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--edge-related)" stroke-width="1.5" marker-end="url(#diagram-arrow)"></line>${edge.label ? `<text class="diagram-edge-label" x="${midX}" y="${midY}" text-anchor="middle">${esc(edge.label)}</text>` : ""}`;
  }).join("");
  const nodeSvg = [...nodes.entries()].map(([id, label]) => {
    const p = pos.get(id);
    return `<g class="diagram-node"><rect x="${p.x}" y="${p.y}" width="${boxW}" height="${boxH}" rx="6"></rect><text x="${p.x + boxW / 2}" y="${p.y + boxH / 2 + 4}" text-anchor="middle">${esc(label)}</text></g>`;
  }).join("");
  return `<svg class="diagram-svg" viewBox="0 0 ${width} ${height}" role="img" preserveAspectRatio="xMidYMid meet">${_diagramArrowDefs()}${edgeSvg}${nodeSvg}</svg>`;
}

function renderSequenceDiagram(text) {
  const lines = text.split("\n").slice(1).map((line) => line.trim()).filter(Boolean);
  const order = [];
  const seen = new Set();
  const messages = [];
  const add = (name) => { if (name && !seen.has(name)) { seen.add(name); order.push(name); } };
  for (const line of lines) {
    const participant = line.match(/^participant\s+(.+)$/i);
    if (participant) { add(participant[1].trim()); continue; }
    const msg = line.match(/^(\w[\w -]*?)\s*(--?>>?|--?>)\s*(\w[\w -]*?)\s*:\s*(.*)$/);
    if (msg) { add(msg[1].trim()); add(msg[3].trim()); messages.push({ from: msg[1].trim(), to: msg[3].trim(), text: msg[4].trim(), dashed: msg[2].includes("--") }); }
  }
  if (!order.length) throw new Error("no participants");
  const colW = 150, topH = 40, rowH = 46;
  const width = 24 + order.length * colW;
  const height = topH + 30 + messages.length * rowH + 20;
  const colX = (name) => 24 + order.indexOf(name) * colW + colW / 2 - 24;
  const heads = order.map((name) => {
    const x = colX(name);
    return `<g class="diagram-node"><rect x="${x - 55}" y="12" width="110" height="${topH}" rx="6"></rect><text x="${x}" y="${12 + topH / 2 + 4}" text-anchor="middle">${esc(name)}</text></g><line class="diagram-lifeline" x1="${x}" y1="${12 + topH}" x2="${x}" y2="${height - 12}" stroke-dasharray="4 4"></line>`;
  }).join("");
  const arrows = messages.map((message, index) => {
    const x1 = colX(message.from), x2 = colX(message.to);
    const y = topH + 40 + index * rowH;
    const dash = message.dashed ? ' stroke-dasharray="5 4"' : "";
    return `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="var(--edge-agent)" stroke-width="1.5"${dash} marker-end="url(#diagram-arrow)"></line><text class="diagram-edge-label" x="${(x1 + x2) / 2}" y="${y - 6}" text-anchor="middle">${esc(message.text)}</text>`;
  }).join("");
  return `<svg class="diagram-svg" viewBox="0 0 ${width} ${height}" role="img" preserveAspectRatio="xMidYMid meet">${_diagramArrowDefs()}${heads}${arrows}</svg>`;
}

function _diagramArrowDefs() {
  return `<defs><marker id="diagram-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker></defs>`;
}

function markdown(text) {
  const lines = text.split("\n");
  const out = [];
  let inCode = false;
  let code = [];
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`);
        code = [];
      }
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    const heading = line.match(/^(#{3,6})\s+(.+)/);
    if (heading) out.push(`<h4>${esc(heading[2])}</h4>`);
    else if (line.trim().startsWith("- ")) out.push(`<p>• ${inline(line.trim().slice(2))}</p>`);
    else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  return out.join("");
}

function inline(text) {
  return esc(text).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function palettePreview(name) {
  return { indigo: "#6676f6", teal: "#18a999", amber: "#d9941a", ruby: "#d94b63", violet: "#8f63e8" }[name];
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function escAttr(value) {
  return esc(value).replace(/`/g, "&#96;");
}

boot().catch((error) => {
  app.innerHTML = `<div class="boot">Memory Trace failed to load: ${esc(error.message)}</div>`;
});
