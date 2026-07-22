import { useEffect, useRef, useState } from "react";
import { mermaidConfig, readPaletteToken, type TraceLook } from "./mermaidConfig";

// Renders one authored decision-diagram sidecar block through Mermaid itself.
//
// This replaced arc2d.ts, a hand-written renderer covering a flowchart and
// sequence-diagram subset. The deciding argument is JNL's: a sidecar is
// Markdown, and it is read in VS Code and on GitHub as well as here. Both of
// those run real Mermaid, so a diagram that is correct everywhere else must not
// fail in Trace - the sidecar is the source of truth and Trace is a projection
// over it. Reproducing all thirty Mermaid diagram types by hand was never the
// alternative; using Mermaid is.
//
// Mermaid renders asynchronously and returns SVG markup, so this sets innerHTML
// where the previous renderer built JSX elements. That gives up a property the
// old component had for free - JSX escaped label text, so there was no
// injection surface at all. It is deliberately traded, not overlooked, and paid
// for by securityLevel "strict" in mermaidConfig, which runs labels through
// DOMPurify. Note that Mermaid emits node labels as HTML inside foreignObject
// regardless of the htmlLabels flag, so sanitising is the whole boundary here -
// see the measurement recorded in mermaidConfig.ts.
//
// A parse or render failure falls back to the raw source in a <pre>, never a
// blank frame - the same guarantee the arc2d version made.
let renderSequence = 0;

export function DiagramView({
  source,
  look,
  theme,
  onRendered,
}: {
  source: string;
  look: TraceLook;
  theme: string;
  onRendered?: () => void;
}) {
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const hostRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    void (async () => {
      try {
        // Dynamic import: Mermaid is large and no view needs it until a
        // diagram is actually on screen, so it stays off the initial bundle's
        // critical path rather than taxing every startup.
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize(mermaidConfig(look, readPaletteToken));
        // Ids must be unique per render; Mermaid uses them for internal defs
        // (markers, gradients) that would otherwise collide between diagrams.
        const { svg: markup } = await mermaid.render(`trace-diagram-${++renderSequence}`, source);
        if (!cancelled) setSvg(markup);
      } catch {
        if (!cancelled) {
          setSvg(null);
          setFailed(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // `theme` is a dependency even though it is not read directly: the palette
    // is resolved from CSS custom properties at initialize time, so switching
    // light/dark must force a re-render to pick the new values up.
  }, [source, look, theme]);

  // Fires after the markup is in the DOM, so a measuring parent (the modal
  // viewer's fit-to-window) can wait for a size that actually exists.
  useEffect(() => {
    if (svg && hostRef.current) onRendered?.();
  }, [svg, onRendered]);

  if (failed) {
    return <pre className="diagram-source">{source}</pre>;
  }
  if (!svg) {
    return <div className="diagram-loading" aria-busy="true" />;
  }
  return <div className="diagram-host" ref={hostRef} dangerouslySetInnerHTML={{ __html: svg }} />;
}
