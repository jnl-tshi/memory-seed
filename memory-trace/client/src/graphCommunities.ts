import type { RendererGraphNode } from "./api";
// Explicit .ts extension: this is a VALUE import, so node's ESM loader has to
// resolve it when the test runner loads this module directly. The type-only
// import above is erased and never resolved, which is why it needs none.
import { blendOklab, mixHex, pastelOf, shiftLightness } from "./colour.ts";

// Community colour, in ONE place. The legend and the graph nodes must agree, so
// they call the same function rather than each deriving a colour from the same
// fingerprint - two derivations are how a legend ends up quietly lying.

/**
 * Sixteen slots for the fifteen communities authored topics produce.
 *
 * GENERATED, not hand-picked: sixteen evenly spaced OKLCh hues at chroma 0.11,
 * lightness alternating 0.62/0.74. The previous set was assembled by adding
 * variants to a six-colour list, and it showed - its two closest colours sat
 * 0.0351 apart in OKLab, with three near-identical blues, so communities were
 * hard to tell apart even once every one had a distinct hex value. This set
 * measures 0.0831, a 2.4x improvement, pinned by a test rather than by eye.
 *
 * Chroma 0.11 is a deliberate stop short of the optimum. The search peaked at
 * 0.14 (0.0989 separation) but that reads as a saturated chart palette next to
 * a warm humanist UI; 0.11 keeps the terracotta/ochre/sage/teal/slate register
 * while still clearing the old set by a wide margin.
 *
 * Alternating lightness is what buys most of the separation: neighbouring hues
 * differ in lightness as well as hue, so adjacent slots separate on two axes.
 *
 * Both themes use one palette, so every colour has to survive both grounds -
 * measured at 1.93:1 against the light background and 4.78:1 against the dark.
 */
export const COMMUNITY_COLOURS = [
  "#be6877", "#e8907e", "#b97340", "#d1a255", "#96872d", "#9eb665",
  "#59985b", "#5bc19d", "#0a9a94", "#43bdd4", "#3590bf", "#7eadf0",
  "#797ec7", "#b89ae4", "#a76eab", "#de8eb8",
];

/** The measured floor this palette must keep clearing. */
export const MINIMUM_COLOUR_SEPARATION = 0.08;

// Nodes with no qualifying authored topic are genuinely unassigned. They take a
// neutral tone rather than a palette colour, so "no community" reads as absence
// rather than as a seventeenth category.
export const UNASSIGNED_COLOUR = "#7c8a85";

const TOPIC_PREFIX = "topic:";

/**
 * Mirrors MINIMUM_COMMUNITY_TOPIC_FREQUENCY in graph_projection.py.
 *
 * Duplicated deliberately and harmlessly: it is used ONLY to decide the order
 * colours are handed out in, so if the two ever drift the consequence is that
 * swatches shift, not that a node is mis-assigned. Community membership is
 * decided entirely server-side.
 */
export const COMMUNITY_TOPIC_FLOOR = 10;

/**
 * slug -> root of its hierarchy, as the server's `topic_roots` facet supplies
 * it. Every canonical slug and alias is a key and a root maps to itself, so an
 * absent map (or an absent key) degrades to identity: without a hierarchy every
 * slug IS its own root, which is exactly the pre-hierarchy behaviour.
 */
export type TopicRoots = Readonly<Record<string, string>>;

export function rootOf(slug: string, roots: TopicRoots | null): string {
  return roots?.[slug] ?? slug;
}

/**
 * The key a slug takes its colour from, given which topic is in FOCUS.
 *
 * With no topic filter the key is the ROOT: the whole corpus is on screen, and
 * one hue per family is what makes the map splittable at a glance.
 *
 * Filter down to a root and that same rule turns the view one flat colour -
 * every node now shares the family, so the family has stopped being information.
 * Inside the focused subtree the key becomes the node's OWN slug, so `goal`,
 * `proposal` and `roadmap` separate where they were all `proposal-lifecycle`
 * (JNL, 2026-07-27). Slugs outside the focus keep their root, because a node can
 * carry a second topic from elsewhere and that topic's family still reads.
 *
 * The focus is matched at its own root, so focusing a CHILD expands its whole
 * family rather than colouring one child and flattening its siblings.
 */
