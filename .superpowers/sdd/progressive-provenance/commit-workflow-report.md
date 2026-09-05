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

## Independent-review correction — pending checkpoint

This section supersedes the earlier local-configuration description of
activation. The correction is deliberately append-only so the first
implementation claim remains auditable.

### Corrected activation boundary

- Activation never reads or writes `git config`: not local, global, system, or
  worktree configuration. It does not alter Git identity, credentials,
  aliases, or general Git behavior.
- The only activation state is a full canonical Task Packet in the exact
  worktree Git directory, selected by a digest of the active branch name. A
  nearby append-only JSONL receipt records every actual replacement.
- The managed hook ignores editable configuration values. Before stamping
  `Memory-Implements`, it verifies the packet fingerprint, packet identity,
  writing intent, exact branch and canonical worktree, an ancestor base SHA,
  selected materialized decision evidence, and that every staged path remains
  in the packet allowlist. Invalid or missing artifacts fail closed for
  implementation attribution while normal commits remain usable.
- Replacing scope, runtime binding, or `implements` requires a nonblank reason
  of at least twelve characters. The replacement receipt retains that reason;
  repeating an identical activation leaves both artifact and receipt history
  intact rather than clearing prior evidence.

### Cadence corrections

- `.memory-seed/`, `.AGENTS/`, agent-worktree/control directories, and routing
  files are excluded from cadence **file** and **churn** dimensions. Session
  text still contributes to authored-entry and decision dimensions.
- Packet compilation measures cadence from its explicit measured `base_sha`.
  After activation, `commit_cadence()` uses that same verified packet base
  before considering `main`/`master`; a stacked-base regression proves the
  base layer is not counted as task work.
- The hook's ten-record limit now counts every newly authored record before
  trailer deduplication. Duplicate authored records cannot evade the cap;
  emitted trailers remain deduplicated without truncating attribution.

### Adapter handoff / allowlist conflict

`SessionMergeBranchResult.integration_preview_contract()` is now the stable
core payload that includes `cadence` and `cadence_warnings`. The current Task
Packet explicitly forbids the downstream adapter files, so this worker did not
edit them. The surfaces track must update these exact files:

- `memory_seed/cli.py`: render the core integration-preview contract's cadence
  and warnings for the session-merge dry-run output.
- `memory_seed/mcp_server.py`: serialize those same fields in the session-merge
  MCP result.

Those required paths are outside `dispatch.execution.allowed_files` and named
in `forbidden_files`; a follow-up packet must own the adapter and its tests.

### Review-fix validation

- `tests/test_hooks.py`: config-only activation fails closed; a
  fingerprint-verified artifact stamps only packet refs; duplicate authored
  records trip the cap.
- `tests/test_task_packet.py`: no local or isolated-global config content is
  modified; receipt reason preservation, idempotence, and stacked-base cadence
  are covered.
- `tests/test_commit_cadence.py` and `tests/test_session_merge.py`: control
  paths do not count as product files/churn and the core contract carries
  cadence to adapters.

The exact required validation after these corrections was:

- `python -X utf8 -m pytest -q tests/test_hooks.py tests/test_task_packet.py tests/test_situate.py tests/test_session_merge.py tests/test_commit_cadence.py`
  — **49 passed, 84 subtests passed in 92.66s**.
- `git diff --check` — passed before the correction checkpoint.

The containing checkpoint's SHA is supplied by the mandatory final worker
handoff because a committed report cannot self-contain its own Git object ID.
The implementation commits before that self-reference boundary are
`254b86b4684aeefd62a6a6dab3098d7fc2963568` and the correction checkpoint
recorded in that handoff.

### Supplemental-context debit for this correction

No broad orientation, memory, policy, Constitution, or external source was
loaded. The only supplemental project reads were the packet-allowed core,
activation, hook, and five named test files needed to reproduce the review
findings. The additional boundary (no global Git settings) came directly from
the assigned user clarification, not from a project-memory hop.
