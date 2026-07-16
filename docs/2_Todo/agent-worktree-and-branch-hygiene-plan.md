---
title: Agent worktree and branch hygiene
status: active
priority: P3
next_action: Implement a dry-run classifier and Git-native bounded removal retry before changing lifecycle guidance.
sources:
  - ../7_Superseded/worktree-gc-proposal.md
  - ../7_Superseded/agent-namespaced-branch-worktree-lifecycle-proposal.md
---

# Agent Worktree and Branch Hygiene

Status: **ACTIVE, P3**. This plan combines the cleanup executor and the policy that consumes it.

## Decisions

- Worktrees are agent-owned session environments under `.<agent>/worktrees/<session>`.
- Branches are task workstreams named `<agent>/<kind>/<topic>` for new work.
- Existing branch names are grandfathered; no bulk rename is required.
- Cleanup starts with a dry-run classification and never assumes merge status implies a clean worktree.

## Phase 1 - safe executor

- Classify each worktree as active, dirty, unmerged, removable, locked, or unknown.
- Default to dry-run and show the evidence for every classification.
- Remove only clean, merged, registered worktrees through Git-native operations.
- On Windows/OneDrive locks, use bounded retry with clear process guidance.
- If Git-native removal still fails, stop with a manual next step. Do not fall back to raw recursive deletion.
- Keep branch deletion separate and approval-gated.

## Phase 2 - lifecycle guidance

- Reconcile `agent_collaboration.md`, End Of Turn, and Task Packet examples around worktree=session and
  branch=task.
- Create one branch per coherent workstream, keep follow-on fixes on that branch, and integrate with visible
  `--no-ff` history when configured.
- After integration, classify worktree and branch independently; retain either when uncommitted or unmerged
  work exists.

## Acceptance criteria

- Dry-run classifications are deterministic and fixture-tested.
- Dirty, unmerged, foreign-namespace, root, and locked worktrees cannot be removed automatically.
- OneDrive lock exhaustion leaves registered state and user data intact with explicit recovery guidance.
- New examples consistently use `<agent>/<kind>/<topic>`.
