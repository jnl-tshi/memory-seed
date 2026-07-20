import assert from "node:assert/strict";
import test from "node:test";
import { searchResultCursor, stepSearchCursor } from "./searchNavigation.ts";

test("empty result sets have no cursor", () => {
  assert.equal(stepSearchCursor(-1, 0, 1), -1);
});

test("a fresh cursor starts at the first or last result", () => {
  assert.equal(stepSearchCursor(-1, 4, 1), 0);
  assert.equal(stepSearchCursor(-1, 4, -1), 3);
});

test("cursor steps in both directions and wraps", () => {
  assert.equal(stepSearchCursor(1, 4, 1), 2);
  assert.equal(stepSearchCursor(1, 4, -1), 0);
  assert.equal(stepSearchCursor(3, 4, 1), 0);
  assert.equal(stepSearchCursor(0, 4, -1), 3);
});

test("an invalid stale cursor restarts safely", () => {
  assert.equal(stepSearchCursor(8, 3, 1), 0);
  assert.equal(stepSearchCursor(8, 3, -1), 2);
});

test("click selection resolves its cursor without changing the result set", () => {
  const results = ["first", "second", "third"] as const;
  assert.equal(searchResultCursor(results, "second"), 1);
  assert.deepEqual(results, ["first", "second", "third"]);
});

test("a result absent from the list reports no cursor", () => {
  // Newly reachable: the cursor is now derived against the FILTERED result
  // array, so a result the filter dropped resolves to -1 rather than to a
  // position in some other list.
  assert.equal(searchResultCursor(["first", "second"], "filtered-out"), -1);
});
