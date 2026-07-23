import { useCallback, useEffect, useRef, useState } from "react";
import { DiagramView } from "./DiagramView";
import { fitTransform, panBy, zoomAbout, type Transform } from "./diagramZoom";
import type { TraceLook } from "./mermaidConfig";

// Modal decision-diagram viewer, matching the vanilla UI's behaviour: a
// diamond badge or a reader figure opens a zoomable, pannable panel. The React
// client previously rendered diagrams inline only, with an inert badge reading
// "open the entry to view" - so a diagram larger than the inspector column had
// no way to be read at all.
//
// Escape closes, a backdrop click closes, a click inside the panel does not.
//
// A multi-diagram entry stacks several viewports in a scrolling body. The wheel
// is therefore SHARED between two jobs: scroll the list, or zoom a diagram. A
// diagram claims the wheel only once it is ACTIVE (clicked); until then the
// wheel scrolls past it. Without that gate every diagram ate the wheel and you
// could not scroll from one to the next - you were stuck zooming whichever one
// the pointer happened to be over.
export type DiagramBlock = { title?: string | null; source: string };

export function DiagramViewer({
  title,
  blocks,
  look,
  theme,
  onClose,
}: {
  title: string;
  blocks: DiagramBlock[];
  look: TraceLook;
  theme: string;
  onClose: () => void;
}) {
  // At most one diagram is active. null means "none - the wheel scrolls".
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        // Escape first releases an active diagram (so the wheel scrolls again),
        // and only closes the modal when nothing is active - two natural steps
        // out rather than one that skips the middle.
        if (activeIndex !== null) setActiveIndex(null);
        else onClose();
      }
    };
    // Capture phase: the graph and Trail also bind Escape, and the topmost
    // surface should win rather than racing on bubble order.
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [onClose, activeIndex]);

  return (
    <div
      className="diagram-viewer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="diagram-viewer" role="dialog" aria-modal="true" aria-label="Decision diagram">
        <div className="diagram-viewer-head">
          <span className="count">{title || "Decision diagram"}</span>
          <button type="button" className="diagram-viewer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div
          className="diagram-viewer-body"
          // A press that lands outside every viewport (the gaps, a caption)
          // releases the active diagram, so the wheel goes back to scrolling.
          onMouseDown={(event) => {
            if (!(event.target as HTMLElement).closest(".diagram-viewport")) setActiveIndex(null);
          }}
        >
          {blocks.length === 0 ? (
            <div className="empty">No diagram available for this entry.</div>
          ) : (
            blocks.map((block, index) => (
              <ZoomableDiagram
                key={index}
                title={block.title}
                source={block.source}
                look={look}
                theme={theme}
                active={activeIndex === index}
                onActivate={() => setActiveIndex(index)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ZoomableDiagram({
  title,
  source,
  look,
  theme,
  active,
  onActivate,
}: {
  title?: string | null;
  source: string;
  look: TraceLook;
  theme: string;
  active: boolean;
  onActivate: () => void;
}) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [transform, setTransform] = useState<Transform>({ scale: 1, x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  // True once the reader has zoomed or panned this diagram. While false the
  // view is still "just fitted", so a viewport resize (window resize, the
  // inspector dock moving) re-fits and stays centred; once the reader has taken
  // control we leave their framing alone.
  const adjusted = useRef(false);
  // The wheel handler is attached natively (below) rather than via onWheel, so
  // it reads `active` through a ref instead of closing over the prop.
  const activeRef = useRef(active);
  activeRef.current = active;

  const fit = useCallback(() => {
    const viewport = viewportRef.current;
    const stage = stageRef.current;
    if (!viewport || !stage) return;
    // Measure the stage's UNSCALED size: getBoundingClientRect reflects the
    // current transform, so fitting from it would compound each time.
    const width = stage.scrollWidth;
    const height = stage.scrollHeight;
    adjusted.current = false;
    setTransform(fitTransform(viewport.clientWidth, viewport.clientHeight, width, height));
  }, []);

  // Fit is driven by the renderer's completion, not by a source change.
  // Mermaid renders asynchronously, so the old "one rAF after source changed"
  // timing measured an empty stage and fitted to nothing. `fit` is a stable
  // useCallback, which is what keeps passing it as onRendered from looping.
  const fitWhenPainted = useCallback(() => {
    requestAnimationFrame(fit);
  }, [fit]);

  // Keep a fitted diagram centred when its viewport changes size. Skipped once
  // the reader has zoomed or panned, so a resize never yanks their view back.
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      if (!adjusted.current) fit();
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [fit]);

  // Wheel is attached NATIVELY with { passive: false }, not through React's
  // onWheel. React registers its delegated root wheel listener as passive, so
  // preventDefault() inside onWheel is silently ignored - an active diagram
  // would zoom AND let the body scroll underneath at the same time. A native
  // non-passive listener is the only place preventDefault actually bites.
  // Inactive: return without preventing default, so the wheel scrolls the body
  // between diagrams. Active: prevent default and zoom, nothing else moves.
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const onWheel = (event: WheelEvent) => {
      if (!activeRef.current) return;
      event.preventDefault();
      adjusted.current = true;
      const rect = viewport.getBoundingClientRect();
      const pointX = event.clientX - rect.left;
      const pointY = event.clientY - rect.top;
      setTransform((current) => zoomAbout(current, event.deltaY < 0 ? 1.12 : 1 / 1.12, pointX, pointY));
    };
    viewport.addEventListener("wheel", onWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", onWheel);
  }, []);

  return (
    <figure className={`diagram-view${active ? " active" : ""}`}>
      {title && <figcaption className="count">{title}</figcaption>}
      <div
        className="diagram-viewport"
        ref={viewportRef}
        onMouseDown={(event) => {
          // A press activates this diagram and, in the same gesture, arms a
          // drag - so you can click-and-drag to pan in one motion.
          onActivate();
          drag.current = { x: event.clientX, y: event.clientY };
        }}
        onMouseMove={(event) => {
          // Pan only once active: a press on an inactive diagram activates it
          // this frame, and panning waits for the next.
          if (!drag.current || !active) return;
          const dx = event.clientX - drag.current.x;
          const dy = event.clientY - drag.current.y;
          drag.current = { x: event.clientX, y: event.clientY };
          adjusted.current = true;
          setTransform((current) => panBy(current, dx, dy));
        }}
        onMouseUp={() => {
          drag.current = null;
        }}
        onMouseLeave={() => {
          drag.current = null;
        }}
      >
        <div
          className="diagram-stage"
          ref={stageRef}
          style={{
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            transformOrigin: "0 0",
          }}
        >
          <DiagramView source={source} look={look} theme={theme} onRendered={fitWhenPainted} />
        </div>
        {!active && <div className="diagram-hint" aria-hidden="true">Click to zoom</div>}
      </div>
      <div className="diagram-zoom-bar">
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => { adjusted.current = true; setTransform((c) => zoomAbout(c, 1 / 1.25, 0, 0)); }}
        >
          −
        </button>
        <button type="button" aria-label="Reset zoom" onClick={fit}>
          Fit
        </button>
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => { adjusted.current = true; setTransform((c) => zoomAbout(c, 1.25, 0, 0)); }}
        >
          +
        </button>
      </div>
    </figure>
  );
}
