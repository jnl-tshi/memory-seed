---
priority: P2
next_action: JNL to rule each row; the rulings become the project's only validity ground truth.
---

# Adjudication queue — the rows two independent workers could not settle

Generated 2026-07-27 from the held-out run: **22 contested of 77**. Uncontested rows are
deliberately absent — two independent haiku workers already agree on those, so human judgement
there buys nothing. This is the whole ask, and it is bounded.

**Why these are needed:** every validity figure so far rests on a proxy. Authored tags were measured
upheld only ~50% of the time when contested; the file-derived gold set was shown unsound (a Trail
feature that also touched `models.py` was labelled `trace-api`). Rulings here are the first ground
truth the project would actually have.

**Areas:** graph · trail · trace-cache · trace-harness · inspector · diagram-view · trace-api ·
TRACE-WIDE (the app frame, no single part) · seed · NONE (roadmap, release, git housekeeping)

**Activities:** ui-design · bugfix · documentation · proposal-lifecycle · git-workflow · release ·
tooling-evaluation · agent-collaboration · performance · security (or a child of any of these)

## The topic tree, for ruling these rows

Counts are entries currently resolving to that slug. **PROPOSED** items are not in
`topics.yaml` yet — they are what these rulings help decide, so treat them as available answers.

### AREA — *which part of the system*

- `memory-trace` (203) — The companion review UI package and its views.
  - `graph` **PROPOSED** (~70) — the relationship map VIEW; moves from being a root.
    Keeps no children — its current four are edge-MODEL concepts and move to `lifecycle-edges`.
  - `trail` **PROPOSED** (~32) — the chronological timeline view
  - `trace-cache` **PROPOSED** (~12) — startup, caching, freshness, worktree switching
  - `trace-harness` **PROPOSED** (~8) — Storybook, Playwright, e2e, a11y gates, CI wiring
- `memory-seed` (121) — RESIDUAL area - use ONLY when no narrower area applies, and never alon
  - `lifecycle-edges` **PROPOSED** (~45) — the edge MODEL: evolves/evolved_by, continuity, supersession
    - `continuity` (1)  *(moves from `graph`)*
    - `related-entries` (1)  *(moves from `graph`)*
    - `schema` (1)  *(moves from `graph`)*
    - `supersession` (1)  *(moves from `graph`)*
- `session-logging` (51) — Entry authoring, DRAFT discipline, harvest, and append-only chronology
  - `backfill` (2) — Recording work into the log after the fact.
  - `decision-harvest` (1) — Harvesting decisions out of a session into logged entries.
- `control-plane` (31) — Agent rules, skills governance, and reusable runtime files.
  - `agent-rules` (1) — The agent-rules runtime file and the policy it carries.
  - `governance-profile` (2) — Profile-keyed governance of shipped control-plane content.
  - `lazy-loading` (1) — Progressive disclosure of control-plane content so agents load only wh
  - `skill-architecture` (2) — How skills are structured, discovered, and governed.
- `retrieval` (19) — Search, ranking, and the public retrieval service.
- `mcp-tools` (18) — MCP tool surface and CLI command design.
  - `cli` (2) — The command-line surface - command design, flags, and output.
- `session-fuse` (13) — Branch-session fuse and merge-branch integration machinery.
- `mermaid` (13) — Decision-diagram sidecars and diagram authoring.
- `windows-encoding` (7) — UTF-8 policy, cp1252 hazards, and encoding hygiene.
- `process-management` (7) — Package process discovery, shutdown, and upgrade workflows.
  - `upgrade-workflow` (1) — Upgrading an installed package and the safe-shutdown path around it.
- `hooks` (5) — Session-start, prompt, and stop hooks.
- `session-layout` (4) — Session file layouts, migrations, and multi-user structure.
  - `migration` (2) — Moving an existing session tree onto a new layout.
  - `multi-user-sessions` (1) — Per-user session structure and the switch away from the flat layout.

**Answers that are not slugs:**

- `TRACE-WIDE` — the Trace app as a whole, not any one part: frame, panes, settings, theme,
  typography, tabs, find bar. Stays on `memory-trace` itself.
