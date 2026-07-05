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
  results: [],
  timeline: null,
  graph: null,
  selected: null,
  selectedId: null,
  nextCursor: null,
  loadSeq: 0,
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
  if (state.view === "graph") await loadGraph();
}

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
  const params = qs({
    entry_id: state.graphScope === "neighborhood" ? state.selected?.entry_id || state.selectedId : "",
    granularity: "entry",
    agent: state.agent,
    user: state.user,
    topic: state.topic,
    date_from: state.dateFrom,
    date_to: state.dateTo,
    depth: 1,
    edge_types: [...state.graphEdgeTypes].join(","),
    limit: state.graphScope === "all" ? 500 : 90,
  });
  state.graph = await api(`/api/graph?${params}`);
  return token === state.loadSeq;
}

async function selectChunk(chunkId, rerender = true, token = state.loadSeq) {
  state.selectedId = chunkId;
  const selected = await api(`/api/chunks/${encodeURIComponent(chunkId)}`);
  if (token !== state.loadSeq) return false;
  state.selected = selected;
  if (state.view === "graph") await loadGraph(token);
  if (rerender) render();
  return true;
}

function render() {
  const scrollState = captureCenterScroll();
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.dataset.accent = state.accent;
  app.innerHTML = `
    <div class="app">
      ${topbar()}
      <div class="shell">
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
}

function topbar() {
  const tabs = [["search", "Search"], ["timeline", "Timeline"], ["graph", "Graph"]]
    .map(([key, label]) => `<button type="button" class="tab ${state.view === key ? "active" : ""}" data-view="${key}">${label}</button>`)
    .join("");
  return `
    <header class="topbar">
      <div class="brand"><span class="brand-mark"></span><span>Memory Lense</span></div>
      <div class="runtime-chip"><span class="runtime-dot"></span><span>${esc(state.runtime?.label || "runtime")}</span><span>${state.runtime?.entry_count || 0} entries</span></div>
      <div class="searchbox"><span>⌕</span><input id="query" value="${escAttr(state.query)}" placeholder="Search memory, tags, files, decisions" spellcheck="false"></div>
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
    <div class="chip-list">${Object.entries(facets.topics || {}).slice(0, 40).map(([topic, count]) => `<button type="button" class="chip ${state.topic === topic ? "active" : ""}" data-topic="${escAttr(topic)}">#${esc(topic)} <span class="count">${count}</span></button>`).join("")}</div>
    <div class="section-title"><span>Granularity</span></div>
    <div class="segmented">${["entry", "section", "all"].map((item) => `<button type="button" class="tab ${state.granularity === item ? "active" : ""}" data-granularity="${item}">${item}</button>`).join("")}</div>`;
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
  if (state.view === "graph") return `<section class="${densityClass}">${graphView()}</section>`;
  return `<section class="${densityClass}">${searchView()}</section>`;
}

function searchView() {
  return `
    <div class="viewbar">
      <span class="meta"><strong>${state.results.length}</strong> ${state.granularity === "entry" ? "entries" : "results"} shown ${state.nextCursor ? "of more" : ""}</span>
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
  if (state.density === "compact") {
    return `<div class="results">${state.results.map((item) => `<div class="compact-row ${item.chunk_id === state.selectedId ? "selected" : ""}" data-chunk="${escAttr(item.chunk_id)}" title="Open entry"><span>${item.date} ${item.time || ""}</span><span>${esc(item.title)}${(item.matched_sections || []).length ? ` <span class="count">· ${(item.matched_sections || []).length} matched section${(item.matched_sections || []).length === 1 ? "" : "s"}</span>` : ""}</span><span class="optional-wide">${esc(item.agent_type || "")}</span><span>${Number(item.score || 0).toFixed(1)}</span></div>`).join("")}</div>`;
  }
  return `<div class="results">${state.results.map((item) => `
    <article class="card ${item.chunk_id === state.selectedId ? "selected" : ""}" data-chunk="${escAttr(item.chunk_id)}">
      <div class="card-head"><span>${item.date} ${item.time || ""}</span><span>${esc(item.agent_type || "")}</span><span class="score">${Number(item.score || 0).toFixed(1)}</span></div>
      <h3>${esc(item.title)}</h3>
      <p class="excerpt">${highlight(item.excerpt || "", state.query)}</p>
      ${matchedSectionChips(item)}
      <div class="chip-list compact-hide">${(item.topics || []).slice(0, 5).map((topic) => `<span class="chip">#${esc(topic)}</span>`).join("")}<span class="count optional-wide">${esc(item.score_explanation || "")}</span></div>
    </article>`).join("")}</div>`;
}

