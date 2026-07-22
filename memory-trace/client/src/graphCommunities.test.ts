import assert from "node:assert/strict";
import test from "node:test";

import { minimumSeparation, oklabDistance } from "./colour.ts";
import {
  COMMUNITY_COLOURS,
  colourForCommunity,
  communityColourScale,
  communityLegend,
  inferredCommunityColours,
  MINIMUM_COLOUR_SEPARATION,
  UNASSIGNED_COLOUR,
} from "./graphCommunities.ts";

// The fifteen communities the real corpus produces, with their measured counts.
const CORPUS_TOPICS: Record<string, number> = {
  "memory-trace": 165, "ui-design": 80, "memory-seed": 66, graph: 62, "git-workflow": 57,
  documentation: 55, "proposal-lifecycle": 54, "session-logging": 40, bugfix: 25,
  "agent-collaboration": 21, "control-plane": 19, release: 17, "mcp-tools": 15,
  retrieval: 14, "session-fuse": 12,
  // Below the floor: cannot name a community, must not consume a colour slot.
  mermaid: 8, licensing: 1,
};

const node = (id: string, topic: string | null) =>
  ({
    id,
    community: topic
      ? { id: `community:topic:${topic}`, label: topic.replace("-", " "), fingerprint: `topic:${topic}` }
      : { id: "community:unassigned", label: "Unassigned", fingerprint: "derived:unassigned" },
  }) as never;

test("the legend counts each community present", () => {
  const legend = communityLegend([node("a", "graph"), node("b", "graph"), node("c", "ui-design")]);
  assert.deepEqual(
    legend.map((entry) => [entry.topic, entry.count]),
    [["graph", 2], ["ui-design", 1]],
  );
});

test("larger communities come first", () => {
  const legend = communityLegend([node("a", "graph"), node("b", "ui-design"), node("c", "ui-design")]);
  assert.deepEqual(legend.map((entry) => entry.topic), ["ui-design", "graph"]);
});

test("unassigned is always last, even when it is the largest group", () => {
  // It usually IS the largest - roughly a third of nodes carry no qualifying
  // topic - and sorting purely by size would put "No topic" at the top of a
  // legend of topics.
  const legend = communityLegend([node("a", null), node("b", null), node("c", null), node("d", "graph")]);
  assert.deepEqual(legend.map((entry) => entry.label), ["graph", "No topic"]);
});

test("the unassigned group is labelled as an absence, not as a community", () => {
  const [entry] = communityLegend([node("a", null)]);
  assert.equal(entry.label, "No topic");
  assert.equal(entry.topic, null);
  assert.equal(entry.colour, UNASSIGNED_COLOUR);
});

test("legend swatches match the colour the nodes are painted", () => {
  // The reason both live in one module. If the legend derived its own colour,
  // this is the test that would fail when the two drifted.
  const nodes = [node("a", "graph"), node("b", "ui-design"), node("c", null)];
  for (const entry of communityLegend(nodes)) {
    const member = nodes.find((candidate) => (candidate as never as { community: { id: string } }).community.id === entry.id);
    assert.equal(entry.colour, colourForCommunity(member!));
  }
});

test("an empty graph produces no legend rather than an empty box", () => {
  assert.deepEqual(communityLegend([]), []);
});

test("every real community gets its own colour", () => {
  // The regression this scale exists for. Hashing collided on the live corpus -
  // control-plane and documentation both landed on #6688e8 - which a legend
  // renders as two rows with identical swatches.
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const qualifying = Object.entries(CORPUS_TOPICS).filter(([, count]) => count >= 10).map(([topic]) => topic);
  const colours = qualifying.map((topic) => colourOf(node(topic, topic)));
  assert.equal(new Set(colours).size, qualifying.length, "two communities share a colour");
});

test("control-plane and documentation are distinguishable", () => {
  const colourOf = communityColourScale(CORPUS_TOPICS);
  assert.notEqual(colourOf(node("a", "control-plane")), colourOf(node("b", "documentation")));
});

test("a topic below the floor never consumes a colour slot", () => {
  // Slots are scarce; spending one on a topic that can never name a community
  // is what would push the real communities back into collisions.
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const documentation = colourOf(node("a", "documentation"));
  const withoutRareTopics = communityColourScale(
    Object.fromEntries(Object.entries(CORPUS_TOPICS).filter(([, count]) => count >= 10)),
  );
  assert.equal(documentation, withoutRareTopics(node("a", "documentation")));
});

test("a colour does not change as more of the graph loads", () => {
  // The scale is bound to corpus counts, so a partial view colours identically.
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const partial = communityLegend([node("a", "graph")], CORPUS_TOPICS);
  const full = communityLegend([node("a", "graph"), node("b", "release"), node("c", null)], CORPUS_TOPICS);
  assert.equal(partial[0].colour, full[0].colour);
  assert.equal(partial[0].colour, colourOf(node("a", "graph")));
});

