# Progressive Provenance — Commit Workflow Report

## Status

Implemented and packet-activated on `codex/feature/provenance-commit-workflow`.

- Base SHA: `c1e96aa88dc2ad9009386a2109ba012905ab5889`
- Final head and commit list: recorded in the worker handoff after this report's
  containing checkpoint is created.
- Network, push, merge, Git hunk projection, temporal analytics, CLI/MCP/ESR,
  and Seed Pod lifecycle changes: not performed.

## Delivered contract

- `activate_task_packet()` validates the compiled writing packet against its
  measured branch/worktree and stores its exact `execution.implements` refs in
  branch-scoped local Git configuration. A changed allowed/forbidden/new-file
  scope or binding requires a reasoned explicit update.
- The managed `prepare-commit-msg` hook reads that activation without a history
  search and appends deduplicated `Memory-Implements:` trailers alongside its
  `Memory-Entry:` trailers.
- The hook counts only added `entry_id:` records in non-sidecar session files.
  Existing trailers, packet implementation refs, and sidecar references never
  affect the ten-entry ordinary-commit limit. A live-approved,
  durable `Memory-Bulk-Reason:` preserves every trailer for legitimate bulk
  work; nothing is truncated.
- `commit_cadence()` measures branch delta from the merge base and warns at
  moderate `3/5/8/300` and high `6/10/16/750`
  entries/decisions/files/churn thresholds. One high or two moderate signals
  recommend a tested checkpoint. The signal appears in worktree guard,
  situate, compiled Task Packet defaults, and dry-run integration results.

## Validation

- `python -X utf8 -m pytest -q tests/test_hooks.py tests/test_task_packet.py tests/test_situate.py tests/test_session_merge.py tests/test_commit_cadence.py`
  — 46 passed, 84 subtests passed in 82.98s.
- `git diff --check` — passed before commit.

## API handoff

Consumers with a compiled writing packet call:

```python
from memory_seed.task_packet import activate_task_packet

activation = activate_task_packet(packet, cwd=worktree)
```

On a scope/binding replacement, pass an explicit `binding_update_reason` of at
least twelve non-whitespace characters. The hook then consumes the activated
branch configuration automatically; no commit-history lookup is involved.

## Concerns

- Branch-local Git configuration is intentionally operational state, not an
  append-only project record. The resulting commit trailers are the durable,
  shared provenance evidence.
- The bulk-reason trailer records a live approval assertion durably; the hook
  cannot independently verify who granted it.

## Task Packet effectiveness reflection

The packet was effective: it supplied exact decision anchors, a clean bound
worktree/base, explicit non-goals, mandated tests, and a narrow write set. It
also made the activation boundary clear enough to keep implementation refs out
of history searches. The only supplemental source inspection was limited to
existing hook/fuse test patterns needed to preserve compatible behavior.

## Supplemental context debits

The Task Packet was the sole initial context. Afterward, the following
project/memory/governance reads were necessary and read-only:

1. Permitted implementation files (`memory_seed/core.py`, `task_packet.py`,
   `situate.py`, and both managed hook copies) — to extend their existing
   contracts rather than invent parallel ones.
2. Existing hook and session-fuse test files — to preserve established shim,
   trailer, and integration-preview behavior; they were not edited.
3. The active session tail — to append this worker checkpoint with the exact
   decision-level source links. No broad orientation, policy, or Constitution
   file was loaded outside the packet's materialized evidence.
4. Brief read-only checks of the excluded CLI/MCP adapter locations — only to
   confirm that packet activation could remain an internal API and avoid an
   out-of-scope adapter edit; no code or tests there were changed.
