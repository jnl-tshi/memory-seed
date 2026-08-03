import assert from "node:assert/strict";
import { test } from "node:test";

import { adrQuery, adrsQuery, setActiveWorktree } from "./api.ts";

test("ADR queries use their typed v1 paths and retain active worktree scope", async () => {
  const requested: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (input: string | URL) => {
    requested.push(String(input));
    return new Response(JSON.stringify({ adrs: [] }), { status: 200 });
  }) as typeof fetch;

  try {
    setActiveWorktree("C:/workspace/feature adr");
    await adrsQuery();
    await adrQuery("adr_cache/decision");

    assert.deepEqual(requested, [
      "/api/v1/adrs?worktree=C%3A%2Fworkspace%2Ffeature%20adr",
      "/api/v1/adrs/adr_cache%2Fdecision?worktree=C%3A%2Fworkspace%2Ffeature%20adr",
    ]);
  } finally {
    setActiveWorktree(null);
    globalThis.fetch = originalFetch;
  }
});
