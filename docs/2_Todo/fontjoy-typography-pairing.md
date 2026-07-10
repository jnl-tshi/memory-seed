# Fontjoy typography pairing for Memory Trace

Status: Active (approved 2026-07-10) — low priority UI polish
Priority: P-low (ride the next Memory Trace UI pass, or a small standalone change)
Source: dev-tools reel triage (`docs/1_Inbox/dev-tools-reel-10of10-websites.md`); web research + user decision 2026-07-10 (see session entry).
Scope: Choose a heading/body font pairing via [Fontjoy](https://fontjoy.com) and apply it to the Memory Trace UI by **self-hosting** the font files.
Non-goals: No runtime font-pairing feature; no dependency on Fontjoy or the Google Fonts CDN at runtime; no change to Memory Seed core.
Dependencies: none (Trace static assets only).
Acceptance criteria:
- A heading + body pairing selected and recorded.
- Font files (WOFF2) self-hosted under `memory-trace/memory_trace/static/` with each font's `OFL.txt`/`LICENSE` retained.
- `@font-face` + CSS variables wired in `memory-trace/memory_trace/static/styles.css`; no CDN call, no JS, no build step.
- Trace renders the new type offline.

## Why
Memory Trace already ships themes and accent palettes but has no deliberate type pairing. Fontjoy provides a neural-net heading/body match in one click.

## Leverage plan
1. Pick a pairing in Fontjoy; record the two Google Fonts families.
2. Download the WOFF2 files; place under Trace static assets with license files.
3. Wire `@font-face` + CSS variables in `styles.css`.

## Legal (🟢 clear)
Fontjoy only recommends fonts; the fonts are **Google Fonts** under **SIL OFL 1.1** or **Apache 2.0** — free for commercial/open-source use. Only obligation: keep each font's license file when self-hosting.

## Positioning note (decided)
**Self-host, not CDN.** Trace is a local, privacy-conscious review tool; the Google Fonts CDN transmits the viewer's IP to Google on each load (basis of a 2022 German GDPR ruling). Self-hosting keeps Trace fully local/offline and is explicitly permitted by OFL/Apache.
