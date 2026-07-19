// Eased Trail scrolling with a middle-third stability band.
//
// Selecting an entry from outside the Trail (context panel, find bar) has to
// bring its row into view without yanking the list around. Two rules:
//
//   1. If the row already sits in the middle third of the viewport, do not move
//      at all. Small hops between neighbouring entries then feel completely
//      stable, because the previous selection is what set the scroll position.
//   2. Otherwise ease it to the NEAR edge of that band — the top edge when the
//      row is above, the bottom edge when it is below — so the list travels the
//      minimum distance and the direction of travel stays legible.
//
// Native `scrollIntoView({behavior:"smooth"})` can target neither that edge nor
// scale its duration, which is why this does its own rAF pass.

/** The band runs from `viewport/3` to `viewport*2/3`. */
export const TRAIL_BAND_FRACTION = 1 / 3;

export const TRAIL_SCROLL_MIN_MS = 180;
export const TRAIL_SCROLL_MAX_MS = 600;

/**
 * Target `scrollTop` to bring `rowCenter` to the near edge of the middle third,
 * or `null` when the row is already inside the band and must not move.
 *
 * All values are in the scroll container's content coordinates.
 */
export function bandScrollTarget(
  rowCenter: number,
  scrollTop: number,
  viewportHeight: number,
  maxScroll: number,
): number | null {
  if (!(viewportHeight > 0)) return null;
  const bandTop = viewportHeight * TRAIL_BAND_FRACTION;
  const bandBottom = viewportHeight * (1 - TRAIL_BAND_FRACTION);
  const offset = rowCenter - scrollTop; // where the row sits inside the viewport
  if (offset >= bandTop && offset <= bandBottom) return null;
  // Above the band -> land on its top edge; below -> land on its bottom edge.
  const raw = offset < bandTop ? rowCenter - bandTop : rowCenter - bandBottom;
  const clamped = Math.max(0, Math.min(Math.max(0, maxScroll), raw));
  // Clamping at either extreme can leave us exactly where we already are.
  return Math.abs(clamped - scrollTop) < 0.5 ? null : clamped;
}

/** Longer journeys take longer, but bounded so a full-corpus jump stays brisk. */
export function scrollDurationFor(distance: number): number {
  const travel = Math.abs(distance);
  return Math.round(Math.max(TRAIL_SCROLL_MIN_MS, Math.min(TRAIL_SCROLL_MAX_MS, TRAIL_SCROLL_MIN_MS + travel * 0.35)));
}

/** Symmetric acceleration and deceleration. */
export function easeInOutCubic(t: number): number {
  const clamped = Math.max(0, Math.min(1, t));
  return clamped < 0.5 ? 4 * clamped * clamped * clamped : 1 - Math.pow(-2 * clamped + 2, 3) / 2;
}

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

/**
 * Animate `element.scrollTop` to `target`. Returns a cancel function — callers
 * must invoke it before starting another run so a new selection interrupts the
 * old journey instead of fighting it.
 */
export function animateScrollTo(element: HTMLElement, target: number, duration: number): () => void {
  const from = element.scrollTop;
  const delta = target - from;
  if (delta === 0 || duration <= 0 || prefersReducedMotion()) {
    element.scrollTop = target;
    return () => {};
  }
  let frame = 0;
  let cancelled = false;
  const started = performance.now();
  const step = (now: number) => {
    if (cancelled) return;
    const progress = Math.min(1, (now - started) / duration);
    element.scrollTop = from + delta * easeInOutCubic(progress);
    if (progress < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
  return () => {
    cancelled = true;
    cancelAnimationFrame(frame);
  };
}
