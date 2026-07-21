import { useCallback, useEffect, useRef, useState } from "react";
import { DiagramView } from "./DiagramView";
import { fitTransform, panBy, zoomAbout, type Transform } from "./diagramZoom";

// Modal decision-diagram viewer, matching the vanilla UI's behaviour: a
// diamond badge or a reader figure opens a zoomable, pannable panel. The React
// client previously rendered diagrams inline only, with an inert badge reading
// "open the entry to view" - so a diagram larger than the inspector column had
// no way to be read at all.
//
// Escape closes, a backdrop click closes, a click inside the panel does not.
export type DiagramBlock = { title?: string | null; source: string };

export function DiagramViewer({
  title,
  blocks,
  onClose,
}: {
  title: string;
  blocks: DiagramBlock[];
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    // Capture phase: the graph and Trail also bind Escape, and the topmost
    // surface should win rather than racing on bubble order.
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [onClose]);

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
        <div className="diagram-viewer-body">
          {blocks.length === 0 ? (
            <div className="empty">No diagram available for this entry.</div>
          ) : (
            blocks.map((block, index) => (
              <ZoomableDiagram key={index} title={block.title} source={block.source} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ZoomableDiagram({ title, source }: { title?: string | null; source: string }) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [transform, setTransform] = useState<Transform>({ scale: 1, x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);

  const fit = useCallback(() => {
    const viewport = viewportRef.current;
    const stage = stageRef.current;
    if (!viewport || !stage) return;
    // Measure the stage's UNSCALED size: getBoundingClientRect reflects the
    // current transform, so fitting from it would compound each time.
    const width = stage.scrollWidth;
    const height = stage.scrollHeight;
    setTransform(fitTransform(viewport.clientWidth, viewport.clientHeight, width, height));
  }, []);

  useEffect(() => {
    // One frame's delay: the SVG must be laid out before it can be measured.
    const id = requestAnimationFrame(fit);
    return () => cancelAnimationFrame(id);
  }, [fit, source]);

  return (
    <figure className="diagram-view">
      {title && <figcaption className="count">{title}</figcaption>}
      <div
        className="diagram-viewport"
        ref={viewportRef}
        onWheel={(event) => {
          event.preventDefault();
          const rect = event.currentTarget.getBoundingClientRect();
          setTransform((current) =>
            zoomAbout(
              current,
              event.deltaY < 0 ? 1.12 : 1 / 1.12,
              event.clientX - rect.left,
              event.clientY - rect.top,
            ),
          );
        }}
        onMouseDown={(event) => {
          drag.current = { x: event.clientX, y: event.clientY };
        }}
        onMouseMove={(event) => {
          if (!drag.current) return;
          const dx = event.clientX - drag.current.x;
          const dy = event.clientY - drag.current.y;
          drag.current = { x: event.clientX, y: event.clientY };
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
          <DiagramView source={source} />
        </div>
      </div>
      <div className="diagram-zoom-bar">
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => setTransform((c) => zoomAbout(c, 1 / 1.25, 0, 0))}
        >
          −
        </button>
        <button type="button" aria-label="Reset zoom" onClick={fit}>
          Fit
        </button>
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => setTransform((c) => zoomAbout(c, 1.25, 0, 0))}
        >
          +
        </button>
      </div>
    </figure>
  );
}
