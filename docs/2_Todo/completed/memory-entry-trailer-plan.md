---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - git-workflow
  - graph
---

# Memory-Entry Trailer Stamping Plan

> **Status:** IMPLEMENTED 2026-07-11 - approved by the user the same day (imported-only, no cap,
> plus the optional skill-guidance follow-up); shipped in `session_merge_branch()` with tests.
> One implementation note: "imported only" is realised as the fuse's `planned_entries` set
> directly - entries already on the base commit never enter that set, and `already_present` is
> not subtracted because it only records that git's own auto-merge had already placed an entry
> in the working tree before the fuse ran (subtracting it would skip cleanly-auto-merged
> entries).
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

## Open questions - resolved 2026-07-11

- Trailers list only newly imported entries (user-approved). Modified/repaired entries are
  rewrites of the same entry and are not stamped; entries already on the base commit are never
  claimed.
- No cap (user-approved): trailer lines are cheap, and a partial list would make
  `find_trailer_commits` silently miss entries.
- The optional follow-up shipped in the same pass: `session_logging.md` nudges ordinary
  session-append commits to carry the trailer manually; `agent_collaboration.md` documents the
  automatic stamp at merge time (live + seed twins, byte-identical).
