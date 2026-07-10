# Reference: 21st.dev — copy-paste UI components

**Disposition:** Reference / inspiration-only (decided 2026-07-10). Not an active proposal. Browse for interaction/layout ideas and hand-implement good patterns in Memory Trace's existing vanilla CSS. Revisit direct adoption only if Trace is ever re-platformed onto React/Tailwind for independent reasons.
**Source:** dev-tools reel triage (`docs/1_Inbox/dev-tools-reel-10of10-websites.md`); web research + user decision 2026-07-10.

## What it is
[21st.dev](https://21st.dev) ([serafimcloud/21st](https://github.com/serafimcloud/21st)) — a community marketplace of copy-paste UI components ("npm for design engineers"). Search, copy the code, drop it in.

## Legal (🟢 with a caveat)
Repo/platform are **MIT** ("every file is MIT-licensed and yours to keep"), free for commercial/open-source use. Caveat: it's a *community* marketplace and per-component licensing/third-party assets aren't uniformly guaranteed — verify any specific component before shipping it. (Hand-implementing the design in our own CSS avoids this entirely.)

## Why reference-only (the fit reason)
Components are **React + Tailwind CSS + Radix UI** (shadcn/ui-inspired). **Memory Trace is a hand-written vanilla-JS static app** (`memory-trace/memory_trace/static/{index.html, app.js, styles.css}` — no framework, no bundler, no Tailwind). A copied component does not drop in. Direct use would require either hand-porting to vanilla CSS (losing the React/Tailwind value) or re-platforming Trace to React (disproportionate to Trace's deliberately lean stack). So 21st.dev is kept as a **design-idea source**, not a dependency.

## If revisited
Only a decision to re-platform Memory Trace onto React/Tailwind (for independent reasons) would make direct 21st.dev adoption worthwhile.

## Related
- Cross-reference: `docs/2_Todo/fontjoy-typography-pairing.md` (adopted from the same reel), `docs/4_Reference/fffuel-svg-css-generators.md` (also reference-only).
