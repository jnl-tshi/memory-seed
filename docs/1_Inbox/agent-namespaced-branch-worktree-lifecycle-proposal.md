---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - agent-collaboration
  - worktrees
  - git-workflow
---

# Agent-namespaced branch + worktree naming and lifecycle (worktree = session, branch = task)

Status: **PROPOSED** (2026-07-13). Inbox.
Priority: P2 — multi-agent hygiene; consolidates and completes scattered, partly-shipped pieces.
Source: User 2026-07-13 — "worktree and branch naming (both should state agent type), post-merge hygiene
(clean up old branches/merges no longer needed unless uncommitted), and lifecycle management for both
needs to be well defined"; refined — "the worktree should be scoped to a session not a task, branches
can own the tasks."

## Problem — the three concerns are defined unevenly, inconsistently, and at the wrong grain

- **Worktree naming: shipped, but mis-scoped in the doc.** The guard defines `.<agent>/worktrees/<task>`
  (`agent-worktree-namespace-guard-plan.md`, `agent_collaboration.md` line 130) — yet actual practice is
  **session-scoped** (`.codex/worktrees/session-2026-07-13`). The `<task>` leaf is the misnomer.
- **Branch naming: under-defined and inconsistent.** The only guidance is a fallback
  `<owner>/<kind>/<topic>` (`agent_collaboration.md` line 16/128) where `<owner>` is **not required to be
  the agent**. In practice this repo mixes agent-prefixed hyphen branches (`claude-feature-topics-p1`,
  `codex-fix-session-fuse`) with **bare, agent-less** ones (`feature-freshness-ranking`,
  `feature-integration-mode` — created this very session).
- **Post-merge hygiene: worktrees only, branches unsystematized.** Worktree cleanup has the end-of-turn
  "Stale Worktree Sweep" (`end_of_turn.md`) and the proposed `worktree gc` (`worktree-gc-proposal.md`);
  branch cleanup has only "don't delete before handoff" (`agent_collaboration.md` line 152).
- **Lifecycle: scattered across gates**, and wrongly implies branch and worktree share one grain.

## Proposal

### 1. Both artifacts state the agent — worktree owns the *session*, branch owns the *task*

| Artifact | Scope | Form | Example |
|---|---|---|---|
| Worktree | one per agent **session** | `.<agent>/worktrees/[<user>/]<session>` | solo `.codex/worktrees/session-2026-07-13`; multi-user `.codex/worktrees/jean/session-2026-07-13` |
| Branch | one per **task** | `<agent>/<kind>/<topic>` | `claude/feature/freshness-ranking` |

- A single **session worktree** hosts the agent's work for that session; the agent checks out one **task
  branch** at a time inside it, merges, then moves to the next task's branch. One durable worktree, many
  ephemeral task branches. (Matches actual practice — Codex already runs `session-2026-07-13`.)
- `<agent>` ∈ configured namespaces (`claude`, `codex`, `gemini`, `cursor`, or a project-configured
  agent). **Required on both** — no bare `feature-*` branches, no agent-less worktree dirs.
- `<session>` is a stable session id/date (e.g. `session-2026-07-13`); `<kind>` ∈
  `feature|fix|refactor|test|docs`.
- **User scoping (multi-user only).** When 2+ human participants are registered, the worktree gains a
  `<user>` segment: `.<agent>/worktrees/<user>/<session>` (e.g. `.codex/worktrees/jean/session-...`).
  This reuses the **same participant-count gate** that already flips session logs from flat to per-user
  (`session_target()`, `multi-user-session-memory-proposal.md`) — so a **solo repo stays flat**
  `.<agent>/worktrees/<session>` and nothing changes (per the `user_identity` note: solo → flat, layout
  switches only at 2+ participants). `<user>` is the registered user slug (e.g. `jean`), the same
  identity session entries carry in `user_initials`. Branches stay `<agent>/<kind>/<topic>` even
  multi-user — a task branch's author is already recorded in its session entry (`user_initials`,
  `branch:`), so the `<user>` segment lives where the filesystem actually needs to disambiguate two
  people's concurrent sessions: the worktree.
- **Parallel fan-out exception:** when an agent spawns parallel *writing* workers, each worker gets a
  short-lived **worker worktree** under the same namespace (e.g. `.claude/worktrees/session-<id>-worker-<n>`),
  removed as soon as its branch integrates — not held to session end.
- **Symmetry / consistency:** the agent is legible from either artifact (`.<agent>/…` and `<agent>/…`);
  a task branch's `<agent>` must match its session worktree's namespace (`worktree guard` enforces).
  *(Open decision unchanged: slash `<agent>/<kind>/<topic>` vs. the repo's hyphen `<agent>-<kind>-...`;
  recommend slash; existing branches grandfathered.)*

### 2. Two lifecycles, deliberately decoupled

Worktree is session-scoped, branch is task-scoped, so they do **not** move in lockstep — one session
worktree spans many task-branch lifecycles.

