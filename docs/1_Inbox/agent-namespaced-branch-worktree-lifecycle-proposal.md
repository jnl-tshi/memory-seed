---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - agent-collaboration
  - worktrees
  - git-workflow
---

# Agent-namespaced branch + worktree naming and lifecycle (well-defined, symmetric, with post-merge hygiene)

Status: **PROPOSED** (2026-07-13). Inbox.
Priority: P2 — multi-agent hygiene; consolidates and completes scattered, partly-shipped pieces.
Source: User 2026-07-13 — "worktree and branch naming (both should state agent type), post-merge hygiene
(clean up old branches/merges no longer needed unless uncommitted), and lifecycle management for both
needs to be well defined."

## Problem — the three concerns are defined unevenly and inconsistently

- **Worktree naming: defined + shipped.** `.codex/worktrees/<task>`, `.claude/worktrees/<task>`, etc.,
  enforced by `memory-seed worktree guard` (`agent-worktree-namespace-guard-plan.md`,
  `agent_collaboration.md` line 130).
- **Branch naming: under-defined and inconsistent.** The only guidance is a fallback
  `<owner>/<kind>/<topic>` (`agent_collaboration.md` line 16/128) where `<owner>` is **not required to be
  the agent**. In practice this repo mixes agent-prefixed hyphen branches (`claude-feature-topics-p1`,
  `codex-fix-session-fuse`) with **bare, agent-less** ones (`feature-freshness-ranking`,
  `feature-integration-mode` — created this very session). Branch names do **not** reliably state the
  agent, and don't mirror the worktree namespace.
- **Post-merge hygiene: worktrees only, branches unsystematized.** Worktree cleanup has the end-of-turn
  "Stale Worktree Sweep" (`end_of_turn.md`) and the proposed `worktree gc` (`worktree-gc-proposal.md`).
  For **branches** there is only "don't delete before handoff" (`agent_collaboration.md` line 152) — no
  rule for retiring merged branches.
- **Lifecycle: scattered across gates**, never stated as one branch+worktree state model.

## Proposal

### 1. Symmetric agent-namespaced naming — both state the agent

| Artifact | Form | Example |
|---|---|---|
| Worktree (shipped) | `.<agent>/worktrees/<task>` | `.claude/worktrees/freshness-ranking` |
| Branch (this proposal) | `<agent>/<kind>/<topic>` | `claude/feature/freshness-ranking` |

- `<agent>` ∈ the configured namespaces (`claude`, `codex`, `gemini`, `cursor`, or a project-configured
  agent). **Required** — no bare `feature-*` branches.
- `<kind>` ∈ `feature|fix|refactor|test|docs` (the existing kind set).
- **Recommended slash form** for branch↔worktree symmetry (a branch `claude/feature/x` pairs visibly with
  worktree `.claude/worktrees/x`) and native grouping in Git tooling. *(Open decision: slash
  `<agent>/<kind>/<topic>` vs. the repo's current hyphen `<agent>-<kind>-<topic>`. Recommend slash;
  hyphen is the lower-churn alternative. Existing branches are grandfathered either way — they're
  ephemeral and merge commits preserve topology.)*
- **Consistency rule:** a branch's `<agent>` segment must match the worktree namespace it is authored in;
  `worktree guard` already knows the namespace and can flag a mismatch.

### 2. One lifecycle state model (branch + worktree move in lockstep)

| State | Branch | Worktree | Entry gate (owner) |
|---|---|---|---|
| `planned` | name allocated in packet | namespace + path allocated | Scope Gate (orchestrator) |
| `active` | checked out on base | created in `.<agent>/worktrees/` | Worker Identity + Worktree Gate (worker verifies `base_sha`, guard passes) |
| `validated` | commits present | tree may be dirty→committed | Pre-Review Validation Gate (suite green at a **named HEAD**) |
| `merged` | integrated into mainline | tree clean | Integration Gate (`session merge-branch` / `--no-ff`, one at a time) |
| `retired` | eligible for deletion | eligible for removal | **Post-merge hygiene (below)** |

The states and their first four gates already exist in `agent_collaboration.md`; this proposal adds the
explicit **`retired`** end-state and the rule for reaching it, and names the whole progression so it's
one contract instead of scattered lines.

### 3. Post-merge hygiene — retire the pair together, uncommitted work blocks it

A branch+worktree pair becomes **`retired`-eligible** when **both**: the branch is merged into the
mainline **and** the worktree tree is clean. Then:

- **Remove the worktree** via `memory-seed worktree gc` (see `worktree-gc-proposal.md` — with the
  Windows/OneDrive lock retry), and
- **Delete the merged local branch** (topology is preserved in the `--no-ff` merge commit).

**Cleanup is blocked** (with a stated reason, never silent) when the worktree has **uncommitted
changes** (the sweep's first litmus — park/commit or get explicit discard approval first), or the branch
is **unmerged**, the worktree is **locked**, or it belongs to **another agent's active namespace**.

- **Timing:** at end-of-turn (the Stale Worktree Sweep) and on demand (`worktree gc`).
- **Branch-label preference:** honor "keep labels visible until handoff" via a config toggle rather than
  always-delete.
- **Config (`.memory-seed/project.yaml`):** the existing `worktrees.namespaces` map, plus a branch
  `prefix_policy` (require agent segment: `warn|block`) and `post_merge_cleanup: auto|prompt|manual`
  (recommend `prompt`).

### 4. Enforcement

- `worktree guard` extends to warn when a branch name lacks or mismatches its `<agent>` segment (it
  already classifies the worktree namespace).
- `doctor` / `branch status` surface: retired-eligible pairs (merged + clean), and misnamed
  (agent-less/mismatched) branches.

## Non-goals

- No auto-deletion of unmerged or dirty branches/worktrees; uncommitted work always blocks and is
  surfaced.
- No history rewriting; merge commits keep topology after branch deletion.
- Existing branch names are grandfathered — the naming rule applies to new work.
- Does not force cleanup when the user wants branch labels retained.

## Acceptance criteria

- New branches and worktrees both carry the `<agent>` segment; `worktree guard` warns on a bare or
  mismatched branch.
- `doctor`/`branch status` list retired-eligible pairs and misnamed branches.
- Cleanup removes a merged+clean pair (worktree via `worktree gc`, then the branch) and refuses — with a
  reason — on dirty/unmerged/locked/foreign, honoring `post_merge_cleanup`.
- `agent_collaboration.md` + seed twin carry the naming table, the five-state lifecycle, and the hygiene
  rule; parity tests pass.

## Relationship to existing coverage (checked — consolidates, does not duplicate)

- `docs/2_Todo/completed/agent-worktree-namespace-guard-plan.md` — **worktree** naming/guard (kept; this
  adds the symmetric **branch** naming it left unspecified).
- `.memory-seed/skills/agent_collaboration.md` — the loose branch fallback (line 16/128) and gates 1–9;
  this **amends** the naming and **adds** the `retired` state + hygiene rule (implementation edits the
  live skill + seed twin, pending approval, since it is a locked control-plane file).
- `docs/1_Inbox/worktree-gc-proposal.md` — the **executor** this policy drives for worktree removal;
  this proposal adds the **branch-deletion** half and the shared retire-eligibility rule.
- `.memory-seed/skills/end_of_turn.md` "Stale Worktree Sweep" — the manual discipline this formalizes
  into a defined lifecycle state.
- `docs/2_Todo/completed/worktree-dependency-strategy-plan.md` — isolation/dependency tiers (unchanged).
