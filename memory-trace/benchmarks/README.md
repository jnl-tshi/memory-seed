# Renderer Benchmark Tooling

`renderer-benchmark.js` is the source for the packaged B0a renderer-evidence harness. The committed
assets live in `../memory_trace/static/renderer-benchmark.js` and `.css`; Memory Trace serves them at
`/benchmarks/renderer` without a Node.js runtime.

The repository keeps browser-verification dependencies local and gitignored. To rebuild the packaged
assets in a developer checkout, install the pinned local tools and run the build script:

```powershell
npm install --save-dev --save-exact vis-network@10.1.0 cytoscape@3.34.0 esbuild@0.28.1
node scripts/build-renderer-benchmark.mjs
```

The harness is B0a evidence only. Do not route the shipped Graph tab through either candidate or change
the SVG fallback until the renderer selection gate is complete.
