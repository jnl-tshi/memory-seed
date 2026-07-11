# Memory Trace interaction-recording harness

Records real interactions in the vanilla Memory Trace UI as video, then exports an embeddable
GIF. Complements the Phase 0 screenshot baseline
(`docs/4_Reference/memory-trace-phase0-baseline/`) with motion evidence, and doubles as the
capture tool for future parity sign-off (roadmap Phase 4: "10,000-entry target measured" /
migration parity review).

Not part of the automated test suite - `python -m unittest discover` never touches this
directory (it contains no `test*.py` files). Run it manually when a recording is wanted.

## Setup (one-time)

Playwright is already a repo-root dependency (`package.json` / `node_modules` at the repo
root - both gitignored as local browser-verification tooling, matching this project's existing
convention). From the repo root:

```powershell
npm install                       # only if node_modules/playwright is missing
npx playwright install chromium   # downloads the Chromium binary Playwright drives (one-time, ~300MB)
```

GIF export additionally requires `ffmpeg` on `PATH` (set `FFMPEG_BIN` to override the binary
name/path). Skip GIF export with `--no-gif` if ffmpeg is unavailable - the source `.webm`
is still produced.

## Usage

1. Serve a Memory Trace corpus (the real project, or a synthetic one from
   `../fixtures/generate_synthetic.py`):

   ```powershell
   $env:PYTHONPATH = "<repo-root>;<repo-root>\memory-trace"
   python -m memory_trace.cli --cwd <project-dir> --port 8791 --no-open --rebuild-cache
   ```

2. Run a scenario from this directory (or pass full paths from elsewhere):

   ```powershell
   node capture.mjs <scenario> http://127.0.0.1:8791 <out-dir>
   ```

   Produces `<out-dir>/<scenario>.webm` and `<out-dir>/<scenario>.gif`.

## Scenarios (`scenarios.mjs`)

| Name | What it shows |
|---|---|
| `trail-selection-lifecycle` | Two-stage selection: resting -> selected (saturated routes, reader opens) -> muted/pinned (second click) -> restored (third click) |
| `search-as-function` | Type a query -> ranked dropdown + in-place match markers -> Enter cycles matches -> clear |
| `graph-explore` | Switch to Graph -> hover a node (neighbourhood highlight) -> select it |

Add a scenario by exporting a new `async (page, baseUrl) => { ... }` entry in `SCENARIOS` -
`capture.mjs` requires no other changes to pick it up.

## Output conventions

Recordings are on-demand artifacts, like the synthetic datasets - not committed by default.
Point `<out-dir>` at a scratch location for a one-off look, or at a `docs/4_Reference/...`
path when a recording is deliberately being added to the baseline evidence (as the Phase 0
screenshots were).
