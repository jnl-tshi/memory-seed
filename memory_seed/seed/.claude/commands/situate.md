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
3. Apply `situate`'s measured latest-session `context_route`: read the whole file when `direct`; when
   `summarize`, use `orientation.md`'s read-only economy-worker contract (≤800 tokens, whole-file coverage,
   source-linked conclusions). Do not use `memory_search` for latest state.
4. Verify the published version only for release/version questions; read next steps only for planning.
5. Brief in ≤ 6 lines from the measured facts and direct/derived session context.

Read-only orientation: reconcile and brief — do not edit, commit, or start work.
