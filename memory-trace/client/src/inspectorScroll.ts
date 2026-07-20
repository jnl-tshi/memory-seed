// Bringing the matched section into view in the Inspector.
//
// Deliberately NOT `bandScrollTarget` from trailScroll.ts. That one exists to
// suppress jitter: consecutive Trail selections are usually neighbouring rows,
// so leaving anything already inside the middle third alone is what makes small
// hops feel stable. The Inspector has no such continuity — every step swaps the
// whole document — so there is no jitter to suppress, and centring a heading
// pushes the body it introduces below the fold on a short pane, which is the
// one thing the reader actually wants to see.
//
// Top-anchored with a small margin instead: the heading lands just under the
// top edge and its section reads downward from there.

/** Breathing room above the heading so it does not sit flush against the edge. */
export const READER_SCROLL_MARGIN = 24;

/**
 * Target `scrollTop` that brings `elementTop` to just below the top edge, or
 * `null` when the pane cannot or need not move.
 *
 * All values are in the scroll container's content coordinates.
 */
export function readerScrollTarget(
  elementTop: number,
  scrollTop: number,
  viewportHeight: number,
  maxScroll: number,
  margin: number = READER_SCROLL_MARGIN,
): number | null {
  if (!(viewportHeight > 0)) return null;
  const clamped = Math.max(0, Math.min(Math.max(0, maxScroll), elementTop - margin));
  // Clamping at either extreme can leave us exactly where we already are — the
  // same guard bandScrollTarget uses, and the reason a section near the very
  // top of a short entry does not produce a pointless 2px animation.
  return Math.abs(clamped - scrollTop) < 0.5 ? null : clamped;
}
