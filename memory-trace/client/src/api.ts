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

export type GraphQueryOptions = {
  entryId?: string | null;
  depth?: number;
  edgeTypes?: RendererGraphEdge["edge_type"][];
  limit?: number;
  topic?: string | null;
  dateFrom?: string | null;
  path?: string | null;
};

/** Every edge type the filter row offers. Order is the row's order. */
export const GRAPH_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["related", "supersedes", "evolves", "topic"];

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
 * related 533 / evolves 127 / supersedes 6 / topic 334. Excluding it returns
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
export const DEFAULT_GRAPH_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["related", "supersedes", "evolves"];

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
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  if (options.path) params.set("path", options.path);
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

export type TrailQueryOptions = { topic?: string | null; dateFrom?: string | null; limit?: number };

// The Trail is a dedicated product surface: /api/v1/trail fixes its own edge set
// (branch/supersedes/evolves/related) and entry granularity, so — unlike the
// graph — it takes no edge_types parameter.
export function trailQuery(options: TrailQueryOptions = {}): Promise<TrailResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 1000));
  if (options.topic) params.set("topic", options.topic);
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  return api<TrailResponse>(`/trail?${params.toString()}`);
}
