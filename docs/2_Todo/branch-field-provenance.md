---
title: What `branch:` records, and the half of it code cannot fix
status: active
priority: P3
next_action: JNL decides between options A-D for the shared-checkout case (the decidable case is already fixed). No action needed for this repository's current layout.
blocked_by: []
---

# What `branch:` Records, and the Half of It Code Cannot Fix

Status: **ACTIVE — one decision open.** Raised as item 5 of
[`0_NEXT_STEPS.md`](0_NEXT_STEPS.md) ("cross-session `branch:` contamination"), investigated
2026-07-26 against a synthetic-repository matrix rather than by reasoning. The investigation split
the item cleanly in two: a decidable case, now fixed, and an undecidable one that needs a judgement
call from JNL. **This repository's current layout is not affected by either.**

## What was claimed, and what is actually true

The item read:

> `session append` stamps `branch:` from the shared git HEAD, so a second agent appending while
> another has a feature branch checked out records the wrong branch. Affects every git-derived
> field, not just this one.

Two corrections, both empirical.

**"Affects every git-derived field" is overstated.** `branch:` is the *only* git-derived field on an
entry. `session_append_entry` makes exactly one git call (the `_auto_captured_branch` helper in
`memory_seed/core.py`, previously a bare `_git_capture` inline). Everything else on the entry is
caller-supplied or locally computed: `user_initials`, `agent_type`, `agent_name`, `project_path`,
`subproject_path`, `topics` and the lifecycle refs all arrive as arguments; `read_local_user` reads
`.memory-seed/local-user`, a file, not `git config`; and `generate_session_entry_id` hashes
timestamp/title/initials/agent/paths. The diagram, topic and link sidecars carry no branch at all
(`_DiagramSidecarRecord` and `_LinkSidecarRecord` have no such field). The other git readers in the
codebase — `branch_status`, `session fuse`, `merge-branch`, `prepare-pr` — either take `--branch`
explicitly or are read-only advisories that write no durable history. **The item shrinks to one
field.**

**Worktree isolation is a consequence of `.memory-seed` being committed, not of worktrees.** This is
the finding that reframes the item. `resolve_runtime` walks up from `cwd` looking for
`.memory-seed`, and `branch:` is read from the HEAD of whatever it lands on. Because this repository
*tracks* `.memory-seed`, every real worktree checks out its own copy, the walk-up stops there, and
git reports that worktree's own HEAD. Parallel worktree-isolated agents — the way this repo runs
today — each record their own branch correctly. Had `.memory-seed` been gitignored, the identical
worktree layout would silently stamp the primary's branch instead.

## The empirical matrix

Measured by building synthetic repositories and reading `branch:` out of a `dry_run` render. Pinned
as regression tests in `tests/test_session_append.py::BranchProvenanceTests`.

| Layout | `workspace_root` resolves to | `branch:` recorded | Correct? |
|---|---|---|---|
| Primary checkout | primary | primary's HEAD | Yes, but shared |
| Real worktree, `.memory-seed` **tracked** | the worktree | the worktree's own branch | **Yes — this repo** |
| Real worktree, `.memory-seed` **untracked** | primary | primary's HEAD | **No — silently wrong** |
| Plain nested dir (no `.git`, no `.memory-seed`) | primary | primary's HEAD | Yes, but shared |
| Detached HEAD / not a repository | — | omitted | Yes |

"Shared" means the value is right for the checkout but is whatever branch happens to be checked out
at write time — so two agents in that position record each other's branches.

## What was fixed (no decision required)

Row 3 produces a **wrong durable value with no concurrency at all**, so the task's own principle
decides it: a wrong `branch:` is append-only history, and recording a wrong value is worse than
recording none. The fix extends the *existing* omission rule rather than adding machinery — the
docstring already said the field is "omitted when detached or not a repository", and this adds one
clause: omitted also when the memory dir belongs to a different working tree than the caller.

Detection is exact and needs no heuristic: compare `rev-parse --show-toplevel` for the caller's
directory against the same for `workspace_root`. They agree in every layout that behaves correctly,
and disagree precisely when the entry will be written into another tree's `.memory-seed`. Omitting
is the honest answer specifically because *neither* HEAD is right there — the session is on the
worktree's branch, but the entry file lands in the primary's memory dir and will be committed on the
primary's branch.

**Blast radius.** The same rule now also omits `branch:` for a caller inside a **submodule** whose
superproject owns the memory dir. That is judged correct — the submodule's branch is not the
superproject's, and the entry is committed on the superproject's. The "`.memory-seed` above a
repository root" layout already omitted before this change and is unaffected. This repository tracks
`.memory-seed`, so **the new omission never fires here**; it protects downstream users, which is the
argument for shipping it rather than only proposing it. `memory-seed` ships on PyPI and a user who
gitignores `.memory-seed` gets silently wrong branches in every worktree.

## The open decision: two agents sharing one checkout

Rows 1 and 4 are the same working tree with the same HEAD. An agent's *session* branch is never
passed to the CLI, so there is no state from which to recover it — git is being asked a question it
does not have the answer to. **No code change can fix this**, only a policy about what to do when
the answer is unknowable. Pinned as
`test_shared_checkout_concurrency_is_still_invisible` so the omission rule above is not mistaken for
a complete answer.

Options, for JNL:

- **A — Do nothing; document the workaround.** `session append` already accepts `--branch` and
  `--no-branch` (they predate this investigation). Guidance: when several sessions share a working
  tree, pass `--branch` explicitly. Zero cost, zero enforcement; relies on the agent remembering.
- **B — Warn when the repository has more than one worktree.** Cheap to implement, but it would fire
  on *every* legitimate append from the primary checkout in this repository, which is now routine.
  High false-positive rate against a real signal; likely trained-to-ignore within a week.
- **C — Require `--branch` or `--no-branch` when a lock/marker shows a concurrent session.** Real
  enforcement, but needs session-identity state that does not exist today and would have to be
  invented and maintained.
- **D — Have the agent harness pass `--branch` unconditionally.** Moves the answer to the one party
  that actually knows it, at the cost of a convention every harness must honour. Composes well with
  A.

**Recommendation: A now, D as the standing convention**, on the grounds that the value is only
knowable by the caller and B/C both spend enforcement budget on a signal that cannot distinguish the
bad case from the common good one. Recorded as a recommendation, not a decision — B and C remain
genuinely available and this is JNL's call.

## Why this is P3 and not urgent

The item was escalated on the belief that parallel worktree agents were actively recording wrong
branches. They are not: this repository tracks `.memory-seed`, so worktree isolation holds, and the
matrix above shows every layout in current use recording either a correct value or none. The
decidable defect is fixed. What remains is a design question about a configuration this repository
does not currently run.
