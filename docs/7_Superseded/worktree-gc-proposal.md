---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - agent-collaboration
  - worktrees
  - git-workflow
superseded_by: "../5_Completed/agent-worktree-and-branch-hygiene-plan.md"
superseded_on: "2026-07-16"
---

# `memory-seed worktree gc` — mechanize the stale-worktree sweep (with Windows/OneDrive lock retry)

Status: **SUPERSEDED 2026-07-16** by
[`agent-worktree-and-branch-hygiene-plan.md`](../5_Completed/agent-worktree-and-branch-hygiene-plan.md)
(shipped complete 2026-07-20).
Priority: P3 — hygiene tooling; the discipline already exists, this mechanizes its one flaky step.
Source: This session's manual worktree cleanup (used+merged worktrees lingering; `git worktree remove`
failing on OneDrive locks).

> **Retraction note.** This replaces `subagent-orchestration-contract-proposal.md` (filed earlier this
> session), which duplicated already-shipped work — see "Relationship to existing coverage" below. Only
> the worktree-GC gap it named was genuinely new; that gap is this proposal.

## Problem — the sweep is a manual step, and its one mechanical action is flaky

Used-and-merged worktrees accumulate. This session left three merged-and-clean worktrees un-removed and
had to hand-clean them, and `git worktree remove` **failed on OneDrive file locks** ("Permission
denied") — succeeding only on a later `rm -rf` retry, then `git worktree prune`. Two concrete gaps:

1. Cleanup is a **manual checklist step** (`.memory-seed/skills/end_of_turn.md` "Stale Worktree Sweep",
   from `mse_xdzsgmsezqt3tjd0`) — recall-dependent, so it gets skipped.
2. The removal itself is **flaky on Windows/OneDrive** — a synced worktree holds locks that make a
   single `git worktree remove` fail, leaving a half-state (branch gone, folder stranded).

## Current behavior (grounded)

- The **discipline** exists: `end_of_turn.md` "Stale Worktree Sweep" — identify candidates by
  merged-branch status, **check for uncommitted changes first** (a merged branch's worktree can still
  carry working state), discard only with explicit per-worktree user approval.
- The **namespace guard** (`agent-worktree-namespace-guard-plan.md`, implemented 2026-07-13) explicitly
  lists *"do not move, rename, delete, or repair existing worktrees automatically"* as a non-goal — so
  actually removing worktrees is deliberately left unbuilt.
- No command executes the sweep; nothing handles the OneDrive/Windows lock retry.

## Proposal — `memory-seed worktree gc [--dry-run] [--force] [--json]`

- **Classify** every worktree: `removable` (branch merged into the mainline **and** working tree clean),
  or a reason to keep — `dirty` (uncommitted — the sweep's first litmus), `unmerged`, `locked`,
  `foreign-namespace-active` (defer to the guard), or `current`. `--dry-run` prints the classification
  and stops.
- **Remove** the `removable` ones with a **lock-aware retry**: the exact `git worktree remove` → brief
  wait → `rm -rf` → `git worktree prune` escalation this session needed, reporting any that stay locked
  with a suggested manual step (pause OneDrive / close the editor), rather than a bare "Permission
  denied".
- **Safety:** never touches `dirty`/`unmerged`/another agent's active worktree; a `locked` worktree
  needs `--force`; deletion of a merged branch is offered but separate (append-only history is intact in
  the merge commit).
- **Surfacing (optional):** `doctor` gains a one-line "N removable / M stale worktrees" summary —
  answers the open "sweep including orphan heuristics?" discuss point in
  `cheap-tooling-hardening-proposals.md` (P4).

## Non-goals

- Does not create, switch, or repair worktrees (stays complementary to the namespace guard).
- Does not remove dirty, unmerged, or another agent's active worktree.
- Does not spawn agents or coordinate them.

## Acceptance criteria

- `worktree gc --dry-run` classifies each worktree with a keep/remove reason matching the sweep litmus
  (uncommitted-first).
- `worktree gc` removes merged+clean worktrees, retries past a transient lock, and names any it could
  not remove with a next step — no silent half-state.
- Tests cover Windows path/space handling, the dirty/unmerged/locked hold-backs, and the lock-retry path.

## Relationship to existing coverage (checked — the orchestration protocol is already covered)

The broader "orchestration contract" I first drafted was **already shipped**; naming the docs, per the
duplication check:

- **Worker identity / commit-stamped validation / one-at-a-time integration** →
  `docs/5_Completed/agent-fanout-workflow-plan.md` (Worker Identity Gate, Integration Gate,
  `base_sha`/preflight task-packet fields) — live in `.memory-seed/skills/agent_collaboration.md`.
- **Worktree isolation + dependency tiers** → `docs/5_Completed/worktree-dependency-strategy-plan.md`.
- **Wrong-namespace / peer-agent write coordination** →
  `docs/5_Completed/agent-worktree-namespace-guard-plan.md` + `memory-seed worktree guard` /
  `memory_worktree_guard` (implemented 2026-07-13).
- **The end-of-turn cleanup discipline** → `.memory-seed/skills/end_of_turn.md` "Stale Worktree Sweep".

The **only** uncovered residue is executing that sweep as a command with lock-aware retry — this doc.