export function colourKeyOf(
  slug: string,
  roots: TopicRoots | null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): string {
  const root = rootOf(slug, roots);
  if (focus && root === rootOf(focus, roots)) {
    // The CANONICAL slug, not the authored spelling. `topic_roots` cannot tell an
    // alias from a child — both map to a root — so keying on the raw slug would
    // give `perf` its own colour beside `performance` and draw one concept as two
    // swatches. A child resolves to itself and still separates.
    return canonical?.[slug] ?? slug;
  }
  return root;
}

/**
 * Root -> palette slot.
 *
 * COLOUR IS ASSIGNED AT THE ROOT LEVEL; grouping and filtering keep reading the
 * child. The reason is not a smaller legend today - measured on this corpus the
 * palette is 17 slots either way, because the frequency floor already excludes
 * every child (each carries 1-6 entries against a floor of 10). It is that the
 * slot table is an ORDERED list, so a child crossing the floor inserts into it
 * and shifts every slot after it, repainting communities that did not change.
 * Keying by root makes child growth colour-neutral and pins the palette at the
 * root count, which is what keeps the graph stable through a topic sweep that
 * exists precisely to move entries onto children.
 *
 * Counts are ROLLED UP before the floor is applied, not merely looked up
 * through the map. A node whose only topic is a rare child (`merge`, 5 entries)
 * would otherwise still get no colour, when its root `git-workflow` is one of
 * the largest communities on the graph - the specificity the author recorded
 * would cost them their place on the map. Rolling up first is what makes the
 * child a refinement of the parent rather than an exile from it.
 *
 * When the server's `topic_wheel` is available, slot ORDER follows it: the
 * wheel is a circular seriation of topic CO-OCCURRENCE, and the base palette is
 * a hue circle, so wheel-adjacent topics land on adjacent hues. That is what
 * makes communities read as colour NEIGHBOURHOODS (memory-trace sits beside
 * ui-design, which co-occurs with it on 82 entries, instead of a third of the
 * wheel away by spelling) - and what lets a multi-topic node's mixed colour
 * stay in-family rather than cancelling toward mud.
 *
 * The wheel seriates SLUGS, so it is mapped to roots and de-duplicated rather
 * than read directly. Any root that qualifies only via roll-up has no wheel
 * position at all and is appended alphabetically. Today that tail is empty (all
 * 17 qualifying roots clear the floor on their own counts); it stops being
 * empty the moment a sweep moves entries off a parent onto its children, which
 * is the case this whole change exists to survive. Slots and wheel therefore
 * agree on their unit - both roots - instead of a root-keyed table being driven
 * by a slug-ordered list, which would silently leave such a root colourless.
 *
 * Without the wheel (facets not yet loaded), alphabetical order keeps the old
 * behaviour as a stable fallback.
 */
