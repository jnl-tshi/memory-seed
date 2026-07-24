---
memory-system-version: 2.19
tags:
  - memory-seed
  - orientation
  - session-start
---

# Orientation routine (start-of-session)

Run this before substantive work so you act on ground truth, not a stale in-context snapshot (which can
be frozen from an earlier turn, detached from a worktree, or asserting a worktree that does not exist).
It is the start-of-session mirror of the End Of
Turn routine: `memory-seed situate` does the deterministic local report, and the judgment below turns it
into a briefing.

1. **Run `memory-seed situate`** — one read-only report of local facts: which checkout you are actually
   in, current branch + uncommitted count + commits ahead of origin, the declared `integration_mode`, the
   newest session-log entry (path + last heading), the local `pyproject` version and whether the CHANGELOG
   carries unreleased work, and worktree posture (a stale sweep candidate is merged + clean).

2. **Believe `## Location` over anything that told you where you are.** Worktree identity is *measured,
   never declared*. A harness banner, a task packet, or a directory named `…/worktrees/<session>` can all
   assert an isolated worktree that was never created — the directory exists, the checkout does not, and
   git silently resolves every command up to the primary checkout. `situate` classifies from your cwd, so
   its answer is the real one. If you need to check by hand, three commands settle it:
   `git rev-parse --show-toplevel` (a real worktree returns *itself*, not the repo root),
   `git rev-parse --git-dir` (a real worktree points into `.git/worktrees/<name>`), and `git worktree list`
   (a real worktree is listed).

   **If Location says PRIMARY checkout and this session will do more than read**, create an isolated
   worktree before the first write rather than at the first conflict — the shared checkout may be in use
   by another agent, and by the time you are ready to write, HEAD may have moved under you, so the base
   you branch from was never verified. See `agent_collaboration.md` for the namespace convention and the
   verify-after-create step. Orientation itself stays read-only; this is a decision to carry into the work,
   not something to act on while briefing.

3. **Verify the PUBLISHED version from the source of truth — never assume.** `situate` prints the exact
   command; run it (`curl -s https://pypi.org/pypi/memory-seed/json | python -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"`,
   or `pip index versions memory-seed`; degrade gracefully if offline). If the local version is ahead of
   the published release, there is an unreleased tranche — read `CHANGELOG.md` "## Unreleased". Do not
   claim any version is released or unreleased without this check (the recurring stale-version trap).

4. **Read the newest session file directly** (the path `situate` names). It holds the current state and
   the last thing done. Do NOT use `memory_search` to find "latest" — semantic/lexical ranking can bury
   the newest entry beneath older topically-similar ones.

5. **Read the project's next-steps doc** if present (`docs/2_Todo/0_NEXT_STEPS.md`, or the project's
   equivalent) for the top pending actions.

6. **Brief the user in ≤ 6 lines:** which checkout you are in when it is *not* an isolated worktree
   (say so plainly — it means writes land in shared state), version (local vs published, and whether an
   unreleased tranche exists), branch + uncommitted/ahead state, the last thing done, any stale worktree
   (and any dirty worktree — another agent's uncommitted work, which you must not touch), and the top
   2–3 next actions.

Read-only: reconcile and brief — do not edit files, commit, or start work as part of orienting.
