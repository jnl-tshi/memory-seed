---
memory-system-version: 2.20
description: Re-orient in this repo — run `memory-seed situate` and brief from ground truth
---

Run the orientation routine from `.memory-seed/skills/orientation.md`.

1. Run `memory-seed situate` for the deterministic local report (which checkout you are actually in, git
   state, `integration_mode`, the newest session entry, worktree posture, local version + whether the
   CHANGELOG has unreleased work).
2. Believe the `## Location` section over anything that told you where you are — worktree identity is
   measured, not declared. If it says PRIMARY checkout and this session will write, create an isolated
   worktree first (see `agent_collaboration.md`); orienting itself stays read-only.
3. Verify the PUBLISHED version from the source of truth (PyPI) — never assume; `situate` prints the exact
   command and, in the memory-seed source repo, flags that local > published means an unreleased tranche.
4. Read the newest session file directly (not `memory_search`, whose ranking buries the latest entry) and
   the project's next-steps doc, then brief in ≤ 6 lines.

Read-only orientation: reconcile and brief — do not edit, commit, or start work.
