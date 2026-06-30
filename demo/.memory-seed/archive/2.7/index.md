---
memory-system-version: 2.7
tags:
  - memory-seed
  - runtime-index
  - sub-project
  - demo
  - hyperframes
---

# Demo Sub-Project Runtime Index

## Purpose

This is the agent memory runtime for the `demo/` sub-project, which contains a HyperFrames HTML-to-video composition that serves as the product demo for Memory Seed.

## Runtime Boundary

- Active runtime: `demo/.memory-seed/` (this file)
- Parent runtime: root `.memory-seed/` (one level up)
- This sub-project is not opened independently as a repository — it shares routing files with HyperFrames.

## Inheritance

- Policy: inherits parent policy (root `.memory-seed/policy.md`) unless locally overridden below.
- Active state: local only.
- Skills: parent skills inherited by default. Local skill files are for overrides or genuinely local runbooks only.

## Always Read

1. `demo/CLAUDE.md` — HyperFrames skill routing (required before editing any composition)
2. `demo/.memory-seed/agent-rules.md`
3. `demo/.memory-seed/index.md`
4. Root `.memory-seed/policy.md` (inherited)
5. `demo/.memory-seed/skills/index.md`

## Lazy Skills

Use `demo/.memory-seed/skills/index.md` as the trigger registry. Load full skill files only when the task matches:

- Root `.memory-seed/skills/local_compilation.md` — for validating the composition with `npm run check` or `npm run render`
- Root `.memory-seed/skills/release_publishing.md` — if the rendered MP4 is being published

## Active State

- Sub-project type: HyperFrames video composition (HTML/CSS/JS → MP4)
- Output: `demo/memory-seed-demo.mp4` — 30-second product demo, 1920×1080
- Entry point: `demo/index.html` — single-file composition, 5 scenes
- CLI: `npm run dev` (preview), `npm run check` (lint+validate), `npm run render` (render to MP4)
- Current status: composition written and validated (0 errors). Ready for preview and render.
- Remaining warnings: `google_fonts_import` (acceptable for network-connected render), `timeline_track_too_dense` (single-file for now, refactor into sub-compositions if scenes grow)

## Topology

- `demo/index.html` — main HyperFrames composition (5 scenes, 30 s)
- `demo/CLAUDE.md` — HyperFrames skill routing (keep; do not overwrite with memory-seed routing)
- `demo/AGENTS.md` — HyperFrames agent entry point (keep)
- `demo/package.json` — npm scripts for HyperFrames CLI
- `demo/hyperframes.json` — HyperFrames project config
- `demo/.memory-seed/` — this runtime

## Storyboard Reference

| Time | Scene | Key content |
|------|-------|-------------|
| 0–5 s | The Problem | "AI agents forget everything between sessions." |
| 5–12 s | The Solution | Memory Seed logo + `.memory-seed/` file tree |
| 12–20 s | How It Works | `memory-seed init` → bootstrap → `memory_search()` result |
| 20–27 s | Why It Works | Local-First · Any Agent · Git-Native badges |
| 27–30 s | CTA | `pip install memory-seed` · github URL |

## Design Decisions

- Single `index.html` file for the full 30-second composition (no sub-compositions yet).
- All scenes on `data-track-index="10`; background on 0–1; no scene overlap.
- GSAP `fromTo` for all animations — deterministic on seeking.
- Google Fonts (JetBrains Mono + Inter) loaded via CDN; acceptable for network-connected render.
- `-apple-system` fallback removed; replaced with `Arial, sans-serif`.

## Session Memory

- Append meaningful work notes to `demo/.memory-seed/sessions/YYYY-MM-DD.md`.
- Keep entries publishable and free of secrets.
