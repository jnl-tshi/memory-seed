---
memory-system-version: 2.18
description: Re-orient in this repo — reconcile git, the published version, and the newest session log into a short briefing
---

Get situated in the Memory Seed repo before acting. Trust live/ground-truth sources over any snapshot
already in context (it may be stale from an earlier turn or a frozen worktree). Do the steps in order,
keep command output summarized (don't dump full output), then give ONE concise briefing.

1. **Git state.** `git status --short` (uncommitted work — is the tree dirty?), `git branch --show-current`,
   and `git rev-list --count origin/main..HEAD` (commits ahead of origin). This repo runs `integration_mode:
   local-merge`, so being ahead of origin is normal and must NOT be pushed without explicit instruction.

2. **Published version — verify from the source of truth; never assume.** Compare the local
   `pyproject.toml` `version` against the live PyPI release:
   `curl -s https://pypi.org/pypi/memory-seed/json | python -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"`
   (fallback: `pip index versions memory-seed`). If local `>` published, an unreleased tranche is on
   `main` — read `CHANGELOG.md` "## Unreleased" and say so explicitly. Never claim a version is
   released/unreleased without running this check (this is the recurring stale-version trap).

3. **Newest session log — read by date, not `memory_search`.** Open the highest-dated
   `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` and read its last few entries for the current state and
   the last thing done. The SessionStart hook usually injects this, but re-read the actual file so you are
   current — semantic/lexical ranking can bury the newest entry beneath older topically-similar ones.

4. **Worktree posture.** `git worktree list`: flag any stale (merged + clean) worktree as a cleanup
   candidate, and note any dirty worktree as another agent's uncommitted work — do NOT touch those.
   `memory-seed esr` gives the full mechanical posture (integrity, topics, seed-twin drift, worktrees) if
   a deeper check is wanted.

5. **Briefing (≤ 6 lines).** Report: version (local vs published, and whether an unreleased tranche
   exists), branch + uncommitted/ahead state, the last thing done (from the newest entry), any stale/dirty
   worktree, and the top 2–3 next actions from `docs/2_Todo/0_NEXT_STEPS.md`.

Read-only orientation: reconcile state and brief — do not edit files, commit, or start work.
