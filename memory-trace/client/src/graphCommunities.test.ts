import assert from "node:assert/strict";
import test from "node:test";

import { hexToOklab, minimumSeparation, oklabDistance } from "./colour.ts";
import {
  authoredNodeColour,
  colourForCommunity,
  colourForSlot,
  COMMUNITY_COLOURS,
  communityColourScale,
  communityLegend,
  inferredCommunityColours,
  MINIMUM_COLOUR_SEPARATION,
  topicColourScale,
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

// --- Inferred pastel for entries with no topic ---

const edge = (source: string, target: string) => ({ source, target });
const scale = communityColourScale(CORPUS_TOPICS);

test("a topicless node takes a pastel of the community it connects to", () => {
  const inferred = inferredCommunityColours([node("plain", null), node("g1", "graph")], [edge("plain", "g1")], scale);
  assert.ok(inferred.has("plain"));
  assert.ok(!inferred.has("g1"), "a node with its own topic is never overridden");
  const full = scale(node("g1", "graph"));
  assert.notEqual(inferred.get("plain"), full, "inferred must never equal the authored colour");
  // Pastel means LIGHTER than the full colour, not blended toward a dark page.
  assert.ok(hexToOklab(inferred.get("plain")!)[0] > hexToOklab(full)[0]);
});

test("more agreeing neighbours means a stronger colour", () => {
  const one = inferredCommunityColours(
    [node("p", null), node("g1", "graph")],
    [edge("p", "g1")],
    scale,
  ).get("p")!;
  const three = inferredCommunityColours(
    [node("p", null), node("g1", "graph"), node("g2", "graph"), node("g3", "graph")],
    [edge("p", "g1"), edge("p", "g2"), edge("p", "g3")],
    scale,
  ).get("p")!;
  const full = scale(node("g1", "graph"));
  assert.ok(
    oklabDistance(three, full) < oklabDistance(one, full),
    "three agreeing neighbours must sit closer to the full colour than one",
  );
});

test("strength is capped below the authored colour even under overwhelming agreement", () => {
  const many = [node("p", null), ...Array.from({ length: 12 }, (_, i) => node(`g${i}`, "graph"))];
  const inferred = inferredCommunityColours(many, many.slice(1).map((n, i) => edge("p", `g${i}`)), scale);
  assert.notEqual(inferred.get("p"), scale(node("g0", "graph")));
});

test("mixed neighbourhoods blend rather than letting the majority take the node", () => {
  const mixed = inferredCommunityColours(
    [node("p", null), node("g1", "graph"), node("g2", "graph"), node("r1", "release")],
    [edge("p", "g1"), edge("p", "g2"), edge("p", "r1")],
    scale,
  ).get("p")!;
  const pureGraph = inferredCommunityColours(
    [node("p", null), node("g1", "graph"), node("g2", "graph"), node("g3", "graph")],
    [edge("p", "g1"), edge("p", "g2"), edge("p", "g3")],
    scale,
  ).get("p")!;
  assert.notEqual(mixed, pureGraph, "a release vote must pull the blend off the pure graph colour");
});

test("residue travels down a topicless chain and weakens with every hop", () => {
  // g1 -> a -> b -> c: a chain of topicless entries hanging off one classified
  // node. Each link should be fainter (further from the full colour) than the
  // one before it.
  const nodes = [node("g1", "graph"), node("a", null), node("b", null), node("c", null)];
  const chain = [edge("g1", "a"), edge("a", "b"), edge("b", "c")];
  const inferred = inferredCommunityColours(nodes, chain, scale);
  const full = scale(node("g1", "graph"));
  const fade = ["a", "b", "c"].map((id) => oklabDistance(inferred.get(id)!, full));
  assert.ok(fade[0] < fade[1] && fade[1] < fade[2], `residue must decay along the chain, got ${fade}`);
});

test("residue stops dead at the hop cap", () => {
  const ids = ["a", "b", "c", "d", "e"];
  const nodes = [node("g1", "graph"), ...ids.map((id) => node(id, null))];
  const chain = [edge("g1", "a"), edge("a", "b"), edge("b", "c"), edge("c", "d"), edge("d", "e")];
  const inferred = inferredCommunityColours(nodes, chain, scale);
  assert.ok(inferred.has("c"), "hop 3 is inside the cap");
  assert.ok(!inferred.has("d"), "hop 4 is beyond the cap and must stay neutral");
  assert.ok(!inferred.has("e"));
});

test("classified nodes never relay residue", () => {
  // g1 -> r1 -> b: the walk from g1 must NOT pass through classified r1, so b
  // sees only release, not graph.
  const nodes = [node("g1", "graph"), node("r1", "release"), node("b", null)];
  const inferred = inferredCommunityColours(nodes, [edge("g1", "r1"), edge("r1", "b")], scale);
  const viaRelease = inferredCommunityColours([node("r1", "release"), node("b", null)], [edge("r1", "b")], scale);
  assert.equal(inferred.get("b"), viaRelease.get("b"), "graph's colour must not leak through release");
});

test("ties do not depend on edge order", () => {
  const nodes = [node("plain", null), node("g1", "graph"), node("r1", "release")];
  const forward = inferredCommunityColours(nodes, [edge("plain", "g1"), edge("plain", "r1")], scale);
  const backward = inferredCommunityColours(nodes, [edge("plain", "r1"), edge("plain", "g1")], scale);
  assert.equal(forward.get("plain"), backward.get("plain"));
});

test("a topicless island with no classified contact stays neutral", () => {
  const inferred = inferredCommunityColours([node("a", null), node("b", null)], [edge("a", "b")], scale);
  assert.equal(inferred.size, 0);
});

// --- Wheel ordering and topic mixtures ---

const WHEEL = ["ui-design", "memory-trace", "graph", "retrieval", "documentation", "memory-seed", "release"];

test("the wheel decides hue order, not the alphabet", () => {
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);
  // memory-trace is wheel-adjacent to ui-design, so their palette slots are
  // consecutive; alphabetically they are far apart.
  assert.equal(bySlug("ui-design"), colourForSlot(0));
  assert.equal(bySlug("memory-trace"), colourForSlot(1));
  assert.equal(bySlug("graph"), colourForSlot(2));
});