function colourSlots(
  corpusTopics: Readonly<Record<string, number>> | null,
  wheel: readonly string[] | null,
  roots: TopicRoots | null = null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): Map<string, number> {
  // Roll corpus counts up to the root before the floor is applied, so a root
  // qualifies on the strength of its whole subtree.
  const rolled = new Map<string, number>();
  for (const [slug, count] of Object.entries(corpusTopics ?? {})) {
    const root = rootOf(slug, roots);
    rolled.set(root, (rolled.get(root) ?? 0) + count);
  }
  // Absent facets: every slug is assumed to qualify, matching the old fallback.
  const qualifies = (root: string) =>
    corpusTopics === null ? true : (rolled.get(root) ?? 0) >= COMMUNITY_TOPIC_FLOOR;

  const ordered: string[] = [];
  const seen = new Set<string>();
  const push = (key: string) => {
    if (seen.has(key)) return;
    seen.add(key);
    ordered.push(key);
  };
  if (wheel?.length) for (const topic of wheel) { const root = rootOf(topic, roots); if (qualifies(root)) push(root); }
  // Alphabetical tail: qualifying roots the wheel never mentions. This is the
  // whole fallback when there is no wheel, and the completeness guarantee when
  // there is one.
  for (const root of [...rolled.keys()].sort()) if (qualifies(root)) push(root);

  // The focused family's members are APPENDED, never interleaved. The slot table
  // is an ordered list, so inserting a child would shift every slot after it and
  // repaint communities that did not change — the precise instability that put
  // colour on the root in the first place. Appending leaves every root's slot
  // exactly where it was, so focusing repaints only inside the focus.
  //
  // And a colour is only spent when it SEPARATES something (JNL, 2026-07-27): a
  // family contributing one member has nothing to distinguish, so no key is
  // added and the member falls back to its parent's colour through the lookup in
  // `topicColourScale`. Two or more and each earns its own.
  //
  // The floor does not apply here. Every child on this corpus carries 1-6 entries
  // against a floor of 10 (`merge` 5, `goal` 6, `cli` 1), so applying it would
  // leave the one view whose purpose is to separate those children with nothing
  // to separate. The floor exists to keep long-tail topics out of the
  // corpus-wide palette; inside a single family there is no tail to exclude.
  if (focus && corpusTopics) {
    const focusRoot = rootOf(focus, roots);
    const members = new Set<string>();
    for (const slug of Object.keys(corpusTopics)) {
      if (rootOf(slug, roots) !== focusRoot) continue;
      members.add(canonical?.[slug] ?? slug);
    }
    if (members.size > 1) for (const member of [...members].sort()) push(member);
  }
  return new Map(ordered.map((key, index) => [key, index]));
}

/**
 * Colour by topic SLUG - the per-topic view the node mixture is built from.
 *
 * The slug is resolved to its root before the lookup, so `trail` and
 * `memory-trace` return the same colour while the caller keeps holding the
 * child slug for everything else it does with it.
 */
export function topicColourScale(
  corpusTopics: Readonly<Record<string, number>> | null,
  wheel: readonly string[] | null = null,
  roots: TopicRoots | null = null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): (slug: string) => string | null {
  const slots = colourSlots(corpusTopics, wheel, roots, focus, canonical);
  return (slug) => {
    // The focused key first, the ROOT as the fallback. That fallback is what
    // "derive the parent's colour" is made of: a family with only one member on
    // the map gets no key of its own, so the lookup misses and the child lands on
    // its parent's slot. No branch decides it — the absence of a slot does.
    const slot = slots.get(colourKeyOf(slug, roots, focus, canonical)) ?? slots.get(rootOf(slug, roots));
    return slot === undefined ? null : colourForSlot(slot);
  };
}

/**
 * A node's authored colour is the MIXTURE of its qualifying topics.
 *
 * Roots are deliberately NOT de-duplicated before blending, so a node tagged
 * `branch-history`, `git-workflow` and `agent-collaboration` weights
 * git-workflow 2:1 where the flat vocabulary weighted it 1:1. That is the
 * entry's own emphasis showing through - it really did say two git-workflow
 * things and one collaboration thing - rather than an artefact to correct.
 *
 * An entry tagged both `graph` and `memory-trace` is about both, and painting
 * it purely as its community-naming topic hid that. The blend is a uniform
 * OKLab mean, which only became viable with the wheel ordering: adjacent hues
 * mix to the hue between them, where the alphabetical wheel mixed unrelated
 * hues into grey. Single-topic nodes blend to exactly their community colour,
 * so the legend swatch stays a faithful key for the majority case.
 */
