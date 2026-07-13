# Goal run: Memory Trace surface (Claude)

Status: ACTIVE goal prompt (authored 2026-07-13, user-approved scope)
Owner: Claude, in the `.claude/worktrees/memory-trace-trail` worktree (branch
`worktree-memory-trace-trail`). Paired with the concurrent Codex core run
(`goal-run-core-parity-codex.md`) - different packages, minimal collision surface.

## Mission

Complete these three items, in order, one merge per item:

### 1. Port the Trail merge/lifecycle surface to `/api/v1`

The vanilla implementation (commit-accurate merges, `graph()` `merges`/`branches` keys, chunk
`merged_by`) shipped legacy-only under the "vanilla only, polish first" ruling and has since
survived a full release cycle - the polish condition is met. Extend the versioned contract:

- Add `merges`/`branches` to the v1 graph/trail response models and `merged_by` to the v1 chunk
  model (`memory-trace/memory_trace/models.py` + the `/api/v1/*` routes in `lense.py`).
- Regenerate the committed contract fixtures (`openapi.v1.json`, generated TypeScript types) and
  update `test_v1_api_contract.py` / `test_openapi_contract_fixture.py` expectations.
- Retire the now-obsolete test assertion that v1 strips these keys (it pinned the old scope
  boundary); update `docs/3_Spec/lifecycle-edge-linking-sidecars.md` and
  `docs/3_Spec/graph-edge-contract.md` where they state the boundary. Sidecar-sourced lifecycle
  edges already flow through the shared service, so v1 graph edges inherit them automatically -
  verify with a test rather than assuming.

### 2. Topics Phase 4, Trace half: indexed-topic rendering

Read `docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md` Phase 4 for the intended scope
(Codex owns the MCP-topic-tools half - do not build those). Render stored `topics:` as
first-class UI: topic chips on entries/reader sourced from the indexed field (with the
tag/context derivation kept as the fallback for old entries), vocabulary-aware filtering, and
whatever Phase 4 specifies for facets. Vanilla `app.js` + legacy API first, consistent with how
every Trace feature has landed; add to `/api/v1` only if trivial while you are in the models.

### 3. Decision-diagram sidecars in Trace views - DESIGN WITH THE USER FIRST

This was deferred 2026-07-11 explicitly "with scope to be designed with the user" (session entry
`mse_j4wn8rqk2t6x0vhs`). Do not pick a design unilaterally. Prepare a short options brief
(candidate shapes already recorded: diagram indicator on Trail rows / Graph nodes, inline Trail
expansion, dedicated affordance - add mockup sketches or DOM prototypes if cheap), then STOP and
ask the user to choose. Implement only the chosen scope.

**Stretch (only if all three land):** `docs/2_Todo/fontjoy-typography-pairing.md` - it "rides the
next Trace UI pass", and this is that pass.

## Working rules

- Work only in your worktree; never edit the primary checkout (the temp-copy era is over - verify
  UI via the `memory-trace-worktree` launch configuration, port 8766, `--static-root`).
- Per item: tests first-class (both suites green: `PYTHONPATH="." python -m pytest tests -q` and
  `PYTHONPATH=".;memory-trace" python -m pytest memory-trace/tests -q`), live verification in the
  browser, session entry, then merge.
- Session entries via `memory-seed session append` (repo-local invocation:
  `PYTHONPATH="." python -c "from memory_seed.cli import main; import sys; sys.argv=['memory-seed','session','append',...]; sys.exit(main())"`).
  Never hand-roll ids. Commit trailers are stamped by the installed `prepare-commit-msg` hook.
- Merge each completed item to local `main` with `session merge-branch`, then fast-forward your
  worktree from `main` before starting the next item. Codex is merging to the same `main`
  concurrently: pull/ff before every merge attempt; if a real conflict appears, the agent merging
  second owns the resolution. CHANGELOG `## Unreleased` bullets: append yours and resolve
  conflicts by keeping both sides.
- Run `memory-seed esr` at each item boundary; run the Lifecycle Link Sweep and propose any
  sidecar edges for user approval per the end_of_turn skill.
- NO pushes to origin, NO release cut, NO `/api/v1` breaking changes (additive only) - all three
  are user decisions.

## Escalation contract

- STOP and ask the user (AskUserQuestion or plain question) for: the item-3 design choice
  (mandatory); any `/api/v1` change that is not purely additive; anything that would rewrite
  committed session history; scope surprises that would double an item's size; and any destructive
  operation outside your worktree.
- Solve autonomously and RECORD (in the item's session entry, failed approaches under `A:`):
  test/fixture churn, small refactors the item forces, doc-drift you create and fix, tooling
  friction, and bug fixes in code you touch anyway.