test("a topic missing from the wheel is not silently given a colour", () => {
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);
  assert.equal(bySlug("licensing"), null, "below-floor topics stay colourless");
});

test("a single-topic node's mixture is exactly its community colour", () => {
  // The legend swatch stays a faithful key for the majority case.
  const single = { ...node("a", "graph"), source: { topics: ["graph"] } } as never;
  assert.equal(
    authoredNodeColour(single, CORPUS_TOPICS, WHEEL),
    topicColourScale(CORPUS_TOPICS, WHEEL)("graph"),
  );
});

test("a multi-topic node is painted the mixture, between its topics", () => {
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);
  const mixed = { ...node("a", "graph"), source: { topics: ["graph", "memory-trace"] } } as never;
  const blend = authoredNodeColour(mixed, CORPUS_TOPICS, WHEEL)!;
  const pureGraph = bySlug("graph")!;
  const pureTrace = bySlug("memory-trace")!;
  assert.notEqual(blend, pureGraph);
  assert.notEqual(blend, pureTrace);
  // Between means between: closer to each parent than the parents are to
  // each other.
  const span = oklabDistance(pureGraph, pureTrace);
  assert.ok(oklabDistance(blend, pureGraph) < span);
  assert.ok(oklabDistance(blend, pureTrace) < span);
});

test("below-floor topics do not drag the mixture", () => {
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);
  const noisy = { ...node("a", "graph"), source: { topics: ["graph", "licensing"] } } as never;
  assert.equal(authoredNodeColour(noisy, CORPUS_TOPICS, WHEEL), bySlug("graph"));
});

test("the mixture without any qualifying topic is null, never a guess", () => {
  const bare = { ...node("a", null), source: { topics: ["licensing"] } } as never;
  assert.equal(authoredNodeColour(bare, CORPUS_TOPICS, WHEEL), null);
});

test("every slot gets a unique colour, past the base palette too", () => {
  // The modulo wrap this replaces meant community 17 silently collided with
  // community 1 - the identical-swatches bug waiting for one more topic to
  // cross the floor.
  const colours = Array.from({ length: 48 }, (_, slot) => colourForSlot(slot));
  assert.equal(new Set(colours).size, colours.length);
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