- `seed` — Memory Seed work that merely carries the tag (validation, parsing, entry-ids).
- `NONE` — not about the system: roadmap, changelog, release process, git housekeeping.

### ACTIVITY — *what kind of work*

- `ui-design` (100) — Interface layout, visual hierarchy, interaction design, and rendered U
- `proposal-lifecycle` (81) — Roadmap, proposals, goals, and docs-lifecycle movement.
  - `goal` (6) — Goal directives and the staged execution runs that discharge them.
  - `proposal` (6) — Drafting and revising a proposal document.
  - `roadmap` (4) — Roadmap authoring, refinement, and staging.
- `documentation` (65) — README, audits, and public-facing docs accuracy.
  - `document-ingestion` (1) — Bringing external documents and transcripts into the corpus as notes.
  - `functionality-audit` (3) — Auditing shipped behaviour against what the docs claim, and closing th
  - `readme` (1) — The README front door and its accuracy.
- `git-workflow` (64) — Branching, merging, integration topology, and push/publish mechanics.
  - `branch-history` (3) — Branch topology, provenance, and history guardrails.
  - `git-publishing` (1) — Push and publish mechanics against the remote.
  - `merge` (5) — Merging a branch into main and the integration step itself.
- `agent-collaboration` (50) — Subagents, worktrees, task packets, and multi-agent hazards.
- `bugfix` (35) — Defect repairs, corrections, and cleanup passes.
  - `cleanup` (1) — Tidying passes that remove residue rather than fix a reported defect.
  - `memory-repair` (1) — Repairing the memory tree itself - malformed entries, misplaced files,
  - `process-correction` (2) — Correcting a followed process rather than a defect in code.
- `release` (17) — Version cuts, changelog folds, packaging, and publish gates.
  - `changelog` (1) — Changelog folds, Unreleased hygiene, and release notes.
  - `release-packaging` (2) — Packaging and distribution artifacts for a cut.
  - `release-preflight` (1) — Pre-cut checks and gates before a version is published.
- `tooling-evaluation` (10) — External tool/library assessment and licensing checks.
  - `design-evaluation` (1) — Weighing an internal design before committing to an implementation.
  - `licensing` (1) — Licence checks on external tools and libraries before adoption.
- `performance` (4) — Profiling, caching, and speed work across core and Trace.
- `security` (1) — Supply-chain and repo hardening - OpenSSF posture, CI security gates, 
- `testing` **PROPOSED** (~8) — building/maintaining the apparatus that proves code works

**Depth rule** (the one that took worker agreement from 54% to 82%): use the PARENT unless filing
the entry under a SIBLING of that child would be plainly wrong. Two plausible siblings means parent.

---

### 1. 2026-07-11 15:26 - Trace UI pass merged to main (Trail-first, search-as-function)

`mse_d5rq9wkx3n7t1vjb`

> ### Decision - D: The claude-feature-trace-ui-pass branch (30 commits: the whole gitgraph Trail product, commit packaging, evidence-based main inference, plus today's tab restructure - Timeline retired, Trail primary/default, Graph secondary, search as a function over both) is me

*files touched:* merge commit `54e1cf7` (34 files); session fuse imported 27 branch entries across

- **activity split** — worker 1 said `git-workflow`, worker 2 said `merge`

```
area     -> session-logging
activity -> merge
```

### 2. 2026-07-11 16:24 - Phase 0: deterministic synthetic corpora generator

`mse_n8xv3qtw6k2m5rcj`

> ### Decision - D: First Phase 0 deliverable (next-generation roadmap): a deterministic synthetic-corpus generator at memory-trace/tests/fixtures/generate_synthetic.py. Same (count, seed) -> byte-identical .memory-seed/sessions tree (month-grouped, real schema); shape exercises th

*files touched:* `memory-trace/tests/fixtures/generate_synthetic.py`,

- **area split** — worker 1 said `trace-harness`, worker 2 said `NONE`

```
area     -> trace-harness
activity -> testing
```

### 3. 2026-07-12 00:38 - Bundle Memory Trace as optional extra

`mse_etm5m5682sseasgm`

