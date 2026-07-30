import type { TrailEvent } from "./api.ts";
import { inDecisionGroup, stripTitleStamp } from "./trailModel.ts";

/** Match the searchable, recorded Trail fields without changing the result window. */
export function trailRowMatchesOwn(node: TrailEvent, searchTerm: string): boolean {
  return searchTerm !== "" && (
    stripTitleStamp(node.title).toLowerCase().includes(searchTerm) ||
    (node.branch || "").toLowerCase().includes(searchTerm) ||
    (node.entry_id || "").toLowerCase().includes(searchTerm)
  );
}

/** A decision group is one chronological context, so one matching child lights its siblings. */
export function matchingTrailGroupEntries(nodes: Iterable<TrailEvent>, searchTerm: string): Set<string> {
  const matched = new Set<string>();
  if (searchTerm === "") return matched;
  for (const node of nodes) {
    if (inDecisionGroup(node) && trailRowMatchesOwn(node, searchTerm) && node.entry_id) matched.add(node.entry_id);
  }
  return matched;
}

export function trailRowMatches(node: TrailEvent, searchTerm: string, matchedGroups: ReadonlySet<string>): boolean {
  return trailRowMatchesOwn(node, searchTerm) || Boolean(inDecisionGroup(node) && node.entry_id && matchedGroups.has(node.entry_id));
}

/** Match-only mode narrows presentation, never the current selected context. */
export function visibleInTrailMatchMode(
  node: TrailEvent,
  showMatchesOnly: boolean,
  matches: boolean,
  selectedEntryId: string | null,
): boolean {
  return !showMatchesOnly || matches || node.entry_id === selectedEntryId;
}
