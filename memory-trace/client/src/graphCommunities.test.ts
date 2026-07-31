import assert from "node:assert/strict";
import test from "node:test";

import { minimumSeparation, oklabDistance } from "./colour.ts";
import {
  authoredNodeColour,
  colourForCommunity,
  colourForSlot,
  COMMUNITY_COLOURS,
  communityColourScale,
  communityLegend,
  hasAuthoredCommunity,
  MINIMUM_COLOUR_SEPARATION,
  topicColourScale,
  UNASSIGNED_COLOUR,
  wearsAuthoredRim,
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

test("a topicless linked node stays neutral", () => {
  const topicless = {
    ...node("plain", null),
    // The relationship is intentionally present but cannot become a topic
    // channel. GraphWorkspace passes only this authored source to colouring.
    source: { topics: [], decision_topics: {}, links: ["g1"] },
  } as never;
  assert.equal(authoredNodeColour(topicless, CORPUS_TOPICS), null);
  assert.equal(communityColourScale(CORPUS_TOPICS)(topicless), UNASSIGNED_COLOUR);
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

test("decision-only topics author a parent's display colour without changing entry topics", () => {
  const decisionOnly = {
    ...node("a", "graph"),
    source: { topics: [], decision_topics: { d1: ["graph"], d2: ["memory-trace", "graph"] } },
  } as never;
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);
  const colour = authoredNodeColour(decisionOnly, CORPUS_TOPICS, WHEEL);
  const deDuplicated = authoredNodeColour(
    { ...node("b", "graph"), source: { topics: ["graph", "memory-trace"], decision_topics: {} } } as never,
    CORPUS_TOPICS,
    WHEEL,
  );
  assert.ok(colour, "decision topics make the parent authored rather than unassigned");
  assert.notEqual(colour, bySlug("graph"), "the de-duplicated union includes memory-trace too");
  assert.equal(colour, deDuplicated, "repeated decision topics do not add colour weight");
});

test("authored decision rows retain only their own ordinal topics", () => {
  const parent = {
    ...node("parent", "graph"),
    source: { topics: [], decision_topics: { d1: ["graph"], d2: ["memory-trace"] } },
  } as never;
  const d1 = { ...node("parent:d1", "graph"), source: { topics: [], decision_topics: { d1: ["graph"] } } } as never;
  const d2 = { ...node("parent:d2", "memory-trace"), source: { topics: [], decision_topics: { d2: ["memory-trace"] } } } as never;
  const bySlug = topicColourScale(CORPUS_TOPICS, WHEEL);

  assert.ok(authoredNodeColour(parent, CORPUS_TOPICS, WHEEL), "the union colours the parent for display");
  assert.equal(authoredNodeColour(d1, CORPUS_TOPICS, WHEEL), bySlug("graph"));
  assert.equal(authoredNodeColour(d2, CORPUS_TOPICS, WHEEL), bySlug("memory-trace"));
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

// --- Colour reads the ROOT, grouping reads the child ---
//
// Measured on the real corpus when this landed: 54 canonical slugs, 23 of them
// roots, but only 17 slugs clear the community floor and all 17 are ALREADY
// roots - so the palette is 17 slots before and after. This is not a count
// reduction. What these tests pin is the property that survives corpus growth:
// the slot table is ordered, so a child crossing the floor must not be able to
// insert into it and repaint communities that did not change.

// `merge` and `branch-history` are children of `git-workflow`; `trail` is a
// child of `memory-trace`; `memory-trace-ui` is a genuine spelling alias.
const ROOTS: Record<string, string> = {
  "git-workflow": "git-workflow", merge: "git-workflow", "branch-history": "git-workflow",
  "memory-trace": "memory-trace", trail: "memory-trace", "memory-trace-ui": "memory-trace",
  graph: "graph", "ui-design": "ui-design", documentation: "documentation",
};

test("a child takes its root's colour", () => {
  const bySlug = topicColourScale(CORPUS_TOPICS, null, ROOTS);
  assert.equal(bySlug("merge"), bySlug("git-workflow"));
  assert.equal(bySlug("trail"), bySlug("memory-trace"));
});

// --- focus: root colour splits the corpus, child colour splits one family ---
// The real corpus counts for the children of `git-workflow`. Both are far below
// the community floor of 10, which is the whole difficulty.
const FOCUS_TOPICS: Record<string, number> = { ...CORPUS_TOPICS, merge: 5, "branch-history": 3 };

test("focused on a root, its children take DISTINCT colours", () => {
  // JNL, 2026-07-27. Root colour is what makes the whole map splittable; once
  // the view IS one root, the family has stopped being information and the
  // children become it.
  const focused = topicColourScale(FOCUS_TOPICS, null, ROOTS, "git-workflow");
  const inside = ["git-workflow", "merge", "branch-history"].map(focused);
  assert.ok(inside.every((colour) => colour !== null), `every focused child needs a colour: ${inside}`);
  assert.equal(new Set(inside).size, inside.length, `children must differ: ${inside}`);
});

test("outside the focus, colour is unchanged", () => {
  // Caught by this test on first write: expanding the focus INTO the ordered slot
  // table shifted every slot after it and repainted communities that had not
  // changed - the exact instability that put colour on the root to begin with.
  // Focused members are appended past the root table for that reason.
  const focused = topicColourScale(FOCUS_TOPICS, null, ROOTS, "git-workflow");
  const flat = topicColourScale(FOCUS_TOPICS, null, ROOTS, null);
  for (const slug of ["memory-trace", "trail", "graph", "documentation", "ui-design"]) {
    assert.equal(focused(slug), flat(slug), `${slug} is outside the focus and must not move`);
  }
});

test("a family with only one member present derives its PARENT's colour", () => {
  // JNL, 2026-07-27: a colour is only worth spending when it separates something.
  // `graph` has no authored children on this corpus, so focusing it must not mint
  // a new hue - the node keeps the family colour the reader already knows.
  const focused = topicColourScale(FOCUS_TOPICS, null, ROOTS, "graph");
  const flat = topicColourScale(FOCUS_TOPICS, null, ROOTS, null);
  assert.equal(focused("graph"), flat("graph"));
  // A child with no authored siblings behaves the same way. `trail` is the only
  // memory-trace member here besides the parent... which is two, so use a family
  // that genuinely has one: documentation.
  const docs = topicColourScale({ ...CORPUS_TOPICS, readme: 3 }, null, { ...ROOTS, readme: "documentation" }, "documentation");
  const docsFlat = topicColourScale({ ...CORPUS_TOPICS, readme: 3 }, null, { ...ROOTS, readme: "documentation" }, null);
  assert.notEqual(docs("readme"), docsFlat("readme"), "two members present, so they separate");
});

test("an alias never splits from the slug it denotes, even inside the focus", () => {
  // topic_roots cannot tell an alias from a child - both map to a root - so the
  // canonical map is what stops `memory-trace-ui` drawing a second swatch for
  // `memory-trace` the moment that family is focused.
  const CANON: Record<string, string> = {
    "memory-trace": "memory-trace", trail: "trail", "memory-trace-ui": "memory-trace",
    "git-workflow": "git-workflow", merge: "merge", "branch-history": "branch-history",
  };
  const topics = { ...CORPUS_TOPICS, trail: 4, "memory-trace-ui": 2 };
  const focused = topicColourScale(topics, null, ROOTS, "memory-trace", CANON);
  assert.equal(focused("memory-trace-ui"), focused("memory-trace"), "an alias is a spelling, not a concept");
  assert.notEqual(focused("trail"), focused("memory-trace"), "a child is a concept and still separates");
});

test("the floor is waived inside the focus, or the focused view is colourless", () => {
  // merge carries 5 and branch-history 3, against a floor of 10. Applying it
  // would leave exactly the view whose purpose is to separate them with nothing
  // to separate. Outside the focus the floor still bites.
  const focused = topicColourScale(FOCUS_TOPICS, null, ROOTS, "git-workflow");
  assert.notEqual(focused("merge"), null);
  assert.notEqual(focused("branch-history"), null);
  assert.equal(focused("licensing"), null, "1 entry outside the focus stays below the floor");
});

test("focusing a CHILD expands its whole family, not just itself", () => {
  // Otherwise focusing `merge` would colour one node and flatten its siblings,
  // which is the same loss of information in a smaller frame.
  const viaChild = topicColourScale(FOCUS_TOPICS, null, ROOTS, "merge");
  const viaRoot = topicColourScale(FOCUS_TOPICS, null, ROOTS, "git-workflow");
  for (const slug of ["merge", "branch-history", "git-workflow", "memory-trace"]) {
    assert.equal(viaChild(slug), viaRoot(slug), `${slug} should key the same either way`);
  }
});

test("the legend follows the same key as the nodes when focused", () => {
  // A legend keyed on roots beside nodes keyed on children is the drift the
  // shared derivation exists to prevent.
  const nodes = [node("a", "git-workflow"), node("b", "merge"), node("c", "branch-history")];
  const legend = communityLegend(nodes, FOCUS_TOPICS, null, ROOTS, "git-workflow");
  const colourOf = communityColourScale(FOCUS_TOPICS, null, ROOTS, "git-workflow");
  for (const entry of legend) {
    const owner = nodes.find((item) => (item as unknown as { community: { id: string } }).community.id === entry.id)!;
    assert.equal(entry.colour, colourOf(owner));
  }
  assert.equal(new Set(legend.map((entry) => entry.colour)).size, 3, "three children, three swatches");
});

test("an alias takes the same colour as the slug it is a variant of", () => {
  // The corpus stores whatever spelling was authored and is never rewritten, so
  // an alias that never reaches the map is an entry that never gets a colour.
  const bySlug = topicColourScale(CORPUS_TOPICS, null, ROOTS);
  assert.equal(bySlug("memory-trace-ui"), bySlug("memory-trace"));
});

test("counts roll up to the root BEFORE the floor is applied", () => {
  // The whole point of a child being a refinement rather than an exile. `merge`
  // has 5 entries against a floor of 10 and would be colourless on its own; its
  // root `git-workflow` is one of the largest communities on the graph.
  const withChild = { ...CORPUS_TOPICS, merge: 5, "branch-history": 3 };
  const bySlug = topicColourScale(withChild, null, ROOTS);
  assert.notEqual(bySlug("merge"), null, "a rare child must not go colourless under a large parent");
  assert.equal(bySlug("merge"), bySlug("branch-history"), "siblings share the parent's colour");
});

test("a child crossing the floor does not shift any other community's colour", () => {
  // The regression this change exists for. Slots are positions in an ORDERED
  // list, so without root-keying a newly qualifying child inserts into it and
  // repaints every community after it - during exactly the topic sweep whose
  // purpose is to move entries onto children.
  const before = topicColourScale(CORPUS_TOPICS, null, ROOTS);
  const after = topicColourScale({ ...CORPUS_TOPICS, merge: 40 }, null, ROOTS);
  for (const slug of Object.keys(CORPUS_TOPICS)) {
    assert.equal(after(slug), before(slug), `${slug} was repainted by an unrelated child`);
  }
});

test("without a roots map every slug is its own root", () => {
  // The pre-hierarchy behaviour has to survive untouched: a vocabulary with no
  // parents declared, and a client whose facets have not loaded, both land here.
  const flat = topicColourScale(CORPUS_TOPICS, WHEEL);
  const identity = topicColourScale(CORPUS_TOPICS, WHEEL, {});
  for (const slug of Object.keys(CORPUS_TOPICS)) assert.equal(identity(slug), flat(slug));
});

test("a root that qualifies only by roll-up still gets a colour", () => {
  // The wheel seriates SLUGS. Keying slots by root while letting a slug-ordered
  // wheel drive them would leave a root with no wheel position colourless -
  // planting the exact bug this change exists to prevent, one sweep later, when
  // a parent's own count falls below the floor as its children absorb entries.
  const swept = { ...CORPUS_TOPICS, "git-workflow": 2, merge: 30, "branch-history": 25 };
  const bySlug = topicColourScale(swept, WHEEL, ROOTS);
  assert.notEqual(bySlug("merge"), null, "root qualifying only via roll-up must not be skipped");
  assert.equal(bySlug("merge"), bySlug("git-workflow"));
});

test("the legend and the nodes still agree once colour climbs to the root", () => {
  // The warning in the module header, re-checked at the new level: one function,
  // both consumers. A second derivation is how a legend starts quietly lying.
  const nodes = [node("a", "merge"), node("b", "git-workflow"), node("c", "graph"), node("d", null)];
  const colourOf = communityColourScale(CORPUS_TOPICS, WHEEL, ROOTS);
  for (const entry of communityLegend(nodes, CORPUS_TOPICS, WHEEL, ROOTS)) {
    const member = nodes.find((candidate) => (candidate as never as { community: { id: string } }).community.id === entry.id);
    assert.equal(entry.colour, colourOf(member!));
  }
});

test("the legend names the parent when a row borrowed its colour", () => {
  // Sibling rows share a swatch by design now. Saying whose colour it is turns
  // a repeated swatch into information rather than an apparent mix-up.
  const legend = communityLegend([node("a", "merge"), node("b", "git-workflow")], CORPUS_TOPICS, WHEEL, ROOTS);
  const child = legend.find((entry) => entry.topic === "merge")!;
  const parent = legend.find((entry) => entry.topic === "git-workflow")!;
  assert.equal(child.rootLabel, "Git Workflow");
  assert.equal(parent.rootLabel, null, "a root is not its own parent");
  assert.equal(child.colour, parent.colour, "the shared swatch is the point");
});

test("a node whose only topics are child slugs still authors a colour", () => {
  // The regression that bit this change in live verification. The renderer used
  // to reach the authored mixture only when the node's COMMUNITY qualified, and
  // grouping still applies the floor PER SLUG - so an entry tagged with nothing
  // but children is named `unassigned` by the server even though it plainly
  // authored topics. Gating the fill on the community handed those entries a
  // borrowed pastel from their neighbours instead of the root colour they had
  // earned. Measured live on mse_nyk16t2d8xexetgv, whose four topics are all
  // children of `control-plane`.
  const childOnly = {
    ...node("a", null), // community: derived:unassigned
    source: { topics: ["merge", "branch-history"] },
  } as never;
  const authored = authoredNodeColour(childOnly, CORPUS_TOPICS, WHEEL, ROOTS);
  assert.notEqual(authored, null, "child-only topics must still produce an authored colour");
  assert.notEqual(authored, UNASSIGNED_COLOUR);
  // Both children roll to one root, so the mixture is exactly that root's colour.
  assert.equal(authored, topicColourScale(CORPUS_TOPICS, WHEEL, ROOTS)("git-workflow"));
});

test("an authored node keeps its rim in the window before facets arrive", () => {
  // With no corpus counts the slot map is empty, so authoredNodeColour returns
  // null for EVERY node. Keying the rim on that alone would leave every
  // authored node rimless until the facets request lands - and rimless is the
  // graph's word for "this colour was borrowed", so the whole graph would
  // briefly disown its own topics.
  const authoredCommunity = { ...node("a", "graph"), source: { topics: ["graph"] } } as never;
  assert.equal(authoredNodeColour(authoredCommunity, null), null, "no facets means no mixture");
  assert.ok(wearsAuthoredRim(authoredCommunity, null), "an authored community earns the rim on its own");
});

test("a child-only node earns the rim its community cannot give it", () => {
  const childOnly = { ...node("a", null), source: { topics: ["merge"] } } as never;
  assert.equal(hasAuthoredCommunity(childOnly), false, "the server groups it as unassigned");
  const authored = authoredNodeColour(childOnly, CORPUS_TOPICS, WHEEL, ROOTS);
  assert.ok(wearsAuthoredRim(childOnly, authored), "but it authored a topic, so it is not inferred");
});

test("a genuinely topicless node stays rimless", () => {
  // The invariant both branches exist to protect: an inferred colour, however
  // saturated, must never wear the mark of an authored one.
  const bare = { ...node("a", null), source: { topics: [] } } as never;
  assert.equal(wearsAuthoredRim(bare, authoredNodeColour(bare, CORPUS_TOPICS, WHEEL, ROOTS)), false);
});

test("the legend still groups and reports by the CHILD slug", () => {
  // Colour climbs; nothing else does. The row is named, counted and identified
  // by the child, which is what the graph filters and reports by.
  const legend = communityLegend([node("a", "merge"), node("b", "merge"), node("c", "git-workflow")], CORPUS_TOPICS, WHEEL, ROOTS);
  assert.deepEqual(
    legend.map((entry) => [entry.topic, entry.count]),
    [["merge", 2], ["git-workflow", 1]],
  );
});
