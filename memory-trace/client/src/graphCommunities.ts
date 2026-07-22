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

/** Topic -> palette slot, from corpus-wide counts. */
function colourSlots(corpusTopics: Readonly<Record<string, number>> | null): Map<string, number> {
  const qualifying = Object.entries(corpusTopics ?? {})
    .filter(([, count]) => count >= COMMUNITY_TOPIC_FLOOR)
    .map(([topic]) => topic)
    .sort();
  return new Map(qualifying.map((topic, index) => [topic, index]));
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
): (node: RendererGraphNode) => string {
  const slots = colourSlots(corpusTopics);
  return (node) => {
    const fingerprint = node.community.fingerprint || node.community.id;
    if (!fingerprint.startsWith(TOPIC_PREFIX)) return UNASSIGNED_COLOUR;
    const topic = fingerprint.slice(TOPIC_PREFIX.length);
    const slot = slots.get(topic);
    return colourForSlot(slot ?? hashSlot(fingerprint));
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
};

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
): CommunityLegendEntry[] {
  const colourOf = communityColourScale(corpusTopics);
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
    groups.set(id, {
      id,
      topic,
      // The backend's label is already humanised; "No topic" is clearer to a
      // reader than the projection's internal "Unassigned".
      label: topic ? node.community.label : "No topic",
      colour: colourOf(node),
      count: 1,
    });
  }
  return [...groups.values()].sort((left, right) => {
    // Unassigned is not a community and never competes for the top of the list,
    // even when it is the largest group - which it often is.
    if (!left.topic !== !right.topic) return left.topic ? -1 : 1;
    return right.count - left.count || left.label.localeCompare(right.label);
  });
}
