import type { RendererGraphNode } from "./api";

// Community colour, in ONE place. The legend and the graph nodes must agree, so
// they call the same function rather than each deriving a colour from the same
// fingerprint - two derivations are how a legend ends up quietly lying.

// Sixteen slots for the fifteen communities authored topics actually produce,
// so the common case is collision-free. Six were enough only while every node
// shared one community and the palette was never exercised.
export const COMMUNITY_COLOURS = [
  "#23a99a", "#6688e8", "#d99a2b", "#c76d99", "#8f76d4", "#6aa869",
  "#c9563f", "#4bb3d4", "#b8862f", "#9d6fa8", "#5f8fd6", "#4f9d78",
  "#d4785a", "#7b93e0", "#a8913a", "#8a5fa0",
];

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
