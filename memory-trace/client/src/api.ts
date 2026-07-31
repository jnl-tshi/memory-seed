import type { components } from "../../tests/contract/types";

export type RuntimeInfo = components["schemas"]["RuntimeInfo"];
export type Facets = components["schemas"]["Facets"];
export type RendererGraphResponse = components["schemas"]["RendererGraphResponse"];
export type RendererGraphNode = components["schemas"]["RendererGraphNode"];
export type RendererGraphEdge = components["schemas"]["RendererGraphEdge"];
export type ChunkResponse = components["schemas"]["ChunkResponse"];
export type SearchResponse = components["schemas"]["SearchResponse"];
export type SearchResult = components["schemas"]["SearchResult"];
export type TrailResponse = components["schemas"]["TrailResponse"];
export type TrailEvent = components["schemas"]["TrailEvent"];
export type BranchInfo = components["schemas"]["BranchInfo"];
export type MergeEvent = components["schemas"]["MergeEvent"];
export type ContinuityItem = components["schemas"]["ContinuityItem"];
export type TrailEdge = components["schemas"]["GraphEdge"];
export type WorktreesResponse = components["schemas"]["WorktreesResponse"];
export type WorktreeInfo = components["schemas"]["WorktreeInfo"];
export type BrowseResponse = components["schemas"]["BrowseResponse"];
export type DirectoryEntry = components["schemas"]["DirectoryEntry"];
export type OpenProjectResponse = components["schemas"]["OpenProjectResponse"];

export type GraphQueryOptions = {
  entryId?: string | null;
  depth?: number;
  edgeTypes?: RendererGraphEdge["edge_type"][];
  limit?: number;
  topic?: string | null;
  area?: string | null;
  activity?: string | null;
  dateFrom?: string | null;
  path?: string | null;
  /** Entry ids that must appear whatever the ranked slice would have chosen -
   *  the Trail's loaded window. Additive and exempt from `limit`. */
  pinnedIds?: string[];
  /**
   * Ask for per-decision rows (`include_decisions`), DEFAULT OFF.
   *
   * A change of GRANULARITY, not a filter: it is what gives a decision-level
   * edge (`B:d2 evolves A:d1`) a real endpoint instead of leaving both entries
   * drawn as orphans. The server scopes the Graph to `decision_row_scope:
   * "linked"`, expanding only the ordinals an edge actually terminates on -
   * blanket expansion measured 446 rows of which 276 were fresh isolates.
   * Because it changes the node set it needs a REFETCH, unlike the edge chips.
   */
  includeDecisions?: boolean;
};

/** Every edge type the filter row offers. Order is the row's order. */
export const GRAPH_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["related", "replaces", "evolves", "topic"];

/**
 * The edge types switched ON initially - authored relationships only.
 *
 * `topic` is deliberately excluded and stays available as a chip. It is not an
 * assertion about a pair of entries: the server builds it by grouping entries
 * under a topic, sorting by time, and joining CONSECUTIVE ones (service.py
 * `chain`). A topic edge therefore means "nothing else carrying this tag
 * happened between these two" - an artefact of sort order, not a relationship.
 * It also double-encodes what node colour now says, since communities are
 * named after authored topics.
 *
 * Measured on the real corpus, with THIS edge set rather than the server's
 * default: including topic returns 1000 edges - the cap, i.e. TRUNCATED - as
 * related 533 / evolves 127 / replaces 6 / topic 334. Excluding it returns
 * 666, comfortably under the cap. So topic edges were not merely spending
 * budget, they were crowding authored edges out of the response entirely, and
 * the 334 topic edges that survived were themselves an arbitrary slice of a
 * larger set. Without them the graph carries EVERY authored relationship.
 *
 * The cost, also measured: 152 of 562 nodes are touched by no other edge and so
 * stop rendering. They skew OLD, not recent - 100% of May entries, 49% of June,
 * 16% of July - because lifecycle linking began later. Those entries genuinely
 * have no authored relationship, and drawing them as connected was the graph
 * asserting something untrue.
 */
export const DEFAULT_GRAPH_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["related", "replaces", "evolves"];

export function isCanonicalEntryId(value: string): boolean {
  return /^(?:mse_[A-Za-z0-9_-]+|ms-[A-Za-z0-9_-]+)$/.test(value.trim());
}

// Active worktree scope: when set, every v1 request carries it, so the whole
// app reads one checkout's corpus at a time.
let activeWorktree: string | null = null;