function matchedSectionChips(item) {
  // One selectable result per session entry; matched subsections surface as
  // highlight context inside it, never as separate selectable records.
  const sections = item.matched_sections || [];
  if (!sections.length) return "";
  return `<div class="chip-list compact-hide">${sections.slice(0, 4).map((section) => `<span class="chip" title="${escAttr(section.excerpt || "")}">Matched section: ${esc((section.heading_path || []).slice(-1)[0] || "(untitled)")}</span>`).join("")}</div>`;
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
      ${Object.entries(byDay).map(([day, items]) => `<div class="day-group" id="day-${day}"><div class="day-head">${day} · ${items.length} entries</div>${items.map((item) => `<div class="timeline-item" data-chunk="${escAttr(item.chunk_id)}" data-entry-datetime="${escAttr(timelineItemDatetime(item))}"><div class="entry-meta"><span>${item.time || "00:00"}</span><span>${esc(item.agent_type || "")}</span></div><div>${esc(item.title)}</div></div>`).join("")}</div>`).join("")}
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
      <span class="spacer"></span>
      <div class="segmented">${[["all", "All entries"], ["neighborhood", "Neighborhood"]].map(([scope, label]) => `<button type="button" class="tab ${state.graphScope === scope ? "active" : ""}" data-graph-scope="${scope}">${label}</button>`).join("")}</div>
      <button type="button" class="chip" data-graph-reset>Reset view</button>
      <button type="button" class="chip" data-graph-fit>Fit view</button>
      <button type="button" class="chip ${state.graphSizeMode === "importance" ? "active" : ""}" data-graph-size title="Toggle node size between link connectivity and importance score">Size: ${state.graphSizeMode === "importance" ? "importance" : "links"}</button>
      ${["related", "topic", "agent", "day"].map((type) => `<button type="button" class="chip ${state.graphEdgeTypes.has(type) ? "active" : ""}" data-edge="${type}">${type}</button>`).join("")}
    </div>
    <div class="graph-stage">
      <svg class="graph-canvas" data-graph-canvas viewBox="0 0 1000 620" role="img">
      <g class="graph-layer" transform="translate(${state.graphTransform.x} ${state.graphTransform.y}) scale(${state.graphTransform.scale})">
      ${graph.edges.map((edge) => {
        const a = positions[edge.source], b = positions[edge.target];
        if (!a || !b) return "";
        const highlight = state.graphHover && (edge.source === state.graphHover || edge.target === state.graphHover);
        const dim = state.graphHover && !highlight;
        return `<line class="graph-edge ${highlight ? "graph-related" : ""} ${dim ? "graph-dim" : ""}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${edgeColor(edge.type)}" stroke-width="${edge.type === "related" ? 2 : 1}"></line>`;
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
      ${graphLegend(graph)}
    </div>`;
}

function graphLegend(graph) {
  const agents = [...new Set((graph.nodes || []).map((node) => node.agent || "unknown"))].sort();
  const edgeTypes = ["related", "topic", "agent", "day"];
  return `
    <div class="graph-legend" aria-label="Graph legend">
      <div class="legend-group"><span class="count">Nodes</span>${agents.map((agent) => `<span class="legend-item" title="${escAttr(agent)}"><span class="legend-swatch" style="background:${agentColor(agent)}"></span>${esc(graphLegendLabel(agent))}</span>`).join("")}</div>
      <div class="legend-group"><span class="count">Edges</span>${edgeTypes.map((type) => `<span class="legend-item"><span class="legend-line" style="background:${edgeColor(type)}"></span>${type}</span>`).join("")}</div>
      <div class="legend-group"><span class="count">Size: ${state.graphSizeMode === "importance" ? "importance" : "links"}</span><span class="count">Near: links/topics/dates</span></div>
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
      <h4>Entry</h4>
      <div class="chip-list">${(selected.sections || []).map((section) => `<span class="chip">${esc(section)}</span>`).join("")}</div>
      <div class="markdown">${markdown(selected.text || "")}</div>
    </section>
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
      const token = ++state.loadSeq;
      await selectChunk(target.dataset.chunk, true, token);
    }
  });
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

function graphTitle(title) {
  const value = String(title || "");
  return value.length > 56 ? `${value.slice(0, 53)}...` : value;
}

function graphLegendLabel(value) {
  const label = String(value || "unknown");
  return label.length > 14 ? `${label.slice(0, 12)}...` : label;
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
  return { related: "var(--accent)", topic: "#8f63e8", agent: "#18a999", day: "#d9941a" }[type] || "var(--muted)";
}

function agentColor(agent) {
  const value = agent || "unknown";
  return agentColors[hashString(value) % agentColors.length];
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

function highlight(text, query) {
  const words = [...new Set((query.toLowerCase().match(/[a-z0-9]{3,}/g) || []))].slice(0, 8);
  if (!words.length) return esc(text);
  const pattern = new RegExp(`(${words.map(escapeRegExp).join("|")})`, "ig");
  return esc(text).replace(pattern, "<mark>$1</mark>");
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

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

boot().catch((error) => {
  app.innerHTML = `<div class="boot">Memory Lense failed to load: ${esc(error.message)}</div>`;
});
