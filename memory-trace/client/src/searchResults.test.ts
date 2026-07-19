import assert from "node:assert/strict";
import test from "node:test";
import { genuineSearchResults } from "./searchResults.ts";

const hit = (id: string, score: number, terms: string[] = []) => ({ id, score, matched_terms: terms });

test("score-0 filler with no matched terms is dropped", () => {
  const results = [hit("real", 12.5, ["trail"]), hit("filler", 0), hit("also-filler", 0)];
  assert.deepEqual(genuineSearchResults(results).map((r) => r.id), ["real"]);
});

test("a semantic-only hit survives on score alone", () => {
  // matched_fields (and so matched_terms) is purely lexical, so a chunk that
  // ranked on embedding similarity carries no terms. An AND filter would
  // silently delete exactly the results semantic search exists to surface.
  assert.deepEqual(genuineSearchResults([hit("semantic", 0.42)]).map((r) => r.id), ["semantic"]);
});

test("a lexical hit survives on terms even at zero score", () => {
  assert.deepEqual(genuineSearchResults([hit("lexical", 0, ["merge"])]).map((r) => r.id), ["lexical"]);
});

test("the server's ranked order is preserved", () => {
  const results = [hit("a", 9, ["x"]), hit("b", 0), hit("c", 4, ["x"]), hit("d", 2, ["x"])];
  assert.deepEqual(genuineSearchResults(results).map((r) => r.id), ["a", "c", "d"]);
});

test("an empty result set stays empty", () => {
  assert.deepEqual(genuineSearchResults([]), []);
});

test("the input array is not mutated", () => {
  const results = [hit("real", 3, ["x"]), hit("filler", 0)];
  genuineSearchResults(results);
  assert.equal(results.length, 2, "filtering must return a new array, not splice the source");
});
