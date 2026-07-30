import assert from "node:assert/strict";
import { test } from "node:test";

import type { TrailEvent } from "./api.ts";
import { matchingTrailGroupEntries, trailRowMatches, visibleInTrailMatchMode } from "./trailSearch.ts";

function node(overrides: Partial<TrailEvent>): TrailEvent {
  return {
    id: "mse_x", chunk_id: "mse_x", entry_id: "mse_x", title: "2026-07-30 12:00 - ordinary entry",
    date: "2026-07-30", datetime: "2026-07-30T12:00:00", branch: "main", branch_inferred: false,
    agent: "codex", topics: [], granularity: "entry", continuity: [], connectivity: 0, importance_score: 0,
    provenance_class: "authored_memory", has_diagram: false, decision_ordinal: null, decision_count: 0, ...overrides,
  } as TrailEvent;
}

test("a Trail search highlights a complete decision group", () => {
  const anchor = node({ id: "mse_group", entry_id: "mse_group", decision_count: 2, title: "2026-07-30 12:00 - Reader work" });
  const d1 = node({ id: "mse_group#decisions/d1-reader", entry_id: "mse_group", decision_ordinal: "d1", title: "D1 - Ship reader" });
  const d2 = node({ id: "mse_group#decisions/d2-evidence", entry_id: "mse_group", decision_ordinal: "d2", title: "D2 - Add exact evidence return" });
  const groups = matchingTrailGroupEntries([anchor, d1, d2], "evidence");

  assert.deepEqual([...groups], ["mse_group"]);
  assert.equal(trailRowMatches(anchor, "evidence", groups), true);
  assert.equal(trailRowMatches(d1, "evidence", groups), true);
  assert.equal(trailRowMatches(d2, "evidence", groups), true);
});

test("match-only filtering retains the selected decision context", () => {
  const selected = node({ id: "mse_selected#decisions/d2", entry_id: "mse_selected", decision_ordinal: "d2" });
  const unrelated = node({ id: "mse_other", entry_id: "mse_other" });

  assert.equal(visibleInTrailMatchMode(selected, true, false, "mse_selected"), true);
  assert.equal(visibleInTrailMatchMode(unrelated, true, false, "mse_selected"), false);
  assert.equal(visibleInTrailMatchMode(unrelated, false, false, "mse_selected"), true);
});
