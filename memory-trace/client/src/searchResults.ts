// Which full-text results are real hits.
//
// The server ranks but never *filters*: `rank_memory_chunks` scores every chunk
// in the pool and returns `ranked[:top_k]` with `top_k = len(pool)`, so
// `/api/v1/search?granularity=entry` comes back with the entire corpus ordered
// by score — and `total` is the corpus size, not the number of matches. The
// genuine hits sit at the front and score-0 filler trails behind them, ordered
// by recency.
//
// A dropdown hid that: you saw the first handful and never scrolled far enough
// to notice. Cycling does not — step past the last real hit and you walk into
// entries that have nothing to do with the query, with the counter cheerfully
// reporting progress. Hence this filter.

/** The two fields that distinguish a hit from filler. */
export type ScoredResult = { score: number; matched_terms: string[] };

/**
 * The results a user would call matches, in the server's ranked order.
 *
 * `score > 0 || matched_terms.length > 0` is deliberately an OR. A semantic
 * match carries a real score with no matched terms (`matched_fields` is purely
 * lexical, so semantic similarity never populates it); a lexical match can
 * score on a tag or heading. Filler has neither. Requiring both would silently
 * drop every semantic-only hit.
 */
export function genuineSearchResults<T extends ScoredResult>(results: readonly T[]): T[] {
  return results.filter((result) => result.score > 0 || result.matched_terms.length > 0);
}