> - Implemented the Memory Trace packaging pivot on an isolated Codex worktree branch.

*files touched:* `pyproject.toml`, `memory-trace/memory_trace/lense.py`, `memory-trace/memory_trace/__init__.py`, `memory_seed/cli.py`, `memory_seed/retrieval.py`.

- **both workers disagree with the file-derived label** `seed`

```
area     -> package
activity -> release-packaging   (`package` now exists; this is distribution, not a Trace part)
```

### 4. 2026-07-12 12:15 - Fuse Codex branches and align Trace packaging docs

`mse_kq3ba0cy9nkpqkm0`

> - Integrated the Codex branch work that should land on `main`, reconciled the useful Trace release strategy documentation from the stale cleanup branch, and left branch deletion for a later pass because the environment blocked the required Git ref write.

*files touched:* `docs/2_Todo/agent-worktree-namespace-guard-plan.md`, `docs/2_Todo/0_NEXT_STEPS.md`,

- **activity split** — worker 1 said `git-workflow`, worker 2 said `merge`

```
area     -> session-logging   (JNL: merges belong to the session machinery)
activity -> merge
```

### 5. 2026-07-12 19:44 - Lifecycle-edge hardening complete: link audit + end-of-session sweep

`mse_8wq2vnr5tkxm3jhc`

> ### Decision - D: Completed Phases 3-4 of the lifecycle-edge hardening (`docs/3_Spec/lifecycle-edge-linking-sidecars.md`). Phase 3: `memory-seed link audit` finds entry pairs sharing `F:` files or topics with no recorded edge - WITHOUT an all-pairs semantic scan (user's efficienc

*files touched:* `memory_seed/retrieval.py` (audit_link_gaps + session_date scope), `memory_seed/cli.py`

- **activity split** — worker 1 said `functionality-audit`, worker 2 said `documentation`

```
area     -> lifecycle-edges
activity -> feature-build   (JNL: new slug)
```

### 6. 2026-07-14 17:03 - Rename internal Memory Trace module lense.py -> service.py + LenseCache/LenseService -> TraceCache/TraceService (public lense alias preserved)

`mse_y3bbadxamz0gntfy`

> ### Decision - D: Renamed the misleading internal Memory Trace module `memory_trace/lense.py` → `memory_trace/service.py` and its classes `LenseCache`/`LenseService` → `TraceCache`/`TraceService`, and fixed all references. Surgical token-replace across the active tree (16 code fi

*files touched:* memory-trace/memory_trace/{service.py←lense.py, __init__.py, cli.py, models.py};

- **activity split** — worker 1 said `cleanup`, worker 2 said `bugfix`

```
area     -> TRACE-WIDE
activity -> cleanup
```

### 7. 2026-07-16 08:51 - Integrate B0a Memory Trace workspace shell

`mse_7twxefmtphr30604`

> - Promoted the completed B0a Memory Trace workspace-shell contract from `codex/feature/b0a-workspace-contract` into local `main` and retired the merged workstream branch.

*files touched:* Local merge commit `eae91d6ec339a69f8d9ad4e7616e518443e6508f`; fused `mse_eaxj1wwfse1weh18`; removed the merged local feature branch.

- **activity split** — worker 1 said `git-workflow`, worker 2 said `merge`

```
area     -> session-logging   (JNL: merges belong to the session machinery)
activity -> merge
```

### 8. 2026-07-16 20:37 - Route exact entry-ID search directly to its entry

`mse_5x149cwk9z49x9fs`

> - Separated exact entry-ID navigation from Memory Trace's relevance-ranked text search after a pasted ID selected a newer semantically related entry instead of the requested record.

*files touched:* Updated `memory-trace/memory_trace/static/app.js` and `memory-trace/tests/test_service.py`.

- **area split** — worker 1 said `TRACE-WIDE`, worker 2 said `trace-api`
- **activity split** — worker 1 said `bugfix`, worker 2 said `ui-design`

```
area     -> topbar   (search is a topbar affordance, not an app-wide change)
activity -> bugfix
```

### 9. 2026-07-17 17:35 - Ship the B0b Inspector reader with search-match highlighting

