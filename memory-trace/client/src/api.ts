import type { components } from "../../tests/contract/types";

export type RuntimeInfo = components["schemas"]["RuntimeInfo"];
export type Facets = components["schemas"]["Facets"];
export type GraphResponse = components["schemas"]["GraphResponse"];
export type GraphNode = components["schemas"]["GraphNode"];
export type ChunkResponse = components["schemas"]["ChunkResponse"];

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export function graphQuery(): Promise<GraphResponse> {
  return api<GraphResponse>("/graph?edge_types=related,supersedes,evolves,topic&limit=60");
}
