// Trail golden-fixture regeneration harness (cheap-tooling P8).
//
// Evaluates the REAL vanilla app.js inside a node `vm` context with a minimal
// DOM stub - enough for the module to load; boot()'s fetch never resolves so
// no rendering runs - then calls the same window.memoryTraceDebug.trailModel
// hook the browser capture procedure used, and serializes the model in the
// golden-fixture shape. No jsdom, no build step: stubs only.
//
// Usage (normally driven by regen_trail_golden.py, not by hand):
//   node regen_trail_golden.mjs <app.js path> <graph.json path> <out.json path>

import { readFileSync, writeFileSync } from "node:fs";
import vm from "node:vm";

const [appPath, graphPath, outPath] = process.argv.slice(2);
if (!appPath || !graphPath || !outPath) {
  console.error("usage: node regen_trail_golden.mjs <app.js> <graph.json> <out.json>");
  process.exit(2);
}

const noop = () => {};
const stubElement = () => ({
  innerHTML: "",
  value: "",
  style: {},
  dataset: {},
  classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
  addEventListener: noop,
  removeEventListener: noop,
  querySelector: () => null,
  querySelectorAll: () => [],
  getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
  focus: noop,
  appendChild: noop,
  setAttribute: noop,
});

const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  document: {
    getElementById: stubElement,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: stubElement,
    addEventListener: noop,
    removeEventListener: noop,
    body: stubElement(),
    documentElement: stubElement(),
  },
  localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
  fetch: () => new Promise(noop), // boot() suspends forever - model only, no app
  matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
  navigator: {},
  location: { search: "", hash: "" },
  history: { replaceState: noop, pushState: noop },
  requestAnimationFrame: (fn) => fn && undefined,
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

vm.createContext(sandbox);
vm.runInContext(readFileSync(appPath, "utf-8"), sandbox, { filename: "app.js" });

const debug = sandbox.window.memoryTraceDebug;
if (!debug || typeof debug.trailModel !== "function") {
  console.error("app.js did not expose window.memoryTraceDebug.trailModel");
  process.exit(1);
}

const graph = JSON.parse(readFileSync(graphPath, "utf-8"));
const model = debug.trailModel(graph);

const out = {
  items: model.items.map((item) =>
    item.kind === "day"
      ? { kind: "day", label: item.label }
      : { kind: "node", id: item.node.id, entry_id: item.node.entry_id, branch: item.node.branch || "" }
  ),
  laneOf: Object.fromEntries(model.laneOf),
  spans: Object.fromEntries([...model.spans].map(([k, v]) => [k, { first: v.first, last: v.last }])),
  linkRows: Object.fromEntries(
    [...model.linkRows].map(([k, v]) => {
      const row = {};
      if (v.forkRow !== undefined) row.forkRow = v.forkRow;
      if (v.mergeRow !== undefined) row.mergeRow = v.mergeRow;
      row.estimated = Boolean(v.estimated);
      return [k, row];
    })
  ),
  lifecycle: model.lifecycle,
  total: model.total,
  laneCount: model.laneCount,
};

writeFileSync(outPath, JSON.stringify(out), "utf-8");
console.log(`model serialized: ${out.items.length} items, laneCount ${out.laneCount}`);
