import { useMemo } from "react";
import { parseDiagram } from "./arc2d";

// Renders one authored Class-2 decision-diagram sidecar block (flowchart or
// sequence-diagram subset) inline in the reader. Ported from the vanilla
// reader's renderDiagramBlock/renderFlowchart/renderSequenceDiagram
// (memory-trace/memory_trace/static/app.js) onto arc2d.ts's layout data, built
// as real SVG/JSX elements instead of an HTML string — JSX escapes node/edge
// text automatically, so there is no injection surface to manage by hand.
// Any diagram type arc2d does not handle, or any parse failure, falls back to
// the raw Mermaid source in a <pre> — never a blank frame.
export function DiagramView({ source }: { source: string }) {
  const layout = useMemo(() => parseDiagram(source), [source]);

  if (!layout) {
    return <pre className="diagram-source">{source}</pre>;
  }

  if (layout.kind === "flowchart") {
    return (
      <svg className="diagram-svg" viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" preserveAspectRatio="xMidYMid meet">
        <ArrowMarkerDefs />
        {layout.edges.map((edge, index) => (
          <g key={index}>
            <path className="diagram-edge" d={edge.path} markerEnd="url(#diagram-arrow)" />
            {edge.label && (
              <text className="diagram-edge-label" x={edge.labelX} y={edge.labelY} textAnchor="middle">
                {edge.label}
              </text>
            )}
          </g>
        ))}
        {layout.nodes.map((node) => (
          <g key={node.id} className="diagram-node" data-diagram-node={node.id}>
            <rect x={node.x} y={node.y} width={node.width} height={node.height} rx={4} />
            <text textAnchor="middle">
              {node.lines.map((line, index) => (
                <tspan
                  key={index}
                  x={node.x + node.width / 2}
                  y={node.y + node.height / 2 - ((node.lines.length - 1) * 16) / 2 + 4 + index * 16}
                >
                  {line}
                </tspan>
              ))}
            </text>
          </g>
        ))}
      </svg>
    );
  }

  return (
    <svg className="diagram-svg" viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" preserveAspectRatio="xMidYMid meet">
      <ArrowMarkerDefs />
      {layout.participants.map((participant) => (
        <g key={participant.name}>
          <g className="diagram-node">
            <rect x={participant.x - 55} y={layout.headTop} width={110} height={layout.headHeight} rx={6} />
            <text x={participant.x} y={layout.headTop + layout.headHeight / 2 + 4} textAnchor="middle">
              {participant.name}
            </text>
          </g>
          <line
            className="diagram-lifeline"
            x1={participant.x}
            y1={layout.headTop + layout.headHeight}
            x2={participant.x}
            y2={layout.lifelineBottom}
            strokeDasharray="4 4"
          />
        </g>
      ))}
      {layout.messages.map((message, index) => (
        <g key={index}>
          <line
            x1={message.x1}
            y1={message.y}
            x2={message.x2}
            y2={message.y}
            stroke="var(--edge-related)"
            strokeWidth={1.5}
            strokeDasharray={message.dashed ? "5 4" : undefined}
            markerEnd="url(#diagram-arrow)"
          />
          <text className="diagram-edge-label" x={(message.x1 + message.x2) / 2} y={message.y - 6} textAnchor="middle">
            {message.text}
          </text>
        </g>
      ))}
    </svg>
  );
}

function ArrowMarkerDefs() {
  return (
    <defs>
      <marker id="diagram-arrow" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={7} markerHeight={7} orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="var(--muted)" />
      </marker>
    </defs>
  );
}