export function authoredNodeColour(
  node: RendererGraphNode,
  corpusTopics: Readonly<Record<string, number>> | null,
  wheel: readonly string[] | null = null,
  roots: TopicRoots | null = null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): string | null {
  const bySlug = topicColourScale(corpusTopics, wheel, roots, focus, canonical);
  const colours = (node.source?.topics ?? [])
    .map(bySlug)
    .filter((colour): colour is string => colour !== null);
  if (!colours.length) return null;
  return blendOklab(colours.map((colour) => [colour, 1] as const));
}

function hashSlot(value: string): number {
  let hash = 0;
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) | 0;
  return Math.abs(hash) % COMMUNITY_COLOURS.length;
}

/**
 * A colour function bound to the corpus, not to the current view.
 *
 * Assignment is by RANK over the topics that clear the community floor, rather
 * than by hashing the fingerprint. Hashing was subset-independent and stable,
 * but at 15 communities over 16 slots collisions are near-certain by the
 * birthday bound - and it did collide in practice: `control-plane` and
 * `documentation` both landed on #6688e8, which a legend renders as two rows
 * with identical swatches. Only topics above the floor can ever name a
 * community, and there are about as many of those as there are colours, so
 * ranking them is collision-free where hashing was not.
 *
 * The ordering comes from corpus-wide counts, so it does NOT shift as more of
 * the graph loads. It is alphabetical rather than by count so that a topic
 * merely overtaking another in volume cannot swap two colours; only a topic
 * newly crossing the floor shifts the ones after it, which is rare.
 *
 * Falls back to the old hash when facets have not loaded yet, so the graph is
 * never colourless while the shell metadata is still in flight.
 */
export function communityColourScale(
  corpusTopics: Readonly<Record<string, number>> | null,
  wheel: readonly string[] | null = null,
  roots: TopicRoots | null = null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): (node: RendererGraphNode) => string {
  const bySlug = topicColourScale(corpusTopics, wheel, roots, focus, canonical);
  return (node) => {
    const fingerprint = node.community.fingerprint || node.community.id;
    if (!fingerprint.startsWith(TOPIC_PREFIX)) return UNASSIGNED_COLOUR;
    // The community keeps naming the CHILD - that is the grouping, and it is
    // what the legend row, the filter and the inspector all report. Only the
    // colour looked up for it climbs to the root.
    return bySlug(fingerprint.slice(TOPIC_PREFIX.length)) ?? colourForSlot(hashSlot(fingerprint));
  };
}

/**
 * A distinct colour for EVERY slot, not just the first sixteen.
 *
 * Slots beyond the base palette reuse its hues at shifted perceptual
 * lightness - one round lighter, the next darker - so slot 16 is slot 0's hue
 * light, slot 32 is slot 0's hue dark, and no two slots ever share an exact
 * colour. The previous modulo wrap meant a seventeenth community silently
 * COLLIDED with the first, which is the legend-with-identical-swatches bug in
 * a new disguise, merely waiting for the corpus to grow one more topic past
 * the floor.
 *
 * Same-hue-different-lightness pairs are less separated than the measured base
 * palette, which is accepted: they only exist past sixteen communities, and a
 * legend distinguishes them by label while the swatches still differ.
 */
export function colourForSlot(slot: number): string {
  const base = COMMUNITY_COLOURS[slot % COMMUNITY_COLOURS.length];
  const round = Math.floor(slot / COMMUNITY_COLOURS.length);
  if (round === 0) return base;
  // Rounds alternate lighter/darker and step outward, so every round lands on
  // a lightness no earlier round used: +0.14, -0.14, +0.28, -0.28, ...
  const step = Math.ceil(round / 2) * 0.14;
  return shiftLightness(base, round % 2 === 1 ? step : -step);
}

/** Corpus-unaware colouring, used only before facets arrive. */
export const colourForCommunity = communityColourScale(null);

/** True when the node carries an authored topic community (not inferred, not unassigned). */
export function hasAuthoredCommunity(node: RendererGraphNode): boolean {
  return (node.community.fingerprint || node.community.id).startsWith(TOPIC_PREFIX);
}