`mse_wv9pzg6ayy0wa61j`

> ### Decision - D: Advance B0b by replacing the Inspector's placeholder (metadata list + one-line excerpt) with a real reader in a new `EntryReader.tsx`: a markdown-rendered entry body (frontmatter code block, h3-h6 headings, bullets, inline code/bold), search-match subsection hig

*files touched:* `memory-trace/client/src/EntryReader.tsx` (new), `memory-trace/client/src/App.tsx`,

- **activity split** — worker 1 said `release`, worker 2 said `ui-design`

```
area     -> inspector
activity -> feature-build   (the reader did not exist before - a capability, not a restyle)
```

### 10. 2026-07-18 10:30 - Ship the B0b Trail view: git-graph timeline over the v1 trail contract

`mse_74fb71s2cdrwqrqp`

> ### Decision - D: Port the vanilla Trail to `/next` as a new `Trail` presentation mode. The layout math lives in a pure, framework-free `trailModel.ts` (a faithful port of `app.js:709-1008`): newest-first sort + day-separator rows, client-side windowing, branch spans, commit-time

*files touched:* `memory-trace/client/src/trailModel.ts` (new), `TrailWorkspace.tsx` (new), `App.tsx`, `api.ts`,

- **activity split** — worker 1 said `release`, worker 2 said `ui-design`

```
area     -> trail
activity -> feature-build   (the Trail view is new here)
```

### 11. 2026-07-18 21:15 - Design feedback round 2: toggle placement, title width, edge semantics, trail tuning panel

`mse_sxyp8xf0v84d07w6`

> ### Decision - D: Four fixes from JNL's annotated screenshot: (1) inspector title `max-width: 250px` -> `none` so it fills a widened pane; (2) the nav-collapse toggle moved from the right topbar cluster to the far left (beside the pane it controls); (3) edge semantics recoloured 

*files touched:* `memory-trace/client/src/styles.css`, `App.tsx`, `TrailWorkspace.tsx`, rebuilt static/react.

- **area split** — worker 1 said `TRACE-WIDE`, worker 2 said `trail`

```
area     -> TRACE-WIDE
activity -> ui-design
```

### 12. 2026-07-18 22:17 - Trail complete: brackets and two-stage selection, continuity lanes, diagram badges

`mse_f8ywqzzwke72rdv0`

> ### Decision - D: The three remaining Trail slices in one workstream. **4b** - the full two-rule model: same-branch `related` edges now render as row brackets (chain-primary = entries the selection cites, pastel chain-secondary = inbound + bounded second-order, ported from the va

*files touched:* `memory-trace/memory_trace/models.py`, `memory-trace/tests/contract/{openapi.v1.json,types.ts}`,

- **both workers disagree with the file-derived label** `trace-api`

```
area     -> trail
activity -> feature-build   (brackets, continuity lanes and badges are new capabilities)
```

### 13. 2026-07-19 00:31 - Fixed-rhythm worktree train loader with hold-until-loaded

`mse_c7t7a609yvr1bzgy`

> ### Decision - D: JNL's idea, implemented as specified: the vanilla "train of thought" worktree loader (track, stations "Leaving the platform / Reading branch memory / Arriving at <label>", sliding train, pulsing halo, serif caption) is ported to `/next` as a workspace overlay wi

*files touched:* `memory-trace/client/src/App.tsx`, `styles.css`, rebuilt static/react,

- **area split** — worker 1 said `trace-cache`, worker 2 said `TRACE-WIDE`

```
area     -> TRACE-WIDE
activity -> feature-build   (a loading mechanism that did not exist; JNL: wide impact zone)
```

### 14. 2026-07-19 11:33 - Research hand-drawn Trail path geometry

`mse_ndh71vxkzt82ax6r`

> - Researched the React Trail's hand-drawn line effect and compared procedural spline geometry, SVG turbulence, Rough.js, D3 curves, and variable-width freehand strokes.

- **area split** — worker 1 said `trail`, worker 2 said `NONE`
- **activity split** — worker 1 said `activity-none`, worker 2 said `ui-design`

```
area     -> trail
activity -> design-evaluation
```

