import type { AdrEvent, AdrRecord, TrailEvent } from "./api";

export type AdrDecisionNavigation = {
  entryId: string;
  chunkId: string;
  heading: string;
};

export function resolveAdrDecisionNavigation(
  decisionRef: string,
  rows: readonly TrailEvent[],
): AdrDecisionNavigation | null {
  const match = /^(?<entryId>[^:]+):(?<ordinal>d[1-9][0-9]*)$/i.exec(decisionRef);
  const entryId = match?.groups?.entryId;
  const ordinal = match?.groups?.ordinal?.toLowerCase();
  if (!entryId || !ordinal) return null;
  const row = rows.find((candidate) => candidate.entry_id === entryId && candidate.decision_ordinal?.toLowerCase() === ordinal);
  if (!row) return null;
  return { entryId, chunkId: row.chunk_id, heading: row.title };
}

export function filterAdrs(records: readonly AdrRecord[], query: string): AdrRecord[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [...records];
  return records.filter((record) => [
    record.adr_id,
    record.title,
    record.current.decision,
    record.current.why,
    ...(record.topics ?? []),
  ].join(" ").toLowerCase().includes(needle));
}

export type AdrAuthority = {
  label: "Authoritative" | "Last accepted / retired";
  decisionRef: string | null;
  replacementAdr: string | null;
};

export function adrAuthority(record: AdrRecord): AdrAuthority {
  if (record.current_status === "superseded") {
    return {
      label: "Last accepted / retired",
      decisionRef: record.authoritative_decision ?? null,
      replacementAdr: record.superseded_by ?? null,
    };
  }
  return { label: "Authoritative", decisionRef: record.authoritative_decision ?? null, replacementAdr: null };
}

export function adrEvents(record: AdrRecord): AdrEvent[] {
  return record.events ?? [];
}

export function rejectedDecisions(record: AdrRecord): string[] {
  return record.rejected_decisions ?? [];
}

export function resetAdrScope() {
  return { records: [] as AdrRecord[], selectedId: null as string | null, selected: null as AdrRecord | null, error: null as string | null };
}
