import type { RendererGraphNode } from "./api";
// Explicit .ts extension: this is a VALUE import, so node's ESM loader has to
// resolve it when the test runner loads this module directly. The type-only
// import above is erased and never resolved, which is why it needs none.
import { mixHex } from "./colour.ts";

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
    return COMMUNITY_COLOURS[(slot ?? hashSlot(fingerprint)) % COMMUNITY_COLOURS.length];
  };
}

/** Corpus-unaware colouring, used only before facets arrive. */
export const colourForCommunity = communityColourScale(null);

/** How far an inferred colour is pulled toward the background. */
export const INFERRED_FADE = 0.6;

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
 * DIRECT NEIGHBOURS ONLY, one hop, never transitively. Propagating inferred
 * colours would be label propagation - a clustering algorithm - and choosing a
 * clustering algorithm is exactly the decision that authored-topic communities
 * were adopted to avoid. An inferred colour is never itself a source.
 *
 * The fade is the honesty: it is deliberately weak enough that an inferred node
 * never reads as a full member. Ties break on community id so the result does
 * not depend on edge order.
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
  fadeToward: string,
  fade: number = INFERRED_FADE,
): Map<string, string> {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const assigned = (node: RendererGraphNode) =>
    (node.community.fingerprint || node.community.id).startsWith(TOPIC_PREFIX);

  const neighbourCommunities = new Map<string, Map<string, number>>();
  const note = (nodeId: string, neighbourId: string) => {
    const self = byId.get(nodeId);
    const neighbour = byId.get(neighbourId);
    if (!self || !neighbour || assigned(self) || !assigned(neighbour)) return;
    const tally = neighbourCommunities.get(nodeId) ?? new Map<string, number>();
    tally.set(neighbour.community.id, (tally.get(neighbour.community.id) ?? 0) + 1);
    neighbourCommunities.set(nodeId, tally);
  };
  for (const edge of edges) {
    note(edge.source, edge.target);
    note(edge.target, edge.source);
  }

  const exemplar = new Map<string, RendererGraphNode>();
  for (const node of nodes) if (assigned(node) && !exemplar.has(node.community.id)) exemplar.set(node.community.id, node);

  const inferred = new Map<string, string>();
  for (const [nodeId, tally] of neighbourCommunities) {
    const [winner] = [...tally.entries()].sort(
      (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
    );
    const source = exemplar.get(winner[0]);
    if (source) inferred.set(nodeId, mixHex(colourOf(source), fadeToward, fade));
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
