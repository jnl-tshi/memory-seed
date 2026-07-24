// Which relationship wins the line between two entries. Pure, so the rule can
// be unit tested without a Cytoscape instance.

// How consequential a relationship is, lowest wins. A supersession is the
// strongest claim two entries can make about each other; an evolution refines
// without retiring; `related` is an authored association; `topic` is mere
// shared vocabulary.
export const EDGE_PRIORITY: Record<string, number> = {
  replaces: 0,
  evolves: 1,
  related: 2,
  branch: 3,
  topic: 4,
  agent: 5,
  day: 6,
};

// Undirected: A->B and B->A occupy the same line on the map, so they compete
// for it regardless of which way their arrows point.
export function pairKey(source: string, target: string): string {
  return source < target ? `${source} ${target}` : `${target} ${source}`;
}

export type PresentableEdge = { id: string; source: string; target: string; type: string };

/** Ids of edges that lose their pair's line and must not be drawn.
 *
 * Two entries often carry several relationships at once, which drew coincident
 * lines and let the weakest one (a topic tag) paint over the strongest (a
 * supersession). Only the most consequential relationship survives.
 *
 * The winner is chosen among the types currently switched ON in the filter
 * row, so switching a type off PROMOTES whatever it was covering rather than
 * blanking the pair. Edges of a switched-off type are not returned here at all
 * — they are already hidden by the filter, and conflating the two would make
 * an outranked edge stay hidden after its winner was filtered away.
 */
export function outrankedEdgeIds(edges: PresentableEdge[], visibleTypes: readonly string[]): Set<string> {
  const strongest = new Map<string, { id: string; rank: number }>();
  for (const edge of edges) {
    if (!visibleTypes.includes(edge.type)) continue;
    const key = pairKey(edge.source, edge.target);
    const rank = EDGE_PRIORITY[edge.type] ?? Number.MAX_SAFE_INTEGER;
    const held = strongest.get(key);
    if (!held || rank < held.rank) strongest.set(key, { id: edge.id, rank });
  }
  const outranked = new Set<string>();
  for (const edge of edges) {
    if (!visibleTypes.includes(edge.type)) continue;
    if (strongest.get(pairKey(edge.source, edge.target))?.id !== edge.id) outranked.add(edge.id);
  }
  return outranked;
}
