const state = {
  runtime: null,
  facets: null,
  // On-device worktree switching: `worktrees` is the list from /api/worktrees,
  // `worktree` is the selected one's id (a resolved path), `worktreeDefault` is
  // the launch checkout - the empty/default selection sends no param so the
  // server serves its own checkout. Changing this re-points every fetch at the
  // chosen worktree's branch-specific memory.
  worktrees: [],
  worktree: "",
  worktreeDefault: "",
  // Worktree-switch loading overlay: a subway-map progress animation (the Trail
  // as a train line - "train of thought"). worktreeStage advances 0->1->2 at the
  // real fetch boundaries so stations light up as genuine milestones.
  worktreeLoading: false,
  worktreeStage: 0,
  worktreeToLabel: "",
  view: storedView() || "trail",
  theme: localStorage.getItem("ml:theme") || "dark",
  accent: localStorage.getItem("ml:accent") || "indigo",
  query: "",
  agent: "",
  user: "",
  topic: "",
  granularity: "entry",
  density: "comfortable",
  dateFrom: "",
  dateTo: "",
  graphScope: "all",
  graphSizeMode: localStorage.getItem("ml:graphSizeMode") || "links",
  graphEdgeTypes: new Set(["related"]),
  graphTransform: { x: 0, y: 0, scale: 1 },
  graphHover: "",
  trailWindow: 60,
  leftCollapsed: localStorage.getItem("ml:leftCollapsed") === "1",
  rightCollapsed: localStorage.getItem("ml:rightCollapsed") === "1",
  // Second click on the selected entry mutes its edge emphasis (related
  // routes hidden, lifecycle routes back to pastel) while the entry stays
  // pinned with a border and the reader keeps showing it.
  selectionMuted: false,
  sectionOpen: readStoredJson("ml:sections", { views: false, filters: true, topics: true }),
  topicsExpanded: false,
  // Search is a function over the Trail and Graph, not a destination view:
  // results feed the ranked dropdown, matchEntries drives in-place highlight
  // and dimming in whichever view is open.
  results: [],
  matchEntries: new Set(),
  searchOpen: false,
  pendingTrailScroll: false,
  graph: null,
  selected: null,
  selectedId: null,
  loadSeq: 0,
  // Entry-level UI results plan: when a search result's best match came from a
  // subsection, remember which heading to highlight/scroll-to inside the parent
  // entry reader (never a separate selectable record).
  matchHint: null,
  pendingMatchScroll: false,
};

// Timeline and Search retired as tabs 2026-07-11: Trail is the chronological
// successor and search became a function over Trail/Graph, so stale stored
// view preferences land on Trail instead of a dead tab.
function storedView() {
  const stored = localStorage.getItem("ml:view");
  return stored === "timeline" || stored === "search" ? "trail" : stored;
}

function readStoredJson(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return value && typeof value === "object" ? { ...fallback, ...value } : fallback;
  } catch {
    return fallback;
  }
}

const app = document.getElementById("app");
const agentColors = ["#6f7cff", "#18a999", "#d9941a", "#d94b63", "#8f63e8", "#4f98d9"];
let paneObserver = null;
// Set while restoreFocusedInput() refocuses the search box as a re-render
// bookkeeping detail - the search box's own "focusin" listener checks this so
// that internal focus restoration never re-triggers a dropdown reopen.
let restoringFocus = false;

function api(path) {
  return fetch(withWorktree(path)).then((response) => {
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  });
}

