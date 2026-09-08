---
title: What `branch:` records, and the half of it code cannot fix
status: resolved
priority: P3
next_action: None. Decided (JNL, 2026-07-26): A now, D as the standing convention; both are documented. The decidable case was already fixed in code.
blocked_by: []
---

# What `branch:` Records, and the Half of It Code Cannot Fix

Status: **RESOLVED — code half fixed, policy half decided and adopted (JNL, 2026-07-26).** Raised as item 5 of
[`0_NEXT_STEPS.md`](../2_Todo/0_NEXT_STEPS.md) ("cross-session `branch:` contamination"), investigated
2026-07-26 against a synthetic-repository matrix rather than by reasoning. The investigation split
the item cleanly in two: a decidable case, fixed in code, and an undecidable one that needed a
judgement call from JNL — now made and adopted. **This repository's current layout is not affected by
either.**

## What was claimed, and what is actually true

The item read:

> `session append` stamps `branch:` from the shared git HEAD, so a second agent appending while
> another has a feature branch checked out records the wrong branch. Affects every git-derived
> field, not just this one.

Two corrections, both empirical.

**"Affects every git-derived field" is overstated.** `branch:` is the *only* git-derived field on an
entry. `session_append_entry` makes exactly one git call (the `_auto_captured_branch` helper in
`memory_seed/core.py`, previously a bare `_git_capture` inline). Everything else on the entry is
caller-supplied or locally computed: `user_initials`, `agent_type`, `project_path`,
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

## The decided policy: two agents sharing one checkout

Rows 1 and 4 are the same working tree with the same HEAD. An agent's *session* branch is never
passed to the CLI, so there is no state from which to recover it — git is being asked a question it
does not have the answer to. **No code change can fix this**, only a policy about what to do when
the answer is unknowable. Pinned as
`test_shared_checkout_concurrency_is_still_invisible` so the omission rule above is not mistaken for
a complete answer.

The options that were weighed:

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

**DECIDED (JNL, 2026-07-26): A now, D as the standing convention.** On the grounds that the value is
only knowable by the caller, and that B and C both spend enforcement budget on a signal that cannot
distinguish the bad case from the common good one. B and C are closed, not merely unchosen: B would
fire on every legitimate primary-checkout append, and C requires session-identity state that does not
exist and would have to be invented and maintained.

### Where the decision is written down

Both halves are guidance, since neither has a code surface to change. Two files, chosen so an agent
and a human each hit it on the path they actually walk, cross-referencing rather than duplicating:

- **A — the workaround.** `.memory-seed/skills/session_logging.md`, appended to the prose that already
  defines the `branch` field: the shared-working-tree caveat, both `--branch` and `--no-branch`, and
  why omitting the field beats stamping a durable label you cannot vouch for. This is the file
  `agent-rules.md` routes to for the End Of Turn append, so every agent writing an entry loads it, and
  it is the canonical definition of the field the guidance qualifies. Cross-referenced from
  `README.md`'s `session append` command reference — where a human looks, and where the two flags were
  previously undocumented altogether.
- **D — the standing convention.** `.memory-seed/skills/agent_collaboration.md`, as a bullet under
  "Branch And Worktree Defaults": a harness (or an orchestrator appending for a worker) passes
  `--branch` unconditionally, taken from the Task Packet's `working_branch`. That section is loaded
  for any branch/worktree work, sits beside the worktree-identity rules that share this failure mode,
  and the packet field it draws from is defined a few sections above.

Deliberately **not** in `.memory-seed/agent-rules.md`: this is procedural detail, which by the repo's
own skill-architecture rule belongs in a lazily loaded skill rather than the non-deferrable startup
contract — true regardless of how much budget the file has. (The budget itself was raised 260 → 280 on
2026-07-29 to give two other thin, high-consequence startup steps more weight; that headroom is spent,
not available for procedural detail like this.) Deliberately **not** in
`.memory-seed/policy.md` either, which is scoped to behavioral constraints only and has no seed twin,
so a downstream user would never receive it.

Both skills have twins under `memory_seed/seed/.memory-seed/skills/`, updated byte-identically, so
downstream `memory-seed init` / `update` users get the same guidance. The guidance is written
generically for that reason — it does not assume this repository's tracked-`.memory-seed` layout.

## Why this is P3 and not urgent

The item was escalated on the belief that parallel worktree agents were actively recording wrong
branches. They are not: this repository tracks `.memory-seed`, so worktree isolation holds, and the
matrix above shows every layout in current use recording either a correct value or none. The
decidable defect is fixed, and the undecidable half was a design question about a configuration this
repository does not currently run — now settled as documented policy rather than code, which is why
resolving it cost two paragraphs of guidance and no behavior change.