/**
 * Whether a node wears the darkened rim that marks authored membership.
 *
 * EITHER test passing is enough, and both are needed:
 *
 * - `authored` covers the case the community cannot see. An entry tagged only
 *   with child slugs is named `unassigned` by the server, because grouping
 *   applies the floor per slug, yet it has a root colour and genuinely authored
 *   its topics.
 * - `hasAuthoredCommunity` covers the window before facets arrive. With no
 *   corpus counts the slot map is empty, so `authoredNodeColour` returns null
 *   for EVERY node and the fill falls back to the hash. Keying the rim on
 *   `authored` alone would leave every authored node rimless until the facets
 *   request lands - and rimless is the graph's word for "this colour was
 *   borrowed", so the whole graph would briefly disown its own topics.
 */
export function wearsAuthoredRim(node: RendererGraphNode, authored: string | null): boolean {
  return authored !== null || hasAuthoredCommunity(node);
}

/**
 * Border colour for a node that AUTHORED its community: a darker rim of its own
 * colour. The rim is the at-a-glance mark separating authored membership from
 * the borrowed pastels - an inferred node is rimless however strong its tint,
 * so the two can never be confused even where a five-vote tint approaches full
 * saturation.
 */
export function authoredBorderColour(nodeColour: string): string {
  return shiftLightness(nodeColour, -0.18);
}

/** Direct-neighbour evidence at which an inferred colour reaches full strength. */
export const INFERENCE_SATURATES_AT = 5;

/**
 * Ceiling on inferred strength. Deliberately below 1: an entry that borrowed
 * its colour must never render identically to one that authored a topic, no
 * matter how many neighbours agree. The remaining pastel is the tell.
 */
export const MAX_INFERRED_STRENGTH = 0.8;

/**
 * Per-hop attenuation for chains of topicless entries: a second-hop vote is
 * worth 35% of a first-hop vote, a third-hop 12%, and so on. Small enough that
 * the residual visibly dies along a chain; the hop cap makes it exactly zero.
 */
export const CHAIN_DECAY = 0.35;

/** Hops beyond which no residual colour travels at all. */
export const CHAIN_MAX_HOPS = 3;

type EdgeLike = { source: string; target: string };

/**
 * Faded colours for nodes that have no topic of their own, borrowed from the
 * communities they connect to.
 *
 * Roughly a third of nodes carry no qualifying topic and were rendered a single
 * flat neutral, which said "unclassified" but nothing about where the entry
 * sits. Its neighbours usually do say: an untagged entry linked to three
 * `graph` entries is, in every sense that matters to a reader, near the graph
 * work. Tinting it toward that community restores the context without
 * inventing membership.
 *
 * Three rules are encoded, and their order matters:
 *
 * WHICH communities - the colour is a weighted perceptual blend across every
 * community voting for the node, so an entry between two of them looks like it
 * is between them rather than confidently one of them.
 *
 * HOW MUCH evidence - strength scales with the weight of votes, so one link is
 * barely tinted and five agreeing links are nearly the full colour, capped
 * below full: an inferred node must never be mistakable for an authored one.
 *
 * HOW FAR - residual colour travels down CHAINS OF TOPICLESS ENTRIES, decaying
 * by CHAIN_DECAY per hop and stopping dead at CHAIN_MAX_HOPS. Every walk seeds
 * at a topic -> no-topic edge and moves only through topicless nodes:
 * classified entries never receive residue (they have their own colour) and
 * never relay it (their colour already speaks for them, at full strength, one
 * hop into the chain). This is deliberately NOT label propagation - nothing
 * iterates to convergence, nothing is ever assigned a membership, and the
 * bounded decay guarantees the tint dies out instead of flooding a component.
 * An earlier version forbade transitivity outright; JNL chose the bounded
 * residual instead, and the hop cap plus topicless-only corridor is what keeps
 * that choice distinct from running a clustering algorithm.
 *
 * Caveat worth knowing: unlike an authored community colour, this one CAN
 * change as more of the graph loads, because it depends on which neighbours are
 * present. That is inherent to inferring from context, and is the reason the
 * inference is shown faded rather than solid.
 */