export function setActiveWorktree(path: string | null) {
  activeWorktree = path;
}

export async function api<T>(path: string): Promise<T> {
  let scoped = path;
  if (activeWorktree) {
    scoped += `${path.includes("?") ? "&" : "?"}worktree=${encodeURIComponent(activeWorktree)}`;
  }
  const response = await fetch(`/api/v1${scoped}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export function worktreesQuery(): Promise<WorktreesResponse> {
  return api<WorktreesResponse>("/worktrees");
}

// Browsing and opening a project both bypass `api<T>()` deliberately: they
// read/act on the SERVER's filesystem and the process-wide project registry,
// not the currently active worktree's corpus, so the `?worktree=` scoping
// api<T>() always appends would be meaningless (or misleading) on both.

/** Subdirectories of `path` (server filesystem), or the home directory when
 * omitted - the folder picker's one call per navigation step. */
export async function browseQuery(path?: string | null): Promise<BrowseResponse> {
  const params = new URLSearchParams();
  if (path) params.set("path", path);
  const qs = params.toString();
  const response = await fetch(`/api/v1/browse${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<BrowseResponse>;
}

/** Validates `path` as a correctly-initialised memory-seed project and, if it
 * passes, registers it as a switchable worktree entry. `ok: false` with
 * `issues` is a normal outcome (not an initialised project yet), not a
 * request error - only a genuine transport/server failure throws. */
export async function openProject(path: string): Promise<OpenProjectResponse> {
  const params = new URLSearchParams({ path });
  const response = await fetch(`/api/v1/projects?${params.toString()}`, { method: "POST" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<OpenProjectResponse>;
}

// connectedNodeIds was removed when every node started rendering. Its premise
// ("an isolated entry is noise, not overview content") is the opposite of the
// current rule: edgeless entries render in a halo around the connected core,
// because hiding a fifth of the corpus made the coverage readout look like a
// cap. The edge-endpoint set still gets computed for layout partitioning —
// connectedIds in graphLayout.ts, next to the code that uses it.

export function graphQuery(options: GraphQueryOptions = {}): Promise<RendererGraphResponse> {
  const params = new URLSearchParams();
  const edgeTypes = options.edgeTypes ?? DEFAULT_GRAPH_EDGE_TYPES;
  params.set("edge_types", edgeTypes.join(","));
  params.set("limit", String(options.limit ?? 60));
  if (options.entryId) params.set("entry_id", options.entryId);
  if (options.depth) params.set("depth", String(options.depth));
  if (options.topic) params.set("topic", options.topic);
  if (options.area) params.set("area", options.area);
  if (options.activity) params.set("activity", options.activity);
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  if (options.path) params.set("path", options.path);
  if (options.pinnedIds?.length) params.set("pinned_ids", options.pinnedIds.join(","));
  // Only ever sent when ON: the server default is false, and an explicit
  // `include_decisions=false` on every request would make the entry-level
  // surface look like something that has to be asked for.
  if (options.includeDecisions) params.set("include_decisions", "true");
  return api<RendererGraphResponse>(`/graph/projection?${params.toString()}`);
}

// The old limit of 12 was sized for a dropdown you scrolled by eye. Cycling
// walks the whole set, and genuine hits are now separated from the server's
// score-0 filler client-side (see searchResults.ts), so asking for 12 would
// truncate real matches before the filter ever ran. Not the full corpus:
// every result carries an excerpt, so the payload grows quickly.
export const SEARCH_LIMIT = 100;

export function searchQuery(query: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query.trim(), limit: String(SEARCH_LIMIT), granularity: "entry" });
  return api<SearchResponse>(`/search?${params.toString()}`);
}

export type TrailQueryOptions = { topic?: string | null; area?: string | null; activity?: string | null; dateFrom?: string | null; limit?: number };

// The Trail is a dedicated product surface: /api/v1/trail fixes its own edge set
// (branch/replaces/evolves/related) and entry granularity, so — unlike the
// graph — it takes no edge_types parameter.
export function trailQuery(options: TrailQueryOptions = {}): Promise<TrailResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 1000));
  if (options.topic) params.set("topic", options.topic);
  if (options.area) params.set("area", options.area);
  if (options.activity) params.set("activity", options.activity);
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  return api<TrailResponse>(`/trail?${params.toString()}`);
}
