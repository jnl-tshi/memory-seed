import assert from "node:assert/strict";
import { test } from "node:test";

import type { AdrRecord, TrailEvent } from "./api.ts";
import { adrAuthority, adrEvents, filterAdrs, rejectedDecisions, resetAdrScope, resolveAdrDecisionNavigation } from "./adrWorkspaceModel.ts";

function row(overrides: Partial<TrailEvent>): TrailEvent {
  return {
    id: "mse_source#decisions/d2-cache-format", chunk_id: "mse_source#decisions/d2-cache-format", entry_id: "mse_source",
    title: "D2 - Choose the cache format", date: "2026-08-03", datetime: "2026-08-03T10:00:00Z", branch: null,
    branch_inferred: false, agent: "codex", topics: [], granularity: "decision", continuity: [], connectivity: 0,
    importance_score: 0, provenance_class: "authored_memory", has_diagram: false, decision_ordinal: "d2", decision_count: 2,
    ...overrides,
  } as TrailEvent;
}

function record(overrides: Partial<AdrRecord> = {}): AdrRecord {
  return {
    adr_id: "adr_cache_format", title: "Cache format", topics: ["cache"], created_at: "2026-08-03T10:00:00Z",
    source: "write-time", current_status: "accepted", authoritative_decision: "mse_source:d2", pending_decisions: ["mse_pending:d1"],
    rejected_decisions: ["mse_rejected:d1"], superseded_by: null, membership: [], digest: "digest", path: null,
    current: { decision_ref: "mse_source:d2", decision: "Use a typed cache format.", reason: "Stable clients.", impact: "Initial decision.", why: "Stable clients.", evolution: "Initial decision." },
    events: [
      { kind: "revision-proposed", event_id: "proposed", timestamp: "2026-08-03T10:00:00Z", source: "write-time", decision: "Use a typed cache format.", why: "Stable clients.", evolution: "Initial decision.", reason: "", predecessors: [{ decision: "mse_old:d1", relation_assertion: "link:mse_source:d2:evolves:mse_old:d1" }, { decision: "mse_other:d1", relation_assertion: "link:mse_source:d2:evolves:mse_other:d1" }] },
      { kind: "reviewed-no-change", event_id: "unchanged", timestamp: "2026-08-04T10:00:00Z", source: "write-time", decision: "", why: "", evolution: "", reason: "Still valid." },
      { kind: "revision-rejected", event_id: "rejected", timestamp: "2026-08-05T10:00:00Z", source: "write-time", decision: "", why: "", evolution: "", reason: "Rejected." },
    ],
    source_excerpts: {},
    ...overrides,
  } as AdrRecord;
}

test("ADR source navigation uses the exact Trail decision row identity and heading", () => {
  const navigation = resolveAdrDecisionNavigation("mse_source:d2", [row({ title: "D2 - Choose the cache format" })]);
  assert.deepEqual(navigation, {
    entryId: "mse_source",
    chunkId: "mse_source#decisions/d2-cache-format",
    heading: "D2 - Choose the cache format",
  });
  assert.equal(resolveAdrDecisionNavigation("mse_source:d3", [row({})]), null);
});

test("a singular D1 ADR resolves to its entry-row Trail identity and Decision heading", () => {
  const navigation = resolveAdrDecisionNavigation("mse_source:d1", [row({
    id: "mse_source", chunk_id: "mse_source", title: "2026-08-03 10:00 - Choose the cache format",
    granularity: "entry", decision_ordinal: null, decision_count: 1,
  })]);
  assert.deepEqual(navigation, { entryId: "mse_source", chunkId: "mse_source", heading: "Decision" });
  assert.equal(resolveAdrDecisionNavigation("mse_source:d1", [row({ decision_ordinal: null, decision_count: 2 })]), null);
});

test("a superseded ADR retires its accepted head and names the replacement", () => {
  assert.deepEqual(adrAuthority(record({ current_status: "superseded", superseded_by: "adr_trace_cache" })), {
    label: "Last accepted / retired", decisionRef: "mse_source:d2", replacementAdr: "adr_trace_cache",
  });
});

test("ADR presentation retains branching predecessors, no-change, pending, and rejected states", () => {
  const item = record();
  const events = adrEvents(item);
  assert.equal(events[0].predecessors?.length, 2);
  assert.equal(events.find((event) => event.kind === "reviewed-no-change")?.reason, "Still valid.");
  assert.deepEqual(item.pending_decisions, ["mse_pending:d1"]);
  assert.deepEqual(rejectedDecisions(item), ["mse_rejected:d1"]);
});

test("ADR search returns no results without discarding the indexed records", () => {
  const records = [record()];
  assert.deepEqual(filterAdrs(records, "does not exist"), []);
  assert.equal(records.length, 1);
});

test("switching worktrees clears stale ADR selection, detail, and error state", () => {
  assert.deepEqual(resetAdrScope(), { records: [], selectedId: null, selected: null, error: null });
});