export function inferredCommunityColours(
  nodes: readonly RendererGraphNode[],
  edges: readonly EdgeLike[],
  colourOf: (node: RendererGraphNode) => string,
  saturatesAt: number = INFERENCE_SATURATES_AT,
): Map<string, string> {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const assigned = (node: RendererGraphNode) =>
    (node.community.fingerprint || node.community.id).startsWith(TOPIC_PREFIX);

  const adjacency = new Map<string, string[]>();
  const link = (from: string, to: string) => {
    const out = adjacency.get(from) ?? [];
    out.push(to);
    adjacency.set(from, out);
  };
  for (const edge of edges) {
    link(edge.source, edge.target);
    link(edge.target, edge.source);
  }

  const exemplar = new Map<string, RendererGraphNode>();
  for (const node of nodes) if (assigned(node) && !exemplar.has(node.community.id)) exemplar.set(node.community.id, node);

  // Per topicless node: community id -> accumulated vote weight. Seeded ONLY
  // at topic -> no-topic pairings, then walked outward through topicless nodes
  // with the vote decaying per hop. Each seed's walk visits a node once (the
  // strongest, i.e. shortest, path wins) so a cycle cannot re-inflate votes.
  const votes = new Map<string, Map<string, number>>();
  const cast = (nodeId: string, communityId: string, weight: number) => {
    const tally = votes.get(nodeId) ?? new Map<string, number>();
    tally.set(communityId, (tally.get(communityId) ?? 0) + weight);
    votes.set(nodeId, tally);
  };
  for (const seed of nodes) {
    if (!assigned(seed)) continue;
    const communityId = seed.community.id;
    // Breadth-first from this classified node. Every step - including the
    // first - may only ENTER a topicless node, so the walk necessarily starts
    // at a topic -> no-topic pairing and the corridor it travels is topicless
    // by construction. Classified nodes are origins, never waypoints.
    const depth = new Map<string, number>();
    let frontier: string[] = [];
    for (const neighbour of adjacency.get(seed.id) ?? []) {
      const node = byId.get(neighbour);
      if (!node || assigned(node) || depth.has(neighbour)) continue;
      depth.set(neighbour, 1);
      frontier.push(neighbour);
    }
    while (frontier.length) {
      const next: string[] = [];
      for (const current of frontier) {
        const hops = depth.get(current)!;
        cast(current, communityId, CHAIN_DECAY ** (hops - 1));
        if (hops >= CHAIN_MAX_HOPS) continue;
        for (const neighbour of adjacency.get(current) ?? []) {
          const node = byId.get(neighbour);
          if (!node || assigned(node) || depth.has(neighbour)) continue;
          depth.set(neighbour, hops + 1);
          next.push(neighbour);
        }
      }
      frontier = next;
    }
  }

  const inferred = new Map<string, string>();
  for (const [nodeId, tally] of votes) {
    // BLEND across every community in proportion to its accumulated vote,
    // rather than letting a majority take the node outright. An entry sitting
    // between two communities genuinely sits between them, and a
    // winner-takes-all colour would assert a membership the evidence does not
    // support.
    const weighted: Array<readonly [string, number]> = [];
    let evidence = 0;
    for (const [communityId, weight] of tally) {
      const source = exemplar.get(communityId);
      if (!source) continue;
      weighted.push([colourOf(source), weight] as const);
      evidence += weight;
    }
    if (!weighted.length) continue;
    const blended = blendOklab(weighted);
    // STRENGTH scales with the accumulated evidence. A single direct
    // neighbour is a hint; five agreeing ones are close to a statement; and a
    // node three hops down a chain holds a fraction of a vote, so it renders
    // as the faint residue JNL asked for. Saturating rather than linear, so
    // one-versus-two neighbours reads clearly while ten does not run away.
    const strength = Math.min(MAX_INFERRED_STRENGTH, evidence / saturatesAt);
    inferred.set(nodeId, mixHex(pastelOf(blended), blended, strength));
  }
  return inferred;
}

