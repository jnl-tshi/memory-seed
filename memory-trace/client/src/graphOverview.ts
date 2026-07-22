// When "Show more" has genuinely run out of Overview to page into.
//
// Extracted as a pure module (same reason as graphLayout/graphEdges) because
// the previous inline rule was wrong in a way only a measurement caught, and
// the corrected rule needs cases asserted without a DOM.
//
// The old rule was `graph.nodes.length < overviewLimit`: "the server returned
// fewer nodes than I asked for, so the corpus is exhausted". Measured against
// this repo's 589-entry corpus that retires the button far too early. The
// server applies the SAME limit to nodes and to edges, and the node count
// saturates long before the edge count does:
//
//   limit=540  nodes=540  edges=540  rendered(connected)=360
//   limit=600  nodes=555  edges=600  rendered=397   <- old rule stopped here
//   limit=660  nodes=555  edges=660  rendered=449
//   limit=800  nodes=555  edges=800  rendered=462
//   limit=1000 nodes=555  edges=1000 rendered=467
//
// At limit=600 the node count (555) is already saturated, so the old test
// fired — but 70 more entries were still reachable purely because more EDGES
// would be served. Overview capped out at 397 of 589 entries with no way to
// go further.
//
// The corrected rule is growth-based, which also terminates cleanly against
// the server's hard 1000 cap (where a bigger ask simply returns the same
// payload): a fetch that brought back no more nodes AND no more edges than
// the previous one means there is nothing left to page into. The
// under-the-limit test is kept as the FIRST-fetch case, where there is no
// previous payload to compare against, and is now applied to both axes.
export type OverviewCounts = { nodes: number; edges: number };

export function overviewCounts(graph: { nodes: unknown[]; edges: unknown[] }): OverviewCounts {
  return { nodes: graph.nodes.length, edges: graph.edges.length };
}

export function overviewExhausted(
  current: OverviewCounts | null,
  previous: OverviewCounts | null,
  requestedLimit: number,
): boolean {
  if (!current) return false;
  // A larger ask that yielded nothing new on either axis: the end.
  if (previous && current.nodes <= previous.nodes && current.edges <= previous.edges) return true;
  return current.nodes < requestedLimit && current.edges < requestedLimit;
}
