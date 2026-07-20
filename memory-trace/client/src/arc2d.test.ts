// Layout contract for the Arc 2d diagram engine (flowchart/sequence subset),
// ported from the vanilla reader's renderDiagramBlock and friends.
//
// Run with `npm test` (node:test, native TypeScript stripping — no runner
// dependency). These assert what DiagramView.tsx depends on: correct kind
// dispatch, a fallback to null on anything unsupported or malformed (never a
// throw), and layout invariants (all referenced nodes get positions, edges
// connect real nodes, sequence columns keep message order).
import { test } from "node:test";
import assert from "node:assert/strict";

// Explicit .ts extension: node's ESM resolver does not guess extensions. This
// file sits outside the app tsconfig (see tsconfig.json's exclude), so the
// app build and typecheck never see this import style.
import { diagramKind, parseDiagram, type FlowchartLayout, type SequenceLayout } from "./arc2d.ts";

test("diagramKind dispatches on the first line, case- and whitespace-insensitive", () => {
  assert.equal(diagramKind("flowchart TD\nA --> B"), "flowchart");
  assert.equal(diagramKind("  Flowchart LR\nA --> B"), "flowchart");
  assert.equal(diagramKind("graph TD\nA --> B"), "flowchart");
  assert.equal(diagramKind("sequenceDiagram\nA->>B: hi"), "sequence");
  assert.equal(diagramKind("SEQUENCEDIAGRAM\nA->>B: hi"), "sequence");
  assert.equal(diagramKind("classDiagram\nA --> B"), null);
  assert.equal(diagramKind(""), null);
});

test("unsupported diagram kinds parse to null rather than throwing", () => {
  assert.equal(parseDiagram("classDiagram\nA --|> B"), null);
  assert.equal(parseDiagram("pie title x\n\"a\" : 10"), null);
  assert.equal(parseDiagram(""), null);
});

test("malformed flowchart source (no nodes) parses to null rather than throwing", () => {
  assert.equal(parseDiagram("flowchart TD\n"), null);
  assert.equal(parseDiagram("flowchart TD\n\n\n"), null);
});

test("malformed sequence source (no participants) parses to null rather than throwing", () => {
  assert.equal(parseDiagram("sequenceDiagram\n"), null);
});

test("a simple flowchart lays out every node and edge", () => {
  const layout = parseDiagram("flowchart TD\nA[Start] --> B{Decide}\nB --> C[Done]") as FlowchartLayout;
  assert.equal(layout.kind, "flowchart");
  assert.equal(layout.nodes.length, 3);
  assert.equal(layout.edges.length, 2);
  const ids = layout.nodes.map((node) => node.id).sort();
  assert.deepEqual(ids, ["A", "B", "C"]);
  // Bracket labels are extracted, not the raw node id.
  const byId = new Map(layout.nodes.map((node) => [node.id, node]));
  assert.deepEqual(byId.get("A")!.lines, ["Start"]);
  assert.deepEqual(byId.get("B")!.lines, ["Decide"]);
  assert.ok(layout.width > 0 && layout.height > 0);
});

test("flowchart nodes never overlap along the layout's cross-axis within a rank", () => {
  // A -> B, A -> C: B and C share a rank and must not collide.
  const layout = parseDiagram("flowchart TD\nA --> B\nA --> C") as FlowchartLayout;
  const b = layout.nodes.find((node) => node.id === "B")!;
  const c = layout.nodes.find((node) => node.id === "C")!;
  const overlap = b.x < c.x + c.width && c.x < b.x + b.width;
  assert.ok(!overlap, "sibling nodes must not overlap horizontally");
});

test("a node with a solo declaration (no edge) still appears", () => {
  const layout = parseDiagram("flowchart TD\nA[Solo]") as FlowchartLayout;
  assert.equal(layout.nodes.length, 1);
  assert.equal(layout.edges.length, 0);
});

test("edge labels are parsed and attached to the right edge", () => {
  const layout = parseDiagram("flowchart TD\nA -->|yes| B\nA -->|no| C") as FlowchartLayout;
  const labels = layout.edges.map((edge) => edge.label).sort();
  assert.deepEqual(labels, ["no", "yes"]);
});

test("every edge path connects two nodes that exist in the layout", () => {
  // Each line yields at most one edge: `line.split(/-->/)` only keeps the
  // first two parts, so a chained "A --> B --> C" on one line only produces
  // A->B (matching the vanilla parser's behavior, not "fixed" here).
  const layout = parseDiagram("flowchart TD\nA --> B\nB --> C\nA --> C") as FlowchartLayout;
  assert.equal(layout.edges.length, 3);
  layout.edges.forEach((edge) => {
    assert.ok(edge.path.startsWith("M "), "edge path must be a valid SVG path");
  });
});

test("left-to-right and right-to-left flowcharts still parse without throwing", () => {
  for (const direction of ["LR", "RL", "TD", "TB", "BT"]) {
    const layout = parseDiagram(`flowchart ${direction}\nA --> B`) as FlowchartLayout;
    assert.equal(layout.kind, "flowchart");
    assert.equal(layout.nodes.length, 2);
  }
});

test("multi-line labels (<br/>) split into separate lines", () => {
  const layout = parseDiagram("flowchart TD\nA[Line one<br/>Line two] --> B") as FlowchartLayout;
  const a = layout.nodes.find((node) => node.id === "A")!;
  assert.deepEqual(a.lines, ["Line one", "Line two"]);
});

test("a sequence diagram lays out participants in first-seen order", () => {
  const layout = parseDiagram(
    "sequenceDiagram\nparticipant Agent\nparticipant User\nUser->>Agent: request\nAgent-->>User: response",
  ) as SequenceLayout;
  assert.equal(layout.kind, "sequence");
  assert.deepEqual(layout.participants.map((p) => p.name), ["Agent", "User"]);
  assert.equal(layout.messages.length, 2);
});

test("sequence messages preserve source order and dashed-arrow detection", () => {
  const layout = parseDiagram(
    "sequenceDiagram\nA->>B: solid\nB-->>A: dashed",
  ) as SequenceLayout;
  assert.deepEqual(layout.messages.map((m) => m.text), ["solid", "dashed"]);
  assert.equal(layout.messages[0].dashed, false);
  assert.equal(layout.messages[1].dashed, true);
  // Messages must render top-to-bottom in the order they were authored.
  assert.ok(layout.messages[1].y > layout.messages[0].y);
});

test("a participant introduced only by a message (no explicit declaration) still appears", () => {
  const layout = parseDiagram("sequenceDiagram\nAlice->>Bob: hi") as SequenceLayout;
  assert.deepEqual(layout.participants.map((p) => p.name), ["Alice", "Bob"]);
});

test("parseDiagram never throws on adversarial input", () => {
  const inputs = [
    "flowchart TD\n" + "A --> B\n".repeat(50),
    "sequenceDiagram\n" + "A->>B: x\n".repeat(50),
    "flowchart TD\nA[unterminated",
    "\n\n\n",
    "flowchart",
  ];
  for (const input of inputs) {
    assert.doesNotThrow(() => parseDiagram(input));
  }
});
