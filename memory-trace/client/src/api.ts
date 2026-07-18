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

export type GraphQueryOptions = {
  entryId?: string | null;
  depth?: number;
  edgeTypes?: RendererGraphEdge["edge_type"][];
  limit?: number;
  topic?: string | null;
  dateFrom?: string | null;
};

export const DEFAULT_GRAPH_EDGE_TYPES: RendererGraphEdge["edge_type"][] = ["related", "supersedes", "evolves", "topic"];

export function isCanonicalEntryId(value: string): boolean {
  return /^(?:mse_[A-Za-z0-9_-]+|ms-[A-Za-z0-9_-]+)$/.test(value.trim());
}

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export function graphQuery(options: GraphQueryOptions = {}): Promise<RendererGraphResponse> {
  const params = new URLSearchParams();
  const edgeTypes = options.edgeTypes ?? DEFAULT_GRAPH_EDGE_TYPES;
  params.set("edge_types", edgeTypes.join(","));
  params.set("limit", String(options.limit ?? 60));
  if (options.entryId) params.set("entry_id", options.entryId);
  if (options.depth) params.set("depth", String(options.depth));
  if (options.topic) params.set("topic", options.topic);
  if (options.dateFrom) params.set("date_from", options.dateFrom);
  return api<RendererGraphResponse>(`/graph/projection?${params.toString()}`);
}

export function searchQuery(query: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query.trim(), limit: "12", granularity: "entry" });
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