**Session worktree** (per agent session):

| State | Meaning |
|---|---|
| `opened` | worktree created at `.<agent>/worktrees/<session>` at session start |
| `active` | agent works task branches inside it, one at a time |
| `retired` | session ends, tree is clean, all its task branches merged → removed |

**Task branch** (per task, inside a session worktree):

| State | Gate (owner) |
|---|---|
| `planned` | name allocated in the task packet (Scope Gate) |
| `active` | checked out in the session worktree; `base_sha` verified (Worker Identity Gate) |
| `validated` | suite green at a **named HEAD** (Pre-Review Validation Gate) |
| `merged` | integrated into mainline one at a time (`session merge-branch` / `--no-ff`) |
| `retired` | merged branch deleted (post-merge hygiene) |

Many task branches pass `planned → retired` over one session worktree's life; the worktree retires only
when the session itself ends.

### 3. Post-merge hygiene — decoupled cleanup; uncommitted always blocks

- **Per task (prompt, right after merge):** once a task branch is `merged` and nothing needs its label,
  **delete the branch** (topology preserved in the `--no-ff` merge commit). The session worktree stays and
  moves to the next task.
- **Per session (end-of-turn / end-of-session):** at session end, the **session worktree** is
  `retired`-eligible when its tree is **clean** and all its task branches are merged → remove via
  `memory-seed worktree gc`. **Worker worktrees** are removed as soon as their branch integrates, never
  held to session end.
- **Blocked, with a stated reason, never silent** when the worktree has **uncommitted changes** (park /
  commit / explicit-discard first), a branch is **unmerged**, the worktree is **locked**, or it is
  **another agent's active session** namespace.
- **Config (`.memory-seed/project.yaml`):** `worktrees.namespaces` (exists) + branch `prefix_policy`
  (`warn|block`) + `post_merge_cleanup: auto|prompt|manual` (task-branch deletion) +
  `session_worktree_gc: on-session-end|manual`. The `<user>` worktree segment needs **no new knob** — it
  follows the existing `participants:` registration (present iff 2+ participants).

### 4. Enforcement

- `worktree guard` extends to warn when a task branch name lacks or mismatches its `<agent>` segment (it
  already classifies the session worktree's namespace).
- `doctor` / `branch status` surface: retired-eligible session worktrees (clean + all-merged), merged
  task branches awaiting deletion, and misnamed (agent-less / mismatched) branches.

## Non-goals

- No auto-deletion of unmerged or dirty branches/worktrees; uncommitted work always blocks and is
  surfaced.
- No history rewriting; merge commits keep topology after branch deletion.
- Existing branch/worktree names are grandfathered — the rule applies to new work.
- Does not force cleanup when the user wants labels retained.

## Acceptance criteria

- New session worktrees are `.<agent>/worktrees/[<user>/]<session>` (the `<user>` segment present iff
  2+ participants are registered, matching the session-log gate) and new task branches are
  `<agent>/<kind>/<topic>`; `worktree guard` warns on a bare/mismatched branch or an agent-less worktree.
- `doctor`/`branch status` list retired-eligible session worktrees, merged task branches, and misnamed
  branches.
- Cleanup deletes a merged task branch (per `post_merge_cleanup`) and removes a clean, fully-merged
  session worktree at session end (via `worktree gc`); refuses — with a reason — on
  dirty/unmerged/locked/foreign.
- `agent_collaboration.md` + seed twin carry the session-vs-task naming, the two lifecycles, and the
  hygiene rule; parity tests pass.

## Relationship to existing coverage (checked — consolidates, does not duplicate)

- `docs/2_Todo/completed/agent-worktree-namespace-guard-plan.md` — worktree namespace/guard (kept; this
  **re-scopes the leaf from `<task>` to `<session>`** to match practice, and adds the symmetric **branch**
  naming it left unspecified).
- `.memory-seed/skills/agent_collaboration.md` — the loose branch fallback (line 16/128) and gates 1–9;
  this **amends** the naming and **adds** the two decoupled lifecycles + hygiene rule (implementation
  edits the live skill + seed twin, pending approval — locked control-plane file).
- `docs/1_Inbox/worktree-gc-proposal.md` — the **executor** this policy drives for session-worktree and
  worker-worktree removal; this proposal adds the per-task **branch-deletion** half and the retire rules.
- `.memory-seed/skills/end_of_turn.md` "Stale Worktree Sweep" — the manual discipline this formalizes.
- `docs/2_Todo/completed/worktree-dependency-strategy-plan.md` — isolation/dependency tiers (unchanged).
- `docs/2_Todo/completed/multi-user-session-memory-proposal.md` + the `session_target()` participant-count
  gate — the multi-user mechanism the `<user>` worktree segment reuses (same 2+-participant trigger as
  per-user session files), so worktree and session-log user-scoping activate together.