// Every data fetch carries the selected worktree so the server serves that
// checkout's branch memory. The default selection sends no param (the server
// uses its own launch checkout); /api/worktrees is the enumeration itself and
// is never scoped.
function withWorktree(path) {
  if (!state.worktree || state.worktree === state.worktreeDefault) return path;
  if (path.startsWith("/api/worktrees")) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}worktree=${encodeURIComponent(state.worktree)}`;
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
  await loadWorktrees();
  [state.runtime, state.facets] = await Promise.all([api("/api/runtime"), api("/api/facets")]);
  seedDates();
  await loadView();
  installDelegatedEvents();
  render();
}

// Enumerate on-device worktrees once at boot; the dropdown defaults to the
// launch checkout (main in the normal case). Failures are non-fatal - Trace
// just runs single-checkout, as it always has.
async function loadWorktrees() {
  try {
    const data = await api("/api/worktrees");
    state.worktrees = data.worktrees || [];
    state.worktreeDefault = data.default || "";
    const preferred = state.worktrees.find((w) => w.is_default) || state.worktrees[0];
    state.worktree = preferred ? preferred.id : "";
  } catch {
    state.worktrees = [];
    state.worktree = "";
  }
}

// Minimum on-screen time for the worktree-switch loader, so a warm-cache switch
// (tens of ms) doesn't flash the animation and vanish - it should read as an
// intentional journey between stops.
const WORKTREE_LOADER_MIN_MS = 650;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Advance the loader to a station imperatively (attribute flip only, no full
// re-render) so the CSS transition slides the train and lights the next stop
// smoothly - a render() here would recreate the element and reset the motion.
function setWorktreeStage(n) {
  state.worktreeStage = n;
  const loader = document.querySelector(".worktree-loader");
  if (loader) loader.dataset.stage = String(n);
}

// Switching worktrees swaps the entire data source: clear the current
// selection and graph, then reload runtime/facets/view against the new
// checkout's branch memory. The subway loader shows for the whole trip.
async function switchWorktree(id) {
  if (id === state.worktree) return;
  const target = state.worktrees.find((w) => w.id === id);
  state.worktree = id;
  state.worktreeToLabel = target ? target.label : "";
  state.selected = null;
  state.selectedId = null;
  state.graph = null;
  state.query = "";
  state.results = [];
  state.matchEntries = new Set();
  state.searchOpen = false;
  // Show the loader BEFORE the awaits - switchWorktree otherwise renders only at
  // the end, leaving the old view frozen through the whole switch.
  state.worktreeLoading = true;
  state.worktreeStage = 0;
  const startedAt = Date.now();
  const token = ++state.loadSeq;
  render();
  const [runtime, facets] = await Promise.all([api("/api/runtime"), api("/api/facets")]);
  if (token !== state.loadSeq) return;
  state.runtime = runtime;
  state.facets = facets;
  seedDates();
  setWorktreeStage(1);
  await loadView();
  if (token !== state.loadSeq) return;
  setWorktreeStage(2);
  await sleep(Math.max(0, WORKTREE_LOADER_MIN_MS - (Date.now() - startedAt)));
  if (token !== state.loadSeq) return;
  state.worktreeLoading = false;
  render();
}

function seedDates() {
  const bounds = state.facets?.runtime?.date_bounds || [];
  state.dateFrom = bounds[0] || "";
  state.dateTo = bounds[1] || "";
}

async function loadView() {
  if (state.query.trim()) await refreshSearch();
  if (state.view === "graph" || state.view === "trail") await loadGraph();
}

// Trail is a git-graph timeline: intra-branch lineage gives the branch lanes,
// and relationship edges (supersedes/evolves/related) route through dedicated
// dotted lanes left of main. Fixed edge set - not the graph view's chips.
const TRAIL_EDGE_TYPES = "branch,supersedes,evolves,related";

// Search over the current view: server-side ranking (sections and files
// included) produces the ranked dropdown plus the entry match set that the
// Trail and Graph highlight in place. Typing never selects or navigates.
const SEARCH_LIMIT = 50;

async function refreshSearch(token = state.loadSeq) {
  if (!state.query.trim()) {
    state.results = [];
    state.matchEntries = new Set();
    state.searchOpen = false;
    return true;
  }
  const params = qs({
    q: state.query,
    limit: SEARCH_LIMIT,
    granularity: state.granularity,
    agent: state.agent,
    user: state.user,
    topic: state.topic,
    date_from: state.dateFrom,
    date_to: state.dateTo,
  });
  const page = await api(`/api/search?${params}`);
  if (token !== state.loadSeq) return false;
  state.results = page.results;
  state.matchEntries = new Set(page.results.map((item) => item.entry_id).filter(Boolean));
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
      <div class="shell ${state.leftCollapsed ? "left-collapsed" : ""} ${state.rightCollapsed ? "right-collapsed" : ""}">
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
  applyTrailScroll();
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
  // This focus() call is re-render bookkeeping (preserving caret continuity
  // through a full DOM rebuild), not a real user refocus - it must not trip
  // the search box's "reopen the dropdown on refocus" listener, or a
  // deliberate close (Enter/Escape) would reopen itself on its own re-render.
  restoringFocus = true;
  el.focus();
  restoringFocus = false;
  if (typeof focusState.start === "number" && typeof el.setSelectionRange === "function") {
    try {
      el.setSelectionRange(focusState.start, focusState.end);
    } catch {
      // Same input types as above.
    }
  }
}

function topbar() {
  // Trail is the primary surface (chronological evidence), Graph the
  // secondary exploration surface - the next-generation blueprint's ordering.
  const tabs = [["trail", "Trail"], ["graph", "Graph"]]
    .map(([key, label]) => `<button type="button" class="tab ${state.view === key ? "active" : ""}" data-view="${key}">${label}</button>`)
    .join("");
  return `
    <header class="topbar">
      <button type="button" class="icon-button" data-toggle-left title="${state.leftCollapsed ? "Show sidebar" : "Hide sidebar"}">☰</button>
      <div class="brand"><span class="brand-mark"></span><span>Memory Trace</span></div>
      <div class="runtime-chip"><span class="runtime-dot"></span><span>${esc(state.runtime?.label || "runtime")}</span><span>${state.runtime?.entry_count || 0} entries</span></div>
      ${worktreePicker()}
      <div class="searchbox-wrap">
        <div class="searchbox"><span>⌕</span><input id="query" value="${escAttr(state.query)}" placeholder="Search memory, tags, files, decisions" spellcheck="false"></div>
        ${searchDropdown()}
      </div>
      <div class="segmented">${tabs}</div>
      <button type="button" class="icon-button" data-theme title="Theme">${state.theme === "dark" ? "◐" : "◑"}</button>
      <div class="palette">${["indigo", "teal", "amber", "ruby", "violet"].map((name) => `<button type="button" class="${state.accent === name ? "active" : ""}" data-accent="${name}" title="${name}" style="background:${palettePreview(name)}"></button>`).join("")}</div>
      <button type="button" class="icon-button" data-toggle-right title="${state.rightCollapsed ? "Show reader" : "Hide reader"}">▤</button>
    </header>`;
}

// Worktree switcher: shows each on-device worktree (branch) and re-points the
// whole Trail at the selected checkout's memory. Hidden when there's only the
// one launch checkout - nothing to switch between.
function worktreePicker() {
  if (state.worktrees.length < 2) return "";
  return `
    <label class="worktree-picker" title="Show the Trail for another on-device worktree">
      <span class="worktree-icon" aria-hidden="true">⑃</span>
      <select id="worktree-select" data-worktree-select>
        ${state.worktrees
          .map((w) => `<option value="${escAttr(w.id)}" ${w.id === state.worktree ? "selected" : ""}>${esc(w.label)}${w.is_primary ? "" : " ·wt"}</option>`)
          .join("")}
      </select>
    </label>`;
}

// Ranked results dropdown under the search box: the relevance-ordered jump
// list (the roadmap's "ranked results drawer" shape). Clicking a result
// selects the entry in the current view; the match markers stay in place.
function searchDropdown() {
  if (!state.searchOpen || !state.query.trim()) return "";
  const top = state.results.slice(0, 10);
  if (!top.length) {
    return `<div class="search-dropdown"><div class="search-empty">No matches for "${esc(state.query.trim())}" with the current filters.</div></div>`;
  }
  const more = state.matchEntries.size - top.length;
  return `
    <div class="search-dropdown">
      ${top.map((item) => {
        const matched = (item.matched_sections || []).length;
        return `<button type="button" class="search-result" data-search-jump data-chunk="${escAttr(item.chunk_id)}" title="${escAttr(item.title)}"><span class="search-result-title">${esc(stripTitleStamp(item.title))}</span><span class="count">${item.date} ${item.time || ""}${matched ? ` · ${matched} matched section${matched === 1 ? "" : "s"}` : ""}</span></button>`;
      }).join("")}
      ${more > 0 ? `<div class="search-empty">+${more} more highlighted in the ${state.view === "graph" ? "graph" : "trail"}</div>` : ""}
    </div>`;
}

// Shared viewbar fragment: match count + next/previous cycling + clear,
// shown in whichever view is open while a query is active.
function searchStatus() {
  if (!state.query.trim()) return "";
  const count = state.matchEntries.size;
  const capped = state.results.length >= SEARCH_LIMIT;
  return `
      <span class="meta search-hits">⌕ <strong>${count}${capped ? "+" : ""}</strong> match${count === 1 && !capped ? "" : "es"}</span>
      <button type="button" class="chip" data-match-prev title="Previous match (Shift+Enter)">↑</button>
      <button type="button" class="chip" data-match-next title="Next match (Enter)">↓</button>
      <button type="button" class="chip" data-search-clear title="Clear search">×</button>`;
}

function leftPane() {
  const facets = state.facets || { agents: {}, users: {}, topics: {}, runtime: {} };
  return `
    <div class="metric-grid">
      <div class="metric"><strong>${facets.runtime.entry_count || 0}</strong><span>entries</span></div>
      <div class="metric"><strong>${facets.runtime.chunk_count || 0}</strong><span>chunks</span></div>
    </div>
    ${sidebarSection("views", "Saved Views", `
      ${savedButton("Recent work", "", "trail")}
      ${savedButton("Design decisions", "design decision", "trail")}
      ${savedButton("Related graph", "", "graph")}`)}
    ${sidebarSection("filters", "Filters", `
      ${facetSelect("agent-filter", "agent", facets.agents, state.agent, "All agents")}
      ${facetSelect("user-filter", "user", facets.users, state.user, "All users")}
      <label class="field-label" for="date-from">From</label><input type="date" id="date-from" value="${escAttr(state.dateFrom)}">
      <label class="field-label" for="date-to">To</label><input type="date" id="date-to" value="${escAttr(state.dateTo)}">
      <label class="field-label">Granularity</label>
      <div class="segmented">${["entry", "section", "all"].map((item) => `<button type="button" class="tab ${state.granularity === item ? "active" : ""}" data-granularity="${item}">${item}</button>`).join("")}</div>
      <button type="button" class="chip filters-reset" data-reset>Reset filters</button>`)}
    ${sidebarSection("topics", "Topics", `<div class="chip-list">${topicChips(facets)}</div>`)}`;
}

// Collapsible sidebar sections (dropdown-style disclosure): open state
// persists so the sidebar keeps the user's chosen density across sessions.
function sidebarSection(key, title, body) {
  const open = state.sectionOpen[key] !== false;
  return `
    <section class="side-section">
      <button type="button" class="side-section-head" data-section="${key}" aria-expanded="${open}"><span>${title}</span><span class="count">${open ? "▾" : "▸"}</span></button>
      ${open ? `<div class="side-section-body">${body}</div>` : ""}
    </section>`;
}

// Facet dropdowns: a select with counts costs one row of screen real estate
// regardless of how many values the facet has.
function facetSelect(id, kind, values, active, allLabel) {
  const entries = Object.entries(values || {});
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return `
    <label class="field-label" for="${id}">${kind === "agent" ? "Agent" : "User"}</label>
    <select id="${id}" data-filter-select="${kind}">
      <option value="">${esc(allLabel)} (${total})</option>
      ${entries.map(([key, count]) => `<option value="${escAttr(key)}" ${active === key ? "selected" : ""}>${esc(key)} (${count})</option>`).join("")}
    </select>`;
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

function savedButton(label, query, view) {
  return `<button type="button" class="row-button" data-saved-query="${escAttr(query)}" data-saved-view="${escAttr(view)}"><span class="swatch"></span><span>${label}</span><span class="count">preset</span></button>`;
}

function centerPane() {
  const densityClass = `density-${state.density}`;
  if (state.worktreeLoading) return `<section class="${densityClass}">${worktreeLoader()}</section>`;
  if (state.view === "graph") return `<section class="${densityClass}">${graphView()}</section>`;
  return `<section class="${densityClass}">${trailView()}</section>`;
}

// Worktree-switch loader as a subway line: the Trail is a train line, so a
// switch is a short journey between stops. Three stations = the three real load
// milestones (depart -> reading branch memory -> arrive); the train car slides
// station to station via a CSS transition as switchWorktree flips data-stage,
// the travelled track lights up behind it, and a soft halo pulses so it reads as
// alive between stops. "Train of thought", literally. Echoes the Trail's own
// vocabulary - a vertical line, circular station dots, the accent lane colour.
function worktreeLoader() {
  const stations = [
    "Leaving the platform",
    "Reading branch memory",
    `Arriving${state.worktreeToLabel ? ` at ${esc(state.worktreeToLabel)}` : ""}`,
  ];
  const cx = 34;
  const ys = [30, 120, 210];
  const track = `<line class="wt-track" x1="${cx}" y1="${ys[0]}" x2="${cx}" y2="${ys[2]}"></line>`;
  const litTrack = `<line class="wt-track-lit" x1="${cx}" y1="${ys[0]}" x2="${cx}" y2="${ys[2]}" pathLength="1"></line>`;
  const dots = ys.map((y, i) => `<circle class="wt-station" data-i="${i}" cx="${cx}" cy="${y}" r="5.5"></circle>`).join("");
  const labels = ys
    .map((y, i) => `<text class="wt-label" data-i="${i}" x="${cx + 18}" y="${y + 4}">${stations[i]}</text>`)
    .join("");
  // Train car rides at y=0 in its own group; the group is translated to the
  // active station by CSS, so the transition animates the slide.
  const train = `<g class="wt-train"><circle class="wt-train-halo" cx="${cx}" cy="0" r="11"></circle><rect x="${cx - 9}" y="-6" width="18" height="12" rx="4"></rect></g>`;
  return `
    <div class="worktree-loader" data-stage="${state.worktreeStage}" role="status" aria-live="polite">
      <svg class="wt-map" viewBox="0 0 240 240" width="240" height="240" aria-hidden="true">
        ${track}${litTrack}${dots}${labels}${train}
      </svg>
      <div class="wt-caption">
        <div class="wt-title">Switching worktree${state.worktreeToLabel ? ` &middot; ${esc(state.worktreeToLabel)}` : ""}</div>
        <div class="wt-sub">following the train of thought&hellip;</div>
      </div>
    </div>`;
}

function graphView() {
  const graph = state.graph;
  if (!graph) return `<div class="empty">Graph loading</div>`;
  const positions = graphPositions(graph.nodes, graph.edges);
  const related = graphRelatedIds(graph, state.graphHover);
  // Search as a function over the graph: matching nodes keep full presence
  // (and earn a label), everything else dims - same grammar as hover focus.
  const searching = Boolean(state.query.trim());
  const entryOf = new Map(graph.nodes.map((node) => [node.id, node.entry_id || ""]));
  const isMatch = (id) => state.matchEntries.has(entryOf.get(id) || "");
  return `
    <div class="viewbar">
      <span class="meta">${graph.nodes.length} nodes · ${graph.edges.length} edges</span>
      ${filterChips()}
      ${searchStatus()}
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
        const dim = (state.graphHover && !highlight) || (searching && !isMatch(edge.source) && !isMatch(edge.target));
        // supersedes: directed + dashed status edge, never conflated with related.
        const width = edge.type === "supersedes" ? 2.2 : edge.type === "branch" ? 1.6 : edge.type === "related" ? 2 : 1;
        const dash = edge.type === "supersedes" ? ' stroke-dasharray="6 4"' : "";
        const marker = edge.type === "supersedes" ? ' marker-end="url(#arrow-supersedes)"' : "";
        return `<line class="graph-edge graph-edge-${edge.type} ${highlight ? "graph-related" : ""} ${dim ? "graph-dim" : ""}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${edgeColor(edge.type)}" stroke-width="${width}"${dash}${marker}></line>`;
      }).join("")}
      ${(() => {
        // Progressive disclosure: labels are shown for the hovered node, its
        // neighbourhood, the selection, and the top-connected nodes only -
        // 260 always-on labels are unreadable. Tooltips carry the rest.
        const sizeOf = (node) => (state.graphSizeMode === "importance" ? Number(node.importance_score || 0) : Number(node.connectivity || 0));
        const ranked = graph.nodes.map(sizeOf).sort((a, b) => b - a);
        const labelCut = Math.max(ranked[Math.min(14, ranked.length - 1)] ?? 0, 0.001);
        return graph.nodes.map((node) => {
          const p = positions[node.id];
          const selected = node.chunk_id === state.selectedId || node.id === state.selected?.entry_id;
          const highlight = state.graphHover && (node.id === state.graphHover || related.has(node.id));
          const match = searching && isMatch(node.id);
          const dim = (state.graphHover && !highlight) || (searching && !match && !selected);
          const sizeVal = sizeOf(node);
          const radius = selected ? 18 : Math.min(16, 7 + sizeVal * 2.2);
          const showLabel = selected || highlight || match || sizeVal >= labelCut;
          const label = showLabel ? `<text class="graph-label" data-graph-label x="${p.x}" y="${p.y - 15}" text-anchor="middle">${esc(graphTitle(node.title))}</text>` : "";
          // Decision-diagram badge: a small diamond at the node's upper-right
          // when the entry carries a Class-2 sidecar. Click opens the popover
          // preview (handled before node selection).
          const bx = p.x + radius * 0.78, by = p.y - radius * 0.78;
          const diagramBadge = node.has_diagram
            ? `<path class="graph-diagram-badge" data-diagram-entry="${escAttr(node.entry_id || "")}" d="M ${bx} ${by - 4.5} L ${bx + 4.5} ${by} L ${bx} ${by + 4.5} L ${bx - 4.5} ${by} Z"><title>Decision diagram — click to preview</title></path>`
            : "";
          return `<g class="graph-node ${highlight ? "graph-related" : ""} ${match ? "search-match" : ""} ${dim ? "graph-dim" : ""}" data-node-id="${escAttr(node.id)}" data-chunk="${escAttr(node.chunk_id)}"><circle class="graph-hit" cx="${p.x}" cy="${p.y}" r="${Math.max(radius + 10, 20)}"></circle><circle cx="${p.x}" cy="${p.y}" r="${radius}" fill="${agentColor(node.agent)}" stroke="${selected ? "var(--accent)" : "var(--bg)"}" stroke-width="3"></circle>${label}${diagramBadge}<title>${esc(node.title)}</title></g>`;
        }).join("");
      })()}
      </g>
      </svg>
    </div>`;
}

// --- Trail: interactive git-graph timeline ----------------------------------
// Newest entry at the top, one straight lane per branch (lowest free lane,
// freed when the branch's visible life ends - interval coloring, the
// "straight branches" scheme git clients use). Lifecycle arcs bow through the
// dotted relationship lanes left of main: related | evolves | replaces.
// Day separators share the fixed row height so SVG y stays index * ROW.
const TRAIL_ROW = 30;
const TRAIL_LANE_W = 14;
const TRAIL_WINDOW_STEP = 60;
// Relationship lanes sit left of main, always dotted: replaces | evolves |
// related. Under the two-rule model related routes are pure branch hops -
// the rarest, densest signal - so they take the innermost lane next to main
// and never cross the other two on their way out. Branch lanes to the right
// are the solid spawned git branches.
const TRAIL_REL_LANES = ["supersedes", "evolves", "related"];
const TRAIL_REL_LANE_W = 12;
// Corner radius for every lane change (gitgraph "rounded" style): straight
// runs, small elbows at the turns. Must stay below half the minimum row gap
// (TRAIL_ROW / 2) and below one lane width so corners never overlap.
const TRAIL_CORNER = 7;
const TRAIL_REL_ZONE = TRAIL_REL_LANES.length * TRAIL_REL_LANE_W + 12;
// All relationship routes share the clearest dash cadence; color alone
// separates the types (user decision - replaces' dash won the readability
// comparison). related routes draw only for the selected entry: as ambient
// traffic they drowned the lifecycle signal.
const TRAIL_DASH = { supersedes: "6 4", evolves: "6 4", related: "6 4" };
const TRAIL_VERB = { supersedes: "replaces", evolves: "evolves", related: "relates to" };
// Each of the first four lanes owns a "pack" of three distinct colors rather
// than one flat color: lanes are already collision-free for anything parallel
// or adjacent, but branches that daisy-chain through the same lane one after
// another still need to read as distinct entries, not a single continuous
// branch, so those lanes cycle their pack's three colors across successive
// branches. Four packs (12 unique bright colors) cover the common case - most
// work rarely runs more than four branches in parallel. Colors are the
// brighter, higher-saturation set (user preference); each pack pairs three
// well-separated hues so the cycle reads clearly, and every member stays
// legible on both the light and dark theme background. Lane 0 leads with
// main's classic indigo. Deeper overflow lanes are handled at assignment time
// (see trailModel): they pin to their pack's middle color instead of cycling.
const trailLaneColorFamilies = [
  ["#6f7cff", "#3fa66a", "#d9941a"],
  ["#d94b63", "#22b8cf", "#7cb342"],
  ["#8f63e8", "#e8590c", "#18a999"],
  ["#db2777", "#3b82f6", "#16a34a"],
];

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
  // Fork/merge targets on main. Ground truth first: the API's graph.branches
  // carries each branch's real merge commit and fork point (merge-base),
  // recovered from the Memory-Entry trailers session merge-branch stamps on
  // merge commits. A commit is a TIME on the trunk, not an entry row, so its
  // anchor is a fractional row interpolated between the two entries whose
  // timestamps bracket it - back-to-back merges spread out by commit time
  // instead of piling onto one entry. Pre-trailer-era branches (no events at
  // all) keep the old positional heuristic, flagged estimated for the hover.
  const mainRowList = [];
  items.forEach((item, index) => {
    if (item.kind === "node" && item.node.branch === "main") mainRowList.push(index);
  });
  const nodeRows = [];
  items.forEach((item, index) => {
    if (item.kind === "node") nodeRows.push({ row: index, stamp: trailStamp(item.node) });
  });
  const interpRow = (iso) => {
    const t = Date.parse(iso || "");
    if (!Number.isFinite(t) || !nodeRows.length) return undefined;
    if (t >= nodeRows[0].stamp) return nodeRows[0].row;
    if (t <= nodeRows[nodeRows.length - 1].stamp) return nodeRows[nodeRows.length - 1].row;
    for (let i = 0; i < nodeRows.length - 1; i += 1) {
      const upper = nodeRows[i];
      const lower = nodeRows[i + 1];
      if (t <= upper.stamp && t >= lower.stamp) {
        const span = upper.stamp - lower.stamp;
        const frac = span > 0 ? (upper.stamp - t) / span : 0.5;
        return upper.row + frac * (lower.row - upper.row);
      }
    }
    return nodeRows[nodeRows.length - 1].row;
  };
  // Trunk merge dots: every merge event touching a visible entry, placed at
  // its commit-time row. Entry heading times can run ahead of the wall clock
  // that stamped the commit, so each dot clamps to sit at least half a row
  // ABOVE (newer than) the newest entry it merged - a merge drawn below its
  // own content would read upside-down. Clicking a dot opens the merged work.
  const mergeEvents = (graph.merges || []).flatMap((event) => {
    const entryRows = (event.entry_ids || []).map((id) => rowOf.get(id)).filter((row) => row !== undefined);
    if (!entryRows.length) return [];
    const newestRow = Math.min(...entryRows);
    let row = interpRow(event.date);
    if (row === undefined) return [];
    row = Math.min(row, newestRow - 0.5);
    return [{ row, sha: event.sha, short: event.short, subject: event.subject, count: entryRows.length, chunkId: items[newestRow].node.chunk_id }];
  });
  const mergeRowBySha = new Map(mergeEvents.map((event) => [event.sha, event.row]));
  const branchMeta = graph.branches || {};
  const linkRows = new Map();
  // Lane occupancy runs fork-to-merge, not just across a branch's own entry
  // rows: branches whose entries occupy disjoint row ranges but converge on
  // the same merge point still run in parallel and must not share a lane.
  const occupancy = new Map();
  spans.forEach((span, branch) => {
    if (branch === "" || branch === "main") return;
    const heuristicFork = mainRowList.find((row) => row > span.last);
    const heuristicMerge = [...mainRowList].reverse().find((row) => row < span.first);
    const info = branchMeta[branch];
    let forkRow;
    let mergeRow;
    let estimated = true;
    let mergeLabel = null;
    let forkLabel = null;
    if (info && !info.estimated) {
      estimated = false;
      if (info.merge) {
        mergeRow = mergeRowBySha.has(info.merge.sha) ? mergeRowBySha.get(info.merge.sha) : interpRow(info.merge.date);
        if (mergeRow !== undefined) mergeRow = Math.min(mergeRow, span.first - 0.5);
        mergeLabel = `${info.merge.short} ${info.merge.subject}`;
      }
      // else: the newest entry is not merged yet - the branch is open and
      // dangles; its earlier merges still show as trunk dots.
      if (info.fork) {
        forkRow = interpRow(info.fork.date);
        if (forkRow !== undefined) forkRow = Math.max(forkRow, span.last + 0.5);
        forkLabel = info.fork.short;
      } else {
        forkRow = heuristicFork;
      }
    } else {
      forkRow = heuristicFork;
      mergeRow = heuristicMerge;
    }
    linkRows.set(branch, { forkRow, mergeRow, estimated, mergeLabel, forkLabel });
    occupancy.set(branch, {
      first: mergeRow !== undefined ? Math.min(span.first, Math.floor(mergeRow)) : span.first,
      last: forkRow !== undefined ? Math.max(span.last, Math.ceil(forkRow)) : span.last,
    });
  });
  if (spans.has("main")) occupancy.set("main", { ...spans.get("main") });
  // main is pinned to the leftmost lane (git-client convention); the rest
  // allocate oldest-first, so the inner lanes hold the older, tighter branches
  // and newer branches stack outward. The Trail is newest-first (top = index
  // 0), so "older" means a larger row index: a branch whose newest entry sits
  // lower down sorts first and claims the innermost free lane. Ties break
  // toward the more compact branch, then the older start. Entries with no
  // recorded branch don't allocate a lane - their dots sit on lane 0.
  const branches = [...occupancy.keys()].sort((a, b) => {
    if (a === "main") return -1;
    if (b === "main") return 1;
    const entryA = spans.get(a);
    const entryB = spans.get(b);
    return (
      (entryB.first - entryA.first)
      || (entryA.last - entryA.first) - (entryB.last - entryB.first)
      || (entryB.last - entryA.last)
    );
  });
  const laneOf = new Map();
  const colorOf = new Map();
  const laneIntervals = [];
  const laneBranchOrder = [];
  branches.forEach((branch) => {
    const span = occupancy.get(branch);
    // Touching at a single shared junction row (one branch merges exactly
    // where the next forks) is daisy-chaining, not parallelism - those
    // branches share a lane, like sequential branches in a git graph. The
    // trunk column (lane 0) is main's alone: a branch that merely touches
    // main's visible span must not render as a continuation of main.
    let lane = laneIntervals.findIndex((intervals, index) => (branch === "main" || index > 0) && intervals.every((occupied) => span.last <= occupied.first || span.first >= occupied.last));
    if (lane === -1) {
      lane = laneIntervals.length;
      laneIntervals.push([]);
      laneBranchOrder.push([]);
    }
    laneIntervals[lane].push(span);
    laneBranchOrder[lane].push(branch);
    laneOf.set(branch, lane);
  });
  // Color keys off lane + position-within-lane, not arrival order: lanes are
  // already guaranteed collision-free for anything parallel or adjacent
  // (laneIntervals never lets overlapping spans share one), so a lane's hue
  // family is never confused with a neighbor's. Within a lane, branches cycle
  // through their family in the order they actually appear top-to-bottom
  // (chronological, not shortest-lived-first), so daisy-chained branches that
  // reuse a freed lane read as distinct back-to-back entries instead of one
  // continuous line.
  laneBranchOrder.forEach((laneBranches, lane) => {
    const family = trailLaneColorFamilies[lane % trailLaneColorFamilies.length];
    laneBranches
      .slice()
      .sort((a, b) => occupancy.get(a).first - occupancy.get(b).first)
      // The first four lanes cycle their pack's three colors across their
      // daisy-chained branches. Deeper lanes (index 4+) are rare and pin to the
      // pack's middle color rather than cycling, so overflow depth stays calm
      // and never masquerades as a lively primary lane.
      .forEach((branch, i) => colorOf.set(branch, lane < 4 ? family[i % family.length] : family[1]));
  });

  const lifecycle = (graph.edges || []).filter(
    (edge) => TRAIL_REL_LANES.includes(edge.type) && rowOf.has(edge.source) && rowOf.has(edge.target)
  );
  return { items, total, rowOf, spans, laneOf, colorOf, laneCount: laneIntervals.length, lifecycle, linkRows, mergeEvents };
}

function trailView() {
  const graph = state.graph;
  if (!graph) return `<div class="empty">Trail loading</div>`;
  const model = trailModel(graph);
  const { items, total, rowOf, spans, laneOf, colorOf, lifecycle, linkRows } = model;
  if (!items.length) return `<div class="empty">No entries with lineage data yet.</div>`;
  const laneX = (branch) => TRAIL_REL_ZONE + (laneOf.get(branch) || 0) * TRAIL_LANE_W + 7;
  const laneCenterX = (lane) => TRAIL_REL_ZONE + lane * TRAIL_LANE_W + 7;
  const relLaneX = (type) => 8 + TRAIL_REL_LANES.indexOf(type) * TRAIL_REL_LANE_W;
  const rowY = (index) => index * TRAIL_ROW + TRAIL_ROW / 2;
  // Rail width reacts to both zones, so the text column shifts right as more
  // branches run in parallel.
  const railWidth = TRAIL_REL_ZONE + model.laneCount * TRAIL_LANE_W + 12;

  // Per-row text indent follows the git-graph silhouette: each row's time+title
  // start just right of the rightmost lane actually alive at that row, so the
  // text edge hugs the lanes (wide where many branches run in parallel, sliding
  // left toward main where only the trunk remains) instead of sitting at a
  // fixed column past the widest point. Envelope uses fork-to-merge occupancy -
  // the same interval that governs lane allocation - so text never crosses a
  // connector or a parallel lane, only clears whatever is present on its row.
  const TRAIL_TEXT_CLEAR = 18; // dot radius + breathing gap past the last lane
  const rowIndent = (lane) => Math.round(laneCenterX(lane) + TRAIL_TEXT_CLEAR);
  const occupancy = new Map();
  laneOf.forEach((_lane, branch) => {
    const span = spans.get(branch);
    if (!span) return;
    if (branch === "main") {
      occupancy.set(branch, { first: span.first, last: span.last });
      return;
    }
    const link = linkRows.get(branch) || {};
    // Merge/fork anchors are fractional (commit-time interpolated); round
    // outward so the text envelope still clears the whole connector.
    occupancy.set(branch, {
      first: link.mergeRow !== undefined ? Math.min(span.first, Math.floor(link.mergeRow)) : span.first,
      last: link.forkRow !== undefined ? Math.max(span.last, Math.ceil(link.forkRow)) : span.last,
    });
  });
  const envelopeLane = new Array(items.length).fill(0);
  laneOf.forEach((lane, branch) => {
    const occ = occupancy.get(branch);
    if (!occ) return;
    for (let i = occ.first; i <= occ.last && i < envelopeLane.length; i += 1) {
      if (lane > envelopeLane[i]) envelopeLane[i] = lane;
    }
  });
  const height = items.length * TRAIL_ROW;
  const selectedEntry = state.selected?.entry_id || "";

  // Lane continuity: connect consecutive visible rows of the same branch.
  // Entries with no recorded branch get a dot but no line - continuity that
  // was never recorded is not drawn.
  const branchRows = new Map();
  items.forEach((item, index) => {
    if (item.kind !== "node") return;
    const branch = item.node.branch || "";
    if (!branchRows.has(branch)) branchRows.set(branch, []);
    branchRows.get(branch).push(index);
  });
  // No-branch legacy entries get dots but never lines - continuity that was
  // never recorded is not drawn.
  const laneSegments = [...branchRows.entries()].filter(([branch]) => branch !== "").flatMap(([branch, rows]) =>
    rows.slice(1).map((row, i) => `<line x1="${laneX(branch)}" y1="${rowY(rows[i])}" x2="${laneX(branch)}" y2="${rowY(row)}" stroke="${colorOf.get(branch)}" stroke-width="2" stroke-opacity="0.55"></line>`)
  );

  // Phantom trunk: main is a single continuous ref, but a stale or
  // branch-heavy view can carry no main ENTRY in its top region - so the
  // branches that merged INTO main up there have no visible trunk to land on
  // (they read as merging into nothing). Where main has real nodes but its
  // newest sits below the top of the view, extend a DASHED, dimmed spine from
  // the top edge down to that newest main node. Dashed + faint deliberately
  // reads as "main continues here, no entries logged at this height" - never
  // confusable with the solid real trunk, and never asserting a live current
  // main. Guarded to main-has-nodes, so a filter that hides main (its rows go
  // empty) draws no phantom rather than a spine through unrelated results.
  const mainRows = branchRows.get("main") || [];
  const phantomTrunk =
    mainRows.length && mainRows[0] > 0
      ? `<line x1="${laneX("main")}" y1="0" x2="${laneX("main")}" y2="${rowY(mainRows[0])}" stroke="${colorOf.get("main") || trailLaneColorFamilies[0][0]}" stroke-width="2" stroke-opacity="0.3" stroke-dasharray="2 5" stroke-linecap="round"></line>`
      : "";

  // Gitgraph forking: fork/merge rows come from the model - the same rows
  // that drive lane occupancy, so connectors and lane allocation always
  // agree. Anchors are commit-accurate where a Memory-Entry trailer exists
  // (fractional, commit-time interpolated) and positional estimates
  // otherwise; the hover says which. Connectors are straight runs with
  // small-radius elbows (the gitgraph "rounded" style): the bend sits right
  // at the junction row, the rest travels vertically in the branch's own
  // lane. An unmerged branch deliberately dangles - no merge is fabricated.
  const connectors = [...linkRows.entries()].flatMap(([branch, { forkRow, mergeRow, mergeLabel, forkLabel }]) => {
    const rows = branchRows.get(branch) || [];
    if (!rows.length) return [];
    const newest = rows[0];
    const oldest = rows[rows.length - 1];
    const bx = laneX(branch);
    const mx = laneX("main");
    const r = TRAIL_CORNER;
    const out = [];
    if (forkRow !== undefined) {
      const yf = rowY(forkRow);
      const yb = rowY(oldest);
      const forkTip = forkLabel ? `forked after ${forkLabel}` : "fork point estimated";
      out.push(`<path class="trail-link" d="M ${mx} ${yf} L ${bx - r} ${yf} Q ${bx} ${yf} ${bx} ${yf - r} L ${bx} ${yb}" fill="none" stroke="${colorOf.get(branch)}" stroke-width="2" stroke-opacity="0.55"><title>${esc(`${branch} · ${forkTip}`)}</title></path>`);
    }
    if (mergeRow !== undefined) {
      const yb = rowY(newest);
      const ym = rowY(mergeRow);
      const mergeTip = mergeLabel ? `merged by ${mergeLabel}` : "merge point estimated";
      out.push(`<path class="trail-link" d="M ${bx} ${yb} L ${bx} ${ym + r} Q ${bx} ${ym} ${bx - r} ${ym} L ${mx} ${ym}" fill="none" stroke="${colorOf.get(branch)}" stroke-width="2" stroke-opacity="0.55"><title>${esc(`${branch} · ${mergeTip}`)}</title></path>`);
    }
    return out;
  });

  // Trunk merge dots: one ring per real merge commit at its commit-time row
  // on the main lane - repeated merges of a long-lived branch stay visible
  // even though the branch renders as a single lane. Clicking selects the
  // merged work (the reader then shows the commit and its sibling entries).
  const mergeDotFill = colorOf.get("main") || trailLaneColorFamilies[0][0];
  const mergeDots = (model.mergeEvents || []).map((event) =>
    `<circle class="trail-merge-dot" cx="${laneX("main")}" cy="${rowY(event.row)}" r="3.5" fill="var(--bg)" stroke="${mergeDotFill}" stroke-width="2" data-chunk="${escAttr(event.chunkId)}"><title>${esc(`${event.short} ${event.subject} · ${event.count} ${event.count === 1 ? "entry" : "entries"}`)}</title></circle>`
  );

  // Relationship edges route through their type's dotted lane with the same
  // small-radius elbows: out from the source dot, along the lane, back in to
  // the target dot. Lifecycle routes rest in their pastel variants; an
  // active (unmuted) selection saturates the routes it touches and reveals
  // its related routes.
  const focusActive = Boolean(selectedEntry) && !state.selectionMuted;
  // Two-rule related model (user-finalised): routes are reserved for
  // branch-hopping relationships; ALL same-branch related context renders as
  // row brackets instead. Full bracket = outbound (entries the selection
  // cites); pastel bracket = inbound mentions + bounded second-order (one
  // extra hop, same branch as the selection only). This also retires the
  // old main-lane merge/N-gap special cases.
  const chainPrimary = new Set();
  const chainSecondary = new Set();
  if (focusActive && rowOf.has(selectedEntry)) {
    const selectedBranch = items[rowOf.get(selectedEntry)].node.branch || "";
    const branchOf = (id) => items[rowOf.get(id)].node.branch || "";
    const related = lifecycle.filter((edge) => edge.type === "related");
    const firstOrder = new Set();
    related.forEach((edge) => {
      if (edge.source === selectedEntry) firstOrder.add(edge.target);
      if (edge.target === selectedEntry) firstOrder.add(edge.source);
    });
    related.forEach((edge) => {
      if (edge.source === selectedEntry && branchOf(edge.target) === selectedBranch) chainPrimary.add(edge.target);
      else if (edge.target === selectedEntry && branchOf(edge.source) === selectedBranch) chainSecondary.add(edge.source);
    });
    related.forEach((edge) => {
      if (firstOrder.has(edge.source) && edge.target !== selectedEntry && !firstOrder.has(edge.target) && branchOf(edge.target) === selectedBranch) chainSecondary.add(edge.target);
      if (firstOrder.has(edge.target) && edge.source !== selectedEntry && !firstOrder.has(edge.source) && branchOf(edge.source) === selectedBranch) chainSecondary.add(edge.source);
    });
    chainPrimary.forEach((id) => chainSecondary.delete(id));
    chainSecondary.delete(selectedEntry);
  }
  // Commit packaging: entries captured by the same git commit as the
  // selection get a right-edge bracket - the left edge belongs to semantic
  // relations, the right edge to packaging.
  const commitSiblings = new Set();
  if (focusActive && state.selected?.entry_id === selectedEntry) {
    (state.selected.commit_entry_ids || []).forEach((id) => {
      if (id !== selectedEntry) commitSiblings.add(id);
    });
  }
  // Adjacent-row test: no other NODE row between the two (a day separator in
  // between still counts as adjacent).
  const adjacentRows = (rowA, rowB) => {
    const lo = Math.min(rowA, rowB);
    const hi = Math.max(rowA, rowB);
    return items.slice(lo + 1, hi).every((item) => item.kind !== "node");
  };
  // Edge-type precedence: when one entry pair carries more than one lifecycle
  // edge, render only the highest-information one - replaces > evolves >
  // related - so a pair that both evolves and relates shows the evolves (it
  // tells you the most), never a weaker duplicate beside it.
  const EDGE_INFO_RANK = { supersedes: 3, evolves: 2, related: 1 };
  const pairKey = (a, b) => (a < b ? `${a}${b}` : `${b}${a}`);
  const strongestByPair = new Map();
  lifecycle.forEach((edge) => {
    const cur = strongestByPair.get(pairKey(edge.source, edge.target));
    if (!cur || EDGE_INFO_RANK[edge.type] > EDGE_INFO_RANK[cur.type]) {
      strongestByPair.set(pairKey(edge.source, edge.target), edge);
    }
  });
  const winsPair = (edge) => strongestByPair.get(pairKey(edge.source, edge.target)) === edge;
  // Daisy-chained evolves within one lane become a single continuous bracket
  // beside the dots - the grouping the chain actually is - instead of a run of
  // little out-and-back hops that add no information the proximity doesn't. An
  // evolves edge brackets when it wins its pair, its rows are adjacent, and
  // both sit in the same lane; union such edges into maximal chains.
  const sameLane = (a, b) => (items[rowOf.get(a)].node.branch || "") === (items[rowOf.get(b)].node.branch || "");
  const bracketEvolves = lifecycle.filter(
    (edge) =>
      edge.type === "evolves" &&
      winsPair(edge) &&
      adjacentRows(rowOf.get(edge.source), rowOf.get(edge.target)) &&
      sameLane(edge.source, edge.target)
  );
  const bracketedEvolves = new Set(bracketEvolves);
  const chainParent = new Map();
  const chainFind = (x) => {
    while (chainParent.get(x) !== x) {
      chainParent.set(x, chainParent.get(chainParent.get(x)));
      x = chainParent.get(x);
    }
    return x;
  };
  bracketEvolves.forEach((edge) => {
    const ra = rowOf.get(edge.source);
    const rb = rowOf.get(edge.target);
    if (!chainParent.has(ra)) chainParent.set(ra, ra);
    if (!chainParent.has(rb)) chainParent.set(rb, rb);
    chainParent.set(chainFind(ra), chainFind(rb));
  });
  const chainRows = new Map();
  [...chainParent.keys()].forEach((row) => {
    const root = chainFind(row);
    if (!chainRows.has(root)) chainRows.set(root, []);
    chainRows.get(root).push(row);
  });
  const EVOLVES_BRACKET_DX = 9;
  const EVOLVES_BRACKET_TICK = 5;
  const evolvesBrackets = [...chainRows.values()].map((rowsIn) => {
    const rowsSorted = rowsIn.slice().sort((a, b) => a - b);
    const branch = items[rowsSorted[0]].node.branch || "";
    const x = laneX(branch) - EVOLVES_BRACKET_DX;
    const top = rowY(rowsSorted[0]);
    const bot = rowY(rowsSorted[rowsSorted.length - 1]);
    const touched = focusActive && rowsSorted.some((r) => items[r].node.entry_id === selectedEntry);
    const stroke = touched ? edgeColor("evolves") : "var(--edge-evolves-soft)";
    const opacity = touched ? 0.95 : focusActive ? 0.5 : 0.9;
    const labels = rowsSorted.map((r) => trailTitle(items[r].node));
    const tip = `<title>evolves chain (${rowsSorted.length}): ${esc(labels.join(" ← "))}</title>`;
    const t = EVOLVES_BRACKET_TICK;
    const d = `M ${x + t} ${top} L ${x} ${top} L ${x} ${bot} L ${x + t} ${bot}`;
    return `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${touched ? 2.6 : 2}" stroke-linejoin="round" stroke-linecap="round" stroke-opacity="${opacity}">${tip}</path>`;
  });
  const arcs = lifecycle.flatMap((edge) => {
    const touched = focusActive && (edge.source === selectedEntry || edge.target === selectedEntry);
    // Precedence: drop any edge that isn't the strongest signal for its pair.
    if (!winsPair(edge)) return [];
    // Adjacent same-lane evolves are drawn as a chain bracket above, not here.
    if (bracketedEvolves.has(edge)) return [];
    if (edge.type === "related" && !touched) return [];
    const sourceItem = items[rowOf.get(edge.source)];
    const targetItem = items[rowOf.get(edge.target)];
    // Same-branch related context is bracketed on the rows, never drawn.
    if (edge.type === "related" && (sourceItem.node.branch || "") === (targetItem.node.branch || "")) return [];
    const sx = laneX(sourceItem.node.branch || "");
    const sy = rowY(rowOf.get(edge.source));
    const tx = laneX(targetItem.node.branch || "");
    const ty = rowY(rowOf.get(edge.target));
    const soft = edge.type !== "related" && !touched;
    const stroke = soft ? `var(--edge-${edge.type}-soft)` : edgeColor(edge.type);
    const marker = soft ? `trail-arrow-${edge.type}-soft` : `trail-arrow-${edge.type}`;
    const opacity = touched ? 0.95 : focusActive ? 0.5 : 0.9;
    const tip = `<title>${esc(trailTitle(sourceItem.node))} ${TRAIL_VERB[edge.type]} ${esc(trailTitle(targetItem.node))}</title>`;
    // Daisy-chained lifecycle edges between ADJACENT rows (each entry
    // replacing/refining the one directly below - the common case when work
    // iterates within a session) would stack the relationship zone into a
    // thicket of out-and-back routes carrying no information the proximity
    // doesn't already give. Same de-cluttering spirit as bracketing
    // same-branch related context: an adjacent lifecycle edge renders as a
    // short direct hop beside the dots, and the routed lanes are reserved for
    // edges that actually span distance.
    if (edge.type === "supersedes" && adjacentRows(rowOf.get(edge.source), rowOf.get(edge.target))) {
      const bow = 11;
      const path = `M ${sx} ${sy} C ${sx - bow} ${sy + (ty - sy) * 0.3}, ${tx - bow} ${ty - (ty - sy) * 0.3}, ${tx} ${ty}`;
      return [`<path d="${path}" fill="none" stroke="${stroke}" stroke-width="${touched ? 2.6 : 2}" stroke-dasharray="${TRAIL_DASH[edge.type]}" stroke-opacity="${opacity}" marker-end="url(#${marker})">${tip}</path>`];
    }
    const lx = relLaneX(edge.type);
    const r = TRAIL_CORNER;
    const dir = ty > sy ? 1 : -1;
    const path = `M ${sx} ${sy} L ${lx + r} ${sy} Q ${lx} ${sy} ${lx} ${sy + r * dir} L ${lx} ${ty - r * dir} Q ${lx} ${ty} ${lx + r} ${ty} L ${tx} ${ty}`;
    return [`<path d="${path}" fill="none" stroke="${stroke}" stroke-width="${touched ? 2.6 : 2}" stroke-dasharray="${TRAIL_DASH[edge.type]}" stroke-opacity="${opacity}" marker-end="url(#${marker})">${tip}</path>`];
  });

  // Search as a function over the Trail: matching rows get a marker dot and
  // keep full presence, everything else dims - the graph structure stays
  // intact so lineage context never disappears under a query.
  const searching = Boolean(state.query.trim());
  const rowMatch = (node) => searching && state.matchEntries.has(node.entry_id || "");

  const dots = items.flatMap((item, index) => {
    if (item.kind !== "node") return [];
    const branch = item.node.branch || "";
    const selected = item.node.entry_id === selectedEntry || item.node.chunk_id === state.selectedId;
    const miss = searching && !rowMatch(item.node) && !selected;
    return [`<circle cx="${laneX(branch)}" cy="${rowY(index)}" r="${selected ? 6.5 : 4.5}" fill="${branch ? colorOf.get(branch) : "var(--faint)"}" fill-opacity="${miss ? 0.35 : 1}" stroke="${selected ? "var(--accent-strong)" : "var(--bg)"}" stroke-width="${selected ? 2.5 : 2}"></circle>`];
  });

  const rows = items.map((item, index) => {
    if (item.kind === "day") return `<div class="trail-day" style="--indent:${rowIndent(envelopeLane[index])}px">${esc(item.label)}</div>`;
    const node = item.node;
    const branch = node.branch || "";
    const tip = branch && spans.get(branch)?.first === index;
    const selected = node.entry_id === selectedEntry || node.chunk_id === state.selectedId;
    const time = node.datetime ? node.datetime.slice(11, 16) : "";
    const searchClass = !searching ? "" : rowMatch(node) ? "search-match" : selected ? "" : "search-miss";
    return `
      <div class="trail-row ${selected ? (state.selectionMuted ? "pinned" : "selected") : ""} ${searchClass} ${chainPrimary.has(node.id) ? "chain-primary" : chainSecondary.has(node.id) ? "chain-secondary" : ""} ${commitSiblings.has(node.id) ? "commit-sibling" : ""}" style="--indent:${rowIndent(envelopeLane[index])}px" data-chunk="${escAttr(node.chunk_id)}" title="${escAttr(node.title)}${branch ? escAttr(` · ${branch}`) : ""}">
        <span class="trail-time">${time}</span>
        ${rowMatch(node) ? `<span class="trail-match-dot"></span>` : ""}
        <span class="trail-title">${esc(trailTitle(node))}</span>
        ${node.has_diagram ? `<button type="button" class="trail-diagram-badge" data-diagram-entry="${escAttr(node.entry_id || "")}" title="Decision diagram — click to preview" aria-label="Preview decision diagram">◇</button>` : ""}
        ${tip ? `<span class="trail-branch" style="color:${colorOf.get(branch)}">${esc(branch)}</span>` : ""}
      </div>`;
  });

  const shown = items.filter((item) => item.kind === "node").length;
  return `
    <div class="viewbar">
      <span class="meta"><strong>${shown}</strong> of ${total} entries · newest first</span>
      ${searchStatus()}
      <span class="spacer"></span>
      <span class="legend-item"><span class="legend-line legend-line-dashed" style="border-color:${edgeColor("supersedes")}"></span>replaces</span>
      <span class="legend-item"><span class="legend-line legend-line-dashed" style="border-color:${edgeColor("evolves")}"></span>evolves</span>
      <span class="legend-item"><span class="legend-line legend-line-dashed" style="border-color:${edgeColor("related")}"></span>related · on select</span>
      ${shown < total ? `<button type="button" class="chip" data-trail-more>Load older</button>` : ""}
    </div>
    <div class="trail-scroll">
      <div class="trail-body">
        <svg class="trail-rail" width="${railWidth}" height="${height}" viewBox="0 0 ${railWidth} ${height}" aria-hidden="true">
          <defs>
            <marker id="trail-arrow-supersedes" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("supersedes")}"></path></marker>
            <marker id="trail-arrow-evolves" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("evolves")}"></path></marker>
            <marker id="trail-arrow-related" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${edgeColor("related")}"></path></marker>
            <marker id="trail-arrow-supersedes-soft" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--edge-supersedes-soft)"></path></marker>
            <marker id="trail-arrow-evolves-soft" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--edge-evolves-soft)"></path></marker>
          </defs>
          <rect class="trail-rel-zone" x="0" y="0" width="${TRAIL_REL_ZONE - 5}" height="${height}" rx="6"></rect>
          ${phantomTrunk}
          ${connectors.join("")}
          ${laneSegments.join("")}
          ${evolvesBrackets.join("")}
          ${arcs.join("")}
          ${dots.join("")}
          ${mergeDots.join("")}
        </svg>
        <div class="trail-rows">${rows.join("")}</div>
      </div>
      ${shown < total ? `<button type="button" class="chip trail-more" data-trail-more>Load older entries</button>` : ""}
    </div>`;
}

