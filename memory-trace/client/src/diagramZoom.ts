// Pure zoom/pan maths for the decision-diagram viewer, extracted from the
// component for the same reason as graphLayout/graphEdges: the arithmetic is
// where the bugs live (clamping, fit-scale, wheel direction) and none of it
// needs a DOM to verify. Ported from the vanilla viewer's
// _diagramFitTransform / initDiagramPanZoom (static/app.js), keeping its
// bounds so both UIs behave identically.

export type Transform = { scale: number; x: number; y: number };

export const MIN_SCALE = 0.08;
export const MAX_SCALE = 6;

export function clampScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

/** Scale + offset that centres the stage inside the viewport with padding.
 *
 * Never scales ABOVE 1: a small diagram in a large viewport is shown at its
 * natural size rather than blown up, which is what "Fit" means for a drawing
 * whose stroke widths are authored, not relative.
 */
export function fitTransform(
  viewportWidth: number,
  viewportHeight: number,
  stageWidth: number,
  stageHeight: number,
  padding = 24,
): Transform {
  const usableWidth = Math.max(1, viewportWidth - padding);
  const usableHeight = Math.max(1, viewportHeight - padding);
  if (stageWidth <= 0 || stageHeight <= 0) return { scale: 1, x: 0, y: 0 };
  const scale = clampScale(Math.min(usableWidth / stageWidth, usableHeight / stageHeight, 1));
  return {
    scale,
    x: (viewportWidth - stageWidth * scale) / 2,
    y: (viewportHeight - stageHeight * scale) / 2,
  };
}

/** Zoom about a fixed point, so the content under the cursor stays put.
 *
 * Without the offset correction the diagram slides out from under the pointer
 * on every wheel tick, which reads as the viewer fighting you.
 */
export function zoomAbout(current: Transform, factor: number, pointX: number, pointY: number): Transform {
  const scale = clampScale(current.scale * factor);
  const ratio = scale / current.scale;
  return {
    scale,
    x: pointX - (pointX - current.x) * ratio,
    y: pointY - (pointY - current.y) * ratio,
  };
}

export function panBy(current: Transform, dx: number, dy: number): Transform {
  return { scale: current.scale, x: current.x + dx, y: current.y + dy };
}