### 15. 2026-07-19 12:02 - Hand-drawn Trail geometry and dark-mode control contrast

`mse_6bmkhqwaax1wh0z3`

> ### Decisions

*files touched:* `memory-trace/client/src/trailPath.ts` (new), `TrailWorkspace.tsx`.

- **both workers disagree with the file-derived label** `TRACE-WIDE`

```
area     -> trail
activity -> ui-design
```

### 16. 2026-07-19 14:48 - Tabbed settings menu, collapsible entry metadata, promoted branch and evolves

`mse_cz735tsd1z96yc46`

> ### Decisions

*files touched:* `memory-trace/client/src/SettingsMenu.tsx` (new), `App.tsx`, `TrailWorkspace.tsx`, `styles.css`.

- **area split** — worker 1 said `trail`, worker 2 said `TRACE-WIDE`

```
area     -> settings
activity -> feature-build   (SettingsMenu.tsx is new - `settings` is now its own pane)
```

### 17. 2026-07-19 21:24 - Verify persistent full-text navigation in the live Trace preview

`mse_3rm3qwn3sentg8xp`

> - Completed live-browser verification of the persistent full-text navigation on the feature worktree preview.

- **area split** — worker 1 said `trace-harness`, worker 2 said `NONE`
- **activity split** — worker 1 said `activity-none`, worker 2 said `ui-design`

```
area     -> topbar   (full-text navigation lives in the find bar)
activity -> testing
```

### 18. 2026-07-19 23:27 - One find bar for both search modes, with the match anchored in the reader

`mse_emv963patckeftx8`

> ### Decisions

*files touched:* `memory-trace/client/src/App.tsx`, `memory-trace/client/src/inspectorScroll.ts`,

- **both workers disagree with the file-derived label** `inspector`

```
area     -> topbar   (the find bar IS the topbar; the reader anchor is secondary)
activity -> ui-design
```

### 19. 2026-07-20 10:06 - Remove locked Codex preview remnant

`mse_59de3twd1d369wy1`

> - Removed the final locked Codex worktree remnant after the user approved stopping its stale local preview server.

*files touched:* Removed `.codex/worktrees/full-text-search-navigation` and `.git/worktrees/full-text-search-navigation`.

- **activity split** — worker 1 said `cleanup`, worker 2 said `bugfix`

```
area     -> NONE
activity -> cleanup
```

### 20. 2026-07-20 20:18 - Phase 0: Storybook + a11y-gated test harness for memory-trace client

`mse_b7jq04zhmc059v4n`

> ### Decision - D: Started the harder half of Phase 0 - the B0b Trail parity gate's three open B2 items (Storybook, Playwright, accessibility acceptance). Closed the first: added a Storybook + a11y-gated test harness to `memory-trace/client`. - R: `storybook@10` + `@storybook/reac

*files touched:* `memory-trace/client/.storybook/` (new), `memory-trace/client/src/SettingsMenu.stories.tsx` (new),

- **activity split** — worker 1 said `proposal-lifecycle`, worker 2 said `ui-design`

```
area     -> trace-harness
activity -> testing
```

### 21. 2026-07-21 19:25 - Edge precedence per pair, in-place inspector links, stable decision indent

`mse_cdndmm2p0dmbkbq9`

> ### Decisions

*files touched:* `memory-trace/client/src/graphEdges.ts` (new: `EDGE_PRIORITY`, `pairKey`, `outrankedEdgeIds`),

- **area split** — worker 1 said `graph`, worker 2 said `trail`
- **activity split** — worker 1 said `ui-design`, worker 2 said `bugfix`

```
area     -> graph
activity -> ui-design
```

### 22. 2026-07-26 01:49 - Run the Storybook interaction tests in CI

`mse_kwm61z11k5336fq4`

> - Put the Storybook interaction tests into CI, closing the gap that let a red test survive on main.

*files touched:* `memory-trace/client/package.json`, `.github/workflows/verify.yml`.

- **activity split** — worker 1 said `proposal-lifecycle`, worker 2 said `git-workflow`

```
area     -> trace-harness
activity -> testing
```