export type CommunityLegendEntry = {
  id: string;
  /** The topic slug, or null for the unassigned group. */
  topic: string | null;
  label: string;
  colour: string;
  count: number;
  /**
   * The root this community's colour came from, when it is not the community's
   * own slug - otherwise null.
   *
   * Colouring at the root means two sibling communities render two rows with
   * the SAME swatch, which is the shape of the collision the rank-based scale
   * was introduced to kill (`control-plane` and `documentation` both landing on
   * #6688e8). The difference is that here it is true rather than accidental:
   * the siblings really do share a parent. Carrying the root turns the repeated
   * swatch into information the row can state - "Merge (Git Workflow)" - so the
   * legend explains the duplication instead of appearing to have lost track of
   * it. Null whenever the community is its own root, which today is every row
   * on this corpus.
   */
  rootLabel: string | null;
};

// str.title() equivalents for the acronyms the vocabulary actually contains,
// mirroring _humanise_topic in graph_projection.py. Only reached for the parent
// qualifier: every other label on the legend is humanised server-side.
const TOPIC_ACRONYMS = new Set(["adr", "api", "cli", "esr", "mcp", "pr", "ui", "yaml"]);

export function humaniseTopic(slug: string): string {
  return slug
    .replace(/_/g, "-")
    .split("-")
    .map((word) => (TOPIC_ACRONYMS.has(word) ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}

/**
 * The communities PRESENT in the current graph, largest first.
 *
 * Derived from the rendered nodes rather than from the corpus, because a legend
 * listing communities that are not on screen is noise - and at full size the
 * palette holds more communities than any one view shows.
 *
 * The unassigned group is always last and always shown when it is non-empty:
 * roughly a third of nodes carry no qualifying topic, and hiding that would
 * make the graph look more completely classified than it is.
 */
export function communityLegend(
  nodes: readonly RendererGraphNode[],
  corpusTopics: Readonly<Record<string, number>> | null = null,
  wheel: readonly string[] | null = null,
  roots: TopicRoots | null = null,
  focus: string | null = null,
  canonical: TopicRoots | null = null,
): CommunityLegendEntry[] {
  // ONE colour derivation, shared with the nodes. The legend never computes a
  // colour of its own - including now that the colour climbs to the root, which
  // is exactly the kind of second derivation that would let the two drift. The
  // focus travels with it for the same reason: a legend keyed on roots beside
  // nodes keyed on children is precisely the drift this guards against.
  const colourOf = communityColourScale(corpusTopics, wheel, roots, focus, canonical);
  const groups = new Map<string, CommunityLegendEntry>();
  for (const node of nodes) {
    const id = node.community.id;
    const existing = groups.get(id);
    if (existing) {
      existing.count += 1;
      continue;
    }
    const fingerprint = node.community.fingerprint || id;
    const topic = fingerprint.startsWith(TOPIC_PREFIX) ? fingerprint.slice(TOPIC_PREFIX.length) : null;
    const root = topic ? rootOf(topic, roots) : null;
    groups.set(id, {
      id,
      topic,
      // The backend's label is already humanised; "No topic" is clearer to a
      // reader than the projection's internal "Unassigned".
      label: topic ? node.community.label : "No topic",
      colour: colourOf(node),
      count: 1,
      rootLabel: root && root !== topic ? humaniseTopic(root) : null,
    });
  }
  return [...groups.values()].sort((left, right) => {
    // Unassigned is not a community and never competes for the top of the list,
    // even when it is the largest group - which it often is.
    if (!left.topic !== !right.topic) return left.topic ? -1 : 1;
    return right.count - left.count || left.label.localeCompare(right.label);
  });
}
