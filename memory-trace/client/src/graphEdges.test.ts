import assert from "node:assert/strict";
import { test } from "node:test";

import { outrankedEdgeIds, pairKey, type PresentableEdge } from "./graphEdges.ts";

const ALL = ["replaces", "evolves", "related", "topic", "branch"];
const edge = (id: string, source: string, target: string, type: string): PresentableEdge => ({ id, source, target, type });
const drawn = (edges: PresentableEdge[], visible = ALL) => {
  const out = outrankedEdgeIds(edges, visible);
  return edges.filter((e) => visible.includes(e.type) && !out.has(e.id)).map((e) => e.type);
};

test("the strongest relationship wins the pair's line", () => {
  // replaces > evolves > related > topic
  assert.deepEqual(
    drawn([edge("1", "a", "b", "topic"), edge("2", "a", "b", "related"), edge("3", "a", "b", "evolves"), edge("4", "a", "b", "replaces")]),
    ["replaces"],
  );
  assert.deepEqual(drawn([edge("1", "a", "b", "topic"), edge("2", "a", "b", "evolves")]), ["evolves"]);
  assert.deepEqual(drawn([edge("1", "a", "b", "topic"), edge("2", "a", "b", "related")]), ["related"]);
  // Declaration order must not decide it.
  assert.deepEqual(drawn([edge("1", "a", "b", "replaces"), edge("2", "a", "b", "topic")]), ["replaces"]);
});

test("direction does not create a second line", () => {
  // A->B and B->A occupy the same line, so they compete for it.
  assert.deepEqual(drawn([edge("1", "a", "b", "related"), edge("2", "b", "a", "replaces")]), ["replaces"]);
  assert.equal(pairKey("a", "b"), pairKey("b", "a"));
});

test("switching a type off promotes what it was covering", () => {
  const edges = [edge("1", "a", "b", "related"), edge("2", "a", "b", "evolves")];
  assert.deepEqual(drawn(edges), ["evolves"], "evolves outranks related");
  assert.deepEqual(
    drawn(edges, ["replaces", "related", "topic", "branch"]),
    ["related"],
    "with evolves filtered out the pair falls back to related, not blank",
  );
});

test("distinct pairs never compete, and a filtered type is not reported as outranked", () => {
  const edges = [edge("1", "a", "b", "related"), edge("2", "c", "d", "topic"), edge("3", "a", "c", "evolves")];
  assert.deepEqual(drawn(edges), ["related", "topic", "evolves"]);
  // An edge hidden by the filter row is the filter's business; reporting it
  // here too would keep it hidden after its winner was filtered away.
  const out = outrankedEdgeIds([edge("1", "a", "b", "topic")], ["related"]);
  assert.equal(out.size, 0);
});

test("an unknown edge type ranks last but is still drawn when alone", () => {
  assert.deepEqual(drawn([edge("1", "a", "b", "mystery")], ["mystery"]), ["mystery"]);
  assert.deepEqual(drawn([edge("1", "a", "b", "mystery"), edge("2", "a", "b", "topic")], ["mystery", "topic"]), ["topic"]);
});