test("the palette clears the measured separation floor", () => {
  // The regression guard for the retune. The previous palette measured 0.0351
  // - three near-identical blues and two ochres - so communities were hard to
  // tell apart even after every one had its own hex value. Adding a colour by
  // eye to this list will trip this.
  const separation = minimumSeparation(COMMUNITY_COLOURS);
  assert.ok(
    separation >= MINIMUM_COLOUR_SEPARATION,
    `closest pair is ${separation.toFixed(4)}, below the ${MINIMUM_COLOUR_SEPARATION} floor`,
  );
});

test("every palette colour is distinct", () => {
  assert.equal(new Set(COMMUNITY_COLOURS).size, COMMUNITY_COLOURS.length);
});

// --- Inferred colour for entries with no topic ---

const edge = (source: string, target: string) => ({ source, target });

test("a topicless node borrows from the community it connects to", () => {
  const nodes = [node("plain", null), node("g1", "graph")];
  const inferred = inferredCommunityColours(nodes, [edge("plain", "g1")], communityColourScale(CORPUS_TOPICS), "#0f1512");
  assert.ok(inferred.has("plain"));
  assert.ok(!inferred.has("g1"), "a node with its own topic is never overridden");
});

test("the borrowed colour is faded, not the community colour itself", () => {
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const nodes = [node("plain", null), node("g1", "graph")];
  const inferred = inferredCommunityColours(nodes, [edge("plain", "g1")], colourOf, "#0f1512");
  const full = colourOf(node("g1", "graph"));
  assert.notEqual(inferred.get("plain"), full);
  // Faded toward the background, so it must sit closer to it than the full one.
  assert.ok(oklabDistance(inferred.get("plain")!, "#0f1512") < oklabDistance(full, "#0f1512"));
});

test("the majority neighbouring community wins", () => {
  const nodes = [node("plain", null), node("g1", "graph"), node("g2", "graph"), node("r1", "release")];
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const inferred = inferredCommunityColours(
    nodes,
    [edge("plain", "g1"), edge("plain", "g2"), edge("plain", "r1")],
    colourOf,
    "#0f1512",
  );
  const viaGraph = inferredCommunityColours([node("p2", null), node("g1", "graph")], [edge("p2", "g1")], colourOf, "#0f1512");
  assert.equal(inferred.get("plain"), viaGraph.get("p2"));
});

test("ties do not depend on edge order", () => {
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const nodes = [node("plain", null), node("g1", "graph"), node("r1", "release")];
  const forward = inferredCommunityColours(nodes, [edge("plain", "g1"), edge("plain", "r1")], colourOf, "#0f1512");
  const backward = inferredCommunityColours(nodes, [edge("plain", "r1"), edge("plain", "g1")], colourOf, "#0f1512");
  assert.equal(forward.get("plain"), backward.get("plain"));
});

test("inference never propagates through another inferred node", () => {
  // One hop only. Propagating would make this label propagation - a clustering
  // algorithm - which is the decision authored-topic communities avoid making.
  const nodes = [node("a", null), node("b", null), node("g1", "graph")];
  const inferred = inferredCommunityColours(
    nodes,
    [edge("a", "g1"), edge("a", "b")],
    communityColourScale(CORPUS_TOPICS),
    "#0f1512",
  );
  assert.ok(inferred.has("a"), "a touches a real community");
  assert.ok(!inferred.has("b"), "b only touches an inferred node and must stay neutral");
});

test("a topicless node with no classified neighbour stays neutral", () => {
  const nodes = [node("a", null), node("b", null)];
  const inferred = inferredCommunityColours(nodes, [edge("a", "b")], communityColourScale(CORPUS_TOPICS), "#0f1512");
  assert.equal(inferred.size, 0);
});

test("the fade follows the theme background", () => {
  const colourOf = communityColourScale(CORPUS_TOPICS);
  const nodes = [node("plain", null), node("g1", "graph")];
  const onDark = inferredCommunityColours(nodes, [edge("plain", "g1")], colourOf, "#0f1512").get("plain");
  const onLight = inferredCommunityColours(nodes, [edge("plain", "g1")], colourOf, "#f5f0e6").get("plain");
  assert.notEqual(onDark, onLight);
});

test("colouring still works before facets have loaded", () => {
  // Falls back to the hash rather than rendering an uncoloured graph.
  const colour = colourForCommunity(node("a", "graph"));
  assert.ok(COMMUNITY_COLOURS.includes(colour));
});

test("ties break by label so the order is stable across renders", () => {
  const first = communityLegend([node("a", "graph"), node("b", "ui-design")]);
  const second = communityLegend([node("b", "ui-design"), node("a", "graph")]);
  assert.deepEqual(first.map((entry) => entry.topic), second.map((entry) => entry.topic));
});
