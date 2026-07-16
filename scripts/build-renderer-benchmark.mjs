import { build } from "esbuild";
import { readFile, writeFile } from "node:fs/promises";

// esbuild is local, gitignored browser-verification tooling; the generated
// static assets are the offline artifact packaged with Memory Trace.
await build({
  entryPoints: ["memory-trace/benchmarks/renderer-benchmark.js"],
  bundle: true,
  format: "iife",
  legalComments: "inline",
  loader: { ".json": "json" },
  minify: true,
  outfile: "memory-trace/memory_trace/static/renderer-benchmark.js",
  platform: "browser",
  target: ["es2020"],
});

const output = "memory-trace/memory_trace/static/renderer-benchmark.js";
const bundled = await readFile(output, "utf8");
await writeFile(output, bundled.replace(/[ \t]+(?=\r?\n)/g, ""), "utf8");
