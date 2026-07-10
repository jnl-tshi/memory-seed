# Inbox: dev-tools reel — "10/10 websites every week"

**Source:** Instagram Reel screen-recording (`20260709_093402000_iOS.MP4`, 44 s, creator @kiksugc), captured 2026-07-09. Transcribed and reviewed 2026-07-10; the source video was replaced by this note.
**Status:** unassessed incoming material for triage (see `proposal_lifecycle.md`). These are external tools featured in the reel, not yet decisions for this project. The "Relevance" notes are a first-pass filter, not commitments.

## Items proposed (5 tools)

### 1. 21st.dev — copy-paste UI component library
- **URL:** https://21st.dev
- **From the video:** "A community library of copy-paste UI components made by developers who actually ship products. Search what you need, copy the code, drop it in. Nothing to configure."
- **Relevance to this project:** Possibly useful for **Memory Trace** UI (the standalone review UI). Components are the kind of ready-made building blocks that could speed up the Trace web stack. Evaluate license/attribution before pulling any component into a distributed package.

### 2. 10x — one sentence → finished iOS app
- **URL:** 10x.app (per on-screen label; confirm)
- **From the video:** "Turns one sentence into a finished iOS submission. Native SwiftUI code, App Store screenshots, and the metadata to ship. You just describe the idea and it does the rest."
- **Relevance to this project:** **Low.** Memory Seed is a Python CLI/MCP + a web review UI, not an iOS app. Noted as a notable AI app-builder, but no obvious fit unless a future mobile companion is ever considered.

### 3. fffuel — free SVG & CSS generators
- **URL:** https://fffuel.co
- **From the video (called "Fuel"):** "20+ free SVG and CSS generators in one place. Tweak the settings, copy the code, no design tool needed." (gradients, patterns, textures, blobs, 3D shapes, spinners, color tools — cccolor/pppalette/hhhue/ssshape/etc.)
- **Relevance to this project:** **Medium.** Directly useful for **Memory Trace** UI polish and for the `frontend-design` work — backgrounds, accent palettes (Trace already exposes accent palettes), and lightweight SVG assets without a design tool. Output is copy-paste SVG/CSS, so no runtime dependency.

### 4. Rive — state-driven interactive animations
- **URL:** https://rive.app
- **From the video:** "Build animations that respond to state — not a static loop, but something that reacts on hover, click, or load. Export the file, add the Rive player, and your UI starts moving like a native app."
- **Relevance to this project:** **Low–medium.** Could add interactive motion to the **Memory Trace** UI or to the `demo/` (HyperFrames) marketing video, but it introduces a runtime player dependency — weigh against Trace's "markdown files are the source of truth, keep the stack lean" posture before adopting.

### 5. Fontjoy — neural-net font pairing
- **URL:** https://fontjoy.com
- **From the video (called "Font Joy"):** "Uses a neural network to generate font pairings. Pick your base font and it finds the heading and body combination that actually works with it. Copy the Google Fonts import link and you're all done."
- **Relevance to this project:** **Medium.** A quick way to pick heading/body pairings for **Memory Trace** typography and any `frontend-design` work. Outputs a Google Fonts import link (zero build cost).

## Triage suggestion

If any are worth pursuing, the two with the clearest fit for the existing **Memory Trace** UI / `frontend-design` surface are **fffuel** (SVG/CSS assets, palettes) and **Fontjoy** (typography pairing) — both are copy-paste with no runtime dependency. 21st.dev and Rive are heavier commitments (component provenance / a runtime player). 10x is out of scope for a Python/web project. Promote to `docs/2_Todo/` only if a concrete UI task motivates one.

## Triage outcome (2026-07-10)

Three items researched (legal + stack fit) and decided by the user:

- **Fontjoy → ADOPTED** (🟢 clean): `docs/2_Todo/fontjoy-typography-pairing.md` — self-host fonts.
- **fffuel → REFERENCE ONLY** (🟡 no-redistribution clause vs public repo): `docs/4_Reference/fffuel-svg-css-generators.md`.
- **21st.dev → REFERENCE ONLY** (🟢 MIT but React/Tailwind vs Trace's vanilla-JS stack): `docs/4_Reference/21st-dev-components.md`.

Still un-triaged from this reel: **10x** (idea→iOS app; likely out of scope) and **Rive** (interactive animations; possible for Trace/marketing, needs a runtime-player call). Assess if/when a concrete need arises.
