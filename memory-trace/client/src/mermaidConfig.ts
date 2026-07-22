// Maps Trace's own presentation settings onto Mermaid's configuration.
//
// Two bindings matter, and both are JNL's: the Settings menu's Drawn/Slick
// toggle drives Mermaid's `look`, and the light/dark theme drives the palette.
// A diagram therefore adopts the surrounding design language automatically
// rather than arriving as a stock Mermaid picture pasted into a warm UI.
//
// Colours are READ FROM CSS custom properties rather than duplicated here.
// styles.css stays the single source of truth for the palette, so a token
// retuned there moves the diagrams with it and the two can never drift.
// Mermaid only accepts hex (not `var(...)` or colour names), which is exactly
// why the values have to be resolved at call time instead of passed through.

/** Trace's stroke style setting: the Settings menu's Drawn/Slick toggle. */
export type TraceLook = "hand" | "slick";

/** Resolves a CSS custom property name (with leading `--`) to its value. */
export type PaletteReader = (token: string) => string;

/** Reads a token off the document root, where both themes define the palette. */
export const readPaletteToken: PaletteReader = (token) =>
  getComputedStyle(document.documentElement).getPropertyValue(token).trim();

// Mermaid derives a great deal from a handful of variables, so this maps the
// few that carry the design language and lets it derive the rest. `cluster*`
// is deliberately included: subgraph grouping is the capability this whole
// change exists to restore, so its container must be styled, not left default.
export function mermaidThemeVariables(read: PaletteReader): Record<string, string> {
  const token = (name: string, fallback: string) => read(name) || fallback;
  const surface = token("--chip", "#e7dec9");
  const ink = token("--text", "#383023");
  const border = token("--border-2", "#ccbd9f");
  const line = token("--muted", "#70624d");
  return {
    background: token("--panel", "#eee7d8"),
    primaryColor: surface,
    primaryTextColor: ink,
    primaryBorderColor: border,
    secondaryColor: token("--hover", "#ece4d2"),
    tertiaryColor: token("--bar", "#eae2d0"),
    lineColor: line,
    textColor: ink,
    mainBkg: surface,
    nodeBorder: border,
    clusterBkg: token("--bar", "#eae2d0"),
    clusterBorder: border,
    noteBkgColor: token("--match-bg", "#f3e8cd"),
    noteTextColor: token("--match-text", "#6b5426"),
    noteBorderColor: token("--match-border", "#c2903a"),
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
  };
}

/**
 * Full Mermaid config for one render pass.
 *
 * `theme: "base"` is the only built-in theme that honours themeVariables — the
 * named themes ignore them — so it is required for the palette binding to work
 * at all, in both light and dark. Polarity comes entirely from the tokens.
 */
export function mermaidConfig(look: TraceLook, read: PaletteReader) {
  return {
    startOnLoad: false,
    theme: "base" as const,
    themeVariables: mermaidThemeVariables(read),
    // The binding JNL asked for: Drawn diagrams in a Drawn Trail.
    look: look === "hand" ? ("handDrawn" as const) : ("classic" as const),
    // Sidecars are locally authored, but they are still file content rendered
    // as markup, and DiagramView sets innerHTML. securityLevel "strict" is what
    // pays for that: Mermaid runs labels through DOMPurify (a direct dependency
    // of the package, not an assumption) before returning the SVG.
    //
    // Measured, not assumed: `flowchart.htmlLabels: false` is NOT honoured by
    // Mermaid 11 here. Rendering a real sidecar produced one <foreignObject>
    // per node - 8 nodes, 8 foreignObjects - while `look` and the palette from
    // the same config object both took effect. Node labels are therefore HTML,
    // and sanitisation rather than markup-avoidance is the security boundary.
    // The flag is left off rather than set to a value Mermaid ignores, which
    // would read as a guarantee this code does not actually have.
    securityLevel: "strict" as const,
    flowchart: { useMaxWidth: true },
    sequence: { useMaxWidth: true },
  };
}
