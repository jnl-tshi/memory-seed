---
memory-system-version: 2.17
tags:
  - memory-seed
  - proposal
  - git-workflow
  - graph
---

# Memory-Entry Trailer Stamping Plan

> **Status:** PROPOSED - drafted 2026-07-11 during the Trace UI pass; awaiting user review.
> **Source:** User direction 2026-07-11 ("draft the proposal doc") while designing Trace's
> commit-identification feature; see session entries of 2026-07-11.
> **Scope:** Core write-path: have `session merge-branch` (and optionally the end-of-session
> commit guidance) stamp `Memory-Entry: <entry_id>` trailers on the commits it creates.
> **Non-goals:** No rewriting of historical commits. No change to Trace's diff-derived commit
> map (it remains the retroactive source; trailers make future data authoritative). No new
> required authoring steps for agents.

## Why

Core already has both halves of commit<->entry linking (`commits:` entry field,
`Memory-Entry:` trailer reading via `find_trailer_commits` / `commit_reference_ids`), but
nothing stamps the data routinely, so the channel is empty in practice. Memory Trace now ships
a diff-derived commit map (each entry -> the oldest commit whose diff added it), which is exact
for history but inferential by nature. Stamping trailers at integration time makes the forward
data authoritative and machine-verifiable, and it powers the CLI `link commits` surface too.

## Decision (proposed)

1. `session_merge_branch()` composes its merge commit message with one
   `Memory-Entry: <entry_id>` trailer per entry its fuse imported (the `planned_entries` set it
   already computes). Zero new user steps.
2. Optional follow-up: the end-of-turn/session skill guidance nudges ordinary commits that
   include session-entry appends to carry the trailer for the appended entry ids.
3. Read surfaces unchanged: `commit_reference_ids` already unions the trailer channel;
   Trace's diff-derived map stays primary (works for all history) with trailers available as
   a cross-check.

## Acceptance criteria

- A merge produced by `session merge-branch` carries one `Memory-Entry:` trailer per fused
  entry, verifiable with `git log --format=%B -1`.
- `find_trailer_commits` resolves each fused entry to that merge commit.
- Existing merge-message content (git's prepared message) is preserved above the trailers.
- Tests cover: trailers present after a merge-branch run; entries with no fuse import produce
  no trailers; malformed entry ids never stamped.
- Docs: agent_collaboration skill (live + seed, byte-identical) notes the automatic trailer.

## Open questions for review

- Should trailers also list entries merely *modified* (repaired) by the fuse, or only newly
  imported ones? (Proposed: imported only - repairs are rewrites of the same entry.)
- Cap for very large fuses? (Proposed: no cap; trailer lines are cheap.)
