# Reference: fffuel — SVG/CSS generators

**Disposition:** Reference-only (decided 2026-07-10). Not an active proposal. fffuel may be used as a *design aid*, but its output is **not** to be committed to this public repo as SVG image files (see license below). If a concrete need arises, hand-author equivalent assets we own outright.
**Source:** dev-tools reel triage (`docs/1_Inbox/dev-tools-reel-10of10-websites.md`); web research + user decision 2026-07-10.

## What it is
[fffuel](https://www.fffuel.co) — 20+ free browser generators for SVG and CSS: gradients, patterns, textures, blobs, AI 3D shapes, spinners, and color tools (cccolor, pppalette, hhhue). Tweak settings, copy output; no design tool needed.

## Why reference-only (the legal reason)
fffuel's [license](https://www.fffuel.co/license/):
- ✅ Free for personal **and commercial** use; **no attribution required**.
- ❌ "You cannot sublicense, resell, share, transfer, or **otherwise redistribute the Images**."

Memory Seed / Memory Trace are treated as publishable/open-source (`memory_hygiene.md`). Committing a generated **SVG file** into a public repo places the raw image where anyone can copy it — which a strict reading of the no-redistribution clause prohibits. Rather than manage that boundary (CSS-output-only was the alternative), the decision is to keep fffuel as an **inspiration source** and ship only assets we author ourselves.

## If revisited
Two paths would unblock direct use: (a) restrict strictly to **CSS-generator output** (code in `styles.css`, not "Images"), or (b) obtain written permission from fffuel to embed generated SVGs in an OSS repo. Neither is pursued now.

## Related
- Cross-reference: `docs/2_Todo/fontjoy-typography-pairing.md` (adopted from the same reel), `docs/4_Reference/21st-dev-components.md` (also reference-only).
