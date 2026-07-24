---
title: Agent worktree and branch hygiene
status: complete
priority: P3
sources:
  - ../7_Replaced/worktree-gc-proposal.md
  - ../7_Replaced/agent-namespaced-branch-worktree-lifecycle-proposal.md
---

# Agent Worktree and Branch Hygiene

> **Status:** COMPLETE 2026-07-20 - both phases shipped. Phase 1 (classifier + `--apply` remover)
> 2026-07-17; Phase 2 (lifecycle-guidance reconciliation) 2026-07-20, closing this plan's only
> remaining obligation.

This plan combined the cleanup executor and the policy that consumes it.

## Decisions

- Worktrees are agent-owned session environments under `.<agent>/worktrees/<session>`.
- Branches are task workstreams named `<agent>/<kind>/<topic>` for new work.
- Existing branch names are grandfathered; no bulk rename is required.
- Cleanup starts with a dry-run classification and never assumes merge status implies a clean worktree.

## Phase 1 - safe executor

> **Classifier SHIPPED 2026-07-17** as `memory-seed worktree classify [--agent] [--integration-branch]
> [--json]` (`memory_seed/worktree_gc.py`). It is read-only and removes nothing. States: `root`,
> `active`, `dirty`, `unmerged`, `locked`, `foreign`, `unknown`, `removable` — every non-`removable`
> verdict carries its evidence. Anything unanswerable (unreadable `git status`, detached HEAD, unknown
> merge status) fails closed to `unknown`, which refuses removal. `foreign` was added beyond the listed
> states: a worktree in another agent's namespace is clean-and-merged yet still not ours to remove.
>
> **The remover (`--apply`) SHIPPED 2026-07-17** under live user consent (destructive: a STOP category).
> `memory-seed worktree classify --apply` **reclassifies at apply time** — a stale `removable` verdict is
> never trusted for a delete — and removes only what the live pass still calls removable, via
> `git worktree remove`, with bounded retry on a lock and **no raw-filesystem fallback**. Branch deletion
> stays a separate, untouched concern. Exit code is 1 if any removal was refused.
>
> Exercised end-to-end against a throwaway clean/merged worktree in a temp repo (removed; branch left
> intact; git deregistered it). The bounded-retry-on-lock path is unit-tested via an injected remover,
> since a real OneDrive lock cannot be summoned on demand — it retries `max_attempts` times then refuses,
> leaving the worktree entirely intact.
>
> *Field note validating the premise:* `git worktree prune` on this repo fails with `Permission denied`
> on four stale `.git/worktrees/*` admin dirs, and `git worktree add` intermittently fails with "Could
> not reset index file" — the OneDrive lock is real and routine, which is exactly why the retry path
> exists and why the remover never deletes by hand.

- Classify each worktree as active, dirty, unmerged, removable, locked, or unknown. ✅
- Default to dry-run and show the evidence for every classification. ✅ (removal requires the explicit `--apply`)
- Remove only clean, merged, registered worktrees through Git-native operations. ✅
- On Windows/OneDrive locks, use bounded retry with clear process guidance. ✅
- If Git-native removal still fails, stop with a manual next step. Do not fall back to raw recursive deletion. ✅
- Keep branch deletion separate and approval-gated. ✅ (apply never touches branches)

## Phase 2 - lifecycle guidance

> **COMPLETE 2026-07-20.** `agent_collaboration.md` carried three stale examples predating the
> worktree=session/branch=task decision recorded in `.memory-seed/index.md:77` (2026-07-13/16): two
> `<owner>/<kind>/<topic>` branch-naming fallbacks (the agent segment is required, not an optional
> "owner") and one `.codex/worktrees/<task>` / `.claude/worktrees/<task>` / etc. worktree-namespace
> example (worktrees are named for the session, not the task). All three fixed and synced to the seed
> twin; `test_agent_collaboration_skill_is_registered_and_agent_rules_stay_lean`'s asserted substring
> updated to match. End Of Turn's Stale Worktree Sweep and the Task Packet YAML template used only
> generic placeholders already — no stale examples found there.

- Reconcile `agent_collaboration.md`, End Of Turn, and Task Packet examples around worktree=session and
  branch=task. ✅
- Create one branch per coherent workstream, keep follow-on fixes on that branch, and integrate with visible
  `--no-ff` history when configured. ✅ (ongoing practice, already followed)
- After integration, classify worktree and branch independently; retain either when uncommitted or unmerged
  work exists. ✅ (ongoing practice, already followed)

## Acceptance criteria

- Dry-run classifications are deterministic and fixture-tested.
- Dirty, unmerged, foreign-namespace, root, and locked worktrees cannot be removed automatically.
- OneDrive lock exhaustion leaves registered state and user data intact with explicit recovery guidance.
- New examples consistently use `<agent>/<kind>/<topic>`.