// Reader topic chips (topic-neighbourhoods plan Phase 4). Sourced from the
// entry's effective topics: authored controlled-vocabulary `topics:` when
// present, else the derived tag/context fallback for pre-vocabulary entries
// (the backend `_topics()` prefers indexed and never mixes the two). Each chip
// reuses the sidebar's `data-topic` handler, so clicking filters the timeline
// by that topic.
function readerTopics(selected) {
  const topics = selected.topics || [];
  if (!topics.length) return "";
  const chips = topics
    .map(
      (topic) =>
        `<button type="button" class="chip topic-chip ${state.topic === topic ? "active" : ""}" data-topic="${escAttr(topic)}">#${esc(topic)}</button>`,
    )
    .join("");
  return `<div class="chip-list topic-chips">${chips}</div>`;
}

function rightPane() {
  const selected = state.selected;
  if (!selected) return `<div class="empty">Select a memory to inspect details.</div>`;
  const linkGroups = [
    ["Related", selected.related_entries || []],
    ["Backlinks", selected.backlinks || []],
  ];
  return `
    <div class="detail-header ${state.selectionMuted ? "pinned" : ""}">
      <div class="entry-meta"><span>${selected.date} ${selected.time || ""}</span><span>${esc(selected.agent_type || "")}</span></div>
      <h2>${esc(selected.title)}</h2>
      <div class="count">${esc(selected.chunk_id)}</div>
    </div>
    <section class="detail-section">
      <h4>Entry${matchNote(selected)}</h4>
      ${readerTopics(selected)}
      <div class="chip-list">${(selected.sections || []).map((section) => `<span class="chip">${esc(section)}</span>`).join("")}</div>
      <div class="markdown">${markdown(selected.text || "")}</div>
    </section>
    ${commitSection(selected)}
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
    const token = ++state.loadSeq;
    const ok = await refreshSearch(token);
    if (!ok || token !== state.loadSeq) return;
    state.searchOpen = Boolean(state.query.trim());
    render();
  }, 180);
  let graphDrag = null;
  let suppressGraphClick = false;

  app.addEventListener("input", (event) => {
    if (event.target?.id === "query") queryInput(event.target.value);
  });

  // Refocusing a box that still holds a query reopens its ranked dropdown -
  // but only a genuine refocus (e.g. clicking back in after clicking away).
  // restoringFocus distinguishes that from render()'s internal caret-
  // preservation refocus, which must never reopen a dropdown the user (or
  // Enter/Escape) just closed.
  app.addEventListener("focusin", (event) => {
    if (restoringFocus) return;
    if (event.target?.id === "query" && state.query.trim() && !state.searchOpen) {
      state.searchOpen = true;
      render();
    }
  });

  // "/" focuses search from anywhere (the box is now on every view);
  // Enter / Shift+Enter cycle matches; Esc closes the dropdown, then leaves.
  window.addEventListener("keydown", async (event) => {
    const tag = event.target?.tagName;
    const typing = tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
    if (event.key === "/" && !typing) {
      event.preventDefault();
      document.getElementById("query")?.focus();
    } else if (event.key === "Enter" && event.target?.id === "query") {
      event.preventDefault();
      await jumpToMatch(event.shiftKey ? -1 : 1);
    } else if (event.key === "Escape" && event.target?.id === "query") {
      if (state.searchOpen) {
        state.searchOpen = false;
        render();
      } else {
        event.target.blur();
      }
    }
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
    if (target.dataset?.worktreeSelect !== undefined) {
      await switchWorktree(target.value);
    } else if (target.dataset?.filterSelect) {
      await updateFilter(target.dataset.filterSelect, target.value);
    } else if (target.id === "date-from") {
      await updateFilter("dateFrom", target.value);
    } else if (target.id === "date-to") {
      await updateFilter("dateTo", target.value);
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
    // Click-away closes the ranked dropdown; the query and markers persist.
    if (state.searchOpen && !event.target.closest?.(".searchbox-wrap")) {
      state.searchOpen = false;
      render();
    }
    const searchHit = event.target.closest("[data-search-jump]");
    if (searchHit) {
      state.searchOpen = false;
      await jumpToChunk(searchHit.dataset.chunk);
      return;
    }
    // Decision-diagram trigger (Trail/Graph badge + reader diagram): open the
    // zoomable viewer. Checked before row/node selection so engaging it never
    // also selects the entry underneath it.
    const diagramTrigger = event.target.closest("[data-diagram-entry]");
    if (diagramTrigger) {
      await openDiagramViewer(diagramTrigger.dataset.diagramEntry);
      return;
    }
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
    if (target.dataset.matchNext !== undefined) {
      await jumpToMatch(1);
      return;
    }
    if (target.dataset.matchPrev !== undefined) {
      await jumpToMatch(-1);
      return;
    }
    if (target.dataset.searchClear !== undefined) {
      state.query = "";
      state.results = [];
      state.matchEntries = new Set();
      state.searchOpen = false;
      // Clear the live input too: render()'s focus preservation would
      // otherwise restore the stale text over the emptied state.
      const box = document.getElementById("query");
      if (box) box.value = "";
      render();
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
    if (target.dataset.toggleRight !== undefined) {
      state.rightCollapsed = !state.rightCollapsed;
      localStorage.setItem("ml:rightCollapsed", state.rightCollapsed ? "1" : "0");
      render();
      return;
    }
    if (target.dataset.section) {
      const key = target.dataset.section;
      state.sectionOpen[key] = state.sectionOpen[key] === false;
      localStorage.setItem("ml:sections", JSON.stringify(state.sectionOpen));
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
      state.searchOpen = false;
      if (target.dataset.savedView) {
        state.view = target.dataset.savedView;
        localStorage.setItem("ml:view", state.view);
      }
      await reloadCurrentView();
      return;
    }
    if (target.dataset.entry) {
      const token = ++state.loadSeq;
      await selectChunk(target.dataset.entry, true, token);
      return;
    }
    if (target.dataset.chunk) {
      // Second click on the already-selected entry toggles muted focus:
      // related routes hide, lifecycle routes go back to pastel, and the
      // entry stays pinned (border) with the reader still on it.
      if (state.selectedId === target.dataset.chunk && state.selected) {
        state.selectionMuted = !state.selectionMuted;
        render();
        return;
      }
      state.selectionMuted = false;
      const hint = matchHintFor(target.dataset.chunk);
      state.matchHint = hint;
      state.pendingMatchScroll = Boolean(hint);
      // Selecting an entry is an explicit "inspect this" - reopen the reader
      // if it was collapsed so the click always produces visible feedback.
      if (state.rightCollapsed) {
        state.rightCollapsed = false;
        localStorage.setItem("ml:rightCollapsed", "0");
      }
      const token = ++state.loadSeq;
      await selectChunk(target.dataset.chunk, true, token);
    }
  });
}

// The Trail's chronological node order (newest first) - the same sort
// trailModel uses, exposed so match cycling and window growth agree with the
// rendered rows without re-deriving the full model.
function trailOrderedNodes() {
  return (state.graph?.nodes || [])
    .filter((node) => node.entry_id)
    .sort((a, b) => trailStamp(b) - trailStamp(a) || String(a.id).localeCompare(String(b.id)));
}

// Grow the Trail window until the target entry's row is rendered, stepping in
// whole TRAIL_WINDOW_STEP pages so "load older" and match jumps stay aligned.
function ensureTrailVisible(chunkId) {
  const index = trailOrderedNodes().findIndex((node) => node.chunk_id === chunkId);
  if (index >= state.trailWindow) {
    state.trailWindow = Math.ceil((index + 1) / TRAIL_WINDOW_STEP) * TRAIL_WINDOW_STEP;
  }
}

// Jump to a searched entry (dropdown click): select it in the current view,
// reopening the reader and scrolling the Trail to the row.
async function jumpToChunk(chunkId) {
  state.selectionMuted = false;
  const hint = matchHintFor(chunkId);
  state.matchHint = hint;
  state.pendingMatchScroll = Boolean(hint);
  if (state.rightCollapsed) {
    state.rightCollapsed = false;
    localStorage.setItem("ml:rightCollapsed", "0");
  }
  if (state.view === "trail") {
    ensureTrailVisible(chunkId);
    state.pendingTrailScroll = true;
  }
  const token = ++state.loadSeq;
  await selectChunk(chunkId, true, token);
}

// Cycle matches in Trail order (newest first): Enter / next steps down the
// trail, Shift+Enter / prev steps back up, wrapping at the ends.
async function jumpToMatch(step) {
  const matches = trailOrderedNodes().filter((node) => state.matchEntries.has(node.entry_id));
  if (!matches.length) return;
  const current = matches.findIndex((node) => node.chunk_id === state.selectedId);
  const next = matches[(current + step + matches.length) % matches.length];
  state.searchOpen = false;
  await jumpToChunk(next.chunk_id);
}

// Post-render: scroll the Trail to a freshly jumped-to row. Idempotent, like
// applyMatchHighlight - the flag only survives one render.
function applyTrailScroll() {
  if (!state.pendingTrailScroll) return;
  state.pendingTrailScroll = false;
  const row = document.querySelector(".trail-row.selected, .trail-row.pinned");
  if (row) row.scrollIntoView({ block: "center" });
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
  // Each figure is clickable to open the same zoomable viewer as the Trail/Graph
  // badge, so a cramped inline diagram can be inspected full-size in place.
  const entry = escAttr(selected.entry_id || "");
  return `
    <section class="detail-section">
      <h4>Decision diagrams <span class="count">· click to zoom</span></h4>
      ${blocks.map((block) => `<figure class="diagram diagram-openable" data-diagram-entry="${entry}" title="Click to inspect (zoom + pan)">${block.title ? `<figcaption class="count">${esc(block.title)}</figcaption>` : ""}${renderDiagramBlock(block.source)}</figure>`).join("")}
    </section>`;
}

// --- Decision-diagram viewer (Trail/Graph badge + reader -> zoomable panel) ---
// The badge (and a click on a reader diagram) lazily fetches the entry's chunk
// (cached), then opens a large CENTRED panel - a reasoning flow needs room to
// inspect, not a 420px preview. Each diagram renders with the built-in Arc 2d
// renderer inside a pan/zoom viewport: wheel zooms toward the cursor, drag pans,
// and a control bar offers zoom out / fit / zoom in. Closed by the × button, a
// backdrop click, Escape, or re-triggering the same entry's badge.
const _diagramChunkCache = new Map();

function closeDiagramViewer() {
  document.querySelector(".diagram-viewer-backdrop")?.remove();
  document.removeEventListener("keydown", _diagramViewerKeydown, true);
}

function _diagramViewerKeydown(event) {
  if (event.key === "Escape") {
    event.stopPropagation();
    closeDiagramViewer();
  }
}

async function openDiagramViewer(entryId) {
  if (!entryId) return;
  const open = document.querySelector(".diagram-viewer-backdrop");
  if (open && open.dataset.entry === entryId) {
    closeDiagramViewer(); // re-triggering the same entry toggles closed
    return;
  }
  closeDiagramViewer();
  // Cache is keyed by worktree+entry: the same entry id resolves to a different
  // chunk per checkout, and api() scopes the fetch to the selected worktree.
  const cacheKey = `${state.worktree || ""}::${entryId}`;
  let chunk = _diagramChunkCache.get(cacheKey);
  if (chunk === undefined) {
    chunk = await api(`/api/chunks/${encodeURIComponent(entryId)}`).catch(() => null);
    _diagramChunkCache.set(cacheKey, chunk);
  }
  const blocks = (chunk?.diagrams || []).flatMap((sidecar) =>
    (sidecar.mermaid_blocks || []).map((source) => ({ source, title: sidecar.title })),
  );
  const backdrop = document.createElement("div");
  backdrop.className = "diagram-viewer-backdrop";
  backdrop.dataset.entry = entryId;
  const body = blocks.length
    ? blocks
        .map(
          (b) => `
        <figure class="diagram-view">
          ${b.title ? `<figcaption class="count">${esc(b.title)}</figcaption>` : ""}
          <div class="diagram-viewport" data-viewport>
            <div class="diagram-stage" data-stage>${renderDiagramBlock(b.source)}</div>
          </div>
          <div class="diagram-zoom-bar">
            <button type="button" data-zoom="out" aria-label="Zoom out">&minus;</button>
            <button type="button" data-zoom="fit" aria-label="Reset zoom">Fit</button>
            <button type="button" data-zoom="in" aria-label="Zoom in">+</button>
          </div>
        </figure>`,
        )
        .join("")
    : `<div class="empty">No diagram available for this entry.</div>`;
  backdrop.innerHTML = `
    <div class="diagram-viewer" role="dialog" aria-modal="true" aria-label="Decision diagram">
      <div class="diagram-viewer-head">
        <span class="count">${esc(chunk?.title || "Decision diagram")}</span>
        <button type="button" class="diagram-viewer-close" data-diagram-close aria-label="Close">×</button>
      </div>
      <div class="diagram-viewer-body">${body}</div>
    </div>`;
  backdrop.querySelector("[data-diagram-close]").addEventListener("click", (e) => {
    e.stopPropagation();
    closeDiagramViewer();
  });
  // Backdrop click closes; clicks inside the panel (target !== backdrop) don't.
  backdrop.addEventListener("mousedown", (e) => {
    if (e.target === backdrop) closeDiagramViewer();
  });
  document.body.appendChild(backdrop);
  backdrop.querySelectorAll(".diagram-view").forEach(initDiagramPanZoom);
  setTimeout(() => document.addEventListener("keydown", _diagramViewerKeydown, true), 0);
}

// Wire wheel-zoom (toward the cursor) + drag-pan + zoom buttons onto one
// diagram figure. Pointer capture keeps a drag glued to the viewport even when
// the cursor leaves it, and avoids leaking window listeners across viewers.
function initDiagramPanZoom(figure) {
  const viewport = figure.querySelector("[data-viewport]");
  const stage = figure.querySelector("[data-stage]");
  if (!viewport || !stage) return;
  const st = { scale: 1, x: 0, y: 0 };
  const clamp = (s) => Math.min(6, Math.max(0.3, s));
  const apply = () => {
    stage.style.transform = `translate(${st.x}px, ${st.y}px) scale(${st.scale})`;
  };
  const zoomAt = (px, py, factor) => {
    const next = clamp(st.scale * factor);
    const k = next / st.scale;
    st.x = px - (px - st.x) * k; // keep the point under (px,py) fixed
    st.y = py - (py - st.y) * k;
    st.scale = next;
    apply();
  };
  const fit = () => {
    st.scale = 1;
    st.x = 0;
    st.y = 0;
    apply();
  };
  viewport.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault(); // or the panel scrolls instead of zooming
      const rect = viewport.getBoundingClientRect();
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
    },
    { passive: false },
  );
  let dragging = false;
  let sx = 0;
  let sy = 0;
  viewport.addEventListener("pointerdown", (e) => {
    dragging = true;
    sx = e.clientX - st.x;
    sy = e.clientY - st.y;
    viewport.setPointerCapture(e.pointerId);
    viewport.classList.add("grabbing");
  });
  viewport.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    st.x = e.clientX - sx;
    st.y = e.clientY - sy;
    apply();
  });
  const endDrag = (e) => {
    dragging = false;
    try {
      viewport.releasePointerCapture(e.pointerId);
    } catch {}
    viewport.classList.remove("grabbing");
  };
  viewport.addEventListener("pointerup", endDrag);
  viewport.addEventListener("pointercancel", endDrag);
  const center = (factor) => {
    const rect = viewport.getBoundingClientRect();
    zoomAt(rect.width / 2, rect.height / 2, factor);
  };
  figure.querySelector('[data-zoom="in"]').addEventListener("click", () => center(1.25));
  figure.querySelector('[data-zoom="out"]').addEventListener("click", () => center(1 / 1.25));
  figure.querySelector('[data-zoom="fit"]').addEventListener("click", fit);
  fit();
}

// Commit packaging: the git commit that first captured this entry ("Authored
// in", diff-derived), plus the merge commit whose Memory-Entry trailer landed
// it on the trunk ("Merged to main by") when that differs, plus the other
// entries that rode the same authoring commit.
function commitSection(selected) {
  const mergedBy = selected.merged_by && selected.merged_by.sha !== selected.commit?.sha
    ? `<div class="entry-meta commit-merged-by"><span class="count">Merged to main by</span><span class="count">${esc(selected.merged_by.short)}</span><span>${esc(selected.merged_by.subject)}</span></div>`
    : "";
  if (selected.commit) {
    const siblings = selected.commit_entries || [];
    return `
    <section class="detail-section">
      <h4>Commit</h4>
      <div class="entry-meta"><span class="count">Authored in</span><span class="count">${esc(selected.commit.short)}</span><span>${esc(selected.commit.subject)}</span></div>
      ${mergedBy}
      ${siblings.length ? `<div class="count commit-note">${siblings.length} other entr${siblings.length === 1 ? "y" : "ies"} in this commit</div>${siblings.map((item) => `<button type="button" class="link-card" data-chunk="${escAttr(item.chunk_id)}">${esc(stripTitleStamp(item.title))}<br><span class="count">${item.date} ${item.time || ""}</span></button>`).join("")}` : `<div class="count commit-note">Only entry in this commit.</div>`}
    </section>`;
  }
  if (selected.commit_tracking) {
    return `
    <section class="detail-section">
      <h4>Commit</h4>
      <div class="count">Not yet committed.</div>
    </section>`;
  }
  return "";
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
  await reloadCurrentView();
}

async function resetFilters() {
  state.agent = "";
  state.user = "";
  state.topic = "";
  state.granularity = "entry";
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

function clearGraphHover() {
  state.graphHover = "";
  render();
}

function resetGraphView() {
  state.graphTransform = { x: 0, y: 0, scale: 1 };
  render();
}

// Every scrollable region in the app. render() rebuilds the DOM, so ANY
// scroll position not captured here silently resets on the next state change
// (the left-pane facet click bug). New scroll containers must be added here.
const SCROLL_PRESERVE_SELECTORS = [".pane.left", ".pane.right", ".scroll", ".trail-scroll"];

function captureCenterScroll() {
  const stateBySelector = {};
  SCROLL_PRESERVE_SELECTORS.forEach((selector) => {
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

// Force-directed layout: Fruchterman-Reingold repulsion + weighted link
// attraction + centering gravity + a collision pass (the d3-force recipe,
// hand-rolled to stay dependency-free). The old layout had attraction only,
// so unrelated nodes clumped. Hash-seeded start keeps it deterministic;
// positions are cached per dataset so pan/hover re-renders never recompute.
let graphLayoutCache = { key: "", positions: null };

function graphPositions(nodes, edges = []) {
  const key = `${nodes.length}|${edges.length}|${nodes[0]?.id || ""}|${nodes[nodes.length - 1]?.id || ""}`;
  if (graphLayoutCache.key === key && graphLayoutCache.positions) return graphLayoutCache.positions;
  const positions = graphForceLayout(nodes, edges);
  graphLayoutCache = { key, positions };
  return positions;
}

function graphForceLayout(nodes, edges) {
  const width = 1000;
  const height = 620;
  const centerX = width / 2;
  const centerY = height / 2;
  const count = Math.max(1, nodes.length);
  const k = Math.max(34, Math.min(90, Math.sqrt((width * height) / count) * 0.9));
  const pos = {};
  nodes.forEach((node, index) => {
    const seed = hashString(node.id || `${index}`);
    const angle = ((seed % 3600) / 3600) * Math.PI * 2;
    const ring = 0.25 + (((seed >>> 8) % 1000) / 1000) * 0.75;
    pos[node.id] = {
      x: centerX + Math.cos(angle) * 420 * ring,
      y: centerY + Math.sin(angle) * 260 * ring,
    };
  });
  const ids = nodes.map((node) => node.id).filter((id) => pos[id]);
  const links = layoutSimilarityLinks(nodes, edges).filter((link) => pos[link.source] && pos[link.target]);
  let temperature = width / 8;
  const iterations = 120;
  for (let iter = 0; iter < iterations; iter += 1) {
    const disp = {};
    ids.forEach((id) => {
      disp[id] = { x: 0, y: 0 };
    });
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const a = pos[ids[i]];
        const b = pos[ids[j]];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.hypot(dx, dy);
        if (dist < 0.01) {
          dx = (((hashString(ids[i]) >>> 4) % 7) - 3) * 0.1 || 0.1;
          dy = 0.1;
          dist = Math.hypot(dx, dy);
        }
        const repulsion = (k * k) / dist;
        disp[ids[i]].x += (dx / dist) * repulsion;
        disp[ids[i]].y += (dy / dist) * repulsion;
        disp[ids[j]].x -= (dx / dist) * repulsion;
        disp[ids[j]].y -= (dy / dist) * repulsion;
      }
    }
    links.forEach((link) => {
      const a = pos[link.source];
      const b = pos[link.target];
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.max(0.01, Math.hypot(dx, dy));
      const weight = Math.min(1, (link.strength || 0.03) * 14);
      const attraction = ((dist * dist) / k) * weight;
      disp[link.source].x -= (dx / dist) * attraction;
      disp[link.source].y -= (dy / dist) * attraction;
      disp[link.target].x += (dx / dist) * attraction;
      disp[link.target].y += (dy / dist) * attraction;
    });
    ids.forEach((id) => {
      const point = pos[id];
      // Gentle centering keeps disconnected clusters on canvas.
      disp[id].x += (centerX - point.x) * 0.04;
      disp[id].y += (centerY - point.y) * 0.04;
      const magnitude = Math.max(0.01, Math.hypot(disp[id].x, disp[id].y));
      const limited = Math.min(magnitude, temperature);
      point.x += (disp[id].x / magnitude) * limited;
      point.y += (disp[id].y / magnitude) * limited;
      point.x = Math.max(24, Math.min(width - 24, point.x));
      point.y = Math.max(24, Math.min(height - 24, point.y));
    });
    temperature = Math.max(2, temperature * 0.95);
  }
  // Collision pass: labels need breathing room beyond point separation.
  const minSeparation = 30;
  for (let pass = 0; pass < 10; pass += 1) {
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const a = pos[ids[i]];
        const b = pos[ids[j]];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.hypot(dx, dy);
        if (dist >= minSeparation) continue;
        if (dist < 0.01) {
          dx = (((hashString(ids[i]) >>> 6) % 7) - 3) * 0.1 || 0.1;
          dy = 0.1;
          dist = Math.hypot(dx, dy);
        }
        const push = (minSeparation - dist) / 2;
        a.x += (dx / dist) * push;
        a.y += (dy / dist) * push;
        b.x -= (dx / dist) * push;
        b.y -= (dy / dist) * push;
      }
    }
  }
  return pos;
}

function layoutSimilarityLinks(nodes, edges) {
  const visible = new Set(nodes.map((node) => node.id));
  const links = [];
  const seen = new Set();
  const push = (source, target, strength) => {
    const key = [source, target].sort().join("|");
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ source, target, strength });
  };
  edges.filter((edge) => edge.type === "related").forEach((edge) => {
    if (!visible.has(edge.source) || !visible.has(edge.target)) return;
    push(edge.source, edge.target, 0.075);
  });
  // Sparse similarity attraction: each node pulls only toward its top-3
  // topic neighbours (date proximity is a tie-break boost, never a link by
  // itself). The old all-pairs link set collapsed the force layout into a
  // hairball on burst-heavy corpora where most entries share a date window.
  const byNode = new Map(nodes.map((node) => [node.id, []]));
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const topicScore = sharedTopicScore(nodes[i], nodes[j]);
      if (topicScore <= 0.15) continue;
      const score = topicScore * (1 + dateProximityScore(nodes[i], nodes[j]) * 0.3);
      byNode.get(nodes[i].id).push({ other: nodes[j].id, score });
      byNode.get(nodes[j].id).push({ other: nodes[i].id, score });
    }
  }
  byNode.forEach((candidates, id) => {
    candidates.sort((a, b) => b.score - a.score);
    candidates.slice(0, 3).forEach((candidate) => push(id, candidate.other, 0.03 + candidate.score * 0.03));
  });
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
  // Honour mermaid's <br/> line breaks (authored so long labels wrap) and size
  // the uniform box to the widest line + tallest label - otherwise long labels
  // overflow their box, which is invisible at thumbnail size but glaring once
  // the diagram is opened full-size in the zoom viewer.
  const labelLines = (label) =>
    String(label)
      .replace(/^["']|["']$/g, "")
      .split(/<br\s*\/?>/i)
      .map((s) => s.trim())
      .filter(Boolean);
  const nodeLines = new Map([...nodes.entries()].map(([id, label]) => [id, labelLines(label).length ? labelLines(label) : [id]]));
  const maxLines = Math.max(1, ...[...nodeLines.values()].map((l) => l.length));
  const longestChars = Math.max(8, ...[...nodeLines.values()].flat().map((l) => l.length));
  const lineH = 16;
  const boxW = Math.min(300, Math.max(130, longestChars * 7 + 22));
  const boxH = Math.max(40, 14 + maxLines * lineH);
  const gapMain = 78, gapCross = 26;
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
  const nodeSvg = [...nodeLines.entries()].map(([id, lns]) => {
    const p = pos.get(id);
    const cx = p.x + boxW / 2;
    const startY = p.y + boxH / 2 - ((lns.length - 1) * lineH) / 2 + 4;
    const tspans = lns.map((ln, i) => `<tspan x="${cx}" y="${startY + i * lineH}">${esc(ln)}</tspan>`).join("");
    return `<g class="diagram-node"><rect x="${p.x}" y="${p.y}" width="${boxW}" height="${boxH}" rx="6"></rect><text text-anchor="middle">${tspans}</text></g>`;
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

// Source entries are hard-wrapped at an authoring column (~100 chars), but
// the reader pane is narrower and its width varies: rendering each source
// LINE as its own block breaks sentences at arbitrary points. Join
// continuation lines back into their logical block - a line continues the
// previous one unless it starts a new structural element - so paragraphs and
// bullets reflow to the pane. Fenced code is preserved verbatim.
function unwrapLines(lines) {
  const out = [];
  let inCode = false;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      inCode = !inCode;
      out.push(line);
      continue;
    }
    if (inCode) {
      out.push(line);
      continue;
    }
    const trimmed = line.trim();
    const startsBlock =
      !trimmed
      || /^#{1,6}\s/.test(trimmed)
      || trimmed.startsWith("- ")
      || trimmed.startsWith("* ")
      || /^\d+\.\s/.test(trimmed)
      || trimmed.startsWith(">")
      || trimmed.startsWith("|");
    const prev = out.length ? out[out.length - 1] : "";
    const prevTrimmed = prev.trim();
    const prevJoinable =
      prevTrimmed
      && !prevTrimmed.startsWith("```")
      && !/^#{1,6}\s/.test(prevTrimmed)
      && !prevTrimmed.startsWith("|");
    if (!startsBlock && prevJoinable) {
      out[out.length - 1] = `${prev.replace(/\s+$/, "")} ${trimmed}`;
    } else {
      out.push(line);
    }
  }
  return out;
}

function markdown(text) {
  const lines = unwrapLines(text.split("\n"));
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

// Phase 0 golden-fixture hook: a read-only surface for baseline capture and
// future React-parity harnesses to call the Trail's layout model directly
// (trailModel is otherwise module-scoped). Not used by the app itself.
window.memoryTraceDebug = { trailModel, trailOrderedNodes };

boot().catch((error) => {
  app.innerHTML = `<div class="boot">Memory Trace failed to load: ${esc(error.message)}</div>`;
});
