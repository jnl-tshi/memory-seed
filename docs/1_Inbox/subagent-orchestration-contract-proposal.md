---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - orchestration
  - git-workflow
  - agent-collaboration
---

# Orchestration contract for worktree-isolated subagent fan-out

Status: **PROPOSED** (2026-07-13). Inbox — spun out of the two-branch orchestration run this session.
Priority: P2 — control-plane portability; codifies a protocol + adds environment self-checks.
Source: This session's orchestration (retrieval-discipline + freshness-ranking, two worktree-isolated
subagents, the user's agent as orchestrator validating before each merge).

## Motivation

The orchestration worked, but every safeguard was re-derived ad hoc and **three real failure modes bit
mid-run**. The lessons currently live only in one agent's personal memory
(`project_stale_worktree_subagents`, `feedback_fanout_subagent_tiers`) — invisible to other agents and
not shipped in the seed. This is the same portability gap the *retrieve-the-why* proposal just closed:
graduate the lessons into the vendor-neutral control plane so **any** orchestrating agent inherits them
by construction, not by luck.

## Lessons learned (evidence-grounded, from this session)

1. **Stale base commit.** Both isolated subagent worktrees spawned at a *stale* commit (`ec9c445`), not
   current `main` — work would have been built on old code. Required a manual `git reset --hard main` +
   a recency-marker check before the workers could safely start.
2. **Shared-checkout contamination.** One worker `cd`'d out of its worktree into the shared primary
   checkout, risking cross-branch writes; the orchestrator had to independently verify the primary
   stayed clean/on `main`.
3. **Branch-name collision.** The orchestrator cut an empty branch that would have collided with the
   branch the worker was about to create — caught only by chance.
4. **Wrong-worktree validation.** The suite was once run against stale content (427 tests) and nearly
   misattributed as the branch's result (correct was 434). A green/failed count is **meaningless
   without the commit hash it was measured at.**
5. **Append-only session discipline.** `session merge-branch` correctly **blocks** a branch that
   *modified* an existing session entry (a reformat of a prior entry could not be fused). Subagents
   must **append** entries, never edit existing ones, or the fuse refuses.
6. **Independent verification before an irreversible step pays for itself.** The advisor caught that a
   contract-level default flip had been validated on only *one* of two lineages — before the flip, not
   after. One cheap adversarial pass prevented a global default change on a single clean example.

## Proposal

**P1 — Portable skill `.memory-seed/skills/subagent_orchestration.md` (+ seed twin).** Codify the
protocol as a checklist future orchestrators follow by default:

- *Before spawning:* pre-allocate every branch name (the orchestrator never creates a branch a worker
  will); hand each worker the **absolute** repo path, the **expected base commit hash**, and a recency
  marker (a file that must exist at that base).
- *Worker preamble:* assert `git rev-parse HEAD` is at / descends from the expected base and that the
  recency marker exists; assert it is in its **own worktree path**, not the shared primary checkout;
  `git reset --hard <base>` if stale; **append** session entries only, never edit an existing one.
- *Orchestrator gate:* run the full suite **inside the worker's worktree**, printing the branch + HEAD
  hash it validated; merge **one branch at a time**; **re-run the suite on the integration branch after
  each merge** (integration effects, especially the second merge); require an **independent adversarial
  check before any irreversible step** (default flip, release, destructive op).

**P2 — Make the self-checks one command: `memory-seed worktree verify --expect-base <hash>
[--marker <path>]`.** Asserts the current worktree is *isolated* (not the primary checkout), at/descended
from the expected base, prints HEAD + branch, and exits non-zero on a stale or shared-checkout
environment. A worker runs it first; the orchestrator runs it before validating and before each merge.
Extends `doctor`; turns lessons 1–4 into a mechanical gate.

**P3 — Graduate the personal memories.** Add a one-line Working-Principles pointer in `agent-rules.md`
for orchestration work and retire `project_stale_worktree_subagents` / `feedback_fanout_subagent_tiers`
into the seeded skill (the portability fix), mirroring the retrieve-the-why graduation.

## Non-goals

- Not a replacement for the Agent/Workflow tooling — it wraps them with discipline, it doesn't reissue
  them.
- Does not force orchestration: solo/small work stays solo (matches `feedback_fanout_subagent_tiers` —
  reserve fan-out for genuinely parallel, independent work).
- No change to `session merge-branch`'s append-only guard; the discipline adapts to the guard, not the
  reverse.

## Acceptance criteria

- A fresh orchestrating agent, following only the skill, spawns workers that verify base + isolation
  before working, append-only, and are validated at a **named commit** before a one-at-a-time merge with
  post-merge revalidation.
- `worktree verify` exits non-zero on (a) a stale base, (b) the shared primary checkout, or (c) a missing
  marker; exits zero and prints HEAD/branch otherwise.
- The two personal memories are represented in the seeded skill (portability), with the personal notes
  reduced to pointers.

## Dependencies / relationship

- `session merge-branch` append-only fuse (the substrate the discipline respects).
- Agent-tool worktree isolation (`isolation: "worktree"`).
- `memory-seed doctor` (P2 extends it).
- Companion in spirit to `proactive-history-retrieval-discipline-proposal.md` (both graduate a personal
  learning into the portable control plane).
