---
implemented_by: executed 2026-07-13 (goal-run session entries + `codex/session-2026-07-13` merges on `main`)
shipped: 2026-07-13
---

# Goal run: Memory Seed core parity + guardrails (Codex)

Status: EXECUTED — spent one-shot brief; all four items shipped and merged; moved to `5_Completed` 2026-07-14
Owner: Codex, in its OWN worktree under `.codex/worktrees/` (create one; never write in the
primary checkout or another agent's namespace). Paired with the concurrent Claude Trace-surface
run (`goal-run-trace-surface-claude.md`) - different packages, minimal collision surface: you own
`memory_seed/` core, Claude owns `memory-trace/`.

## Orientation (read before coding)

- `.memory-seed/skills/session_logging.md`, `end_of_turn.md`, `agent_collaboration.md` - the
  workflow contract, heavily updated in 2.18.
- `docs/3_Spec/lifecycle-edge-linking-sidecars.md` - your item 1's spec, including the stated MCP
  scope boundary you are removing.
- `docs/5_Completed/memory-trace-topic-neighbourhoods-plan.md` Phase 4 - your item 2 (the MCP half
  only; Claude owns the Trace-rendering half - do not touch `memory-trace/`).
- `docs/2_Todo/residual-fuse-non-utf8-silent-skip.md` - your item 3.
- `docs/2_Todo/agent-worktree-namespace-guard-plan.md` - your item 4.

## Mission

Complete these four items, in order, one merge per item:

### 1. MCP-graph sidecar-edge parity

The lifecycle-edge link sidecars (`sessions/links/YYYY-MM/YYYY-MM-DD.md`) currently reach the
Trail but NOT the MCP graph tools - a stated scope boundary in the spec. Close it: MCP
`memory_link_show`, `memory_get_chunk`, and `memory_search` freshness fields
(`superseded_by`/`evolved_by`) must see union(entry YAML, sidecar) edges, matching the Trail.
The reader (`entry_link_sidecars` in `memory_seed/retrieval.py`) and the union semantics
(the lense's `_augment_with_link_sidecars`) already exist - lift the augmentation into a
core-safe location the MCP paths share, without breaking the import direction (`retrieval`
imports `semantic_cache`, never the reverse). Update the spec's scope-boundary section and
`graph-edge-contract.md` when done. Tests must cover: sidecar-only edge visible via each MCP
tool; YAML-only behavior unchanged when no sidecars exist.

### 2. Topics Phase 4, MCP half: topic-management tools

Per the topic-neighbourhoods plan Phase 4: read-only-first MCP tools for the controlled
vocabulary (list/inspect topics, validate usage - mirror `memory-seed topics list`/`check`).
Any WRITE surface (adding topics to `topics.yaml` via MCP) needs a STOP-and-ask first: writes to
a deploy-once project-curated file are a policy question the user decides.

### 3. Fuse non-UTF-8 silent-skip fix (small)

`session fuse` currently skips a non-UTF-8 session file silently; the promoted fix is to BLOCK
with a named file instead. Implement per the proposal doc, with a regression test.

### 4. Agent worktree namespace guard (P1a plan)

Implement `agent-worktree-namespace-guard-plan.md`'s P1: CLI/MCP readout + pre-write guard so a
writing agent can verify it is inside its own agent-owned worktree namespace before editing, with
root-checkout writes requiring explicit override. You are the ideal author - you are running
inside exactly this workflow. Follow the plan; where the plan leaves options open, choose the
smallest honest guard and record the choice. If the plan demands anything that would block the
CURRENT run's own workflow, STOP and ask.

**While in the area (item 4):** the old deferred "git-commit-entry-linking P2 reminder-only
post-commit hook" is likely obsoleted by the shipped `prepare-commit-msg` auto-stamping hook -
verify, and if so record its retirement in the plan doc + session entry rather than building it.

## Working rules

- Session entries via `memory-seed session append` (repo-local invocation:
  `PYTHONPATH="." python -c "from memory_seed.cli import main; import sys; sys.argv=['memory-seed','session','append','--title','...','--user-initials','JNL','--agent-type','codex',...]; sys.exit(main())"`).
  Never hand-roll entry ids. Commit trailers are auto-stamped by the installed
  `prepare-commit-msg` hook (git common dir - covers your worktree).
- Per item: full core suite green (`PYTHONPATH="." python -m pytest tests -q`; also run
  `PYTHONPATH=".;memory-trace" python -m pytest memory-trace/tests -q` when you touch anything
  memory-trace imports, e.g. `retrieval.py`), session entry, then merge.
- Merge each completed item to local `main` with `memory-seed session merge-branch`, then
  fast-forward your worktree from `main` before the next item. Claude is merging to the same
  `main` concurrently: pull/ff before every merge attempt; if a real conflict appears, the agent
  merging second owns the resolution. CHANGELOG `## Unreleased` bullets: append yours and resolve
  conflicts by keeping both sides. Live+seed skill twins must be synced in the same commit
  whenever you edit a seeded skill (`memory-seed esr` reports drift).
- Run `memory-seed esr` at each item boundary; propose Lifecycle Link Sweep sidecar edges for
  user approval per `end_of_turn.md`.
- NO pushes to origin, NO release cut - user decisions.

## Escalation contract

- STOP and ask the user for: any MCP WRITE surface (item 2's write half); any change to the
  append-only guarantees or validated session history; namespace-guard behavior that would block
  the current multi-agent run itself; scope surprises that would double an item's size; any
  destructive operation outside your worktree.
- Solve autonomously and RECORD (in the item's session entry, failed approaches under `A:`):
  test/fixture churn, small refactors an item forces, doc drift you create and fix, and bug fixes
  in code you touch anyway.
