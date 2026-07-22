import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_GRAPH_EDGE_TYPES, GRAPH_EDGE_TYPES } from "./api.ts";

// The split exists because one constant was doing two jobs: which chips the
// filter row offers, and which are switched on. Collapsing them again would
// silently either restore topic as a default or delete its chip entirely.

test("topic is offered as a chip", () => {
  assert.ok(GRAPH_EDGE_TYPES.includes("topic"), "the topic filter must remain available");
});

test("topic is NOT on by default", () => {
  // A topic edge joins the consecutive entries carrying a tag, so it asserts
  // sort-order adjacency rather than a relationship - and node colour already
  // carries topic membership since communities are named after topics.
  assert.ok(!DEFAULT_GRAPH_EDGE_TYPES.includes("topic"));
});

test("every authored relationship type is on by default", () => {
  for (const authored of ["related", "supersedes", "evolves"] as const) {
    assert.ok(DEFAULT_GRAPH_EDGE_TYPES.includes(authored), `${authored} must default to on`);
  }
});

test("the defaults are a subset of what the row can offer", () => {
  // Otherwise a type could be enabled with no chip to turn it back off.
  for (const edgeType of DEFAULT_GRAPH_EDGE_TYPES) {
    assert.ok(GRAPH_EDGE_TYPES.includes(edgeType), `${edgeType} is on by default but has no chip`);
  }
});
